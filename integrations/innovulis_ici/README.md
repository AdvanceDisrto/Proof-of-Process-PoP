# iNNOVULIS™ iCi v0.2 — three-artifact software cryptographic spine

Tracks: **iGFX iRAW**, **iGXP 4096**, **iSC 4160** with a signed, externally keyed sequence chain.

Run: \`bash run_ici.sh\` (Rust stable + cargo-fmt; requires access to crates.io to resolve dependencies).

Corrects the supplied source: iRAW XOR applies to an indexed byte; signatures use one signing key and a separately supplied trusted verifying key; receipt signatures cover **previous and next** chain roots, artifact type, sequence, tick, digest and CIH pending status; the chain root computation is recomputed independently. iGXP and iSC format parsers validate complete fixed lengths, payload length, BLAKE3 digest, and zero padding. Verification of a receipt **alone** does not independently verify its artifact bytes: use \`verify_attached_artifact\` too.

The CLI generates **ephemeral software** signing keys for fixtures. The public key is written to \`build_ici/trusted_pubkey.hex\`, never substituted for a production trust anchor. Chronos ticks are caller-provided, not authenticated hardware timing. The iSC and iGXP formats are **v0.2 reference layouts** and require reconciliation with the existing DEPC/PoP hardware format contracts before production adoption. BLAKE3 chaining is not a Merkle mountain range or remotely anchored ledger; it is a sequential hash chain. This is **not** C2PA certification, physical sensor proof, hardware attestation, irreversible storage, or CIH acceptance.

All receipts say **PENDING PROOF OF PROCESS — CIH VERIFICATION**. No automatic promotion to verified.

No Telegram bot, bitwitness server, or CIH production endpoint is modified by this PR. Only an isolated, importable Rust crate and the opt-in CI workflow are introduced.
