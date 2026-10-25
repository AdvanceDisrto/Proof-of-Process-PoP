from fabric_route_attestation import (
    ChainState,
    RouteAttestationValidator,
    RouteAuthorization,
    RouteReceipt,
)

ROUTE = RouteAuthorization(prefix="203.0.113.0/24", origin_asn=64500, max_length=24)
PAYLOAD = "sha256:patient-block-101"


def validator():
    return RouteAttestationValidator([ROUTE])


def receipt(**overrides):
    data = dict(
        route_prefix="203.0.113.0/24",
        origin_asn=64500,
        landing_station_id="LS-EU-WEST-01",
        landing_station_tee_attestation_verified=True,
        payload_hash=PAYLOAD,
        transit_witness_verified=True,
    )
    data.update(overrides)
    return RouteReceipt(**data)


def test_authorized_attested_route_verifies():
    assert validator().validate_alternate_route(receipt(), PAYLOAD) == ChainState.VERIFIED_PROCESS


def test_unauthorized_origin_is_quarantined():
    assert validator().validate_alternate_route(
        receipt(origin_asn=64501), PAYLOAD
    ) == ChainState.QUARANTINED


def test_authorized_route_without_landing_station_attestation_is_action_required():
    assert validator().validate_alternate_route(
        receipt(landing_station_tee_attestation_verified=False), PAYLOAD
    ) == ChainState.ACTION_REQUIRED


def test_payload_mismatch_is_quarantined():
    assert validator().validate_alternate_route(
        receipt(payload_hash="sha256:tampered"), PAYLOAD
    ) == ChainState.QUARANTINED


def test_missing_transit_witness_is_pending():
    assert validator().validate_alternate_route(
        receipt(transit_witness_verified=False), PAYLOAD
    ) == ChainState.PENDING


def test_route_origin_authorization_is_not_physical_transit_proof():
    result = validator().validate_alternate_route(
        receipt(transit_witness_verified=False), PAYLOAD
    )
    assert result != ChainState.VERIFIED_PROCESS
