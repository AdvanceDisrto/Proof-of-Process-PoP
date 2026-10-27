"""Independent machine receipt verifier; accepts only externally pinned Ed25519 public key.

Never derives criminal guilt or real-world truth from a mathematical signature.
"""
import argparse
import json
import re
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
from .router import canonical, load_json, sha256, MACHINE_DOMAIN


def verify_chain(records: Path, machine_public_key_hex: str):
    if not re.fullmatch(r"[0-9a-f]{64}", machine_public_key_hex):
        raise ValueError("externally pinned public key must be raw Ed25519 32-byte hex")
    key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(machine_public_key_hex))
    previous = "0" * 64
    total = 0
    for total, p in enumerate(sorted(Path(records).glob("*.json")), 1):
        if p.name != f"{total:012d}.json":
            raise ValueError("nonconsecutive machine receipt")
        d = load_json(p.read_bytes())
        if not isinstance(d, dict) or set(d) != {"event", "signature_hex"}:
            raise ValueError("invalid envelope structure")
        e = d["event"]
        if (e.get("protocol") != "ITM-MACHINE-INTAKE-v1" or
            e.get("seq") != total or e.get("prev_event_hash") != previous or
            e.get("settlement_authorized") is not False or
            e.get("physical_actuation_authorized") is not False or
            e.get("underlying_real_world_event_verified") is not False):
            raise ValueError("receipt claims outside authorized scope or chain conflict")
        sign = d["signature_hex"]
        if not isinstance(sign, str) or not re.fullmatch(r"[0-9a-f]{128}", sign):
            raise ValueError("signature encoding rejected")
        try:
            key.verify(bytes.fromhex(sign), MACHINE_DOMAIN + canonical(e))
        except InvalidSignature as exc:
            raise ValueError("machine signature failed") from exc
        previous = sha256(MACHINE_DOMAIN + canonical(e))
    if total == 0:
        raise ValueError("no records to verify")
    return {"receipt_count": total, "last_local_root": previous,
            "result": "LOCAL_MACHINE_INGRESS_SIGNATURES_VERIFIED",
            "underlying_events_verified": False,
            "external_tamper_evident_anchor_present": False}


def main():
    a = argparse.ArgumentParser(description="Verify signed local intake receipts; no underlying claims certified")
    a.add_argument("--records", type=Path, required=True)
    a.add_argument("--machine-public-key-hex", required=True)
    args = a.parse_args()
    print(json.dumps(verify_chain(args.records, args.machine_public_key_hex), sort_keys=True))


if __name__ == "__main__":
    main()

