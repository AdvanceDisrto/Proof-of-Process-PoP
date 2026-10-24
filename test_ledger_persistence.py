from ledger_persistence import to_ledger_record, validate_ledger_record
import pytest


def verified():
    return {
        "receipt_id": "rcpt-1",
        "instance_id": "node-1",
        "provider_name": "provider",
        "hardware_type": "TEE_GPU",
        "workload_hash": "a" * 64,
        "evidence_sha256": "b" * 64,
        "attestation_verification": "VERIFIED",
        "physical_gate": "MEASURED_PASS",
        "evidence_origin": "PHYSICAL_PROVIDER",
        "verifier_receipt_id": "vendor-quote-1",
        "identity_root_id": "did:iska:root:1234",
        "identity_epoch": "iska-cert-1",
        "receipt_signature": "sig",
        "delegation_certificate": {},
    }


def test_verified_record_is_mappable():
    row = to_ledger_record(verified())
    assert row["physical_gate_status"] == "MEASURED_PASS"
    assert row["attestation_verification"] == "VERIFIED"


@pytest.mark.parametrize("field,value", [
    ("physical_gate", "ACTION_REQUIRED"),
    ("attestation_verification", "UNVERIFIED"),
    ("evidence_origin", "SIMULATED"),
])
def test_unverified_record_fails_closed(field, value):
    record = verified()
    record[field] = value
    with pytest.raises(ValueError):
        validate_ledger_record(record)


def test_invalid_workload_hash_fails_closed():
    record = verified()
    record["workload_hash"] = "not-a-hash"
    with pytest.raises(ValueError):
        validate_ledger_record(record)
