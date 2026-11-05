# iNNOVULIS ORS + Trust Fabric research extension

- ORS v0.4 numerical solver retained; physical gate ACTION_REQUIRED.
- iUr `ipqr/utility-receipt/v1` local signed metering **software reports**, not invoice-ready measurements.
- popP `ipqr/providence-receipt/v1` demonstration signature and fail-closed human policy check; demo guardian is never considered authorized.
- iEnergy `ipqr/energy-receipt/v1` proof of *signed data*; does not verify physical generation.
- iCR is intentionally **not** minted: a time window match cannot establish a tradable credit, legal carbon offset, exclusive attribute allocation, or 24/7 CFE.
- Endpoint `/v1/trust/verify` requires **pinned public key**, `/v1/trust/guardian-check` requires independently configured key allowlist.
- UI's `output.css` local fallback hand-authored; GitHub Actions installs Tailwind CLI and compiles genuine Tailwind v4 CSS.
- Python canonical JSON is **not RFC 8785 JCS**; no cross-language canonical-byte claims. Standalone trust prototype not established to be iVerify API compatible.
- No production signing keys included. No public minting endpoint; no secrets needed to verify.
- GitHub Actions CI verifies tests, HTTP smoke and wheel bundling. FastAPI Cloud deployment must be to a **separate ORS app**, not existing iVerify app.

## Public release acceptance
The release name is **iNNOVULIS Trust Fabric v0.4.1**. Target hostname: `www.innovulis.com`.
Do not alter the existing Cloudflare `www` route before an independently verified FastAPI Cloud origin and a cutover plan exist.
The `www` hostname currently routes to an existing Render service. Production cutover is a separate, controlled action.
