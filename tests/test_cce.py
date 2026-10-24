from tools.cce_prototype import CCE, sha, verify_epistemic_genesis

def test_cce_generates_executes_and_verifies():
    c = CCE()
    method, source, synthesis = c.generate_cognition(
        "Find a shortest path through a binary grid.", sha(b"failed-base")
    )
    execution = c.execute(method, source, [[0,1,0],[0,1,0],[0,0,0]])
    expected = [[0,0],[1,0],[2,0],[2,1],[2,2]]
    outcome = c.validate(execution, expected)
    assert outcome["validation"]["success"] is True
    assert outcome["ilogic"]["tier"] == "VERIFIED_PROCESS"
    assert outcome["ilogic"]["attestation_axis"] == "UNATTESTED"
    assert outcome["physical_gate"] == "ACTION_REQUIRED"
    assert verify_epistemic_genesis(outcome) == []

def test_cce_forgery_is_rejected():
    c = CCE()
    method, source, _ = c.generate_cognition("p", sha(b"f"))
    execution = c.execute(method, source, [[0,0],[0,0]])
    outcome = c.validate(execution, [[0,0],[1,1]])
    assert outcome["validation"]["success"] is False
    assert outcome["ilogic"]["tier"] == "REFUTED"
    forged = dict(outcome)
    forged["validation"] = dict(outcome["validation"], success=True)
    assert "genesis_forgery" in verify_epistemic_genesis(forged)

def test_cce_resource_limits_are_bound():
    c = CCE()
    method, source, _ = c.generate_cognition("limits", sha(b"f"))
    execution = c.execute(method, source, [[0]])
    assert execution["constraints"]["timeout_ms"] == 5000
    assert execution["constraints"]["memory_mb"] == 256
    assert execution["constraints"]["kernel_isolation"] is False
