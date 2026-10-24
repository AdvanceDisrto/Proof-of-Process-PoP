from tools.inetty_smallest_proof import run,verify,run_tamper_check,derive_sovereign_ipv6

def test_smallest_proof_verifies(tmp_path):
    r=run(str(tmp_path/"proof.json")); assert r["verification"]["ok"]; assert r["state"]=="VERIFIED_PROCESS"; assert r["transport_tier"]=="SIMULATED"; assert r["physical_gate"]=="ACTION_REQUIRED"

def test_tamper_is_detected():
    assert run_tamper_check()

def test_sovereign_address_is_deterministic():
    key="00"*32
    assert derive_sovereign_ipv6(key)==derive_sovereign_ipv6(key)
