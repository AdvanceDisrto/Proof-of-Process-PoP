# i™ Master Build v2 — truth boundary

- Compiled `ipwa/verifier_bg.wasm` is a **1,665-byte SHA-256 WASM module** (not 342 KB).
- Its source is `ipwa/src/wasm_sha256.c` and the build uses clang wasm32, not Rust.
- Merkle and event digest operations can use this WASM, while **Ed25519 verification uses browser WebCrypto**.
- The independent trust registry is loaded separately from the evidence archive.
- `ipwa/archive.mjs` validates a bounded regular-file-only TAR/GZIP; rejects symlinks, paths with traversal, duplicate files, malformed checksums, decompression bombs.
- `schemas/` are structural validators only, not live eligibility / healthcare / sanctions / AML or TEE proof verification. The finance receipts in `receipts/` are unsigned and explicitly UNVERIFIED.
- `receipts/DNS_RECEIPT.json` records a desired IPFS target; this is not a DNS update or IPFS CID verification.
- No Bitcoin OTS/SPV verifier and no USB YubiKey/TEE validation are supplied.
- The shipped verifier remains fail-closed: **it never authorizes a disbursement or physical actuation**.
- No QR scanner, camera, actual phone-install or airplane-mode test has been certified.
- This is NOT production-ready or hardware certified; do not merge or deploy without owner approval.

Run `node --test tests/ipwa-verifier.test.mjs tests/ipwa-wasm-v2.test.mjs`. Structural schemas also need a JSON Schema Draft 2020-12 validator such as the separate local tests.
