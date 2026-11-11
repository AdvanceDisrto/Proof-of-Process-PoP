# i™ / iBit Machine — observed local software run (2026-10-27)

This PR adds a **fail-closed evidence integrity gate**, not a claim that the whole proposal has shipped.

An independent local simulator package was executed outside GitHub and is available as the conversation artifact `ibt-run-tested.zip`. It is **not included in this PR**. Its 14 local pytest tests passed, and its end-to-end deterministic simulation produced a 3-of-3 signed witness aggregate, a 2-of-3 subset, simulated BPU clean/fault receipts, a test delegation certificate, a PoP self-sovereign receipt, and a signed master manifest. Those local results must be re-executed in an independently provisioned CI runner before being promoted as GitHub build evidence.

## Security corrections to original proposal

- Do **not** use pubkeys extracted from witnesses as independent trust pins. Out-of-band pins are required.
- Do **not** trust an unsigned or fabricated job output as proof of execution; the simulator witnesses a precommitted result hash.
- Do **not** grant ECC correction from a parity syndrome's Hamming weight; a correct decoder and minimum-distance argument are required.
- Do **not** use Ed25519 to encrypt Shamir shares. The proposed XOR placeholder leaks data and is disabled in the local simulator.
- Do **not** treat a timer with restartable in-memory state as a safe dead-man switch. No unattended disclosure is implemented.
- Do **not** treat witness wall-clock agreement as independent time attestation.
- Do **not** treat a per-host software-generated key as physically bound to a manufactured die.
- Do **not** assume a browser localStorage pin propagates across independent site origins.
- Do **not** label fabricated silicon or real TEE/energy measurements as delivered.
- Do **not** count metadata hashes as an MMR proof unless the MMR is independently recomputed.
- The suggested Python `pop_id` prefix operation is malformed when applied to a `sha256:`-prefixed digest; use the raw hex digest.
- Original PoP verification signs `receipt_sha256`-excluded data but mistakenly verifies `signature`-included data; this is a signature bug.

## This PR

`tools/ibit_gate_check.py` verifies the SHA-256 and byte lengths of the artifacts referenced by an iBit master receipt. It **deliberately does not accept signatures** or claim a process was executed. The output says `INTEGRITY_CHECK_PASSED_SIGNATURE_UNVERIFIED`, never `VERIFIED_PROCESS`. An Ed25519 verifier with out-of-band trust pins must be a separate gate.

**Gate**: `ACTION_REQUIRED`. No hardware, TEE, energy measurement, Genesis ceremony, Bitcoin, external audit or production whistleblower deployment is claimed. Review only; do not merge or deploy.
