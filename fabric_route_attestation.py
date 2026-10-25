"""Fail-closed route attestation for the Proof-of-Process Fabric.

Evidence layers are intentionally distinct:
1. Route authorization evidence.
2. Landing-station attestation.
3. Payload integrity.
4. Independently verified physical-transit evidence.

This module does not implement a live RPKI/RTR validator or manufacture a
subsea transit signature. Registry entries and witnesses are CI fixtures.
"""
from dataclasses import dataclass
from enum import Enum


class ChainState(str, Enum):
    VERIFIED_PROCESS = "VERIFIED_PROCESS"
    QUARANTINED = "QUARANTINED"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    PENDING = "PENDING"


@dataclass(frozen=True)
class RouteAuthorization:
    prefix: str
    origin_asn: int
    max_length: int


@dataclass(frozen=True)
class RouteReceipt:
    route_prefix: str
    origin_asn: int
    landing_station_id: str
    landing_station_tee_attestation_verified: bool
    payload_hash: str
    transit_witness_verified: bool


class RouteAttestationValidator:
    def __init__(self, authorized_routes: list[RouteAuthorization]):
        self.authorized_routes = tuple(authorized_routes)

    def _authorized(self, prefix: str, origin_asn: int) -> bool:
        return any(
            roa.prefix == prefix and roa.origin_asn == origin_asn
            for roa in self.authorized_routes
        )

    def validate_alternate_route(
        self, route_receipt: RouteReceipt, expected_payload_hash: str
    ) -> ChainState:
        if not self._authorized(
            route_receipt.route_prefix, route_receipt.origin_asn
        ):
            return ChainState.QUARANTINED

        if not route_receipt.landing_station_tee_attestation_verified:
            return ChainState.ACTION_REQUIRED

        if route_receipt.payload_hash != expected_payload_hash:
            return ChainState.QUARANTINED

        if not route_receipt.transit_witness_verified:
            return ChainState.PENDING

        return ChainState.VERIFIED_PROCESS
