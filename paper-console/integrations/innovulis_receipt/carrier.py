"""The paper is a dumb carrier. QR can be replaced without breaking verification.

The verifier never trusts human-readable ink, printer firmware, QR metadata or
an anchor shipped within the same QR; it checks pinned cryptographic bytes.
"""
from __future__ import annotations
from pathlib import Path
import html
import io
import subprocess
from .codec import encode_qr_text, FormatError


def make_svg(packet: dict, dest: str | Path):
    try:
        import qrcode
        from qrcode.image.svg import SvgPathImage
    except ImportError as err:
        raise ImportError("SVG QR requires the optional 'qrcode' package") from err
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=8, border=4)
    qr.add_data(encode_qr_text(packet))
    try:
        qr.make(fit=True)
    except (ValueError, OverflowError) as err:
        raise FormatError("single-QR capacity exceeded") from err
    img = qr.make_image(image_factory=SvgPathImage)
    img.save(str(dest))
    return qr.version


def make_png(packet: dict, dest: str | Path, box_size: int = 8):
    """Render a high-contrast QR with exact integer pixel modules for scanning."""
    try:
        import qrcode
    except ImportError as err:
        raise ImportError("PNG QR requires the optional 'qrcode' package") from err
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=box_size, border=4)
    qr.add_data(encode_qr_text(packet))
    try:
        qr.make(fit=True)
    except (ValueError, OverflowError) as err:
        raise FormatError("single-QR capacity exceeded") from err
    qr.make_image(fill_color="black", back_color="white").save(str(dest))
    return qr.version


def read_qr_image(image_path: str | Path) -> dict:
    """Decode using local OpenCV; optionally zbarimg if installed. Never calls home."""
    from .codec import decode_qr_text
    path = Path(image_path)
    if path.stat().st_size > 16*1024*1024:
        raise FormatError("QR image too large")
    # An attacker can submit a tiny highly compressed image with huge pixel size.
    # Check dimensions before allowing a decoder to materialize pixel arrays.
    try:
        from PIL import Image
        with Image.open(path) as img:
            if img.width * img.height > 20_000_000:
                raise FormatError("QR raster exceeds safe pixel budget")
    except ImportError:
        pass
    except OSError as exc:
        raise FormatError("invalid image input") from exc
    text = ""
    # ZBar typically decodes large dense printed ipQR symbols more reliably
    # than OpenCV. All readers run locally and supply only untrusted bytes.
    try:
        from PIL import Image
        from pyzbar.pyzbar import decode
        found = decode(Image.open(path))
        for candidate in found:
            if candidate.type == "QRCODE":
                text = candidate.data.decode("utf-8", errors="strict")
                break
    except (ImportError, OSError, ValueError, UnicodeError):
        pass
    if not text:
      try:
        import cv2
        pixels = cv2.imread(str(path))
        if pixels is not None:
            text, _, _ = cv2.QRCodeDetector().detectAndDecode(pixels)
      except (ImportError, ValueError):
        pass
    if not text:
        from shutil import which
        if which("zbarimg"):
            try:
                proc = subprocess.run(["zbarimg", "--quiet", "--raw", str(path)],
                                      capture_output=True, timeout=8, check=False)
                if proc.returncode == 0:
                    text = proc.stdout.decode("utf-8",errors="strict").strip()
            except (subprocess.TimeoutExpired, UnicodeError) as exc:
                raise FormatError("offline QR decode timed out or returned invalid text") from exc
    if not text:
        raise FormatError("QR decode failed; provide exact ipqr1: text from an offline scanner")
    return decode_qr_text(text)


def report_html(packet: dict, verdict: dict, qr_svg: str | None = None) -> str:
    """Standalone printable static report. No scripts, no external fetches."""
    def esc(value):
        return html.escape(str(value), quote=True)
    receipt=packet.get("receipt",{})
    verified = bool(verdict["verified"])
    claim_status = packet.get("receipt", {}).get("verdict", "UNDETERMINED")
    if verified and claim_status == "REFUTED_FALSE":
        label, tone = "SIGNED RECEIPT AUTHENTIC — CLAIM REFUTED_FALSE", "#ff7786"
    elif verified:
        label, tone = "DIGITAL RECEIPT VERIFIED — SCOPED CLAIM", "#7cf9c0"
    else:
        label, tone = esc(verdict["code"]), "#ffcc66"
    signer = verdict.get("accountable_human") or {}
    if signer.get("organization") == "DEMO ONLY":
        label = "SYNTHETIC DEMO ONLY · " + label
        if tone == "#7cf9c0":
            tone = "#ffcc66"
    list_rows="\n".join(f'<div class="row"><span>{esc(k)}</span><b>{esc("PENDING" if v is None else "PASS" if v else "FAIL")}</b></div>'
                         for k,v in verdict.get("checks",{}).items())
    warns="".join(f"<li>{esc(w)}</li>" for w in verdict.get("warnings",[])+verdict.get("failures",[]))
    claim=receipt.get("claim",{})
    qr=qr_svg or "<p>No QR image embedded</p>"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:">
<title>iNNOVULIS Open Receipt Verification</title><style>
:root{{color-scheme:dark}}body{{background:#090e14;color:#f3f8fa;font-family:system-ui,Arial,sans-serif;margin:0;padding:34px}}
.card{{max-width:940px;margin:auto;border:1px solid #45656a;border-radius:24px;background:linear-gradient(135deg,#172429,#060b10);padding:30px;box-shadow:0 16px 36px #0009}}
.eyebrow{{color:#b1cbd3;font-weight:700;letter-spacing:.18em;text-transform:uppercase;font-size:12px}}
h1{{margin:.2em 0 .1em;font-size:34px}}h2{{font-size:19px;margin-top:24px}}
.pill{{display:inline-block;margin-top:14px;color:{tone};border:1px solid {tone};padding:10px;border-radius:12px;font-weight:700}}
.row{{display:flex;justify-content:space-between;border-bottom:1px solid #2a4246;padding:8px 0;gap:18px;word-break:break-word}}
.row b{{text-align:right}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:30px}}.qr{{background:#fff;padding:15px;border-radius:12px;align-self:start}}
.qr svg{{width:100%;height:auto;max-width:500px}}.note{{padding:16px;margin-top:24px;border:1px solid #7b684c;border-radius:12px;color:#f5d4a2}}
small{{color:#b9c8cf}}li{{margin:.5em 0}}@media(max-width:720px){{.grid{{display:block}}body{{padding:10px}}}}@media print{{:root{{color-scheme:light}}body{{background:white;color:black}}.card{{background:white;color:black;box-shadow:none}}.row{{border-color:#bbb}}.note{{color:black}}}}
</style></head><body><main class="card"><div class="eyebrow">iNNOVULIS™ · open, independently auditable</div>
<h1>Universal Receipt</h1><div class="pill">{label}</div><div class="grid"><section>
<h2>Claim and responsibility</h2><div class="row"><span>Subject</span><b>{esc(receipt.get('subject','?'))}</b></div>
<div class="row"><span>Statement</span><b>{esc(claim.get('observed','?'))} ≤ {esc(claim.get('limit','?'))} {esc(claim.get('unit',''))}</b></div>
<div class="row"><span>Issuer verdict</span><b>{esc(receipt.get('verdict','?'))}</b></div>
<div class="row"><span>Verifier result</span><b>{esc(verdict['code'])}</b></div>
<div class="row"><span>Receipt digest</span><b>{esc(verdict.get('receipt_sha256',''))}</b></div>
<div class="row"><span>Trust anchor digest</span><b>{esc(verdict.get('trust_anchor_sha256',''))}</b></div>
<div class="row"><span>Accountable person</span><b>{esc((verdict.get('accountable_human') or {}).get('name','UNVERIFIED'))}</b></div>
<h2>Independent checks</h2>{list_rows}</section><section><h2>QR: untrusted transport</h2><div class="qr">{qr}</div><small>The QR code carries signed data, not its own trust anchor. Scan with an offline, independently pinned verifier.</small></section></div>
<div class="note"><strong>Evidence is not universal truth.</strong> Digital checks do not prove the sensor was authentic or calibrated, the issuer clock was correct, or a human's asserted credentials. Independent revocation freshness and accountable human review remain essential.<ul>{warns}</ul></div>
<small>Standalone static report · no external scripts, fonts, images or network requests.</small></main></body></html>'''
