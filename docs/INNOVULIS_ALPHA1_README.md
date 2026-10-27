# 🧾 iNNOVULIS Alpha-1 — Corporate charter, physical reference design, and receipt verification API

**Reviewable engineering build, not a manufactured product, real hardware telemetry or production deployment.**

This package implements and tests a **real** FastAPI server over the existing ALIL Ed25519 receipt machine. It includes the draft corporate charter, physical prototype/specification, experimental substrate decision, causal integrity controls, simulated Genesis run, commercial rollout gates and OpenAPI contract.

- **API source:** `innovulis/api.py`, with bearer authentication, externally pinned signing key, independently recomputed hash chain, immutable intake queue, verified read endpoints.
- **Simulated Alpha-1 genesis:** `innovulis/simulate.py`, which makes *genuine disposable-key signatures* on synthetic events, then independently verifies receipt signatures without making real financial or physical claims.
- **Documentation:** `docs/INNOVULIS_CORPORATE_CHARTER_DRAFT.md`, `docs/ALPHA1_HARDWARE_ENGINEERING.md`, `docs/CAUSAL_INTEGRITY_GUIDE.md`, `docs/API_INTEGRATION_GUIDE.md`, `docs/ROLLOUT_RELEASE_GATES.md`.
- **Generated API schema:** `openapi.json` with field descriptions and schemas.
- **Tests:** `tests/test_alpha1_api.py`; local tests cover API and causal graph structure with Python 3.13.

## Local execution

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q tests/test_alpha1_api.py
python -m innovulis.simulate --out alpha1-demo-output
python -m innovulis.openapi --check
```

Start the HTTP server only after configuring `INNOVULIS_RUNTIME_ROOT`, `INNOVULIS_MACHINE_PUBLIC_KEY_HEX`, and `INNOVULIS_API_TOKEN` as shown in `docs/API_INTEGRATION_GUIDE.md`. Default configuration returns 503 rather than pretending it is ready; ingestion is independently opt-in.

**Never store your real private signing key or your production API secrets in GitHub, a demonstration archive, a QR code, or a public ledger.** Cryptography makes a claim attributable and tamper-evident, not intrinsically true.
