# iNNOVULIS™ Energy Processing Unit (EPU) v1 — offline verification reference

**Status:** PENDING PROOF OF PROCESS — CIH VERIFICATION. **No physical meter or accredited laboratory relationship has been verified in this package.** The supplied sample signatures use PUBLIC, fixed, software-only test keys, and the calibration records are **synthetic**. Do not cite them as physical energy observations, real certificates, or proof of national standards compliance.

## Why this implementation is narrower than a marketing claim

- **Allocated**: verifier loads a trusted, independently provisioned capacity/domain/priority policy. It *recomputes* first-priority-then-residual allocation and uses Z3 to prove that **the fixed concrete allocation instance** cannot violate those rules. It recalculates SHA-256 `constraints_hash` and `proof_hash` from the independently provisioned policy and the concrete instance. It does **not** claim a general universal resource-allocation theorem. `UNSAT` here means **no counterexample with the checked assignments**, not evidence about all real-world energy flows.
- **Consumed**: registration and execution are Ed25519-signed with a meter key pinned outside the receipt. Calibration is separately Ed25519-signed with a lab key pinned outside the receipt; the meter registration binds its SHA-256 certificate digest. The lab *label* `ISO17025` is not independent evidence of accreditation. Real certificates and accreditation registries require separate independent checks.
- **Meter accuracy**: calibration interval checked against the **job start**. Expired accepted only as `METERED_STALE`, explicitly nonbillable. Self-report cannot become `METERED` even with valid meter signature.
- **Attribution**: `DEDICATED_CIRCUIT` requires a signed dedication flag, `RAPL_PER_JOB` requires independently expected scope digest, and `DIFFERENTIAL` requires recoverable baseline samples and nonzero uncertainty. Those conditions are necessary but insufficient to prove isolation, scoping, baseline stability, or energy correctness on physical hardware.
- **Raw samples**: raw `mW` integer-string power readings and monotonic millisecond timestamps are hashed with real BLAKE3/JCS, loaded from the artifact store, and integrated by trapezoids. Exact `joules_integrated` and `consumption.joules` must match reconstruction. This is *meter observation*, not ground-truth proof.
- **Statuses**: `METERED`, `METERED_STALE`, `NOT_MEASURED`; **`CLAIMED` is rejected**. `ESTIMATED_FROM_UTIL`/`NONE` always produce `NOT_MEASURED` and a null Joules field. `derivation.status` is `NONE`, always.
- **π and τ**: verifier must receive expected bit order `π`, one-time challenge nonce and expected `τ` from an independent provisioning path. It must never reconstruct the expected contract from the receipt being checked. It separates `PI_CONTRACT_MISMATCH`, `TAU_CHALLENGE_MISMATCH`, `REPLAYED_CHALLENGE`, and `CONFIG_MISSING_PI_TAU` so operators don't suppress security warnings because of a provisioning fault. This is a standalone software-binding proof; it does not verify physical signal acquisition.

## One-command test

```bash
python -m pip install -r requirements.txt
bash run_epu.sh
npm install --no-audit --no-fund
npm test
npm run build
```

Run from `integrations/epu`. Python runs T1–T6, π/τ six checks, extended fault tests, Z3 concrete allocation checks, deterministic signed vectors and positive/negative independent validation. Node tests same signed vectors with **real** `@noble/hashes` BLAKE3 and `@noble/curves` Ed25519; RFC8785-JCS is performed with the `canonicalize` library (test vector numeric domain uses safe integers, Decimal joules are strings). `npm run build` generates `build/verifier.html`, a **standalone, offline, no-remote-scripts file**. The bundled library code is included in the HTML file, not downloaded when it is opened.

Offline verifier workflow: obtain a trusted JSON configuration from the operator (separate from the prover), paste that and the receipt bundle into the resulting `verifier.html`, then run verification. The test vectors include `trusted_demo_config` only for repeatable demonstration, never as an acceptable real-world trust anchor.

## Energy arithmetic

Each sample artifact is a JSON object of this form:

```json
{"unit":"mW","samples":[[0,"1000"],[210,"1000"],[420,"1000"]]}
```

Trapezoidal integration gives exactly `0.420000000` J for the **synthetic** 420 ms power trace (1000 mW across the whole interval). `sample_rate_hz` is declared separately and must be validated against real acquisition hardware before physical acceptance. Values are plain integer mW; no conversion from elapsed time *alone* is allowed. The differential method separately subtracts a recovered baseline time series and includes a nonzero uncertainty field.

## Hardware and manufacturing acceptance remains open

The previous conversation described physical printer, INA226, secure element and Arty A7 results. This EPU PR does not establish those physical outcomes: an INA226 driver test is not a traceable calibration certificate, and a chip label or test key is not a verified silicon-root signature. Physical test requirements: instrument a **dedicated** known-reference load; capture raw time-series samples and meter register settings; independently verify meter ID, calibration certificate issuer and expiration; compare integrated Joules with a traceable reference and uncertainty; capture reproducible full CIH receipt chain and independently validate the signer/clock boundary.

Cryptographic signatures prove control of keys and tamper evidence; they do not independently prove meter accuracy, calibration issuer accreditation, physics or semantic truth. **Allocated ≠ consumed ≠ derived.**
