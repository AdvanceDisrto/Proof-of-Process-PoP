#!/usr/bin/env bash
set -euo pipefail
# Demo-only single-runner trusted setup: no public ceremony / no production security.
# Executed only inside CI, no private witness/zkey exported as artifact.
cd "$(dirname "$0")/.."
./node_modules/.bin/snarkjs powersoftau new bn128 12 build/unsafe_0000.ptau
entropy="$(head -c 48 /dev/urandom | od -An -tx1 | tr -d ' \n')"
./node_modules/.bin/snarkjs powersoftau contribute build/unsafe_0000.ptau build/unsafe_0001.ptau \
  --name="CI_SINGLE_PARTICIPANT_DEV_NOT_PRODUCTION" -e="$entropy"
./node_modules/.bin/snarkjs powersoftau prepare phase2 build/unsafe_0001.ptau build/unsafe_final.ptau
./node_modules/.bin/snarkjs groth16 setup build/PretextualShield.r1cs build/unsafe_final.ptau build/unsafe_setup.zkey
entropy="$(head -c 48 /dev/urandom | od -An -tx1 | tr -d ' \n')"
./node_modules/.bin/snarkjs zkey contribute build/unsafe_setup.zkey build/unsafe_dev_final.zkey \
  --name="CI_ONLY_NOT_A_CEREMONY" -e="$entropy"
unset entropy
./node_modules/.bin/snarkjs zkey verify build/PretextualShield.r1cs build/unsafe_final.ptau build/unsafe_dev_final.zkey
./node_modules/.bin/snarkjs zkey export verificationkey build/unsafe_dev_final.zkey build/DEV_ONLY_verification_key.json
./node_modules/.bin/snarkjs zkey export solidityverifier build/unsafe_dev_final.zkey build/DEV_ONLY_Verifier.sol
node scripts/create-dev-witness.mjs
node build/PretextualShield_js/generate_witness.js \
 build/PretextualShield_js/PretextualShield.wasm \
 build/dev-private-input-DO-NOT-UPLOAD.json build/dev-private-witness-DO-NOT-UPLOAD.wtns
./node_modules/.bin/snarkjs wtns check build/PretextualShield.r1cs build/dev-private-witness-DO-NOT-UPLOAD.wtns
./node_modules/.bin/snarkjs groth16 prove build/unsafe_dev_final.zkey \
 build/dev-private-witness-DO-NOT-UPLOAD.wtns build/DEV_ONLY_proof.json build/DEV_ONLY_public.json
./node_modules/.bin/snarkjs groth16 verify build/DEV_ONLY_verification_key.json build/DEV_ONLY_public.json build/DEV_ONLY_proof.json
node scripts/check-public.mjs
printf '\n*** DEVELOPMENT-ONLY GROTH16 PROOF GENERATED AND VERIFIED. NOT A TRUSTED SETUP. ***\n'

