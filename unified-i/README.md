# i™ iNNOVULIS — Universal Integration & Acceptance Fabric v1.0.0-alpha

**EXECUTABLE: software-only integration of seven existing system layers. No fake physical or professional certification.**

The architecture is composed of independently scoped components:

```
  Human / Buddy / Twinions (DETERMINISTIC REVIEW, NOT AUTOMATIC TRUTH)
                |                          |
       Bounded claim compare         18-slot legal intake
                |                          |
                +------------+-------------+
                             |
                  HumanHub signed ipQR demo
                             |
                Open Verifier: pinned trust,
             witness quorum, issuance/revocation,
                 evidence hash checks (DEMO)
                             |
             SQLite hash-linked receipt journal
                             |
          +------------------+-------------------+
          |                                      |
  optical QR + exact-pixel iMorphus          ESC/POS bytes
          |                                      |
       phone/screen                         PRINTER OFF
          +------------------+-------------------+
                             |
                    HUMAN READ ACK
                             |
             PHYSICAL & CLINICAL GATES PENDING
```

## What was actually executed

`unified_i.bridge.run_synthetic_closed_loop` uses the **existing** `HumanHub`, `paper_console`, `innovulis_receipt` open verifier, **actual decoded optical QR pixels**, the already implemented `ipcih` signed capsule and exact-pixel iMorphus carrier, and the actual `twinions_legal` model-conflict checker. Synthetic `PROVEN_TRUE` and `REFUTED_FALSE` receipts both verify cryptographically against the **ephemeral demo anchor**; the result never upgrades the sample to physical/clinical truth.

`unified_i.signing` implements a strict additional interoperable receipt manifest signed by a software Ed25519 key with a domain separator and externally supplied public key pin. It is **not** a substitute for the existing `ipqr1` verifier's revocation, witness and log checks. A separate `unified_i.secure_element` adapter tests ECDSA P-256 signatures with an injected callback but **never** marks hardware provenance as verified.

`unified_i.hardware` performs read-only MCP9808 I²C manufacturer-ID, device-ID and temperature parsing (including negative values) using an injected bus for testing. Hardware remains unattested. `unified_i.board` validates a **candidate** USB-native MCU/I²C netlist's required functional nets and obvious unsafe MCU voltage assumptions. A netlist JSON is **not** a routed schematic, 90Ω impedance design or fab-ready Gerber.

`unified_i.service` is an operator-authenticated local FastAPI status and demonstration evaluator with a green/blue ocean-glass dashboard. It does **not** accept patient information, issue clinical diagnoses, file legal claims, or print physical receipts. Operator tokens are held in the operator's memory, not stored in the web UI.

### Run inside the monorepo

```bash
# prerequisites on Ubuntu 24.04: python3-dev, build tools, libzbar0, libz3-4, node 22
python -m pip install -e 'unified-i[test]' -e ./ipcih-capsule
bash unified-i/ci/run_all.sh
```

This invokes Python unit/integration checks across `unified-i`, `paper-console`, `human-hub`, `twinions-legal` and `ipcih`; a real socket-bound localhost HTTP smoke; a cryptographic signed ipQR → optical-pixel decoding → ESC/POS bytes → journal → human ack demo; strict C++16-vector gate self-test; candidate board semantic audit; OpenSCAD concept shell rendering when installed; and JavaScript WebCrypto checks. If the CI runner lacks physical FPGA/sensors/secure element/printer, it reports `PENDING` instead of `PASS`.

### Test directly from a standalone local checkout

```bash
python -m pytest -q tests
python -m unified_i physical-gates
python -m unified_i audit-board hardware/istick_reference.json
python -m unified_i smoke-synthetic --out evidence/synthetic-smoke
python ci/smoke_http_live.py
bash ci/smoke_hardware.sh
```

For the `smoke-synthetic` command supply the existing sibling package paths via `PYTHONPATH` or install those repositories separately. `ipcih-capsule/` source and tests are included in this PR because the earlier module had been verified locally but was not on `main`.

### Start the local operator console

```bash
# Never commit token; launch with a local operator session
export INNOVULIS_OPERATOR_TOKEN="$(python -c 'import secrets;print(secrets.token_urlsafe(36))')"
python -c 'import os,uvicorn;from unified_i.service import create_app;uvicorn.run(create_app(operator_token=os.environ["INNOVULIS_OPERATOR_TOKEN"]),host="127.0.0.1",port=8792)'
# Open http://127.0.0.1:8792
```

The service binds only to loopback in this runbook; operators must not expose it to a public interface.

## The iStick is still a candidate, not a board

The earlier CH340E-only proposal cannot execute C++ code or directly provide a native I²C master. The reference now proposes a USB-native RP2040-class MCU *candidate* with MCP9808 and ATECC608B-family secure element on a 3.3 V bus. Exact package, regulator, flash, clock, ESD, USB-C CC resistors, impedance, PCB routing, crypto slot policy, OTP lock, and mechanical verification are **not finished**.

**ATECC608A is not recommended for new designs by Microchip**; evaluate supported ATECC608B variants with security engineers and confirm procurement before freezing a schematic. Physical MCU firmware, KiCad ERC/DRC, Gerbers, impedance simulations and tests are all pending. The proof signature is not a PUF proof and cannot prove that a specific computation actually consumed stated joules.

`hardware/PROVISIONING_HOLD.sh` exits nonzero and **cannot lock any key zone**. Factory provisioning requires a separate audited operator process, a chip-specific slot map, backups and irreversible-action approval.

## Repository release rules

- Do not merge the integration PR without user approval.
- Hardware acceptance remains `PENDING`; no mechanical, electrical, clinical, legal, or medical compliance claim.
- Never print unsupported `PROVEN_TRUE` as an unqualified assertion.
- A signed payload authenticates the supplied contents against a **separately trusted key**. It does not establish the truth of the claim.
- All source and witness independence must be evaluated separately; three ephemeral keys from one demo process are **not three independent witnesses**.
- Security code must be reviewed and tested for production; this is a research prototype.

See `docs/COMPONENT_MATRIX.md`, `docs/SECURITY_AND_LIMITS.md`, `docs/ELECTRICAL_AND_MANUFACTURING.md`, and `docs/RELEASE_GATE_SPEC.md`.
