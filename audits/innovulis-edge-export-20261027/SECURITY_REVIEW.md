# iNNOVULIS temporary export — security review (2026-10-27)

Source basis: the **11 files pasted in the ChatGPT conversation**, not an authenticated clone of `lee-innovulis-ecosystem-cf74487267b4469b`. Original temporary repository was not accessible via the connected GitHub app. This document is an audit-only recovery marker; **no source has been deployed, DNS changed, or migration executed**.

## Production blockers (fail closed)

1. **Fabricated blockchain settlement (critical):** `backend/index.js` `POST /api/anchor` returns `status: "ANCHORED"` and a random `tx_hash` without submitting to Polygon or OpenTimestamps. This must instead return `NOT_IMPLEMENTED/NOT_ANCHORED` (HTTP 501) until independently verifiable proof exists. Never write such results as successful anchors.
2. **No DAG verification (critical):** `/api/verify` verifies only Ed25519 over a shallow sorted JSON body, then unconditionally replies `dag: "ACYCLIC"`. It does not recompute node hashes, check edges against parents, validate topological order, check cycles, enforce receipt schema, or trusted issuer pins.
3. **Broken canonicalization:** `JSON.stringify(body, Object.keys(body).sort())` is a *replacer array*, not recursive canonicalization. Nested data fields are filtered or omitted; signed nested DAGs are not faithfully bound. Establish and version an agreed recursive canonical representation across Python/Workers/browser before signing/verifying.
4. **Unauthenticated private-key endpoint (critical):** `POST /api/keygen` returns raw PKCS8 private signing keys to any caller. Remove the API endpoint; create non-extractable keys in the browser, or provision issuer keys through controlled management.
5. **Unauthenticated data disclosure (high):** `GET /api/dag/:agentId` exposes D1 logs to anyone who guesses an agent ID, including payload excerpts. Add server-side authentication, authorization and row ownership boundaries.
6. **LLM classification is not authorization:** `POST /api/analyze` accepts arbitrary user text and returns unconstrained model output. Never authorize purchases, medical changes, or deletions from LLM-generated "PERMIT".
7. **Misleading ipQR (critical to product definition):** `hardware/ipqr.py` uses the `qrcode` package and `cv2.QRCodeDetector`. It generates a normal QR, **not** the custom radial non-QR optical DAG specified for i™ ipQR. The scan path can return a receipt even after invalid signature (print-only failure). Replace with the separately tested radial reference format, then test paper-camera capture separately.
8. **Frontend reports not supported by evidence:** `frontend/lol/index.html` reports `DAG Topology: ACYCLIC` without inspecting DAG; `frontend/proofofprocess/index.html` says a D1 log is permanent even though SQLite records can be edited or deleted. HTML interpolates user-originated values through `innerHTML` without escaping; XSS risk.
9. **No Access enforcement:** "Access Protected" appears only as frontend text; Worker endpoints have no JWT/Access service-token validation. CORS `*` does not authenticate requests. Protect privileged endpoints *at the backend*.
10. **Unsafe automated production deploy:** `.github/workflows/deploy.yml` deploys on a push to `main` and then runs schema SQL against remote D1 with no reviewed promotion gate, negative tests, backup, or evidence binding. Make CI test-only by default, manual production approval separately, and move to versioned migrations.
11. **Unverified operational marketing:** claims of "<5ms", "300+ locations", "forever", "fully offline" (while loading Tailwind CDN), and "$0/month" are not established by source or tests.

## Required recovery plan

- Preserve pasted source as an immutable source-evidence attachment *outside* production; original temp repo expiry does not establish ownership of deployed assets.
- Build a separate quarantined implementation branch, with explicit provenance of reconstructed files; disable `main` deployment triggers.
- Implement a strict schema; recursively canonicalize; Ed25519 verify with optional independent pinned issuer key; hash every node; verify DAG parity, unique IDs, roots, topo ordering; reject tampering.
- Make key generation client-only. Keep high-risk iAp tools disabled until authenticated and independently approved policy + durable audit writes are tested. Never treat an AI's judgement as authorization.
- Make anchor state `NOT_ANCHORED` unless a real chain tx + receipt-specific inclusion proof is independently verified. An RPC provider response alone is not a consensus proof.
- Do not cut over any Cloudflare domain or existing Render service from this export without review, negative tests, and separate release approval.

**Verdict:** UNTRUSTED_EXPORTED_SOURCE / PRODUCTION_DEPLOY_BLOCKED. No independent physical, issuer, or blockchain certification.
