"""Proof-of-Process Fabric topology gate."""
from dataclasses import dataclass
from enum import Enum

class FabricState(str, Enum):
    VERIFIED_PROCESS = "VERIFIED_PROCESS"
    PENDING = "PENDING"
    QUARANTINED = "QUARANTINED"
    ACTION_REQUIRED = "ACTION_REQUIRED"

@dataclass(frozen=True)
class TelemetryPayload:
    payload_hash: str
    origin_signature_valid: bool
    tee_attestation_verified: bool
    ots_proof_present: bool

@dataclass(frozen=True)
class RouteEvidence:
    route_id: str
    authorized: bool
    attestation_verified: bool

def validate_fabric_packet(packet: TelemetryPayload, *, physical_route_compromised: bool, alternate_route: RouteEvidence | None = None) -> FabricState:
    """Fail closed on route disruption until an authorized attested alternate route exists."""
    if physical_route_compromised:
        if alternate_route is None:
            return FabricState.PENDING
        if not alternate_route.authorized or not alternate_route.attestation_verified:
            return FabricState.QUARANTINED
    if not packet.origin_signature_valid:
        return FabricState.QUARANTINED
    if not packet.tee_attestation_verified:
        return FabricState.ACTION_REQUIRED
    if not packet.ots_proof_present:
        return FabricState.ACTION_REQUIRED
    if not packet.payload_hash:
        return FabricState.QUARANTINED
    return FabricState.VERIFIED_PROCESS
