# SSN Privacy Boundary

The Proof-of-Process SSN boundary is a local, fail-closed privacy control.

## Contract

1. Raw SSN-shaped values are detected at the local boundary.
2. Each match is replaced with a random opaque token.
3. The raw value is authenticated-encrypted with AES-256-GCM.
4. Encryption keys are derived per execution with HKDF from a 32-byte master secret.
5. Token commitments use HMAC-SHA-256 rather than a public raw-value hash.
6. The model-facing payload contains only sanitized text.
7. Any later reveal requires a signed LineReceipt whose intent hash binds the exact execution and token.
8. A reveal receipt does not prove identity, consent was uncoerced, TPM custody, or provider behavior.

## Important truth boundary

This is NOT a formal zero-knowledge proof system. It is an authenticated-encryption/tokenization boundary. The implementation can enforce the intended local call path, but it cannot mathematically prove that every other process, logger, browser extension, or unrelated application path is incapable of accessing raw input.

Raw SSNs must never be committed to Git, CI logs, test artifacts, browser telemetry, or provider prompts.

timestamp_utc_ns and other software clocks are software-clock evidence, not physical picosecond measurement.
