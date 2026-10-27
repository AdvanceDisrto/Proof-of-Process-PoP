"""Read-only cross-border transfer receipt validation — NO settlement.

Cryptographic signer authorization does not establish the truth of KYC/AML
assertions, the legality of a wire, the bank's available funds or a Bitcoin
anchor. A successful reference check is never permission to move money.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from federal.disbursement import canonical

HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
ID = re.compile(r"^[0-9a-f]{32}$")
CUR = re.compile(r"^[A-Z]{3}$")
PUB = re.compile(r"^[0-9a-f]{64}$")
SIGNATURE = re.compile(r"^[0-9a-f]{128}$")
REQUIRED_ROLES = (
    "payer", "payee", "kyc_verifier", "sanctions_verifier", "settlement_authority"
)


@dataclass(frozen=True)
class Assessment:
    state: str
    reason: str
    payout_permitted: bool = False
    anchor_verified: bool = False
    sanctions_live_query_performed: bool = False


def assess_transfer(bundle: dict[str, Any], independent_registry: dict[str, Any],
                    *, now_unix: int, seen_ids: set[str]) -> Assessment:
    try:
        if not isinstance(bundle, dict) or not isinstance(independent_registry, dict):
            raise ValueError("transaction bundle or independent trust registry absent")
        body = bundle.get("body")
        if not isinstance(body, dict) or body.get("protocol") != "ITM-GLOBAL-LEDGER-v1":
            raise ValueError("unknown global ledger protocol")
        signed = canonical(body)
        if not isinstance(body.get("transaction_id"), str) or not ID.fullmatch(body["transaction_id"]):
            raise ValueError("invalid transaction ID")
        if body["transaction_id"] in seen_ids:
            raise ValueError("duplicate transaction ID")
        if type(body.get("amount_minor")) is not int or body["amount_minor"] <= 0:
            raise ValueError("amount must be positive integer minor units")
        if not isinstance(body.get("currency"), str) or not CUR.fullmatch(body["currency"]):
            raise ValueError("currency must be ISO-style 3-letter code")
        for field in ("sender_commitment", "receiver_commitment", "purpose_hash"):
            if not isinstance(body.get(field), str) or not HASH.fullmatch(body[field]):
                raise ValueError(f"missing/invalid {field}")
        if type(now_unix) is not int or not(type(body.get("issued_at")) is int and
               type(body.get("expires_at")) is int and body["issued_at"] <= now_unix <= body["expires_at"] and
               0 <= body["expires_at"] - body["issued_at"] <= 600):
            raise ValueError("stale, premature or unbounded authorization time")
        checks = (("kyc", "PASS"), ("aml", "PASS"), ("sanctions", "CLEAR"))
        for name, expect in checks:
            item = body.get(name)
            if not isinstance(item, dict) or item.get("decision") != expect:
                raise ValueError(f"{name} check missing/not cleared")
            if not isinstance(item.get("evidence_root"), str) or not HASH.fullmatch(item["evidence_root"]):
                raise ValueError(f"missing {name} evidence root")
        if independent_registry.get("protocol") != "ITM-GLOBAL-TRUST-v1":
            raise ValueError("unverified external trust registry")
        registry_keys = independent_registry.get("keys")
        att = bundle.get("attestations")
        if not isinstance(registry_keys, dict) or not isinstance(att, list):
            raise ValueError("keys/signatures missing")
        pubs = set()
        for role in REQUIRED_ROLES:
            signatures = [s for s in att if isinstance(s, dict) and s.get("role") == role]
            key = registry_keys.get(role)
            if len(signatures) != 1 or not isinstance(key, dict):
                raise ValueError(f"missing/duplicate signer: {role}")
            record = signatures[0]
            pub = key.get("public_key_hex")
            signature = record.get("signature_hex")
            if (record.get("key_id") != key.get("key_id")
                or not isinstance(pub, str) or not PUB.fullmatch(pub)
                or not isinstance(signature, str) or not SIGNATURE.fullmatch(signature)
                or pub in pubs):
                raise ValueError(f"untrusted/duplicate key: {role}")
            pubs.add(pub)
            try:
                Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub)).verify(
                    bytes.fromhex(signature), signed
                )
            except Exception as error:
                raise ValueError(f"signature invalid: {role}") from error
        return Assessment(
            "SIGNED_EVIDENCE_CHECKS_PASS_SETTLEMENT_BLOCKED",
            "Pinned signers attest to claims, not real-time legal compliance, bank balances, "
            "TEE provenance or transaction finality. External validation/approval still required.",
        )
    except (ValueError, TypeError, KeyError) as exc:
        return Assessment("REJECTED", str(exc))
