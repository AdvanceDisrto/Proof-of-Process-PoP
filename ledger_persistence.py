"""Fail-closed Supabase persistence for independently verified receipts."""
from __future__ import annotations
import os
from typing import Any, Mapping

def validate_ledger_record(receipt: Mapping[str, Any]) -> None:
    if receipt.get("physical_gate") != "MEASURED_PASS":
        raise ValueError("physical_gate must already be MEASURED_PASS")
    if receipt.get("attestation_verification") != "VERIFIED":
        raise ValueError("attestation_verification must be VERIFIED")
    if receipt.get("evidence_origin") in {"SIMULATED", "MOCK", "SYNTHETIC"}:
        raise ValueError("synthetic evidence cannot enter the physical ledger")
    if not receipt.get("verifier_receipt_id"):
        raise ValueError("verifier_receipt_id is required")
    digest = str(receipt.get("workload_hash", ""))
    if len(digest) != 64:
        raise ValueError("workload_hash must be a SHA-256 hex digest")
    bytes.fromhex(digest)

def to_ledger_record(receipt: Mapping[str, Any]) -> dict[str, Any]:
    validate_ledger_record(receipt)
    return {
        "receipt_id": str(receipt["receipt_id"]),
        "instance_id": str(receipt["instance_id"]),
        "provider_name": receipt.get("provider_name"),
        "hardware_type": str(receipt["hardware_type"]),
        "workload_hash": str(receipt["workload_hash"]),
        "evidence_sha256": str(receipt["evidence_sha256"]),
        "attestation_verification": "VERIFIED",
        "physical_gate_status": "MEASURED_PASS",
        "evidence_origin": str(receipt["evidence_origin"]),
        "verifier_receipt_id": str(receipt["verifier_receipt_id"]),
        "identity_root_id": receipt.get("identity_root_id"),
        "identity_epoch": receipt.get("identity_epoch"),
        "receipt_signature": receipt.get("receipt_signature"),
        "delegation_certificate": receipt.get("delegation_certificate"),
        "metadata": receipt.get("metadata") or {},
    }

def commit_verified_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    record = to_ledger_record(receipt)
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials are not configured")
    from supabase import create_client
    client = create_client(url, key)
    response = client.table("reality_ledger").insert(record).execute()
    if not response.data:
        raise RuntimeError("Supabase ledger insert returned no record")
    return response.data[0]
