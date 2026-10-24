from physical.attestation_router import Provider, route


def test_attested_provider_is_candidate_not_measured_pass():
    result = route(require_attestation=True)
    assert result["selected_provider"] == "io.net"
    assert result["status"] == "ELIGIBLE_FOR_ATTESTATION"
    assert result["physical_gate"] == "ACTION_REQUIRED"
    assert result["status"] != "MEASURED_PASS"


def test_no_attestation_provider_fails_closed():
    providers = (
        Provider("compute-only", False, "NONE", "COMPUTE_ONLY", "test"),
    )
    result = route(require_attestation=True, providers=providers)
    assert result["status"] == "ACTION_REQUIRED"
    assert result["physical_gate"] == "ACTION_REQUIRED"


def test_cost_only_compute_never_promotes_physical_gate():
    result = route(require_attestation=False)
    assert result["physical_gate"] == "ACTION_REQUIRED"
    assert "does_not_prove" in result
