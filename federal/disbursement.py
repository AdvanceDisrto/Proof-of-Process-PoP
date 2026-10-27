"""Read-only prepayment receipt checks. No payment execution or fraud adjudication.

Cryptographic signatures protect the signed claims. They DO NOT establish that a
service was rendered, a patient consented, an agency's database is accurate, or
that a key was in a physical YubiKey/TEE.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

REQUIRED_ROLES = (
    "provider", "eligibility_verifier", "dnp_verifier", "service_verifier", "agency_authorizer"
)
HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
PAYMENT_ID = re.compile(r"^[0-9a-f]{32}$")
PUB = re.compile(r"^[0-9a-f]{64}$")
SIG = re.compile(r"^[0-9a-f]{128}$")


@dataclass(frozen=True)
class Decision:
    state: str
    reason: str
    payment_authorized: bool = False
    bounty_authorized: bool = False
    bitcoin_anchor_verified: bool = False


def canonical(payload: Any) -> bytes:
    """Defined subset: standard JSON + only safe integers, no floats/NaN."""
    def validate(obj: Any) -> None:
        if obj is None or isinstance(obj, (str, bool)):
            return
        if type(obj) is int and -(2**53 - 1) <= obj <= 2**53 - 1:
            return
        if isinstance(obj, list):
            for element in obj:
                validate(element)
            return
        if isinstance(obj, dict) and all(type(key) is str for key in obj):
            for element in obj.values():
                validate(element)
            return
        raise ValueError("signed JSON contains unsupported numeric/type value")
    validate(payload)
    return json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def verify_disbursement(bundle: dict, trusted_keys: dict, *, now_unix: int,
                        consumed_payment_ids: set[str]) -> Decision:
    """Accepts independently supplied pinned keys; never releases public funds."""
    try:
        if type(now_unix) is not int:
            raise ValueError("untrusted timestamp type")
        if not isinstance(bundle, dict) or not isinstance(trusted_keys, dict):
            raise ValueError("receipt or trust registry missing")
        body = bundle.get("body")
        if not isinstance(body, dict) or body.get("protocol") != "ITM-FED-DISBURSEMENT-v1":
            raise ValueError("unsupported payment protocol")
        canonical_body = canonical(body)
        if not PAYMENT_ID.fullmatch(str(body.get("payment_id", ""))):
            raise ValueError("invalid payment id")
        if body["payment_id"] in consumed_payment_ids:
            raise ValueError("replayed payment id")
        if type(body.get("amount_cents")) is not int or body["amount_cents"] <= 0:
            raise ValueError("invalid integer-cent payment")
        if not body.get("agency") or not body.get("program"):
            raise ValueError("missing agency or program")
        for field in ("intent_hash", "beneficiary_commitment", "service_commitment"):
            if not isinstance(body.get(field), str) or not HASH.fullmatch(body[field]):
                raise ValueError(f"invalid {field}")
        if not (type(body.get("issued_at")) is int and type(body.get("expires_at")) is int
                and body["issued_at"] <= now_unix <= body["expires_at"]
                and body["expires_at"] - body["issued_at"] <= 600):
            raise ValueError("receipt stale, premature or excessive validity window")
        checks = (
            ("eligibility", "ELIGIBLE"), ("do_not_pay", "CLEAR"),
            ("service", "EXTERNALLY_CORROBORATED")
        )
        for name, expected in checks:
            check = body.get(name)
            if not isinstance(check, dict) or check.get("decision") != expected:
                raise ValueError(f"{name} is not {expected}")
            if not isinstance(check.get("evidence_root"), str) or not HASH.fullmatch(check["evidence_root"]):
                raise ValueError(f"{name} evidence commitment missing")
        if trusted_keys.get("protocol") != "ITM-FED-TRUST-v1":
            raise ValueError("external trust registry missing")
        keymap = trusted_keys.get("keys")
        sigs = bundle.get("attestations")
        if not isinstance(keymap, dict) or not isinstance(sigs, list):
            raise ValueError("keys or attestations missing")
        used_pubkeys: set[str] = set()
        for role in REQUIRED_ROLES:
            entries = [s for s in sigs if isinstance(s, dict) and s.get("role") == role]
            if len(entries) != 1 or not isinstance(keymap.get(role), dict):
                raise ValueError(f"missing or repeated attestation: {role}")
            entry = entries[0]
            key = keymap[role]
            pub = key.get("public_key_hex")
            if (entry.get("key_id") != key.get("key_id") or not isinstance(pub, str)
                    or not PUB.fullmatch(pub) or pub in used_pubkeys):
                raise ValueError(f"untrusted or reused key for {role}")
            signature = entry.get("signature_hex")
            if not isinstance(signature, str) or not SIG.fullmatch(signature):
                raise ValueError(f"malformed signature for {role}")
            used_pubkeys.add(pub)
            try:
                Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub)).verify(
                    bytes.fromhex(signature), canonical_body
                )
            except Exception as exc:
                raise ValueError(f"invalid attestation for {role}") from exc
        return Decision("EVIDENCE_CHECKS_PASS_SETTLEMENT_NOT_AUTHORIZED",
                        "Independent signing keys validate the claims; external adjudication, "
                        "fraud controls, payment-rail integration and lawful authorization are still required.")
    except (ValueError, TypeError, KeyError) as exc:
        return Decision("REJECTED", str(exc))


def duplicate_alert(receipts: list[dict]) -> list[dict]:
    """Potential duplicate commitments only; flags review, never slashes stake."""
    by_key: dict[tuple, str] = {}
    alerts = []
    for body in receipts:
        key = (body.get("beneficiary_commitment"), body.get("service_commitment"),
               body.get("amount_cents"))
        if None in key:
            continue
        prior = by_key.setdefault(key, body.get("payment_id"))
        if prior != body.get("payment_id"):
            alerts.append({"state": "AUDIT_REVIEW_REQUIRED", "first": prior,
                           "possible_duplicate": body.get("payment_id"),
                           "automatic_forfeiture": False})
    return alerts
