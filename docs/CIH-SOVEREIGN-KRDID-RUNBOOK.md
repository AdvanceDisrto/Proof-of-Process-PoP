# iNNOVULIS™ CIH ΔiΔ — Sovereign local .krdid authentication

## What exists in this branch
- Identity authentication: **real Ed25519 request signatures** verified against a locally maintained, operator-enrolled `.krdid` public-key registry.
- Receipt signing: existing CIH node Ed25519 private key, stored locally in owner-restricted file; public key trust anchor remains pinned.
- Storage: **local SQLite**, with the signed receipt and the consumed nonce recorded in one transaction. No Auth0, JWT issuer lookup, Supabase service-role key, or internet access is required for the local issuance path.
- Freshness: timestamp within ±300 seconds of the node clock and a 128-bit random nonce; duplicate `krdid+nonce` is rejected (including after restart).
- Signature binds the `domain`, HTTP method, exact endpoint path, .krdid, timestamp, nonce and whole receipt request. A caller-provided public key is **never** accepted to establish identity. Keys must be enrolled by the trusted local operator.
- `GET /api/v1/health` reports `auth_provider: LOCAL_KRDID_ED25519`, local registry status, node signer, and SQLite status.
- `POST /api/v1/verify` verifies node Ed25519 receipt signature, but does NOT independently prove the factual claim, hardware-origin identity, mesh consensus, or immutability against host compromise.

**Proof tier:** local software-key verification and durable local DB transaction, not hardware-backed attestation or a globally replicated independent trust network. A single CIH host, disk, administrator and key can themselves still be single points of failure; a truly no-SPOF design requires independent nodes, separate root keys, recovery and authenticated replication.

## Windows — run on your existing local repository

Use a second PowerShell terminal. First, update the feature branch without merging:

```powershell
Set-Location "C:\Users\New Customer\Proof-of-Process-PoP"
git status
git pull --ff-only origin feature/innovulis-cih-sovereign-portal-20261110
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-cih-windows.ps1 -TestOnly
```

Generate local .krdid signing identity and enroll its public key in the local SQLite registry. It will **never** overwrite an existing identity:

```powershell
.\.venv\Scripts\python.exe -m cih_api.krdid init-local
.\.venv\Scripts\python.exe -m cih_api.krdid list
```

The private identity key goes under `%LOCALAPPDATA%\iNNOVULIS\CIH\local-krdid-identity.json`. It is a separate key from the CIH node's `signing-keys.json`. Never put either private key into the repository, browser code, tickets, or a chat.

Safely launch the node with its persisted signing keys and no external auth dependency using the companion Windows setup script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-cih-sovereign-windows.ps1
```

The script updates/rechecks the feature branch, runs tests, preserves existing private keys, verifies any listening server before stopping it, launches one new local backend process, executes an actual signed local HTTP receipt, and independently validates the node signature and SQLite write. No remote cloud registration or fake bearer.

Or, if a locally configured server is already running with both `CIH_ED25519_*` environment values and a registered identity, run:

```powershell
.\.venv\Scripts\python.exe -m cih_api.krdid smoke --url http://127.0.0.1:8000
```

Expect:
```json
{
  "status": "VERIFIED_PROCESS_LOCAL",
  "signature_verification": "SIGNATURE_VALID",
  "storage": "LOCAL_SQLITE_COMMITTED",
  "krdid": "local-test-node.krdid"
}
```

## Browser and hosted node boundary

On `artifactgptm.com`, the new UI generates a non-extractable **browser software** Ed25519 CryptoKey (stored in IndexedDB) and shows a command to enroll its public key on the trusted backend host. Enrollment is a separate out-of-band operator action; browser-generated private keys are not hardware attested. No public endpoint accepts arbitrary keys for automatic onboarding.

The existing public Worker gateway can forward the four explicit `X-Krdid*` headers, but **only the CIH backend checks the registry**. A hosted node needs a stable local disk or a replicated trust store, the CIH signing key pair, explicit operator enrollments, and a deployment review before issuing receipts. Render's default ephemeral filesystem is not sufficient for durable post-redeploy evidence. The local Windows machine and hosted node do not share trusted identities or receipt storage automatically.

## Untrusted or absent capabilities

- NO Auth0, JWT issuance, remote identity provider, or token bypass.
- NO accept-any-public-key authentication.
- NO simulated server signatures.
- NO automatic hardware proof from browser WebCrypto.
- NO independent Z3 truth adjudication.
- NO cross-node mesh agreement, recovery, replicated ledger, or single-point-of-failure elimination.
- NO automatic certification of scientific or legal conclusions.
- NO PR merge without user approval.
