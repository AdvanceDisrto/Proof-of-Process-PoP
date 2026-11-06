# AeGi Synthetic Ledger Acceptance

This experimental, standalone software module implements authenticated synthetic telemetry, a real Z3 policy check, Ed25519-signed receipts and blocks, an explicitly domain-separated **binary Merkle tree**, sequential block hashes, and Decimal bookkeeping-only demo credits.

It does **not** implement Homotopy Type Theory verification, a Merkle Mountain Range, energy metering, thermodynamic bounds, quantum computing, actual token minting, distributed consensus, real device capture, or a clinical/utility safety guarantee. A hash of a type-space label is not a HoTT proof; a fixed 32-byte root is not a fixed-size membership proof; a ledger hash is not a cryptographic signature. The mathematical check establishes only whether a bounded synthetic value satisfies the declared integer constraint.

This module is not wired into production CIH, QoW, PoP or ipQR endpoints. It is a separate acceptance candidate, designed to preserve the previously merged software baseline until reviewed.

CI: run the unittest module and execute the smoke. Keep the PR draft until reviewed; no deployment or automatic merge.
