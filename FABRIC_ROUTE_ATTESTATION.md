# Fabric Route Attestation Protocol

The protocol resolves the boundary between a topology reroute and a trusted
physical route claim.

Primary cable cut -> PENDING.

An alternate route can only advance through separate evidence gates:

1. Route authorization — the route prefix and origin ASN are authorized by a
   trusted route-origin registry. Production integration must consume an actual
   RPKI/RTR validation service or equivalent cryptographically verifiable source.
2. Landing-station attestation — the receiving station supplies a verified
   hardware-rooted quote. A string named "TEE signature" is not sufficient.
3. Payload integrity — the payload hash remains identical across the transition.
4. Physical-transit witness — an independently verified witness must attest that
   the designated physical path was observed.

Only all four gates yield VERIFIED_PROCESS.

RPKI/ROA authenticates route-origin authorization. It does not prove that a
specific packet physically traversed a specific submarine cable.

A landing-station TEE quote attests a platform/workload measurement when
independently verified; it does not by itself prove the historical path of a
packet.

The transit_witness_verified field is therefore a software boundary. No real
subsea transit proof is claimed until external infrastructure or physical
instrumentation produces a verifiable witness.

Synthetic CI scenarios:

- Authorized + TEE + matching payload + transit witness -> VERIFIED_PROCESS
- Unauthorized origin -> QUARANTINED
- Authorized route, no landing-station attestation -> ACTION_REQUIRED
- Payload hash mismatch -> QUARANTINED
- Authorized + TEE + no physical-transit witness -> PENDING

A green CI run verifies this deterministic state machine only. It does not claim
a live submarine cable, landing station, RPKI feed, TEE, or physical transit was
observed.
