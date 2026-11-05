# iNNOVULIS iVerify — Complete FastAPI + SPU v0.4.1 CI

This directory contains the *actual locally smoke-tested* FastAPI server, both receipt
APIs, CPU-only SPU simulation and empirical parameter model, HTTP clients,
offline verifiers, and 29 pytest cases. It is intentionally separate from
`innovulis/ci/`, the smaller 29-test reference-only receipt implementation.

## Run

```bash
python -m pip install -r innovulis/api/requirements.txt pytest httpx
cd innovulis
bash run_all_smokes.sh
```

`run_all_smokes.sh` starts a real Uvicorn HTTP server with ephemeral test
credentials, exercises `/health`, `/v1/mint`, `/v1/verify`, `/v1/spu/smoke`,
`/v1/spu/empirical`, `/v1/icore/status`, hash-only `/receipt` and `/verify`,
tests pinned-key and external-banner rejection, executes the 29 pytest
cases, and stops the server. It never deploys to the cloud.

CI is `.github/workflows/innovulis-fastapi-full-integration.yml`.
CI logs, structured HTTP observations, `pytest.log`, `ci-provenance.json` and
`SHA256SUMS.txt` are uploaded as `innovulis-full-fastapi-spu-ci-evidence`.
Signing keys, API keys, and SQLite test databases are excluded.

## Assurance limits

- `PASS` means observed software paths on a CI-hosted CPU, **not** photonic
  measurement or FPGA board execution.
- Physics figures depend on declared input assumptions.
- Hash-only T2 checks source-reference formatting, **not source signatures**.
- The receipt's signer attests to submitted bytes, **not computation truth**.
- Receipt JSON canonicalization is not RFC 8785 JCS.
- CI artifacts are SHA-bound and GitHub-hosted but **not OIDC-attested** by this workflow.
- FastAPI Cloud deployment needs an authenticated app and configured secrets;
  it is not performed by this test workflow.
- The prior `innovulis/ci` reference suite is not a substitute for the actual
  FastAPI server and HTTP integration tests added here.


## Full hosted CI with OIDC (November 4, 2026)
.github/workflows/innovulis-full-smoke.yml tests the actual application HTTP
routes, SPU CPU model, offline receipt verification, and 34 pytest cases.
It emits JUnit XML, SHA256SUMS and logs, then requests GitHub OIDC-backed
provenance for those files. Verify the attestation with gh attestation verify.
No physical FPGA or photonic measurements are implied. T2 source-signature
verification remains separate.
