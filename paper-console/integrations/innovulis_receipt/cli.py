"""Open-source local CLI verification surface. Never contacts the issuer."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .codec import read_json_file, decode_qr_text, sha256, canonical, FormatError
from .engine import verify
from .carrier import make_svg, make_png, read_qr_image, report_html


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(prog="ipqr-verify", description="Offline signed ipQR v1 receipt verifier")
    sub=parser.add_subparsers(dest="cmd",required=True)
    for name in ("verify", "verify-qr-text", "verify-image"):
        p=sub.add_parser(name)
        p.add_argument("--input",required=True,help="Signed receipt JSON, ipqr1: text file or QR image")
        p.add_argument("--trust",required=True,help="Operator-approved public trust JSON (not from QR)")
        p.add_argument("--anchor-pin",required=True,help="Expected SHA-256 trust anchor from independent source")
        p.add_argument("--revocations",required=True,help="Signed offline revocation snapshot")
        p.add_argument("--issuance-log",required=True,help="Independently signed receipt issuance checkpoint")
        p.add_argument("--subject",required=True,help="Expected physical/digital subject ID read independently")
        p.add_argument("--evidence-dir",help="Directory holding original evidence bytes")
        p.add_argument("--challenge-nonce",help="Independently issued 16-byte nonce as 32 lowercase hex")
        p.add_argument("--json-out",help="Write detailed machine-readable decision report")
        p.add_argument("--html-out",help="Write standalone printable decision report")
    p=sub.add_parser("make-qr",help="Create a printable SVG of the signed packet; printer remains untrusted")
    p.add_argument("--input",required=True)
    p.add_argument("--svg",help="Optional vector QR output")
    p.add_argument("--png",help="Recommended scanner-tested pixel-perfect QR output")
    p=sub.add_parser("demo",help="Generate fresh synthetic demo keys/signatures; NEVER production")
    p.add_argument("--out",default="examples/demo")
    p=sub.add_parser("anchor-digest",help="Display SHA-256 of a local trust anchor; NOT a trust bootstrap")
    p.add_argument("--trust",required=True)
    args=parser.parse_args(argv)
    try:
        if args.cmd == "demo":
            from .issuer_demo import write_demo
            data=write_demo(args.out)
            print("DEMO_ONLY trust_anchor_sha256="+data["trust_sha256"]+" output="+args.out)
            return 0
        if args.cmd == "anchor-digest":
            print("UNTRUSTED_LOCAL_ANCHOR_DIGEST="+sha256(canonical(read_json_file(args.trust))))
            return 0
        if args.cmd == "make-qr":
            if not args.svg and not args.png:
                raise FormatError("specify at least one of --svg or --png")
            packet=read_json_file(args.input)
            version=make_svg(packet, args.svg) if args.svg else None
            if args.png:
                version=make_png(packet, args.png)
            print(f"QR_CARRIER_GENERATED version={version}; signature verification NOT performed")
            return 0
        if args.cmd == "verify":
            packet=read_json_file(args.input)
        elif args.cmd == "verify-image":
            packet=read_qr_image(args.input)
        else:
            raw=Path(args.input).read_text(encoding="ascii").strip()
            packet=decode_qr_text(raw)
        trust=read_json_file(args.trust)
        revoked=read_json_file(args.revocations)
        issuance_log=read_json_file(args.issuance_log)
        decision=verify(packet,trust,revoked,issuance_log,
                        expected_anchor_sha256=args.anchor_pin, expected_subject=args.subject,
                        evidence_dir=args.evidence_dir,
                        expected_nonce_hex=args.challenge_nonce)
        output=decision.to_dict()
        print(json.dumps(output,sort_keys=True,indent=2))
        if args.json_out:
            Path(args.json_out).write_text(json.dumps(output,sort_keys=True,indent=2)+"\n")
        if args.html_out:
            from io import StringIO
            qr_markup=None
            if args.cmd in ("verify", "verify-qr-text", "verify-image"):
                # QR is visual transport, never authority; use pixel-perfect modules.
                from tempfile import TemporaryDirectory
                import base64
                try:
                    with TemporaryDirectory() as temp:
                        p=Path(temp)/"qr.png"
                        make_png(packet,p)
                        src=base64.b64encode(p.read_bytes()).decode("ascii")
                        qr_markup=f'<img alt="ipQR signed packet carrier" width="500" height="500" src="data:image/png;base64,{src}">'
                except (ImportError, FormatError):
                    qr_markup=None
            Path(args.html_out).write_text(report_html(packet,output,qr_markup),encoding="utf-8")
        return 0 if decision.verified else 2
    except (FormatError, OSError, UnicodeError, ValueError, TypeError) as err:
        print(json.dumps({"code":"REJECTED", "verified":False,
                          "error":str(err)[:300]},sort_keys=True),file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
