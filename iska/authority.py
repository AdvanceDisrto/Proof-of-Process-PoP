"""i™ Sovereign Key Authority (iSKA).

Root private keys are generated/used locally and are never required by the
provider backend. Provider receipt signing is delegated through a short-lived,
root-signed Ed25519 certificate.

This module proves cryptographic authorization only. It never promotes a
physical gate or asserts hardware execution.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

DOMAIN_DELEGATION = b"iSKA-DELEGATION-v1:"
DOMAIN_RECEIPT = b"iSKA-RECEIPT-v1:"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"), validate=True)


def _public_hex(key: ed25519.Ed25519PublicKey) -> str:
    return key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


@dataclass(frozen=True)
class DelegationCertificate:
    root_id: str
    root_public_key: str
    delegated_public_key: str
    role: str
    scope: tuple[str, ...]
    issued_at: int
    expires_at: int
    certificate_id: str
    signature: str

    def payload(self) -> dict[str, Any]:
        return {
            "delegated_public_key": self.delegated_public_key,
            "role": self.role,
            "scope": list(self.scope),
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "certificate_id": self.certificate_id,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_id": self.root_id,
            "root_public_key": self.root_public_key,
            "payload": self.payload(),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DelegationCertificate":
        payload = value["payload"]
        return cls(
            root_id=str(value["root_id"]),
            root_public_key=str(value["root_public_key"]),
            delegated_public_key=str(payload["delegated_public_key"]),
            role=str(payload["role"]),
            scope=tuple(str(x) for x in payload["scope"]),
            issued_at=int(payload["issued_at"]),
            expires_at=int(payload["expires_at"]),
            certificate_id=str(payload["certificate_id"]),
            signature=str(value["signature"]),
        )


@dataclass(frozen=True)
class ReceiptSignature:
    payload: dict[str, Any]
    signature: str
    delegation_certificate: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt": self.payload,
            "signature": self.signature,
            "identity_chain": {
                "root_identity": self.delegation_certificate["root_id"],
                "delegation_certificate": self.delegation_certificate,
            },
        }


def generate_root_identity() -> tuple[ed25519.Ed25519PrivateKey, str, str]:
    key = ed25519.Ed25519PrivateKey.generate()
    public_key = _public_hex(key.public_key())
    root_id = f"did:iska:root:{public_key[:16]}"
    return key, root_id, public_key


def issue_delegation(
    root_private_key: ed25519.Ed25519PrivateKey,
    root_id: str,
    root_public_key: str,
    *,
    role: str = "PROVIDER_BACKEND",
    scope: tuple[str, ...] = ("SIGN_RECEIPTS",),
    ttl_seconds: int = 30 * 24 * 60 * 60,
    now: int | None = None,
) -> tuple[ed25519.Ed25519PrivateKey, DelegationCertificate]:
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")
    issued_at = int(time.time()) if now is None else int(now)
    delegated_private = ed25519.Ed25519PrivateKey.generate()
    delegated_public = _public_hex(delegated_private.public_key())
    payload = {
        "delegated_public_key": delegated_public,
        "role": role,
        "scope": list(scope),
        "issued_at": issued_at,
        "expires_at": issued_at + ttl_seconds,
        "certificate_id": f"iska-cert-{secrets.token_hex(16)}",
    }
    signature = root_private_key.sign(DOMAIN_DELEGATION + _canonical(payload))
    cert = DelegationCertificate(
        root_id=root_id,
        root_public_key=root_public_key,
        delegated_public_key=delegated_public,
        role=role,
        scope=tuple(scope),
        issued_at=issued_at,
        expires_at=issued_at + ttl_seconds,
        certificate_id=payload["certificate_id"],
        signature=_b64(signature),
    )
    return delegated_private, cert


def verify_delegation(
    certificate: DelegationCertificate | Mapping[str, Any],
    *,
    now: int | None = None,
    required_scope: str = "SIGN_RECEIPTS",
) -> bool:
    cert = (
        certificate
        if isinstance(certificate, DelegationCertificate)
        else DelegationCertificate.from_dict(certificate)
    )
    current = int(time.time()) if now is None else int(now)
    if cert.expires_at <= current or cert.issued_at > current:
        return False
    if required_scope not in cert.scope:
        return False
    try:
        root_public = ed25519.Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(cert.root_public_key)
        )
        root_public.verify(
            _unb64(cert.signature),
            DOMAIN_DELEGATION + _canonical(cert.payload()),
        )
    except (ValueError, TypeError):
        return False
    expected_root_id = f"did:iska:root:{cert.root_public_key[:16]}"
    return secrets.compare_digest(cert.root_id, expected_root_id)


def sign_receipt(
    delegated_private_key: ed25519.Ed25519PrivateKey,
    certificate: DelegationCertificate,
    receipt_payload: Mapping[str, Any],
    *,
    now: int | None = None,
) -> ReceiptSignature:
    current = int(time.time()) if now is None else int(now)
    if not verify_delegation(certificate, now=current):
        raise ValueError("delegation certificate is not valid")
    if "SIGN_RECEIPTS" not in certificate.scope:
        raise ValueError("delegation scope does not permit receipt signing")
    payload = dict(receipt_payload)
    payload.setdefault("spec", "innovulis-hrtf-receipt/1.0")
    payload["identity_epoch"] = certificate.certificate_id
    signature = delegated_private_key.sign(DOMAIN_RECEIPT + _canonical(payload))
    return ReceiptSignature(
        payload=payload,
        signature=_b64(signature),
        delegation_certificate=certificate.to_dict(),
    )


def verify_receipt(
    receipt: Mapping[str, Any],
    *,
    now: int | None = None,
) -> bool:
    try:
        chain = receipt["identity_chain"]
        cert = DelegationCertificate.from_dict(chain["delegation_certificate"])
        if not verify_delegation(cert, now=now):
            return False
        payload = receipt["receipt"]
        signature = _unb64(str(receipt["signature"]))
        delegated_public = ed25519.Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(cert.delegated_public_key)
        )
        delegated_public.verify(
            signature,
            DOMAIN_RECEIPT + _canonical(payload),
        )
        return True
    except (KeyError, ValueError, TypeError, ed25519.InvalidSignature):
        return False


def fingerprint(receipt: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical(receipt)).hexdigest()
