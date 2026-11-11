"""Verify an externally produced PoP Ed25519 receipt against a pinned trusted key.

This gate deliberately does NOT generate ephemeral CI signing keys or claim
hardware/PQC signatures. Missing signer, file or trust anchor => nonzero exit.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from integrations.ireceipt_thermal import verify_domain_envelope, ReceiptRejected

def verify_external_receipt(path: str, trusted_hex: str) -> dict:
    if not trusted_hex or len(trusted_hex) != 64:
        raise ReceiptRejected("Pinned Ed25519 key required")
    try:
        bytes.fromhex(trusted_hex)
    except ValueError:
        raise ReceiptRejected("Invalid Ed25519 key") from None
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    body = verify_domain_envelope(document, {trusted_hex})
    return {"verification": "SIGNATURE_INTEGRITY_ACCEPTED",
            "receipt_id": document["receipt_id"],
            "signed_state": body.get("state", "UNKNOWN"),
            "external_anchor": "NOT_EVALUATED",
            "physical_execution": "NOT_EVALUATED",
            "pqc_signature": "NOT_EVALUATED"}

def main() -> int:
    path = os.getenv("POP_CI_SIGNED_RECEIPT")
    pub = os.getenv("POP_CI_TRUSTED_PUBKEY")
    if not path or not pub:
        print("ACTION_REQUIRED: CI signed receipt and pinned trusted key are required", file=sys.stderr)
        return 2
    try:
        result = verify_external_receipt(path, pub)
    except (OSError, json.JSONDecodeError, ReceiptRejected, KeyError, TypeError) as exc:
        print("REJECTED: external receipt verification failed (" + type(exc).__name__ + ")", file=sys.stderr)
        return 3
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
