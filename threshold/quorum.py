"""iNNOVULIS receipt quorum: independently pinned Ed25519 signatures, NO execution authority.

This does not attest to the truth of the source's claim, the independence of hardware,
model alignment, legal status or external financial settlement.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey, Ed25519PrivateKey
from cryptography.exceptions import InvalidSignature

RECEIPT_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
KEY_RE = re.compile(r"[0-9a-f]{64}\Z")
NONCE_RE = re.compile(r"[0-9a-f]{32}\Z")
SIGN_RE = re.compile(r"[0-9a-f]{128}\Z")
DOMAIN = b"iNNOVULIS-JUROR-ATTESTATION-v1\x00"
OUT_DOMAIN = b"iNNOVULIS-RELAY-RECEIPT-v1\x00"
MAX_TTL = 600

class VerificationError(ValueError):
    """Verification failed closed; no authorization implied."""

def canonical(value: Any) -> bytes:
    """Restricted deterministic JSON (NOT complete RFC 8785). No floats or duplicate keys."""
    def validate(v: Any):
        if isinstance(v, dict):
            if any(not isinstance(k, str) for k in v):
                raise VerificationError("object keys must be strings")
            for item in v.values(): validate(item)
        elif isinstance(v, list):
            for item in v: validate(item)
        elif type(v) is int:
            if abs(v) > (2**53 - 1): raise VerificationError("unsafe integer")
        elif type(v) not in (str, bool, type(None)):
            raise VerificationError("unsupported canonical value")
    validate(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")

def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()

def exact_keys(obj: Any, keys: set[str], label: str):
    if not isinstance(obj, dict) or set(obj) != keys:
        raise VerificationError(f"{label}: unexpected or missing fields")

def valid_hash(v: Any, label: str) -> None:
    if not isinstance(v, str) or not RECEIPT_RE.fullmatch(v):
        raise VerificationError(f"{label}: invalid SHA256")

def validate_registry(registry: dict, pin: str) -> str:
    exact_keys(registry, {"protocol", "policy_sha256", "jurors"}, "registry")
    if registry["protocol"] != "ITM-JUROR-REGISTRY-v1":
        raise VerificationError("registry protocol")
    valid_hash(registry["policy_sha256"], "registry policy")
    if not isinstance(registry["jurors"], dict) or set(registry["jurors"]) != {"juror-a", "juror-b", "juror-c"}:
        raise VerificationError("require exactly three named independent jurors")
    values = list(registry["jurors"].values())
    if any(not isinstance(v, str) or not KEY_RE.fullmatch(v) for v in values) or len(set(values)) != 3:
        raise VerificationError("invalid/duplicate juror keys")
    valid_hash(pin, "pin")
    registry_hash = sha256(canonical(registry))
    if registry_hash != pin:
        raise VerificationError("PIN_MISMATCH: trusted registry changed")
    return registry_hash

ATT_FIELDS = {"juror", "receipt_sha256", "policy_sha256", "request_nonce", "decision", "issued_at", "expires_at", "signature_hex"}
BATCH_FIELDS = {"protocol", "receipt_sha256", "policy_sha256", "request_nonce", "attestations"}

def signing_bytes(payload: dict) -> bytes:
    exact_keys(payload, ATT_FIELDS - {"signature_hex"}, "attestation payload")
    return DOMAIN + canonical(payload)

def evaluate(batch: dict, registry: dict, pin: str, now: int | None = None) -> dict:
    validate_registry(registry, pin)
    exact_keys(batch, BATCH_FIELDS, "batch")
    if batch["protocol"] != "ITM-JUROR-QUORUM-BATCH-v1":
        raise VerificationError("batch protocol")
    valid_hash(batch["receipt_sha256"], "receipt")
    valid_hash(batch["policy_sha256"], "batch policy")
    if batch["policy_sha256"] != registry["policy_sha256"]:
        raise VerificationError("policy mismatch")
    if not isinstance(batch["request_nonce"], str) or not NONCE_RE.fullmatch(batch["request_nonce"]):
        raise VerificationError("invalid request nonce")
    if not isinstance(batch["attestations"], list) or not 1 <= len(batch["attestations"]) <= 3:
        raise VerificationError("expected 1..3 attestations")
    if now is None: now = int(datetime.now(timezone.utc).timestamp())
    if type(now) is not int or now < 0:
        raise VerificationError("bad verifier clock")
    seen: set[str] = set()
    approving: list[str] = []
    rejecting: list[str] = []
    digest_list: list[str] = []
    for att in batch["attestations"]:
        exact_keys(att, ATT_FIELDS, "attestation")
        juror = att["juror"]
        if not isinstance(juror, str) or juror not in registry["jurors"]:
            raise VerificationError("unrecognized juror")
        if juror in seen:
            raise VerificationError("duplicate juror")
        seen.add(juror)
        for k in ("receipt_sha256", "policy_sha256", "request_nonce"):
            if att[k] != batch[k]:
                raise VerificationError("cross-batch replay or conflicting metadata")
        if att["decision"] not in ("APPROVE", "REJECT"):
            raise VerificationError("unknown decision")
        issued, expires = att["issued_at"], att["expires_at"]
        if type(issued) is not int or type(expires) is not int:
            raise VerificationError("invalid timestamp types")
        if issued > now or expires < now or expires <= issued or expires-issued > MAX_TTL:
            raise VerificationError("expired, future, or overlong attestation")
        sig = att["signature_hex"]
        if not isinstance(sig, str) or not SIGN_RE.fullmatch(sig):
            raise VerificationError("signature hex invalid")
        try:
            pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(registry["jurors"][juror]))
            pub.verify(bytes.fromhex(sig), signing_bytes({k: v for k, v in att.items() if k != "signature_hex"}))
        except (ValueError, InvalidSignature) as exc:
            raise VerificationError("BAD_SIGNATURE") from exc
        digest_list.append(sha256(canonical(att)))
        (approving if att["decision"] == "APPROVE" else rejecting).append(juror)
    # Reject-veto is the safe operational policy for the prototype. No unreviewed execution.
    state = "REFUTED_BY_SIGNED_REJECTION" if rejecting else ("QUORUM_APPROVED" if len(approving) >= 2 else "ACTION_REQUIRED")
    return {
        "protocol": "ITM-QUORUM-EVALUATION-v1", "state": state,
        "receipt_sha256": batch["receipt_sha256"], "policy_sha256": batch["policy_sha256"],
        "request_nonce": batch["request_nonce"], "registry_sha256": pin,
        "approved_jurors": sorted(approving), "rejected_jurors": sorted(rejecting),
        "attestation_hashes": sorted(digest_list),
        "threshold": 2, "total_jurors": 3,
        "actuation_authorized": False, "settlement_authorized": False,
        "physical_attestation_verified": False,
    }

def issue_relay_receipt(evaluation: dict, signing_key: Ed25519PrivateKey) -> dict:
    if evaluation.get("protocol") != "ITM-QUORUM-EVALUATION-v1":
        raise VerificationError("not a quorum evaluation")
    return {"evaluation": evaluation,
            "relay_signature_hex": signing_key.sign(OUT_DOMAIN + canonical(evaluation)).hex(),
            "signature_alg": "Ed25519", "protocol": "ITM-RELAY-SIGNED-RECEIPT-v1"}

def verify_relay_receipt(receipt: dict, relay_pub_hex: str) -> bool:
    exact_keys(receipt, {"evaluation", "relay_signature_hex", "signature_alg", "protocol"}, "relay receipt")
    if receipt["protocol"] != "ITM-RELAY-SIGNED-RECEIPT-v1" or receipt["signature_alg"] != "Ed25519":
        raise VerificationError("relay envelope protocol")
    if not KEY_RE.fullmatch(relay_pub_hex) or not SIGN_RE.fullmatch(receipt["relay_signature_hex"]):
        raise VerificationError("invalid relay key or signature")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(relay_pub_hex)).verify(bytes.fromhex(receipt["relay_signature_hex"]), OUT_DOMAIN + canonical(receipt["evaluation"]))
    except InvalidSignature as e:
        raise VerificationError("INVALID_RELAY_SIGNATURE") from e
    return True

