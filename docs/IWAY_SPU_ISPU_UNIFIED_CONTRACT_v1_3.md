# i™ iWay: SPU → iSPU → CIH ΔiΔ — Unified Evidence Contract

**Status:** local software reference; GitHub draft review; no remote provisioning, production deployment, certification, hardware enrollment, or compliance guarantee.

## Architecture

```
Input and source evidence
    │
    ▼
Global Legal Router [operator-verified test context; unknown => REFUSED]
    │
    ▼
Consent Policy Hash Gate [explicit exact policy version/hash]
    │
    ▼
iSPU Orchestrator [bounded local static task and provider plan]
    │
    ▼
SPU Execution [finite static ARC-grid DSL or circle geometry]
    │
    ▼
Quantum-of-Work Observer [actual local wall/cpu timings;
                         cycles and Joules = NOT_MEASURED]
    │
    ▼
Evidence-gated Receipt [request digest + KRDID signature +
                         existing CIH Ed25519 signature + SQLite]
    │
    ▼
Offline Verifier [pinned keys; source artifacts required separately]
```

## What was actually built

- `iway/unified_contract.py` supplies a no-privilege, no-network reference interface covering **24 named Linux distribution profile labels**; it does not install 24 OSes.
- Finite ARC fixture solver does not execute arbitrary generated Python, does not call an LLM, and does not claim official ARC-AGI-1/2/3 scores. The cited `docs.arcprize.org` describes **ARC-AGI-3 as an interactive environment**, a different benchmark.
- `s=r*theta` deterministic geometry is supported separately from ARC-AGI pattern reasoning.
- The optional io.net plan in the downloadable full v1.3 bundle is **dry run only**. No io.net VM API endpoint is asserted to work; no account used or charged.
- Software signatures and SHA-256 receipts are evidence-integrity controls, not a measurement of underlying physical GPU work.
- Legal routing is NOT GeoIP-only and NOT a sanctions determination. An unverified request header cannot become authoritative jurisdiction or genuine consent.
- A local shell command such as `curl https://unknown/install.sh | bash` is deliberately **not** part of this release.
- Actual physical Joules, CPU cycles, energy meter calibration, attested GPU model, Bitcoin OTS anchoring, hardware SPU identities, and production review are unresolved.

## Repository acceptance

```bash
python -m pip install -r cih_api/requirements-dev.txt
python -m pytest -q cih_api/test_iway_unified_contract.py cih_api/test_i_audit_bridge.py cih_api/test_app.py
```

New tests verify (1) 24 exact profile names, (2) no actual deployment, (3) bounded ARC toy and arc-length formula, (4) refusal when consent, country or rule evidence fails, (5) prepared iWay proof submitted to the pre-existing KRDID-signed `POST /api/v1/receipts` and independently checked with `POST /api/v1/verify`, (6) replay, missing authorization and mutation rejection.

The **full downloadable offline bundle v1.3** additionally combines the earlier 105 CIH tests, 52 SPU/iSPU tests, the Linux matrix tests, independent unified multi-receipt verification tests, and one-command local acceptance into a common archive. Its full runtime source is not yet incorporated by this GitHub draft PR; this PR is a narrow integration slice that must pass repo CI before expansion.

## Reality boundaries

A receipt can prove an event or text was signed by a key and certain deterministic checks were run. It cannot establish the underlying source is factually correct, that GPU hardware executed the work, or that laws were complied with. Conservation of physical energy **does not imply computational work is conserved as cryptographic evidence**. Measurements have cost and loss; 100% thermodynamic efficiency is not claimed.

Previous reported Windows v0.4.2 recovery regression remains OPEN until the real recovery log and retry pass.

**HOLD** — No main-branch merge, remote GPU provisioning, DNS changes, data-residency or legal guarantees, privilege escalation, or site deployment without the user's explicit approval.

Reference URLs for follow-up review:
- https://www.linux.org/pages/download/
- https://docs.arcprize.org/
- https://cloud.io.net/
