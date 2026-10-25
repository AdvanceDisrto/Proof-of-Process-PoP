from fabric_topology_validator import FabricState, RouteEvidence, TelemetryPayload, validate_fabric_packet

def packet():
    return TelemetryPayload("8f3c-test", True, True, True)

def test_normal_route_verifies():
    assert validate_fabric_packet(packet(), physical_route_compromised=False) == FabricState.VERIFIED_PROCESS

def test_cable_cut_fails_closed_pending_without_alternate_route():
    assert validate_fabric_packet(packet(), physical_route_compromised=True) == FabricState.PENDING

def test_unattested_alternate_route_is_quarantined():
    route = RouteEvidence("alt-1", True, False)
    assert validate_fabric_packet(packet(), physical_route_compromised=True, alternate_route=route) == FabricState.QUARANTINED

def test_authorized_attested_alternate_route_can_verify():
    route = RouteEvidence("alt-1", True, True)
    assert validate_fabric_packet(packet(), physical_route_compromised=True, alternate_route=route) == FabricState.VERIFIED_PROCESS

def test_bad_origin_signature_is_quarantined():
    p = TelemetryPayload("8f3c-test", False, True, True)
    assert validate_fabric_packet(p, physical_route_compromised=False) == FabricState.QUARANTINED

def test_missing_tee_is_action_required():
    p = TelemetryPayload("8f3c-test", True, False, True)
    assert validate_fabric_packet(p, physical_route_compromised=False) == FabricState.ACTION_REQUIRED
