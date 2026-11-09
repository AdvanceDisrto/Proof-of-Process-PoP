# Release gate contract v1.0

## Machine-readable schema

`unified_i.physical.record_report` returns `i-physical-acceptance/v1`, exactly 15 named gate objects. By default every gate is `PENDING`. Only three **software** HDL checks (`RTL_SIMULATION`, `RTL_LINT`, `GENERIC_SYNTH`) can be annotated `PASSED_SOFTWARE_ONLY` with log hash. The report always sets `physical_acceptance=false` and `production_ready=false` until a **separate future release** introduces independently validated acceptance code.

Current generated sample evidence may include hashes from this runner, but these do not establish that any physical device was touched. The state object cannot be overridden by a caller requesting `PASS`.

## Evidence for physical acceptance (not automated here)

For each device: independently collected serial/USB/I²C identity, exact firmware/bitstream SHA-256, build environment and pin mappings, verified hardware public key and certificate chain, signed operator observation, raw scope/logic-analyzer and sensor calibration logs, source-code/bitstream lineage, reproducible physical tests. Include the instrument's own calibration record, physical photo/video as auxiliary evidence (not sole proof), chain-of-custody and time basis.

## Replay/counterfeit tests

- Old authentic receipt on new subject must be rejected by subject and freshness policy.
- Duplicate nonce or receipt-id on the same subject must not be silently accepted as new evidence.
- Empty/missing witness set or suspicious collusion must fail the independent witness policy.
- Compromised signing key must be blocked under the verifier's revocation and log policy.
- A 2026 receipt cannot be used as evidence of a 2027 live physical measurement without new attestation.
- `SAT` never upgrades a free-text claim to verified factual truth.
- A `SIGNATURE_VALID` state never authorizes clinical intervention, privileged execution, or court filing.
- Optical code can carry a signed capsule but cannot become an untrusted arbitrary app execution channel.

## Source tiers

- `SYNTHETIC` = generated test fixture; no hardware.
- `SOFTWARE_OBSERVED` = runner measured the software's actions only.
- `HARDWARE_UNATTESTED` = device bus read; origin may be spoofed.
- `HARDWARE_SIGNATURE_VERIFIED` = P-256 crypto verified; hardware identity still needs separate evidence.
- `EXTERNAL_WITNESS_REVIEWED` = reserved for future independently verified anchor and signatures; not issued by current demo.

Physical acceptance is not produced by tests that cover only simulation or generic synthesis. Protection against side-channel attacks, quantum proofs, deepfake immunity and absolute truth are outside this implementation and cannot be inferred from its success.
