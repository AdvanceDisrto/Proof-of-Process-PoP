# iNNOVULIS™ CIH ΔiΔ — staged deployment handoff

## Scope and state

**Status: STAGED CODE ONLY.** No automatic production launch, domain switch, Auth0 tenant changes, subscription creation, or Supabase schema migration is implied by opening a PR. Existing innovulis.com routing remains intact until separately approved. Existing patent application **19/031,838** remains distinct from later ΔiΔ improvements.

### Verified infrastructure inventory on 2026-11-10

- Public site `innovulis.com` is currently routed by Cloudflare Worker `innovulis-public-router-20261027`. `www.innovulis.com` has the same Worker route. Do not replace either route without a reviewed cutover.
- Existing Render `innovulis-public-web` is a static service using repository `AdvanceDisrto/Proof-of-Process-PoP`, branch `deploy/innovulis-static-20261027`, with autoDeploy disabled.
- Supabase `BUDDY` is active at `https://tkrxmdonmxpeockpbazl.supabase.co`; it contains many unrelated public tables and functions. The CIH migration is **review only** and has **not** been applied.
- Stripe connector exposes only a **REWIND DISTRO test-mode account**, not a confirmed iNNOVULIS billing account. Do not set up live charges in the wrong merchant account.

## Functional architecture

Browser (Cloudflare Worker/Pages or Render static preview)
→ Auth0 Authorization Code with PKCE for user sign-in (not yet wired: Auth0 domain/client ID required)
→ FastAPI CIH backend (Render primary; FastAPI Cloud alternative, do not duplicate prod)
→ optional Supabase PostgREST using a **backend-only** service role key
→ bounded Ed25519 signed receipts / public key verification.

Cloudflare maintains the public routing and edge controls. The site guide uses on-device text matching and optional explicit microphone activation; it is **not** the real Buddy LLM. The established Buddy link remains available.

## Fail-closed API

- `GET /api/v1/health` reports configured capabilities without exposing secrets.
- `GET /api/v1/architecture` is public design metadata.
- `POST /api/v1/receipts` requires **valid Auth0 RS256 access JWT**, caller-supplied evidence that matches an expected canonical SHA-256 digest, and a **stable Ed25519 signing key**. Missing requirements return 4xx/503; never fabricate a `PROVEN_TRUE` outcome.
- `POST /api/v1/verify` verifies canonical bytes against the **server-pinned public key**. Result is signature integrity, not truth of external claims.
- `POST /api/v1/reconcile` authenticates and rejects signature failures, unknown/missing parent hashes, and duplicate fragments. This is a software integrity prototype, **not measured live mesh reconciliation**.
- If optional Supabase credentials are set, a successful DB insert is required before returning the issued receipt. Without them the response explicitly reports `storage_status=NOT_CONFIGURED`.

## Secrets — place only in server-side provider environment

- `AUTH0_ISSUER`: issuer URI from the confirmed Auth0 tenant, ending in `/`.
- `AUTH0_AUDIENCE`: registered API identifier from the Auth0 tenant.
- `CIH_ED25519_PRIVATE_KEY_B64`: 32-byte **persistent** raw Ed25519 seed, Base64. Generate and manage outside source control in a secrets manager, never at process startup.
- `CIH_ED25519_PUBLIC_KEY_B64`: pinned matching 32-byte raw public key in Base64, distributed to verifiers through a separately trusted channel.
- `CIH_ALLOWED_ORIGINS`: exact approved site origins separated by commas (not `*`).
- Optional `SUPABASE_URL`: project API URL.
- Optional `SUPABASE_SERVICE_ROLE_KEY`: backend-only privileged credential. NEVER expose to web JS, mobile apps, Worker source or GitHub.

Never copy existing environment-secret values from unrelated applications or different identities without validating their scope and permissions.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r cih_api/requirements-dev.txt
python -m pytest -q cih_api/test_app.py
uvicorn cih_api.app:app --host 127.0.0.1 --port 8000
```

Serve `site/` separately (e.g. `python -m http.server --directory site 8080`), or use a static preview service. Authentication and signing remain disabled until configured; this is a deliberate safety control.

## Hosting responsibilities

| Service | Responsibility | Current delivery |
| --- | --- | --- |
| GitHub | source / PR review / Actions tests | staged feature branch; no merge |
| Cloudflare | current domain routing, edge security, eventual static assets deployment | existing public worker retained |
| Render | preview static site and primary FastAPI option | separate preview services, no production cutover |
| FastAPI Cloud | alternate FastAPI deployment target | not provisioned |
| Auth0 | external user identity, JWT validation, organizations later | code supports JWT; tenant configuration pending |
| Supabase | scoped receipt persistence with RLS | SQL migration staged, not run |
| Stripe | Checkout test mode and verified webhooks after correct merchant/pricing | no plan or charge created |
| AMD/NVIDIA/RunPod | optional GPU execution adaptors after measurable runtime evidence | not installed or benchmarked here |
| DigitalOcean/AWS CDK | optional alternative infrastructure | no VMs or AWS stacks created |
| SwiftUI | optional mobile UI consuming the same API | not deployed |

## Stripe implementation gate

Before enabling billing: confirm the correct iNNOVULIS merchant, subscription prices and terms, and Auth0 user→Stripe customer binding. Implement hosted Checkout using a server-created Session and webhook signature verification. **Never mark entitlements from redirect parameters alone**. Store verified `checkout.session.completed`, `invoice.paid`, `customer.subscription.updated/deleted` events idempotently in dedicated, tenant-scoped data. Do not present “Certified Live™” as a legal certification.

## Cutover and verification gate

1. Review the feature branch and CI checks, including API tamper and parent-link tests.
2. Inspect the preview on desktop and mobile; test voice permission, text guide, accessibility and the honest demo badge.
3. Verify Auth0 issuer, audience, scopes, client ID, callbacks, access token audience, and CORS against the chosen canonical domain.
4. Review the isolated SQL migration for permissions, policies, and retention. Deploy to a nonproduction Supabase branch first when approved (branches can incur costs).
5. Test signing with persistent key storage and pinned public key; independently validate signature using known test vectors; rotate and revoke keys through a documented mechanism.
6. Validate payment flow in the correct Stripe test merchant and signature-verified webhooks; no test-mode→live switch by default.
7. After explicit production approval, update the origin behind `innovulis-public-router-20261027` or adopt a new Worker deployment and preserve rollback. Verify both apex and `www` URLs, TLS, headers, old links and service health.
8. Record deployment commit, timestamp, health checks, negative tests and rollback reference in a release receipt.

## Patent notice

Use **“Patent Pending — U.S. Application No. 19/031,838”** only while the application actually remains pending. Do not say that DAG receipts, hardware PUF, proof-of-work, legal arbitration, later ΔiΔ workflows or other unconfirmed improvements are covered by that application. Confirm the active file status with counsel before marketing and publication.
