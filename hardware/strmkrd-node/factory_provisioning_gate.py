"""Read-only P-256 key-possession verifier, NOT a hardware attestation."""
from __future__ import annotations
import argparse
import hashlib
import json
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.exceptions import InvalidSignature

DOMAIN = "STRMKRD-P256-DEVICE-CHALLENGE-v1"

def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def payload(device_serial: str, challenge_hex: str, board_id: str, slot: int) -> dict:
    if not isinstance(device_serial, str) or len(device_serial) != 18:
        raise ValueError("ATECC serial is nine bytes hex")
    if not isinstance(challenge_hex, str) or len(challenge_hex) != 64:
        raise ValueError("nonce must be 32 bytes hex")
    bytes.fromhex(device_serial); bytes.fromhex(challenge_hex)
    if type(slot) is not int or not (0 <= slot <= 15) or not board_id or len(board_id)>100:
        raise ValueError("bad board/slot")
    return {"domain":DOMAIN, "board_id":board_id,"device_serial_hex":device_serial.lower(),
            "challenge_hex":challenge_hex.lower(),"key_slot":slot}

def verify(record: dict) -> dict:
    if record.get("spec")!="strmkrd/rev0/p256-proof-of-possession/v1":
        raise ValueError("invalid spec")
    if record.get("signature_algorithm")!="ECDSA-P256-SHA256":
        raise ValueError("invalid algorithm")
    if record.get("source_tier") not in {"SYNTHETIC_SOFTWARE_KEY","UNVERIFIED_EXTERNAL_DEVICE"}:
        raise ValueError("source tier cannot be promoted")
    message=record["payload"]
    if message != payload(message["device_serial_hex"],message["challenge_hex"],
                          message["board_id"],message["key_slot"]):
        raise ValueError("payload not canonical or not bound to challenge")
    key=serialization.load_pem_public_key(record["public_key_pem"].encode())
    if not isinstance(key,ec.EllipticCurvePublicKey) or not isinstance(key.curve,ec.SECP256R1):
        raise ValueError("not NIST P-256")
    digest=hashlib.sha256(canonical(message)).digest()
    try:
        key.verify(bytes.fromhex(record["signature_der_hex"]),digest,
                   ec.ECDSA(utils.Prehashed(hashes.SHA256())))
    except InvalidSignature as exc:
        raise ValueError("signature invalid") from exc
    return {"status":"ECDSA_P256_PROOF_OF_KEY_POSSESSION_VALID",
            "hardware_origin":"NOT_VERIFIED",
            "provisioning_attestation":"NOT_VERIFIED",
            "does_not_prove":["private key generated on ATECC608C",
                              "sensor hardware authenticity",
                              "factory chain of custody or FIPS validation"]}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record_file")
    args=parser.parse_args()
    try:
        with open(args.record_file,encoding="utf-8") as f:record=json.load(f)
        print(json.dumps(verify(record),indent=2))
    except (ValueError,KeyError,TypeError,UnicodeError,OSError) as exc:
        print(json.dumps({"status":"REJECTED","error_type":type(exc).__name__,
                          "hardware_origin":"NOT_VERIFIED"}))
        raise SystemExit(2)

if __name__=="__main__":
    main()
