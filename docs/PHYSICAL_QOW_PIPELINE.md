# iNNOVULIS physical-sensor → CIH → QoW → PoP → ipQR

## Acceptance scope

This workflow exercises a **synthetic, software-only** signed sensor event, a local CIH state commitment and Ed25519 signature, a formally specified storage-temperature policy, a fresh Z3 recheck, a signed QoW receipt, PoP's actual signed DomainReceipt and domain-separated Merkle aggregator, and an exact generated radial PNG decoding round trip.

1. A synthetic sensor event contains a monotonic sequence, nonce, centi-Celsius measurement and Ed25519 signature. A pre-trusted public key is pinned. This establishes **simulated device identity**, not real device identity, calibration or tamper-resistant measurement.
2. A **local CIH adapter**, not a deployed CIH, checks the signature, rejects replay/gaps in one process, hashes the input event and signs a running state commitment.
3. QoW represents a **non-medical** demo policy: measured centi-Celsius must be between 200 and 800. Z3 checks the declared assertion under axioms binding the synthetic measurement. The resulting signed QoW body binds the exact sensor hash, CIH record hash, and policy hash.
4. The PoP adapter accepts only authenticated PROVEN_TRUE QoW receipts with a fresh independent Z3 solver call. Its existing DomainReceipt and canonical domain-separated Merkle aggregator generate and sign the PoP evidence chain.
5. The ipQR carrier is itself Ed25519-signed and includes the QoW receipt plus PoP master/domain identifiers, Merkle root, and evidence hashes. The decoder checks the generated PNG; it does NOT accept a real phone photo or certify a print.

The CI tests require correct signatures and reject modified sensors, an incorrect pinned key, event replay, an event-sequence gap, a corrupted CIH commitment, out-of-policy synthetic temperature, a validly re-signed but incorrect hypothesis, a corrupted PoP root, and a forged optical carrier.

**This is not a pharmaceutical or clinical dose authorization system.** Sensor measurement authenticity in the physical world, hardware-secure keys, calibration traceability, trusted timestamps, independent witness quorums, production CIH replay persistence, real-world device transport, optical paper and camera tests, FDA validation, TEE, ZK and RFC 3161 remain NOT VERIFIED.

## Run

The workflow checks out exactly the QoW main merge commit 3ee40f7de19070017595d4ff580eb6b978b413c1; workflow failure occurs if QoW cannot be fetched.

- PYTHONPATH=.:_qow_checkout python -m unittest discover -s tests -p test_physical_qow_pipeline.py -v
- PYTHONPATH=.:_qow_checkout python -m integrations.physical_qow_pipeline

GitHub Actions persists JSON signed evidence and a radial PNG as physical-qow-pop-ipqr-evidence. Outputs are fresh with ephemeral test-only signing keys every CI run. **Do not pin generated public keys from tests as production trust anchors.**

## Controls

This work is proposed in PoP PR #57 for review. No automatic merge, production deployment, sensor activation, or patent prosecution action.
