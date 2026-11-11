# i™ Ecosystem Component Inventory — Composed v1

No single CI test certifies the complete hardware, network, legal and clinical ecosystem. Values below describe **this build's executed integrations** and the **unexecuted gates**.

| Component | Checked in this new integration | Still missing for full acceptance |
|---|---|---|
| Open ipQR v1 | Real signed synthetic receipts, 3/5 distinct test signatures, signed log and revocation, real optical decode | Independently sourced trust anchors, independent witness operators, externally anchored log consistency, audited revocation distribution |
| HumanHub | Synthetic consent, user acknowledgment, SQLite receipt event links | Real licensure checks, clinical validation, consent and privacy lifecycle |
| Paper Console | ESC/POS bytes produced; QR carries signed payload | Device-specific printer profile, status/ack, actual paper observation, maintenance and cooling |
| rGPU Terminal | Prior GitHub CI and WebCrypto evidence, not re-tested here | Actual GPU driver and DCGM/RunPod, hardware identity |
| iP.CiH | Full self-contained signed template demo; Pixel-exact iMorphus; 14 JS tests | Camera robustness, color calibration, mobile browser isolation testing, bandwidth/capacity limits, signed app threat review |
| Buddy | Bounded integer checks and explicit unresolved natural language | Independent real-world fact ingestion, formalization review, calibrated evidence and human oversight |
| Twinions | Actual model-disagreement detector returns UNDETERMINED | Independent physical witnesses, defensible policy specification, experts, legal advice |
| Twinions legal | 18-slot workflow, seven user-defined gate names and eleven UNDEFINED slots | Counsel-approved precise gate definitions and jurisdiction-specific law; not a court ruling |
| Tessera-G | Previously executed RTL simulation, lint and Yosys synth; current PR does not fabricate FPGA outputs | Target-specific place/route, bitstream, board readback/IO/clock/temperature tests |
| PoPC-PU | Previously executed 29 RTL bench checks and Yosys generic synth | Physical RISC-V/Z3 hardware compute; this RTL only gates sign requests |
| CIH / QoW | Existing repo integrations, not independently exercised by this PR | Full cross-node physical replay/cryptographic attestation |
| INA226 | Existing sensor driver; no device read in this build | Calibrated real shunt+bus voltage measurements, sample timing, trusted origin |
| MCP9808 | Read-only 16-bit I²C ID and ambient temperature code plus mock tests | Actual I²C device, sensor calibration, host authorization |
| ATECC608 | P-256 crypto challenge mocked by injection; independently pinned public key verified | Real hardware key generation, slot verification, authorized provisioning, cert chain, chip attestation |
| iStick USB | Corrected MCU+I²C netlist semantics, host C++ 16-vector signing-request gate, OpenSCAD conceptual shell | Full KiCad schematic, firmware, PCB layout, verified USB impedance, Gerber, BOM/CPL, production run |
| iTelepathy | Previously consent-gated signed local typed intent transport | Real BCI EEG, physically verified identities, remote network and user consent, safety evaluations |
| Subsea routing | Existing data work; not a verified physical route | Operator-signed routing evidence, chain of custody, external telemetry |
| BLE/NFC/JAB/BrightMarker | Protocol concepts only in this build | Carrier-specific hardware readers, optical stress tests, NFC authenticity, material evaluation and anti-clone evaluation |
| WebRTC portal | NOT implemented or externally verified | Peer auth and pinning, ICE/TURN availability, E2EE semantics, consented media permission, threat model |
| Medical regulation | NOT assessed | Data privacy, risk analysis, applicable FDA/clinical evaluation, clinical study/quality system as required |
| Legal admissibility | NOT assessed | Custody original documents, authenticity and expert testimony, jurisdiction-specific standards |

## Hard guardrails

**Z3 `SAT` ≠ truth.** `SAT` means a constraint set has a satisfying assignment; a proof of a restricted input relation cannot authenticate the input's origin. `UNSAT` means contradiction under encoded assumptions, not automatically that evidence is a lie.

**Signature `VALID` ≠ hardware PUF.** Signer technology and certified hardware origin require independently documented key provenance.

**Joules `RECORDED` ≠ proof of computation.** Power/temperature sensors can be spoofed, and energy consumption is not uniquely determined by one algorithm.

**Receipt `PRINT_PREVIEW` ≠ physical paper.** TCP success also does not prove physical print, or that the paper carried the correct scanned payload.

**A verified legal/clinical transcript is evidence of a record, not a judicial or medical decision.**
