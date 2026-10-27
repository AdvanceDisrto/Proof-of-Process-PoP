# 🧾 i™ ALIL Receipt Auto-forward Router and Privacy Shield (review build)

## What actually works

An independent source-signed, strict JSON input placed in `runtime/inbox/` is checked against an **externally supplied and pinned** Ed25519 source registry. On success, the local receipt machine emits an Ed25519-signed, SHA-256-domain-separated hash-chained **ingestion receipt**, and spools an event for optional HTTPS transport. Signature validation proves key control and byte integrity **only**; `underlying_real_world_event_verified=false` and `settlement_authorized=false` are immutable in this reference implementation.

`--watch` polls every 5 seconds and processes *supported JSON receipt events*; does not monitor users' private email without separately configured consent and a source adapter. Preserves every original inbox file. Rejects unknown keys, bad signatures, unauthorized source identities, duplicate JSON keys, floats, tampering, replay/conflicting receipt IDs. Stops processing if a ledger record is altered.

### Create local throwaway development keys outside source control

```bash
python -m alil.dev_fixture --root runtime
```

This explicitly creates a **demo-only** signed receipt in `runtime/inbox`. Never use these ephemeral keys for actual independent attestations. For Docker on Windows, run once outside Docker and ensure volume file permissions permit UID 65532 to read keys and write the spool.


Use `python -m alil.router --root runtime --registry runtime/registry.json --registry-sha256 PINNED_DIGEST_FROM_INDEPENDENT_CHANNEL --machine-key runtime/machine.key --watch` to run locally. Use `--forward-url https://YOUR-APPROVED-RUNTIME/receipts` and set `INNOVULIS_RECEIPT_TOKEN` securely **only after** controlling and validating that receiver; otherwise records stay in the local outbox. Receiver must implement idempotency and verify the machine signature against its own pinned public registry. **HTTP 2xx is only transport acknowledgment, not remote processing proof.**

The GitHub workspace is not a live runtime. There is no configured iNNOVULIS endpoint, independent signer key or live traffic wired by this PR.

### ZKP + arbitration boundaries

`zkp/PretextualShield.circom` is a privacy-preserving bounded **heuristic comparator design**; a proof can attest to an arithmetic relation, not criminal guilt or truth of the input. `contracts/ReceiptArbitrator.sol` is an experimental 2-of-3 guarded *review registry pause*; no authority over external funds, no chain deployment, no verifier contract yet. Groth16 setup, audit and verification keys are required before production.

Local: `python -m pytest -q tests/test_alil_router.py` (Python cryptography/pytest); `go run go/hashproof/main.go < original.json`; circuit `cd zkp && npm install && npm run compile` with network access. No dependencies are fetched at runtime for the Python intake worker.

**SECURITY:** do not commit keys, registry with private user identities, case records, proof witnesses, personal messages or actual receipts. Add `runtime/` to `.gitignore` (included).

### Docker Desktop (local only)

```bash
# after configuring local runtime/ keys, inbox and permissions:
docker compose -f alil/compose.local.yml up --build -d
docker compose -f alil/compose.local.yml logs --tail=100
```

The Docker service exposes **zero ports**, watches only a local mounted inbox and signs local intake receipts. Production endpoint enrollment, non-exportable HSM/YubiKey signing, certificate pinning, outside anchoring, IAM controls, key rotation, real incoming app connectors and host deployment are not included.

### Independent verifier (no private machine key needed)

```bash
python -m alil.verify --records runtime/records --machine-public-key-hex YOUR_EXTERNALLY_PINNED_32_BYTE_ED25519_PUBLIC_KEY_HEX
```

This verifies the intake-machine's Ed25519 signatures and hash-chain continuity. It does not verify the original source receipts unless source registry and originals are also supplied, and it cannot establish underlying legal facts, physical reality or immutability without a separately witnessed external anchor.

### Pinned registry requirement

The router **refuses to start without** a SHA-256 digest of the Ed25519 source trust registry supplied out-of-band through `--registry-sha256`. Do not trust a fingerprint provided by the same email, QR carrier, or incoming receipt being verified. In Docker, set the `REGISTRY_SHA256` environment variable before starting Compose. This still does not replace an independent hardware signer or continuous revocation-feed updates.

