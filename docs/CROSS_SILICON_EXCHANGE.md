# iRECEIPT Cross-Silicon Development Exchange

Three separate GitHub Actions jobs exchange signed JSON and evidence bytes across native runner architectures:

1. **CPU origin** (ubuntu-24.04, x86_64) produces a signed intent observation, plaintext evidence, and an ephemeral public key.
2. **Edge verification** (ubuntu-24.04-arm, arm64) independently recomputes the payload digest and checks the origin Ed25519 signature, then signs its verification observation referencing the origin receipt ID.
3. **CPU final** (ubuntu-24.04, x86_64) independently verifies both signatures, both evidence byte digests, the parent link, and the edge-verification claim; it exports an assessment artifact.

Use GitHub Actions workflow `iRECEIPT Native Cross-Silicon Exchange`. No secrets or production private keys are required. Keypairs are ephemeral **development** keys. Public keys transfer alongside receipts via workflow artifacts; they are NOT independently enrolled trusted operator/device identities. This tests cross-architecture serialization and signature compatibility, not sovereign production trust or trusted device attestation.

The envelope uses deterministic Python JSON (`ensure_ascii=True, sort_keys=True, separators=(',',':')`), SHA-256 and Ed25519 with protocol domain separation. **It is not RFC 8785 JCS.** ESP32/MCU or independent Rust/C/JS implementations must implement and test identical canonical bytes before compatibility can be claimed.

**Not established:** true physical device identity; independent KMS/HSM signer; genuine GPU inference; NPU/MCU execution; real printer observation; ML-DSA; Bitcoin anchoring; real-time production deployment; CPU/GPU/MCU performance benchmarks. Do not use any receipt by itself to actuate a high-voltage device or bypass independent safety systems.

**Production gate:** Existing authoritative iTensor LIVE root and externally pinned operator policy remain mandatory. Never replace those with the test keypairs used by this workflow. A passing CI job must report only `CROSS_ARCH_DEVELOPMENT_INTEGRITY_PASS`.
