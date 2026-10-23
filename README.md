# i™ Proof of Process (PoP)

**Truth is Processing Made Permanent. The Receipt is the Judge.**

Executable, fail-closed evidence architecture binding declared human/machine process evidence into independently signed domain receipts and an aggregate Merkle commitment.

## Parallel Proof of Process

Independent domains execute concurrently and sign their own results. The aggregator verifies signatures and receipt IDs, constructs a domain-separated binary Merkle tree, and emits either `VERIFIED_PROCESS` or `INCOMPLETE`.

The aggregate proves cryptographic inclusion/integrity of the listed receipts. It does **not** prove simultaneity, picosecond physical timing, hardware independence, physical energy, fabrication, or the truth of payload claims that lack independent evidence.

## Truth boundaries

- Software timestamps are nanosecond-valued clock observations, not physical picosecond measurements.
- Ephemeral Ed25519 keys prove possession for a run, not hardware binding. Production identities require a stable external signer/HSM/TPM evidence path.
- Energy is `ACTION_REQUIRED` with a null value when hardware counters are unavailable or ambiguous.
- PPSO physical promotion requires explicit traceable measurement evidence.
- The reality manifest is a signed taxonomy. Its hash fingerprints the manifest, not the universe.
- Canonical serialization currently uses a deterministic JSON subset and is not claimed as strict RFC 8785 JCS.

## Run

```bash
python -m pip install -r requirements.txt
make build-all
```

Outputs include `PARALLEL_MASTER_RECEIPT.json` and `MASTER_REALITY_LEDGER.json`. CI uploads them as evidence artifacts.

## iBare portable receipt core

`baremetal/` contains a small C receipt core designed to be portable across
x86_64, ARM64, ARM32, and RISC-V builds. The cryptographic core has no libc
dependency and is compiled in CI with `-ffreestanding -fno-builtin`.

The host adapter is intentionally separate: on Linux it can observe whether
`/dev/tpm0` or `/dev/tpmrm0` exists, but **device presence is not TPM
attestation**. A real TPM quote/signature must be supplied by a platform
adapter before a receipt can claim hardware-rooted evidence.

Build and self-test:

```bash
make test-ibare
```

This verifies the SHA-256 known-answer vector, deterministic receipt payload
construction, and both freestanding object compilation and the host adapter.

iBare reports `VERIFIED_PROCESS (Software)` for its generated software receipt
and keeps `Physical Gate: ACTION_REQUIRED` until independently measured
hardware evidence is supplied.
