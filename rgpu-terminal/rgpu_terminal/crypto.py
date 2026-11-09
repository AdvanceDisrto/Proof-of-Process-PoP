"""iNNOVULIS rGPU digital telemetry receipt cryptography. Protocol v1.

The signed bytes are exact canonical UTF-8 bytes; the browser verifies those
same bytes without reserializing JSON or trusting a key supplied by a packet.
All keys in this prototype are *software* keys, NOT TPM/PUF-backed.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import stat
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

DOMAIN = b"iNNOVULIS/RGPU-TELEMETRY/v1\x00"
SCHEMA = "innovulis/rgpu-receipt/v1"
ENVELOPE_SCHEMA = "innovulis/rgpu-envelope/v1"
ZERO_HASH = "0" * 64


class ReceiptError(ValueError):
    pass


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def unb64url(value: str) -> bytes:
    if not isinstance(value, str) or len(value) > 32768 or not value or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in value):
        raise ReceiptError("invalid unpadded base64url")
    try:
        decoded=base64.urlsafe_b64decode(value + '='*((-len(value))%4))
        if b64url(decoded)!=value:
            raise ReceiptError("noncanonical base64url")
        return decoded
    except (ValueError, TypeError) as e:
        raise ReceiptError("invalid base64url") from e


def public_hex(key: ed25519.Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(serialization.Encoding.Raw,
                                          serialization.PublicFormat.Raw).hex()


def public_fingerprint(pubhex: str) -> str:
    return hashlib.sha256(bytes.fromhex(pubhex)).hexdigest()


def load_or_create_identity(path: str | Path) -> ed25519.Ed25519PrivateKey:
    path = Path(path)
    if path.exists() or path.is_symlink():
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077:
                raise ReceiptError("private-key file must be regular and mode 0600")
            if st.st_size > 8192:
                raise ReceiptError("private-key file unexpectedly large")
            with os.fdopen(fd, "rb", closefd=False) as f:
                key = serialization.load_pem_private_key(f.read(), password=None)
        finally:
            os.close(fd)
        if not isinstance(key, ed25519.Ed25519PrivateKey):
            raise ReceiptError("identity file does not contain Ed25519 private key")
        return key
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    key = ed25519.Ed25519PrivateKey.generate()
    encoded = key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        return load_or_create_identity(path)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        try: path.unlink()
        except OSError: pass
        raise
    return key


def make_envelope(payload: dict, key: ed25519.Ed25519PrivateKey) -> dict:
    raw = canonical(payload)
    return {
        "schema": ENVELOPE_SCHEMA,
        "payload_b64u": b64url(raw),
        "payload_sha256": hashlib.sha256(raw).hexdigest(),
        "signature_hex": key.sign(DOMAIN + raw).hex(),
        "issuer_key_fingerprint": public_fingerprint(public_hex(key)),
    }


def verify_envelope(envelope: dict, pinned_pub_hex: str, *, previous: str | None = None,
                    expected_sequence: int | None = None) -> dict:
    if not isinstance(envelope, dict) or set(envelope) != {
            "schema", "payload_b64u", "payload_sha256", "signature_hex",
            "issuer_key_fingerprint"} or envelope["schema"] != ENVELOPE_SCHEMA:
        raise ReceiptError("unknown envelope schema")
    if not isinstance(pinned_pub_hex, str) or len(pinned_pub_hex)!=64:
        raise ReceiptError("explicitly pinned Ed25519 public key required")
    if public_fingerprint(pinned_pub_hex) != envelope["issuer_key_fingerprint"]:
        raise ReceiptError("issuer does not match independent pinned public key")
    raw = unb64url(envelope["payload_b64u"])
    if len(raw) > 16_384:
        raise ReceiptError("oversized payload")
    actual_hash = hashlib.sha256(raw).hexdigest()
    if envelope["payload_sha256"] != actual_hash:
        raise ReceiptError("payload SHA-256 mismatch")
    try:
        signature = bytes.fromhex(envelope["signature_hex"])
        if len(signature)!=64: raise ReceiptError("bad Ed25519 signature size")
        ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(pinned_pub_hex)).verify(signature, DOMAIN + raw)
    except (InvalidSignature, ValueError, TypeError) as e:
        raise ReceiptError("invalid cryptographic signature") from e
    try:
        payload = json.loads(raw)
        if canonical(payload)!=raw or type(payload) is not dict or payload.get("schema")!=SCHEMA:
            raise ReceiptError("noncanonical or unsupported signed payload")
        sequence=payload["sequence"]
        if type(sequence) is not int or sequence < 1:
            raise ReceiptError("invalid sequence")
        if previous is not None and payload["previous_sha256"]!=previous:
            raise ReceiptError("broken hash chain")
        if expected_sequence is not None and sequence!=expected_sequence:
            raise ReceiptError("missing or replayed sequence")
        if not isinstance(payload.get("claim"), str) or not isinstance(payload.get("source_tier"), str):
            raise ReceiptError("unsupported declared claim fields")
        if payload.get("source_tier") not in ("LOCAL_SOFTWARE_ONLY", "SYNTHETIC_DEMO"):
            raise ReceiptError("unapproved evidence tier")
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as e:
        raise ReceiptError("invalid signed payload") from e
    return payload
