# iNNOVULIS™ CIH ΔiΔ — Sovereign local .krdid authentication

## What exists in this branch
- Identity authentication: **real Ed25519 request signatures** verified against a locally maintained, operator-enrolled `.krdid` public-key registry.
- Receipt signing: existing CIH node Ed25519 private key, stored locally in owner-restricted file; public key trust anchor remains pinned.
- Primary storage: **local SQLite**, with the signed receipt, consumed nonce, and optional remote-replication queue entry recorded in one transaction. No Auth0, JWT issuer lookup, Supabase API key, or internet access is required for LOCAL issuance.
- Optional backup: Supabase PostgreSQL as a **secondary replica**, with a backend-only secret key, never as identity provider. Remote failure leaves the locally signed receipt intact with remote_replication_status=PENDING_RETRY. A confirmed remote insert returns REPLICA_ACKNOWLEDGED; no server credential returns NOT_CONFIGURED. Neither database is hardware-immutable.
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

## Optional Supabase replica: BUDDY project

Project: tkrxmdonmxpeockpbazl. No new public.receipts table is required. The existing protected public.cih_receipts table now uses requester_subject rather than the retired auth0_subject field. Applied SQL is preserved in docs/sql/cih-krdid-supabase-mirror.sql.

Row Level Security is enabled. anon and authenticated have no table privileges; service_role has SELECT and INSERT only. Supabase database administrators still have elevated access, so it is not a cryptographically immutable chain.

The publishable key cannot write into the protected receipt table. The preferred **local CIH → Supabase Edge** transport requires **no Supabase secret on Windows or GitHub**: the CIH node sends its genuine signed receipt to the already-deployed `strmkrd-signing/cih-mirror` endpoint. The Edge function verifies the receipt against an operator-enrolled CIH node public key in `cih_node_trust` and uses Supabase's existing server-held `SUPABASE_SERVICE_ROLE_KEY` (or a managed server-only secret) to write. Supabase Auth is not used. The previous direct PostgREST mode remains optional for separate server deployments.

From Windows on the existing feature branch:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-cih-sovereign-windows.ps1 -ConfigureReplica
```

The script selects the **signed Edge receipt mirror** without asking for a secret. It creates a real local signed receipt, verifies the CIH signature, and retries queued copies. The Edge mirror will still reject the request until the CIH NODE signing public key is explicitly enrolled in Supabase `cih_node_trust`. That trust registry currently has **zero enrolled keys**, and no automatic remote enrollment exists.

Check the local replica queue:

```powershell
.\.venv\Scripts\python.exe -m cih_api.replica status
```

Retry manually using the signed Edge transport (no secret on the client):

```powershell
.\.venv\Scripts\python.exe -m cih_api.replica sync --limit 100
```

Every CIH issuance returns storage_status=LOCAL_SQLITE_COMMITTED only after a SQLite transaction. remote_replication_status is separate: REPLICA_ACKNOWLEDGED, NOT_CONFIGURED, CONFIGURATION_INVALID, or PENDING_RETRY. Network errors cannot relabel unreplicated receipts as recorded.

New sb_secret_ credentials are sent exclusively on the apikey header (they are not JWTs). Legacy service_role JWT keys are supported only for migration; Supabase is deprecating legacy keys at the end of 2026.

The remote replica is optional, not a request signer, trust authority, active-active cluster, recovery quorum, or proof of physical truth. A single CIH host and its root key can still be single points of failure. The remote table currently has zero receipts until a trusted CIH signing public key is enrolled and a genuine node-signed receipt is submitted.
## Browser and hosted node boundary

On `artifactgptm.com`, the new UI generates a non-extractable **browser software** Ed25519 CryptoKey (stored in IndexedDB) and shows a command to enroll its public key on the trusted backend host. Enrollment is a separate out-of-band operator action; browser-generated private keys are not hardware attested. No public endpoint accepts arbitrary keys for automatic onboarding.

The feature-branch Worker gateway can forward the four explicit `X-Krdid*` headers, but **only the CIH backend checks the registry**. A hosted node needs a stable local disk or a replicated trust store, the CIH signing key pair, explicit operator enrollments, and a deployment review before issuing receipts. Render's default ephemeral filesystem is not sufficient for durable post-redeploy evidence. The local Windows machine and hosted node do not share trusted identities or receipt storage automatically.

## Untrusted or absent capabilities

- NO Auth0, JWT issuance, remote identity provider, or token bypass.
- NO accept-any-public-key authentication.
- NO simulated server signatures.
- NO automatic hardware proof from browser WebCrypto.
- NO independent Z3 truth adjudication.
- NO cross-node mesh agreement, quorum, automated failover, or single-point-of-failure elimination. One-way Supabase replication is optional and requires a server-only credential.
- NO automatic certification of scientific or legal conclusions.
- NO PR merge without user approval.
