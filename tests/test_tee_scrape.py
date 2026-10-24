import os
from tools.tee_scrape_simulator import detect_tee_hardware, simulate_host_memory_scrape, simulate_attestation_verifier, emit_evidence_receipt

def test_tee_detection_is_explicit():
    result = detect_tee_hardware()
    assert "tee_present" in result
    assert all(k in result for k in ("amd_sev_snp_sysfs","amd_sev_guest_dev","intel_tdx_guest_dev","intel_sgx_dev"))

def test_memory_scrape_reports_only_observed_state():
    result = simulate_host_memory_scrape()
    assert result["child_pid"] is not None
    if result["secret_observable"]:
        assert result["mem_openable"]
    else:
        assert result["failure_reason"] is not None or not result["maps_readable"]

def test_verifier_rejects_empty_quote():
    r=simulate_attestation_verifier({})
    assert r == {"verdict":"REJECT","reason":"NO_VENDOR_CHAIN","physical_gate":"ACTION_REQUIRED"}

def test_verifier_rejects_fake_root():
    r=simulate_attestation_verifier({"vendor_chain":["FAKE_CA"],"measurement_sha256":"abc","nonce_match":True})
    assert r["verdict"]=="REJECT" and r["reason"]=="UNTRUSTED_ROOT" and r["physical_gate"]=="ACTION_REQUIRED"

def test_verifier_rejects_missing_measurement():
    r=simulate_attestation_verifier({"vendor_chain":["AMD_SEV_SNP_ROOT_CA"],"nonce_match":True})
    assert r["reason"]=="MISSING_MEASUREMENT" and r["physical_gate"]=="ACTION_REQUIRED"

def test_verifier_rejects_nonce_mismatch():
    r=simulate_attestation_verifier({"vendor_chain":["AMD_SEV_SNP_ROOT_CA"],"measurement_sha256":"abc","nonce_match":False})
    assert r["reason"]=="NONCE_MISMATCH" and r["physical_gate"]=="ACTION_REQUIRED"

def test_receipt_gate_stays_locked(tmp_path):
    p=tmp_path/"receipt.json"
    receipt=emit_evidence_receipt(str(p))
    assert receipt["physical_gate"]=="ACTION_REQUIRED"
    assert p.exists()
