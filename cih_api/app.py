"""iNNOVULIS CIH ΔiΔ: bounded cryptographic receipt service.

No simulated solver outcomes, fabricated hardware attestation, or self-issued
legal certification. Signed evidence is NOT independent proof of factual truth.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from cih_api.krdid import authenticate, commit_receipt, readiness, consume_nonce

app = FastAPI(title="iNNOVULIS CIH ΔiΔ", version="0.2.0",
              description="Evidence-integrity operations; no automatic truth or hardware certification.")
allowed_origins = [x.strip() for x in os.getenv("CIH_ALLOWED_ORIGINS", "").split(",") if x.strip()]
if allowed_origins:
    app.add_middleware(CORSMiddleware, allow_origins=allowed_origins,
                       allow_methods=["GET", "POST"], allow_headers=["content-type", "x-krdid", "x-krdid-signature", "x-krdid-timestamp", "x-krdid-nonce"])
HASH = re.compile(r"^[a-f0-9]{64}$")
DOES_NOT_PROVE = (
    "the source data are truthful or independently authenticated",
    "the underlying physical or AI process occurred as asserted",
    "that a mathematical solver or hardware trust element executed",
    "legal certification, scientific correctness, or authority"
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(",", ":")).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def decode_b64(name: str) -> bytes:
    value = os.getenv(name, "")
    if not value:
        raise ValueError(name + " is not configured")
    return base64.b64decode(value, validate=True)


def signing_key() -> Ed25519PrivateKey:
    try:
        key = decode_b64("CIH_ED25519_PRIVATE_KEY_B64")
        if len(key) != 32:
            raise ValueError("CIH signing seed must be 32 bytes")
        return Ed25519PrivateKey.from_private_bytes(key)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="SIGNING_KEY_UNAVAILABLE") from exc


def pinned_verify_key() -> Ed25519PublicKey:
    try:
        raw = decode_b64("CIH_ED25519_PUBLIC_KEY_B64")
        if len(raw) != 32:
            raise ValueError("Bad public key")
        return Ed25519PublicKey.from_public_bytes(raw)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="TRUST_ANCHOR_UNAVAILABLE") from exc


def public_key_id(key: Ed25519PublicKey) -> str:
    raw = key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    return "ed25519-sha256:" + sha256(raw)[:24]



class ReceiptRequest(BaseModel):
    claim: str = Field(min_length=3, max_length=1000)
    evidence: dict[str, Any] = Field(min_length=1)
    expected_evidence_sha256: str
    source_id: str = Field(min_length=1, max_length=160)
    parent_receipt_hashes: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("expected_evidence_sha256")
    @classmethod
    def verify_hash_format(cls, value: str) -> str:
        if not HASH.fullmatch(value):
            raise ValueError("Expected evidence SHA-256 must be 64 lowercase hex chars")
        return value

    @field_validator("parent_receipt_hashes")
    @classmethod
    def verify_parents(cls, values: list[str]) -> list[str]:
        if len(set(values)) != len(values) or any(not HASH.fullmatch(v) for v in values):
            raise ValueError("Duplicate or malformed parent hashes")
        return values


class SignedReceipt(BaseModel):
    body: dict[str, Any]
    body_sha256: str
    signature_b64: str
    key_id: str
    storage_status: str = "NOT_RECORDED"


class ReconciliationRequest(BaseModel):
    receipts: list[SignedReceipt] = Field(min_length=1, max_length=50)


def check_signed_receipt(receipt: SignedReceipt) -> bool:
    key = pinned_verify_key()
    if public_key_id(key) != receipt.key_id:
        return False
    serialized = canonical(receipt.body)
    if sha256(serialized) != receipt.body_sha256:
        return False
    try:
        signature = base64.b64decode(receipt.signature_b64, validate=True)
        key.verify(signature, serialized)
        return True
    except (ValueError, InvalidSignature):
        return False



@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    state = readiness()
    return {
        "service": "cih-evidence-api", "version": "0.2.0", "status": "RUNNING",
        "auth_provider": "LOCAL_KRDID_ED25519",
        "auth_configured": state["enrolled"] > 0,
        "krdid_enrolled_count": state["enrolled"],
        "krdid_registry_ready": state["ready"],
        "signer_configured": bool(os.getenv("CIH_ED25519_PRIVATE_KEY_B64")),
        "trusted_key_configured": bool(os.getenv("CIH_ED25519_PUBLIC_KEY_B64")),
        "storage_configured": state["ready"],
        "storage_provider": "LOCAL_SQLITE",
        "hardware_backed_identity": "NOT_ATTESTED",
        "independent_truth_engine": "NOT_CONNECTED",
        "hardware_attestation": "NOT_CONNECTED"
    }


@app.get("/api/v1/architecture")
def architecture() -> dict[str, Any]:
    return {
        "framework": "iNNOVULIS CIH",
        "coordination_layers": ["compute", "communication", "security", "resource-allocation"],
        "sector_examples": ["healthcare", "agriculture", "energy"],
        "verification_capability": "bounded Ed25519 evidence-integrity receipt",
        "does_not_prove": list(DOES_NOT_PROVE)
    }


@app.post("/api/v1/receipts", response_model=SignedReceipt)
def issue_receipt(
    data: ReceiptRequest,
    x_krdid: str | None = Header(default=None),
    x_krdid_signature: str | None = Header(default=None),
    x_krdid_timestamp: str | None = Header(default=None),
    x_krdid_nonce: str | None = Header(default=None),
) -> SignedReceipt:
    auth = authenticate(x_krdid, x_krdid_signature, x_krdid_timestamp,
                        x_krdid_nonce, data.model_dump(mode="json"), "/api/v1/receipts")
    try:
        actual_hash = sha256(canonical(data.evidence))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="INVALID_EVIDENCE_FORMAT") from exc
    if actual_hash != data.expected_evidence_sha256:
        raise HTTPException(status_code=422, detail="EVIDENCE_DIGEST_MISMATCH")
    key = signing_key()
    body = {
        "schema": "innovulis.cih.receipt.v0.1",
        "receipt_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "operation": "evidence_digest_validation",
        "claim": data.claim,
        "source_id": data.source_id,
        "requester_subject": auth["krdid"],
        "request_identity": {
            "method": "LOCAL_ENROLLED_KRDID_ED25519",
            "krdid": auth["krdid"],
            "request_sha256": auth["request_sha256"],
            "public_key_sha256": auth["public_key_sha256"],
            "request_timestamp": auth["timestamp"],
            "nonce": auth["nonce"],
        },
        "evidence_sha256": actual_hash,
        "parent_receipt_hashes": data.parent_receipt_hashes,
        "assessment": "INPUT_DIGEST_MATCHED",
        "warrant": "SELF_DECLARED_SOURCE; KRDID_SIGNATURE_VERIFIED; SIGNED_BY_CIH",
        "does_not_prove": list(DOES_NOT_PROVE),
    }
    serialized = canonical(body)
    receipt = SignedReceipt(body=body, body_sha256=sha256(serialized),
                            signature_b64=base64.b64encode(key.sign(serialized)).decode("ascii"),
                            key_id=public_key_id(key.public_key()))
    record = receipt.model_dump(mode="json")
    record["storage_status"] = "LOCAL_SQLITE_COMMITTED"
    receipt.storage_status = commit_receipt(auth, record)
    return receipt


@app.post("/api/v1/verify")
def verify_receipt(receipt: SignedReceipt) -> dict[str, Any]:
    valid = check_signed_receipt(receipt)
    return {"integrity_valid": valid, "status": "SIGNATURE_VALID" if valid else "REFUTED_SIGNATURE",
            "does_not_prove": list(DOES_NOT_PROVE)}


@app.post("/api/v1/reconcile")
def reconcile_fragment(
    data: ReconciliationRequest,
    x_krdid: str | None = Header(default=None),
    x_krdid_signature: str | None = Header(default=None),
    x_krdid_timestamp: str | None = Header(default=None),
    x_krdid_nonce: str | None = Header(default=None),
) -> dict[str, Any]:
    """Verify signatures plus local parent links; NOT a deployed mesh protocol."""
    auth = authenticate(x_krdid, x_krdid_signature, x_krdid_timestamp,
                        x_krdid_nonce, data.model_dump(mode="json"), "/api/v1/reconcile")
    observed: set[str] = set()
    for index, receipt in enumerate(data.receipts):
        if not check_signed_receipt(receipt):
            raise HTTPException(status_code=409, detail={"status": "REJECTED_SIGNATURE", "index": index})
        parents = receipt.body.get("parent_receipt_hashes")
        if not isinstance(parents, list) or any(p not in observed for p in parents):
            raise HTTPException(status_code=409, detail={"status": "REJECTED_MISSING_PARENT", "index": index})
        if receipt.body_sha256 in observed:
            raise HTTPException(status_code=409, detail={"status": "REJECTED_DUPLICATE", "index": index})
        observed.add(receipt.body_sha256)
    consume_nonce(auth, "reconcile:" + sha256(canonical(data.model_dump(mode="json"))))
    return {"status": "FRAGMENT_INTEGRITY_ACCEPTED", "receipts_checked": len(observed),
            "does_not_prove": ["that a physical mesh synchronized",
                               "that every claimed computation occurred",
                               "that a central ledger has committed these receipts"]}
