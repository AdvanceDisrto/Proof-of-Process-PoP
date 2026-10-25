"""Persistent Ed25519 identity derived from a seed phrase."""
import hashlib
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def derive_from_seed(seed_phrase: str) -> ed25519.Ed25519PrivateKey:
    seed = hashlib.sha256(("buddy-identity-v1:" + seed_phrase).encode()).digest()
    return ed25519.Ed25519PrivateKey.from_private_bytes(seed)

def public_hex(priv: ed25519.Ed25519PrivateKey) -> str:
    return priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
