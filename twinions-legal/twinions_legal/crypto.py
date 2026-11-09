"""Software-only demo signature on receipt, independently pinned public key needed."""
from __future__ import annotations
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
from .ledger import canonical,digest


def sign_demo(snapshot: dict, private_key: Ed25519PrivateKey) -> dict:
    clean={"protocol":"twinions-review-receipt/0.1","snapshot":snapshot,
           "source_tier":"SOFTWARE_DEMO","legal_filing_authority":"NONE"}
    message=canonical(clean)
    sig=private_key.sign(message)
    return {"signed":clean,"signature_b64":base64.b64encode(sig).decode(),
            "payload_sha256":digest(message)}


def verify_receipt(receipt: dict, independently_pinned_public_hex: str) -> bool:
    try:
        if receipt["signed"]["source_tier"]!="SOFTWARE_DEMO":return False
        if receipt["signed"]["legal_filing_authority"]!="NONE":return False
        msg=canonical(receipt["signed"])
        if digest(msg)!=receipt["payload_sha256"]:return False
        pk=bytes.fromhex(independently_pinned_public_hex)
        if len(pk)!=32:return False
        sig=base64.b64decode(receipt["signature_b64"],validate=True)
        if len(sig)!=64:return False
        Ed25519PublicKey.from_public_bytes(pk).verify(sig,msg)
        return True
    except (ValueError,KeyError,TypeError,InvalidSignature):return False
