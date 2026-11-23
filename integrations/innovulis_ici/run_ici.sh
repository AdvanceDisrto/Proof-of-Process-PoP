#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
cargo --version
rustc --version
cargo generate-lockfile
cargo fmt --all -- --check
cargo test --locked --all-targets
cargo build --locked --release
./target/release/innovulis_ici self-test
PK="$(cat build_ici/trusted_pubkey.hex)"
./target/release/innovulis_ici verify-iraw build_ici/DSC_0001.iraw "$PK"
./target/release/innovulis_ici verify-igxp build_ici/igxp_0001.bin
./target/release/innovulis_ici verify-isc build_ici/isc_0001.bin
./target/release/innovulis_ici verify-chain build_ici/ici_attestation_chain.json "$PK"
echo 'ICI_ALL_THREE_SOFTWARE_GATES_PASS'
