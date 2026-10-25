# Proof-of-Process Fabric

## Test-build boundary

The Fabric maps physical network topology to a fail-closed evidence state. It does not turn the existence of submarine cables into proof that a particular packet traversed a particular physical route.

| Condition | State |
|---|---|
| Valid signed/attested packet on an uncompromised route | VERIFIED_PROCESS |
| Physical route disruption with no alternate-route evidence | PENDING |
| Alternate route exists but is not authorized/attested | QUARANTINED |
| Missing physical/TEE evidence | ACTION_REQUIRED |

## Physical mapping

- Landing station: intended physical evidence boundary, not automatically a TEE.
- Fiber route: physical transport/topology, not a cryptographic proof.
- Repeater: optical/electrical infrastructure; this software does not claim every repeater re-verifies a PoP hash.
- Cable cut: topology disruption that causes the PoP software gate to fail closed.
- Alternate path: promotion requires an authorized route identity plus independent attestation evidence.

The phrase "the physical light pulses are the proof" is intentionally not used as a software claim. Light carries data; cryptographic receipts and independent physical evidence establish what can actually be asserted.

## Evidence boundary

The repository already distinguishes physical transport evidence from actual node deployment and hardware evidence. The global physical gate remains ACTION_REQUIRED.

## Build test

Run: pytest -q tests/test_fabric_topology_validator.py

A green result proves the deterministic state-machine behavior, not the existence or integrity of a real subsea cable, landing station, TEE, or alternate physical route.
