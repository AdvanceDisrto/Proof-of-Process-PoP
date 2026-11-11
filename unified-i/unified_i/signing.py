"""Domain-separated Ed25519 software manifests; pinned authority out of band.

Never infer hardware provenance merely from a valid signature.
"""
from __future__ import annotations
import copy
import hmac
import re
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from .codec import ClaimRecord, ContractError, canonical, sha256

DOMAIN=b"iNNOVULIS/unified-claim/v1\x00"

class SignatureRejected(ValueError): pass


def public_hex(key:ed25519.Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()


def sign(record:ClaimRecord, key:ed25519.Ed25519PrivateKey)->dict:
    if not isinstance(key,ed25519.Ed25519PrivateKey):raise SignatureRejected("software Ed25519 signer required")
    body=record.to_dict()
    sig=key.sign(DOMAIN+canonical(body))
    return {"schema":"i-unified-claim/v1","body":body,"signature":sig.hex(),
            "algorithm":"Ed25519", "signer_scope":"SOFTWARE_PRIVATE_KEY_NOT_HARDWARE"}


def verify(packet:dict,*,pinned_public_key_hex:str,pinned_key_id:str,now:int,expected_subject:str,
           minimum_sequence:int=1)->ClaimRecord:
    # The issuer's claimed public key, if any, is never a trust anchor.
    if type(packet) is not dict or set(packet)!={"schema","body","signature","algorithm","signer_scope"}:
        raise SignatureRejected("invalid envelope fields")
    if packet["schema"]!="i-unified-claim/v1" or packet["algorithm"]!="Ed25519":
        raise SignatureRejected("version/algorithm mismatch")
    if packet["signer_scope"]!="SOFTWARE_PRIVATE_KEY_NOT_HARDWARE":
        raise SignatureRejected("cannot upgrade cryptographic provenance")
    if type(pinned_public_key_hex) is not str or not re.fullmatch(r"[0-9a-f]{64}",pinned_public_key_hex):
        raise SignatureRejected("independent public key pin required")
    if type(pinned_key_id) is not str or not pinned_key_id:
        raise SignatureRejected("pinned identity required")
    if type(now) is not int or type(minimum_sequence) is not int:
        raise SignatureRejected("integer clock/sequence only")
    body=packet["body"]
    if type(body) is not dict or set(body)!=set(ClaimRecord.__dataclass_fields__):
        raise SignatureRejected("malformed body")
    try:
        record=ClaimRecord(**{**body,"limitations":tuple(body["limitations"])})
        signature=bytes.fromhex(packet["signature"])
        key=ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(pinned_public_key_hex))
        key.verify(signature,DOMAIN+canonical(body))
    except (ValueError,TypeError,KeyError,InvalidSignature,ContractError) as e:
        raise SignatureRejected("cryptographic or schema validation failed") from e
    if len(signature)!=64:raise SignatureRejected("signature length wrong")
    if record.issuer_key_id!=pinned_key_id or record.subject!=expected_subject:
        raise SignatureRejected("identity/subject binding failed")
    if not record.issued_at <= now <= record.expires_at:
        raise SignatureRejected("receipt outside its time bounds")
    if record.sequence < minimum_sequence:
        raise SignatureRejected("sequence too old")
    return record
