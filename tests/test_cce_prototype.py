from tools.cce_prototype import CCE, verify_epistemic_genesis, sha, run

def test_cce_generation_hash_bound():
    c = CCE()
    method_id, source, synthesis = c.generate_cognition(
        "Find shortest path in a binary grid.",
        sha(b"base-attempt-failed"),
    )
    assert method_id.startswith("method-")
    assert synthesis["source_code_hash"] == sha(source.encode())
    assert synthesis["physical_gate"] == "ACTION_REQUIRED"

def test_cce_execution_verifies_success():
    c = CCE()
    method_id, source, _ = c.generate_cognition(
        "Find shortest path in a binary grid.",
        sha(b"base-attempt-failed"),
    )
    grid = [[0,1,0],[0,1,0],[0,0,0]]
    expected = [[0,0],[1,0],[2,0],[2,1],[2,2]]
    execution = c.execute(method_id, source, grid)
    outcome = c.validate(execution, expected)
    assert execution["exit_code"] == 0
    assert outcome["validation"]["success"] is True
    assert outcome["ilogic"]["truth_axis"] == "ESTABLISHED"
    assert outcome["ilogic"]["tier"] == "VERIFIED_PROCESS"
    assert verify_epistemic_genesis(outcome) == []

def test_cce_wrong_expected_output_refuted():
    c = CCE()
    method_id, source, _ = c.generate_cognition(
        "Find shortest path in a binary grid.",
        sha(b"base-attempt-failed"),
    )
    execution = c.execute(method_id, source, [[0,1],[0,0]])
    outcome = c.validate(execution, {"not": "the-answer"})
    assert outcome["validation"]["success"] is False
    assert outcome["ilogic"]["truth_axis"] == "REFUTED"
    assert outcome["ilogic"]["tier"] == "REFUTED"
    assert verify_epistemic_genesis(outcome) == []

def test_cce_boundary_is_honestly_labeled():
    c = CCE()
    method_id, source, _ = c.generate_cognition(
        "Find shortest path in a binary grid.",
        sha(b"base-attempt-failed"),
    )
    execution = c.execute(method_id, source, [[0]])
    assert execution["constraints"]["no_network"] is True
    assert execution["constraints"]["kernel_isolation"] is False

def test_cce_full_run_keeps_physical_gate_closed():
    r = run()
    assert r["physical_gate"] == "ACTION_REQUIRED"
    assert r["ilogic"]["attestation_axis"] == "UNATTESTED"
