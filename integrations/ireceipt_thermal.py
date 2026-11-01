"""PoP's receipt-to-paper boundary. Does not claim a printer or blockchain witness."""
from __future__ import annotations
import hashlib
import json
from urllib.parse import urlencode, urlparse

from core.crypto import canonical, sha, verify

class ReceiptRejected(ValueError):
    pass

def verify_domain_envelope(envelope: dict, trusted_signers: set[str]) -> dict:
    """Check Ed25519 receipt integrity AND an externally configured signer allowlist."""
    try:
        body = envelope["body"]
        signer = body["signer"]
        pub = signer.removeprefix("ed25519:")
        if not signer.startswith("ed25519:") or pub not in trusted_signers:
            raise ReceiptRejected("Untrusted receipt signer")
        if envelope["receipt_id"] != sha(canonical(body)):
            raise ReceiptRejected("Receipt identifier mismatch")
        if not verify(pub, body, envelope["signature"]):
            raise ReceiptRejected("Signature invalid")
        return body
    except (KeyError, TypeError, AttributeError):
        raise ReceiptRejected("Malformed receipt") from None

def paper_payload(envelope: dict, trusted_signers: set[str], verify_base_url: str | None = None) -> dict:
    body = verify_domain_envelope(envelope, trusted_signers)
    receipt_id = envelope["receipt_id"]
    state = body.get("state", "UNKNOWN")
    # This verifies the receipt signature and trusted key, not execution truth.
    qr_content = receipt_id
    if verify_base_url:
        u = urlparse(verify_base_url)
        if u.scheme != "https" or not u.hostname or u.username or u.password or u.fragment:
            raise ReceiptRejected("HTTPS verifier base URL required")
        qr_content = verify_base_url.rstrip("/") + "?" + urlencode({"receipt_id": receipt_id})
    return {
        "schema": "ipqr/physical-receipt-payload/1",
        "receipt_id": receipt_id,
        "signer": body["signer"],
        "recorded_state": state,
        "signature_integrity": "VERIFIED_WITH_TRUSTED_PUBLIC_KEY",
        "physical_event_verified": False,
        "external_anchor_verified": False,
        "qr_content": qr_content,
        "disclaimer": "SIGNATURE VALID; underlying claims and physical state require independent evidence",
    }

def render_58mm_text(payload: dict) -> str:
    return "\n".join([
        "       i(TM) iNNOVULIS",
        "     EVIDENCE RECEIPT",
        "--------------------------------",
        "STATE: " + str(payload["recorded_state"])[:24],
        "SIG: TRUSTED KEY VERIFIED",
        "PHYSICAL: NOT VERIFIED",
        "ANCHOR: NOT VERIFIED",
        "ID: " + payload["receipt_id"][:24],
        "QR: " + payload["qr_content"],
        "Verify independently.",
        "--------------------------------",
    ]) + "\n"

def print_escpos(payload: dict, printer, *, operator_approved: bool = False) -> None:
    """Hardware print is opt-in; injected printer only, never auto-discover USB."""
    if not operator_approved:
        raise ReceiptRejected("Physical printing requires explicit operator approval")
    if payload.get("signature_integrity") != "VERIFIED_WITH_TRUSTED_PUBLIC_KEY":
        raise ReceiptRejected("Unverified receipt cannot be printed as verified")
    printer.text(render_58mm_text(payload))
    printer.qr(payload["qr_content"], size=5)
    printer.cut()
