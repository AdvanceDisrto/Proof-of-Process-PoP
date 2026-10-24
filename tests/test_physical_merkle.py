from core.physical_merkle import merkle_root, verify_physical_receipt


def verified_receipt(receipt_id="vendor:1"):
    return {
        "physical_gate": "MEASURED_PASS",
        "attestation_verification": "VERIFIED",
        "evidence_origin": "PHYSICAL_PROVIDER",
        "verifier_receipt_id": receipt_id,
        "workload_hash": "a" * 64,
        "hardware_type": "NVIDIA_GPU_TEE",
    }


def test_simulated_leaf_poisoning_fails_closed():
    simulated = verified_receipt("vendor:sim")
    simulated["evidence_origin"] = "SIMULATED"
    assert merkle_root([verified_receipt(), simulated]) is None


def test_large_blob_without_verification_is_rejected():
    fake = {
        "physical_gate": "MEASURED_PASS",
        "attestation_verification": "UNVERIFIED",
        "evidence_origin": "PHYSICAL_PROVIDER",
        "raw_attestation_report_b64": "A" * 4096,
        "verifier_receipt_id": "vendor:fake",
        "workload_hash": "b" * 64,
    }
    assert not verify_physical_receipt(fake).valid
    assert merkle_root([fake]) is None


def test_action_required_leaf_is_rejected():
    receipt = verified_receipt()
    receipt["physical_gate"] = "ACTION_REQUIRED"
    assert merkle_root([receipt]) is None


def test_verified_receipts_produce_deterministic_root():
    a = verified_receipt("vendor:a")
    b = verified_receipt("vendor:b")
    root_ab = merkle_root([a, b])
    root_ba = merkle_root([b, a])
    assert root_ab is not None
    assert root_ab.startswith("sha256:")
    assert root_ab == root_ba
