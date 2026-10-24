import copy

from tools.cce_prime_factor_probe import (
    EXPECTED,
    METHOD_SOURCE,
    run_probe,
    sha256_text,
    verify_receipt,
)

def test_prime_factor_method_does_not_embed_ground_truth_literal():
    assert EXPECTED not in METHOD_SOURCE

def test_prime_factor_probe_matches_harness_truth():
    receipt = run_probe()
    assert receipt["execution"]["stdout"] == EXPECTED
    assert receipt["validation"]["success"] is True
    assert receipt["ilogic"]["truth_axis"] == "ESTABLISHED"
    assert receipt["ilogic"]["attestation_axis"] == "UNATTESTED"
    assert receipt["ilogic"]["tier"] == "VERIFIED_PROCESS"
    assert receipt["physical_gate"] == "ACTION_REQUIRED"
    assert receipt["claims"]["method_was_invented_not_retrieved"] == "UNATTESTED"
    assert verify_receipt(receipt) == []

def test_prime_factor_forged_success_is_rejected():
    receipt = run_probe()
    forged = copy.deepcopy(receipt)
    forged["execution"]["stdout_hash"] = sha256_text("wrong")
    assert verify_receipt(forged)
