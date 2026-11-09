# iNNOVULIS™ Ecosystem Release v1.1.0-alpha
Executable, fail-closed release acceptance is composed with the existing **unified-i** package. The runner adds evidence-bound cross-component execution, a source registry and 30 named release gates; it does not duplicate the existing Trust Fabric.

**Do not mark a device physically accepted because Python tests, Icarus, Verilator or Yosys succeeded.** All 21 external gates remain `PENDING_INDEPENDENT_EVIDENCE`. They cannot be flipped by this API.

Local usage from repository root:

```bash
python -m pip install -e './ecosystem-release[test]'
python -m ecosystem_release inventory --repo . --strict
python -m ecosystem_release run --repo . --profile core --out ecosystem-release/evidence/core
python -m ecosystem_release verify ecosystem-release/evidence/core
```

`integration` executes the real existing `unified-i/ci/run_all.sh` end-to-end synthetic signed ipQR / optical QR / ESC/POS / HumanHub / Twinions bridge and live rGPU two-client WebSocket smoke, plus client WebCrypto tests. `rtl` executes the existing Tessera-G and PoPC Icarus+Verilator+Yosys gates. GitHub CI provisions the required clean Ubuntu software toolchains.

## Aggregate three independent CI job artifacts

The three GitHub Actions jobs publish independent artifact ZIPs. Download all three and run:

```bash
python -m ecosystem_release aggregate \
  ecosystem-v11-core-software-evidence.zip \
  ecosystem-v11-crypto-optical-websocket-evidence.zip \
  ecosystem-v11-tessera-popc-headless-rtl-evidence.zip \
  --out combined_11_gate_acceptance.json
```

This checks that the **core, integration and RTL** jobs come from the **same GitHub checkout commit**, that each raw log matches its SHA-256 hash and chained transcript, each subprocess exited successfully, all **11 software gates** were exercised and all **21 external gates** remain pending. To pin to a commit verified through an independent channel, use `--expected-commit <full SHA>`. The result is software-only evidence, not source-independent attestation, physical truth or a certified medical or legal opinion.

Each log is SHA256-bound in a chained transcript with commit id and exit code. The transcript can be **rewritten by a privileged local attacker** until its root is pinned or independently attested. Neither local signatures nor signed software receipts prove sensor origin, model correctness, clinical/legal merit, medical compliance, PCB manufacturability or physical printing.

No irreversible ATECC provisioning, board flash, production deployment, PR merge or billing is allowed from this workflow.

See `docs/COMPONENT_ACCEPTANCE_MATRIX.md`, `docs/SECURITY_REQUIREMENTS.md`, `docs/PHYSICAL_AND_MANUFACTURING_GATES.md` and `docs/PRODUCTION_HARDENING.md`.
