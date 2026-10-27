# iNNOVULIS Enterprise Verification API — v0.1

**Scope:** Reference FastAPI service for a local, **already-running** ALIL signed-receipt watcher. This is neither a deployed third-party endpoint nor a regulator-recognized identity service. API usage is authenticated and **does not issue government, legal or hardware certifications**.

## Endpoints

| Verb and path | Behavior |
| --- | --- |
| `GET /v1/health` | Process liveness, not integrity or readiness proof. |
| `GET /v1/chain/status` | Recompute persisted machine chain using externally pinned public key; report last local root or fail closed. |
| `GET /v1/receipts/{sequence}` | Return archived signed machine receipt **after** full local chain verification. |
| `POST /v1/receipts/verify` | Verify a submitted machine receipt matches an entry in the locally verified chain. Does not authenticate external physical truth. |
| `POST /v1/causal/inspect` | Inspect confounder/collider/mediator/instrument **shape only**, does not prove causal identifiability. |
| `POST /v1/intake` | Explicitly opt-in; places unverified JSON into the immutable local inbox for separate authenticated watcher review. `202` is **not signature acceptance**. |
| `GET /openapi.json` | Standard OpenAPI schema (no live operation required). |

### Security defaults

- All receipt endpoints require `Authorization: Bearer <high-entropy-token>`. `/v1/health` exposes only limited non-sensitive state. There is no CORS wildcard.
- Use HTTPS termination and least-privilege access for any real deployment. Suggested server binding is loopback only. Never publish `uvicorn --host 0.0.0.0` without an audited gateway.
- `INNOVULIS_MACHINE_PUBLIC_KEY_HEX` comes from an independent trustworthy channel. A key supplied by an untrusted receipt cannot authenticate itself.
- Setting `INNOVULIS_ENABLE_HTTP_INTAKE=true` permits remote ingress **only if the process is network reachable**. Default `false`. Watcher signing is separate and needs private keys, independent registry pin, exclusive append handling, and protected state.
- Ingress limits 1 MB JSON, rejects duplicate JSON property names, floats and nonfinite values, requires auth, stores with exclusive filenames. Rate limiting, mTLS/OIDC, WAF, access logs, key rotation, HSM-based signing, backup/restore and tenant isolation are **not** implemented.
- Public evidence reads are intentionally protected to prevent inadvertent disclosure. Operator should develop field-level privacy redaction before granting enterprise access.

### Local demonstration (no production service)

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q tests/test_alpha1_api.py
python -m innovulis.simulate --out alpha1-demo-output
export INNOVULIS_RUNTIME_ROOT="$PWD/alpha1-demo-output/runtime"
# Copy pinned demo-only public key and choose an independent long random bearer token.
export INNOVULIS_MACHINE_PUBLIC_KEY_HEX="<DEMO_MACHINE_PUBKEY_64_HEX>"
export INNOVULIS_API_TOKEN="<RANDOM_SECRET_MIN_24_CHARS>"
uvicorn innovulis.api:app --host 127.0.0.1 --port 8811
curl -H "Authorization: Bearer $INNOVULIS_API_TOKEN" http://127.0.0.1:8811/v1/chain/status
```

Demonstration keys are discarded, not adequate for production. `alpha1-demo-output` contains evidence with no private keys. The API reads the signed demonstration record to verify chain linkage locally. Running HTTP locally does **not** make the attached screenshots' "Live Streaming" status real.

### Example accepted result (illustrative only)

```json
{
  "result": "LOCAL_MACHINE_RECEIPT_VERIFIED",
  "seq": 1,
  "receipt_hash": "<SHA256_HEX>",
  "local_root": "<SHA256_HEX>",
  "underlying_event_verified": false,
  "hardware_attested": false,
  "external_anchor_verified": false,
  "financial_or_physical_actions_authorized": false
}
```

### Future enterprise integrations (not implemented)

Proposed application flows: signed invoice intake, industrial maintenance, custodial transfer, independent calibrated sensor feeds, equipment manufacturing witness, and W3C Verifiable Credential 2.0 export. **This prototype does not implement VC Data Integrity 1.0, JSON-LD canonicalization or VC status/revocation**, so it should not be labeled W3C-VC compliant. An external anchor can reduce risk of history truncation; purely local chains cannot prevent privileged rollback or signer compromise.

## References

- W3C Verifiable Credentials Data Model v2.0, Recommendation 15 May 2025: https://www.w3.org/TR/vc-data-model/
- NIST FIPS 186-5, Digital Signature Standard: https://csrc.nist.gov/pubs/fips/186-5/final
- Existing internal ALIL source ingestion contract: `alil/router.py`, `alil/verify.py`.
