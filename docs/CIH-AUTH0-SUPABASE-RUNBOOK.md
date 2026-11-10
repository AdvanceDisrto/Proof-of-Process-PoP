# iNNOVULIS™ CIH ΔiΔ — Auth0 / persistent signing / Supabase / Buddy integration

Status: **integration branch prepared; real tenant credentials required before issuance**. These instructions describe bounded cryptographic evidence, not a truth engine or physical hardware certification.

## Actual infrastructure inspected
- Supabase project: **BUDDY**, `tkrxmdonmxpeockpbazl`, `https://tkrxmdonmxpeockpbazl.supabase.co` (ACTIVE_HEALTHY).
- Supabase migration applied to `public.cih_receipts` with `RLS = ON` and no direct `anon`/`authenticated` grants or policies. `service_role` has SELECT/INSERT only at the SQL table-privilege level (the privileged database owner can still change records). A database acknowledgment is **not** an immutable blockchain receipt.
- CIH backend: `https://innovulis-cih-evidence-preview.onrender.com/api/v1/health` on Render; repository branch `feature/innovulis-cih-sovereign-portal-20261110`.
- Browser to CIH gateway: `https://igptm-matrix-api.innovulis-i-edge.workers.dev/api/cih/health` and `POST /api/cih/receipts` (Auth0 Bearer token forwarded only to fixed HTTPS CIH origin).
- Product website: `https://artifactgptm.com`; ArtifactGPTm feature branch `feature/igptm-matrix-buddy-20261110` remains draft/unmerged.

## Stage 2 — Auth0 identity and persistent signing
The Auth0 API resource, SPA application, issuer, audience, and client ID **must be verified in the actual Auth0 tenant**. Do not guess them.

The Auth0 tenant needs:
1. An **API Resource** whose identifier exactly matches `AUTH0_AUDIENCE`.
2. A **Single Page Application** registered for `https://artifactgptm.com`, `https://www.artifactgptm.com`, and the Render preview origin in callback/logout/web-origin lists.
3. RS256-signed API access tokens with the expected issuer, audience, subject, and expiration. **ID tokens cannot authorize API writes.**
4. Optionally RBAC/scopes, multifactor policies, and a separate machine-to-machine app for non-human operations.

On the local Windows checkout, generate a new Ed25519 key **once**:
```powershell
Set-Location "C:\Users\New Customer\Proof-of-Process-PoP"
.\.venv\Scripts\python.exe -m cih_api.provision_keys
```
The tool writes a secret JSON file under `%LOCALAPPDATA%\iNNOVULIS\CIH`, refuses to overwrite, applies a Windows owner ACL, and prints only the **public fingerprint and path**. Move the private/public environment values from that file to an approved secret store (for example Render Environment). **Do not paste private keys into chats, put them into GitHub, or expose them in frontend variables.** Store an encrypted backup offline; rotation otherwise invalidates legacy receipts since v0.1 trusts only one key.

Render CIH backend environment:
```
AUTH0_ISSUER=https://YOUR_VERIFIED_AUTH0_TENANT/
AUTH0_AUDIENCE=YOUR_EXACT_REGISTERED_API_IDENTIFIER
CIH_ED25519_PRIVATE_KEY_B64=[server secret]
CIH_ED25519_PUBLIC_KEY_B64=[public trust anchor]
CIH_ALLOWED_ORIGINS=https://artifactgptm.com,https://www.artifactgptm.com,https://igptm-matrix-artifact-preview.onrender.com
```
The issuer and audience are not secrets, but must be exact. No credential is written in this repository.

## Stage 3 — Supabase evidence persistence
The `cih_receipts` table is already created. The CIH backend additionally needs:
```
SUPABASE_URL=https://tkrxmdonmxpeockpbazl.supabase.co
SUPABASE_SERVICE_ROLE_KEY=[server-side Supabase secret key or legacy service_role credential]
```
Never put a Supabase secret in browser JavaScript or in a Cloudflare public Worker response. The app uses HTTPS, writes `receipt_hash, auth0_subject, receipt_body, signature_b64, key_id` under a server-side credential, and returns `DATABASE_ACKNOWLEDGED` **only after a successful PostgREST response**. Missing config returns `NOT_CONFIGURED`; a database error returns `PERSISTENCE_FAILED` and blocks issuance. The `RLS enabled no policy` informational advisory is **intentional** for this server-only table.

## Stage 4 — Authenticated ArtifactGPTm → Buddy → CIH workflow
- The public edge gateway is fixed to the specific CIH Render origin; it rejects unauthenticated POSTs and redirects.
- Official Auth0 React SDK is used only when the three public frontend build-time values are known:
```
VITE_AUTH0_DOMAIN=YOUR_VERIFIED_TENANT_DOMAIN_NO_HTTPS
VITE_AUTH0_CLIENT_ID=YOUR_VERIFIED_SPA_CLIENT_ID
VITE_AUTH0_AUDIENCE=YOUR_EXACT_REGISTERED_API_IDENTIFIER
```
- The SPA obtains **access** tokens in memory and sends them as `Authorization: Bearer ...` for receipt issuance only after a user clicks the authenticated issuance button.
- The protected API verifies issuer, audience, signature, and expiry against the pinned Auth0 JWKS; it takes the owner subject from the verified token, **not from a caller-controlled field**.
- The browser computes a canonical SHA-256 digest of non-sensitive artifact metadata, then requests `POST /api/cih/receipts` through the Cloudflare gateway.
- Verify the returned signature using `POST /api/receipts/verify`; compare database insert acknowledgment, and check test cases for no token, malformed token, wrong audience, mismatched evidence hash, bad signature, and disconnected storage.

Verification sequence:
```text
Auth0 SPA sign-in → access token → Worker auth-required proxy →
CIH Auth0 JWT validation → canonical evidence digest comparison →
Ed25519 receipt signing → Supabase append acknowledgment →
signed receipt response → separate public signature verifier
```

## Evidence boundary / rollout gate
A working API health endpoint or configured keys alone is **not** an end-to-end completed test. Real issuance remains blocked until tenant configuration, signatures, Supabase credentials, and successful live receipt verification are demonstrated. Human approval is required for merges, secrets, publication of private repositories, or anything irreversible. No Buddy Certified™ or Buddy Certified Live™ award has been issued.
