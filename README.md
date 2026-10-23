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
