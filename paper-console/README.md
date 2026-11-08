# iNNOVULIS™ Paper Console + PoPC-PU v0.1

**Real executable software, FPGA-synthesizable small gate, independent verifier integration. Not a physical trust appliance.**

### The actual acceptance boundary

The Paper Console is a localhost FastAPI + WebSocket timeline with strict source tiers, a persistent SQLite hash-linked event journal, a durable printer spool, and operator-controlled ESC/POS output. Print defaults to **OFF/manual**; nothing reaches a printer without deliberate configuration. An independent ipQR v1.0 verifier checks the signed receipt against an **operator-pinned** trust anchor and supplied evidence bytes before issuing `VERIFIED_DIGITAL_RECEIPT`. The QR is an **untrusted paper carrier**.

Real computations include NumPy image-patch covariance and SVD with full input/covariance/singular-tensor hashes, SHA-256 dataset ingestion, and INA226 shunt + bus-voltage **ready-to-connect** register reading plus trapezoidal power integration. The downloadable demo uses **synthetic inputs**, and does not have an INA226 attached.

The PoPC-PU `rtl/popc_gate.sv` is a synthesizeable, fail-closed, eight-input sign-**request** gate. It does **not** contain a hardware Z3/SAT solver, Merkle engine, PUF, key material, physical ADC, crypto signing, printer UART or sensor authentication; a hostile host can spoof its gate input wires. Actual physical authenticity requires separately verified trust boundaries.

### Reproduce (offline data, no physical printer)

```bash
cd iNNOVULIS_Paper_Console_PoPC_PU_v0.1
python -m pip install -e '.[test]'
python -m pip install cryptography msgpack opencv-python-headless
python -m pip install integrations/innovulis_open_receipt_verifier-1.0.0-py3-none-any.whl
python -m pytest -q tests
python -m paper_console demo --out evidence/demo
python ci/smoke_signed_qr.py evidence/signed-optical
python -m paper_console serve --db paper_console.sqlite3 --port 8780
# open http://127.0.0.1:8780/ (demo stream OFF; token printed on startup)
```

The signed demonstration is created with ephemeral **test-only** Ed25519 keys and five witness keys all controlled in one process (not independent operators). It prints a **REFUTED_FALSE** claim as a genuine signed but *false-declaration* example; the scanner re-decodes actual ESC/POS raster pixels back to exact ipQR text, then independently verifies again.

### Print controls and BLE

- Default `mode=manual` means the daemon does not auto print; `exception` queues *only* independently verified digital receipts whose declared claim verdict is `REFUTED_FALSE`; `continuous` queues all verified digital receipts. Missing signed carrier -> `HOLD`, not a forged paper receipt.
- Minimum 5s between outputs, maximum 30 per hour, durability across process restarts, spool state `CLAIMED` becomes `HOLD` on restart instead of sending possibly duplicate prints.
- `DryRunPrinter` generates real ESC/POS bytes without hardware; `ApprovedPythonEscposPrinter` supports explicitly approved USB/serial devices; `ApprovedTcpPrinter` requires an approved private IP. Paper-out cannot be inferred without a supported model-specific status signal.
- The web UI has an explicit *per-receipt* **Print / BLE** button. If no vendor-specific BLE GATT service/characteristic is configured, it downloads `.escpos` bytes as a preview. With compatible UUIDs, browser supports operator-picked Bluetooth device + 20-byte throttled writes. This is experimental and **not universal**. You must verify your printer's BLE profile; browser capabilities and OS permissions vary. No automatic BLE scanning or pairing.
- Bounded QR raster uses real ipQR1 payload, including quiet zone. If a full signed receipt cannot fit legibly at configured minimum pixels per module, printing is **blocked** rather than trimming payload or forging a placeholder QR. Optical smoke test re-reads the actual raster image independently.

### Atlas: not invented geography

`python -m paper_console atlas --input data/atlas_example.json` validates source URL/license/date, entity IDs, hashes and bounded data. The fixture contains **four illustrative entities**, NOT 50 states/195 countries and NOT any previously mentioned screenshots. To ingest full licensed datasets, supply an attributable operator-reviewed JSON with actual source date and license. External geography is `DATASET_UNVERIFIED`; neither a Z3 consistency check nor an LLM can independently prove the source facts. Timestamp-sensitive "number one" claims are `UNRESOLVED` without appropriate contemporary evidence. A New York→London path does **not** establish that traffic traversed the MAREA cable. TeleGeography's actual licensed geodata cannot be assumed freely redistributable.

### Energy: actual INA226 read *when attached*, not currently connected

`paper_console.energy.INA226(bus_number=1,address=0x40,shunt_ohms=...,calibration_id=...,device_id=...)` requires operator-supplied shunt value/calibration, smbus2, physically wired monitored load and real I2C sensor. It reads signed shunt voltage (2.5µV LSB) and bus voltage (1.25mV LSB), derives amps and watts, and integrates two or more timestamped power samples with a maximum 10-second gap. The sample itself is not a signed hardware attestation. Energy usage is neither a proof of a particular computation nor an unforgeable identifier; Landauer's bound does not validate arbitrary solver workloads.

### Secure element

ATECC608C uses **ECDSA P-256**; it is not a drop-in Ed25519 PUF. `P256HardwareSigner` has no fake signing fallback: it fails closed until a real device adapter and independently provisioned public key are supplied. ECDSA is independently verified in Python; tests use software-generated reference keys and do not establish ATECC hardware.

### Auditable code

- `paper_console/`: FastAPI local WebSocket ticker; event schemas; persistent store; ESC/POS and Web Bluetooth UI; physics and math adapters; independently verified ipQR gate; P-256 boundary.
- `rtl/`: RTL combinatorial-and-clocked sign-request gate and adversarial Icarus testbench.
- `tests/`: security, local network endpoint, math, printer, metadata, replay, source tiers and Open Verifier integration tests.
- `ci/`: real signed QR optical smoke; Icarus/Verilator/Yosys headless smoke.
- `integrations/innovulis_open_receipt_verifier-1.0.0*.whl`: prior independently tested ipQR verifier, included as optional offline install dependency. The source is also under `integrations/innovulis_receipt/` for inspection.

### Critical limitations

There is **no live BCI**, no Pi I2C access, no actual printer connection, no independently attested Joules, no silicon PUF/secure element signature, no actual undersea route measurement, no licensed full-world registry, no hardware Z3 accelerator, no FPGA bitstream, no chip manufactured, no external witnesses, and no real quantum or thermodynamic truth guarantee. A local log can be modified by someone with DB administrator permissions unless its root/hash is independently anchored. A print event does not prove paper successfully emerged.

**A receipt is evidence, never automatic legal admissibility or a transfer of burden of proof.** Preserve the chain of custody and the accountable operator's identity and qualifications externally.

GNU/Linux demo requirements: Python 3.11+, FastAPI, uvicorn, NumPy, `qrcode`, Pillow; Open verifier reference wheel requires cryptography and msgpack. RTL headless tests require `iverilog`, `vvp`, `verilator`, `yosys`. MIT/BSD/Apache and other third-party licenses must be respected for external datasets and tools. This package's own source is Apache-2.0. No monetized resources are created by the supplied tests.

### Verify a real signed receipt into the live audit journal (local CLI)

The `verify` CLI never trusts a self-reported `VERIFIED` flag. It runs the full
independent v1.0 verifier and writes a record into SQLite. A separate terminal
running the localhost dashboard will pick up this record on its next 10-second
poll (WebSockets deliver events posted directly to the service immediately).

```bash
python -m innovulis_receipt demo --out /tmp/ipqr-demo    # SYNTHETIC ONLY
PIN=$(cat /tmp/ipqr-demo/DEMO_ANCHOR_SHA256_NOT_TRUSTED.txt)
python -m paper_console verify \
  --input /tmp/ipqr-demo/receipt.json \
  --trust /tmp/ipqr-demo/trust_anchor.json \
  --anchor-pin "$PIN" \
  --revocations /tmp/ipqr-demo/signed_revocations.json \
  --issuance-log /tmp/ipqr-demo/signed_issuance_log.json \
  --subject sensor:demo-unit-314 \
  --evidence-dir /tmp/ipqr-demo \
  --db paper_console.sqlite3 \
  --preview-escpos evidence/ipqr-demo.escpos
```

The displayed `PIN` is deliberately **NOT independently trusted** and may only
be used for a self-contained synthetic demo. In production, administrators must
provision an approved trust anchor fingerprint through a separate channel.
The CLI *never* sends bytes to physical printer or calls RunPod.
