# CIH ΔiΔ local operation (Windows and Linux)

The earlier example that returned `PROVEN_TRUE` merely because a claim did not contain the word “fail” was **not a valid truth engine**. It has been replaced with a signed-evidence service whose output can be verified cryptographically, with explicit limitations.

## Windows PowerShell

From a cloned copy of the repository:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-cih-windows.ps1
```

## Linux / WSL

```bash
bash scripts/setup-cih-linux.sh
```

The scripts install dependencies and run the test suite first. They start FastAPI at `http://127.0.0.1:8000` only if tests pass. Open `/docs` for the exact request and response schemas and `/api/v1/health` for capability readiness.

## Production contract

- `GET /api/v1/health` and `GET /api/v1/architecture` can operate without credentials.
- `POST /api/v1/receipts` requires a valid Auth0 RS256 bearer token, evidence with matching SHA-256 and a persistent signing key.
- `POST /api/v1/verify` accepts a structured signed receipt and verifies against a pinned public key. It **does not** accept the prior `{claim, evidence_hash: 'abc123'}` payload as a signed receipt.
- `POST /api/v1/reconcile` rejects missing parents and bad signatures; it **does not prove** a real mesh reconnected.
- Use stable secrets from your provider secrets manager. Do not generate new signing keys on every server start.
- If no signers/keys are configured, `503 SIGNING_KEY_UNAVAILABLE` / `TRUST_ANCHOR_UNAVAILABLE` is the correct fail-closed behavior.

## Tampering regression

```bash
python -m pytest -q cih_api/test_app.py
```

Tests sign a fixture, verify it, change the signed claim, then assert the tampered receipt is rejected. Additional tests cover missing auth configuration and parent hashes.

## Public site and production edges

Both `innovulis.com` and `www.innovulis.com` route through Cloudflare to the new CIH portal origin. `api.innovulis.com/api/v1/*` uses an isolated Worker; existing other gateway endpoints are unchanged. Stripe billing and production user provisioning require separate Auth0 and merchant configuration. See `docs/CIH_DEPLOYMENT_STAGING.md`.
