# iNNOVULIS™ Acceptance Gates — Operator Protocol (2026-11-06)

## Current software evidence

- PoP PRs #56, #57, #58 merged; these are software implementation records, **not hardware certification**.
- AeGi synthetic smoke run #42273609955: 16/16 tests and signed synthetic blocks.
- Physical-to-QoW synthetic smoke run #42271563988: 12/12 tests, optical exact-PNG roundtrip.
- On main merge commit 872c1e9ccacc9dc52ea785c9b554abc4c3dc3f4b, generic pytest collection encountered absent `z3` and `qow` module; broad workflow run also encountered missing `torch`. The CI repair PR must pass on its own head and on a later merge commit before post-merge CI can be called healthy.

## Gate A — authenticated real device (PENDING, no device attached to GitHub Actions)

1. Inventory an actual physical sensor (manufacturer, exact model, serial, interface) and preserve **raw bus bytes**, register addresses, calibration and precision information, capture metadata, and host/device identity.
2. Use a suitable secure key boundary. **Microchip ATECC608A/B supports ECDSA P-256, not Ed25519.** Do not label an ATECC608 native signature `ed25519`. Either use a hardware implementation supporting Ed25519 or implement a versioned P-256 ECDSA verifier and carry an explicit signature algorithm in the evidence schema. No silent algorithm substitution.
3. Generate a nonce from a trusted challenge, bind it and a monotonic counter to the raw sensor bytes, and sign canonical bytes at the edge. Verify the device public key against a genuine provisioned identity/certificate or a documented operator-pinned key.
4. Physically compare sensor values against a traceable calibrated reference at multiple conditions; retain uncertainty, tolerance, instrument, and timestamp. Sensor calibration is independent of signing.
5. Run the CIH -> Z3 -> QoW -> PoP pipeline on captured bytes; an independent verifier replays the exact deterministic policy and signed ancestry. Reject stale/reordered/gapped or duplicated frames across **durable process restarts**.
6. Store a non-public operator-reviewed evidence package with bytes, signed frames, certificate/provisioning records, calibration records, exact program versions, and independent signatures. Do not expose sensitive identity or private keys.

**Promotion criterion:** real device, calibration, trust anchor and anti-replay evidence reviewed. A simulator payload with `source_tier=REAL_HARDWARE` is not sufficient.

## Gate B — printed-phone optical verification (PENDING)

1. Preserve the source signed receipt JSON and generated PNG, print settings (DPI, scaling, paper, printer model), and a hash of every printed image.
2. Photograph a real print with a smartphone: at least front-on, angled (20–30 degrees), partial shadow, lower contrast, and controlled blur. Preserve original camera image, EXIF where permissible, device model and test geometry.
3. Implement/test fiducial detection, perspective rectification, sampling calibration and robust bit-error correction. **Current `qow.ipqr.decode` accepts an exactly registered 2000x2000 PNG; `decode_physical_capture` is not implemented.** It is not acceptable to claim photo recovery from a generated PNG.
4. Verify signatures, pinned keys, hashes, formal policy verdict, CIH ancestry and PoP Merkle membership after optical decoding, with offline networking disabled. Verify known-negative tampered/occluded copies fail closed.
5. Report trial counts and per-condition decode success, false-accepts, sensitivity to lighting, and user-facing failure messages; avoid absolute guarantees.

**Promotion criterion:** demonstrable successful real camera images and independent offline cryptographic verification under documented test conditions.

## Gate C — mathematical HoTT / typed invariants (PENDING)

1. Define an exact formal proposition and trusted axiom set in a version-pinned dependent type proof checker (e.g. Lean, Coq or Agda).
2. Check proof terms and the axiom dependencies in CI with independent replay. A SHA-256 of a `domain_universe` string is an identifier, not a HoTT proof, equivalence or univalence certificate.
3. Prove the specific adapter properties claimed: provenance-bound transitions, type-safe state encodings, and rejection of invalid proof terms. Do not infer proofs of AI output truth or absence of hallucinations from these lemmas.
4. Publish source and machine-checked result plus `does_not_prove`. **No typed proofs of the actual AeGi production adapters have been verified.**

## Gate D — thermodynamic QoW metering (PENDING)

1. Identify actual calibrated energy meter and instrumented computation boundary; sample real voltage, current and time or energy readings with recorded uncertainty.
2. Synchronize the measurement scope to the task execution and measure idle baselines, including regulator/PSU overhead and cooling where relevant.
3. Independently verify joules = integral of measured watts over elapsed seconds, time-bound the receipts, and report uncertainty and reproducibility over multiple runs.
4. Do not claim Landauer-optimality or physically necessary energy costs merely from arbitrary workload credits. **Current demo `9.3750` is bookkeeping, not physical token issuance or measured joules.**

## Gate E — CI / Render (PARTIAL)

- Require the generic PoP suites to install dependencies declared in `requirements.txt` and the specialist QoW suite to execute with the exact pinned sibling checkout.
- Record separate PASS / FAIL / SKIP; generic tests may skip a missing sibling module only when the dedicated cross-repository workflow actually runs that module and PASSES on the same candidate revision.
- Render origin `https://proofofprocess.onrender.com/health` returned HTTP 200 in the last keepalive run; custom domain `https://www.proofofprocess.online/health` returned HTTP 404. **This is a live-routing incident, not a test bug; retain failure until the intended custom domain route actually returns success.**
- `confirmed-anchor-update.yml` runs on authenticated `repository_dispatch` with explicit CONFIRMED payload; no dispatch, callback, or GitHub workflow alone establishes blockchain settlement. Never mark Bitcoin verification without independently verified chain evidence.

## Final acceptance policy

`ACCEPT_MERGED_SOFTWARE_INTEGRATION` is not `ACCEPT_REAL_PHYSICAL_HARDWARE`, `ACCEPT_PHYSICAL_CAMERA`, `ACCEPT_HOTT_FORMAL_PROOFS`, `ACCEPT_THERMODYNAMIC_METERING` or `ACCEPT_GLOBAL_PRODUCTION`. No promotion based only on textual claims, mocked statuses, self-reported screenshots, or ephemeral CI-only keys.
