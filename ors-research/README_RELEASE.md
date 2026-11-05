# iNNOVULIS ORS numerical research v0.4.0

This monorepo application lives in `ors-research/`. The FastAPI entrypoint is `ors.service:app`.
It is a software research prototype. `PHYSICAL_GATE=ACTION_REQUIRED`. It is not a
flight-qualified, material-qualified, or safety-engineered orbital ring.

## Local checks

```bash
cd ors-research
python -m pip install -e '.[test]' build
python -m pytest tests -q
python -m build --wheel --no-isolation
uv run fastapi dev
```

Endpoints: `GET /health`, `GET /v1/ors/smoke`.

## Review gates

1. PR workflow must execute 117 tests and local ASGI smoke before any release approval.
2. The source is committed to the review branch; **do not merge without owner approval**.
3. A public GitHub release is produced only by a separately authorized
   `ors-v0.4.0` tag (never by an ordinary PR push).
4. The separate **manual-only** FastAPI Cloud workflow requires the
   `ors-production` environment and dedicated GitHub secrets
   `ORS_FASTAPI_CLOUD_APP_ID` and `ORS_FASTAPI_CLOUD_TOKEN`.
   Never reuse the existing iVerify app ID.
5. Cloud production status is NOT_VERIFIED until public `/health` and
   `/v1/ors/smoke` return successful responses.

## Model limitations

3D frame buckling is an imposed-load linearized eigenanalysis. Curved rotor/stator
models use simplified planar dynamics, assumed material properties, magnetic
control proxies and sometimes externally imposed mathematical trim. There is
no Maxwell field solver, full rotor transport, qualification, or physically
verified hardware. An Ed25519 software receipt authenticates bytes to the
corresponding key but does not make model predictions true.
