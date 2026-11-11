"""Cryptographic primitives and deterministic set-commitment construction."""
from __future__ import annotations
import hashlib
import re
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
from .codec import canonical, sha256, FormatError

HEX32 = re.compile(r"^[0-9a-f]{64}$")
HEX64 = re.compile(r"^[0-9a-f]{128}$")
ISSUER_DOMAIN = b"IPQR:ISSUER:V1\x00"
ENGINEER_DOMAIN = b"IPQR:ENGINEER:V1\x00"
WITNESS_DOMAIN = b"IPQR:WITNESS:V1\x00"
REVOCATION_DOMAIN = b"IPQR:REVOCATIONS:V1\x00"
ISSUANCE_LOG_DOMAIN = b"IPQR:ISSUANCE_LOG:V1\x00"


def check_hex(value, n=64):
    if type(value) is not str or len(value) != n or not re.fullmatch("[0-9a-f]{%d}" % n, value):
        raise FormatError("invalid lowercase hex field")


def msg(domain: bytes, payload: dict) -> bytes:
    return domain + hashlib.sha256(canonical(payload)).digest()


def sign(key: ed25519.Ed25519PrivateKey, domain: bytes, payload: dict) -> str:
    return key.sign(msg(domain, payload)).hex()


def verify_signature(pub_hex: str, domain: bytes, payload: dict, sig_hex: str) -> bool:
    try:
        check_hex(pub_hex, 64)
        check_hex(sig_hex, 128)
        ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(
            bytes.fromhex(sig_hex), msg(domain, payload))
        return True
    except (InvalidSignature, ValueError, TypeError, FormatError):
        return False


def public_hex(key: ed25519.Ed25519PrivateKey) -> str:
    from cryptography.hazmat.primitives import serialization
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def merkle_root(items: list[dict]) -> str:
    """Domain-separated SHA256 Merkle tree. Odd final leaf promoted unchanged.

    Leaves in the caller-prescribed stable ordering. No tree proof in this version:
    the whole small manifest travels in the signed receipt.
    """
    if not isinstance(items, list) or not items:
        raise FormatError("empty Merkle set is not accepted")
    level = [hashlib.sha256(b"\x00" + canonical(item)).digest() for item in items]
    while len(level) > 1:
        level = [hashlib.sha256(b"\x01" + level[i] + level[i + 1]).digest()
                 if i + 1 < len(level) else level[i]
                 for i in range(0, len(level), 2)]
    return level[0].hex()


def witness_commitment(trust: dict) -> str:
    entries = trust["witnesses"]
    return merkle_root([{"id": w["id"], "public_key": w["public_key"]} for w in entries])
