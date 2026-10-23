from main import health, reality_manifest, truth_boundary


def test_public_manifest_fails_closed():
    data = reality_manifest()
    assert data["master_manifest_hash"] is None
    assert data["seal_state"] == "UNCLAIMED / NOT SEALED"
    assert data["physical_gate"] == "ACTION_REQUIRED"
    assert "physical silicon fabrication" in data["does_not_prove"]


def test_truth_boundary_is_explicit():
    data = truth_boundary()
    assert data["fabricated_evidence"] is False
    assert data["physical_gate"] == "ACTION_REQUIRED"
    assert data["the_central_rule"] == (
        "The receipt can record reality; it cannot manufacture reality."
    )


def test_health_contract():
    assert health()["status"] == "ok"
