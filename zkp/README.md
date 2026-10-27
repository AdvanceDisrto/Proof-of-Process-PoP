# i™ Evidence-Bound ZK Heuristic — SOURCE ONLY

No local Circom compiler or npm dependencies were available when this source was prepared; local circuit compilation, proving, witness testing and on-chain verification are **not yet demonstrated**. A dedicated GitHub CI job compiles if dependencies can be installed there. There is **no proof** that a criminal act occurred, no judge-equivalent action, and no entitlement to freeze third-party assets.

Private witness: penaltyBps (0..10,000), entropyBps (0..10,000), chargeStackCount (0..255), witnessSalt (high-entropy secret field element). Public inputs: Poseidon(4) commitment and `thresholdProduct` (0..2^36-1). Public output: `thresholdExceeded = (penaltyBps * entropyBps * chargeStackCount > thresholdProduct)`.

The resulting comparison is a HEURISTIC FLAG. It must never be equated to legal guilt, fraud, or an official determination of pretext. Independent signed evidence must bind the public commitment to a known context and the method's version. Without that binding, a prover can choose any private witness and generate a valid, meaningless flag.

`npm ci` needs a committed lockfile (not yet generated in this air-gapped environment). For review use `npm install --ignore-scripts` and then `npm run compile` in isolated CI. No trusted setup files, proving keys, verification keys or Solidity verifier are published as genuine.

If Groth16 is selected: before any mainnet use, run an independently auditable multi-party **phase-2 ceremony**, publish transcripts, validate with `snarkjs zkey verify`, and commission a security audit. Don't publish private inputs, salts or witness files.

## CI demonstration proofs and Solidity verifier

The GitHub Actions circuit job can run `bash scripts/dev-groth16.sh`: it creates **single-runner development-only** Groth16 ceremony files, proves a fabricated demo witness, checks the proof and an altered public output, and exports a Solidity verifier marked `DEV_ONLY_Verifier.sol`. No private witness, salt, proving key or toxic-waste-related files are included in the published CI artifact. This does **not** fulfill independent production multi-party setup, circuit auditing, authenticated real-world evidence, legal adjudication, or on-chain deployment.

