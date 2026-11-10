# i™ Unified component acceptance matrix

The executable registry `ecosystem_release/catalog.py` contains 22 source-bound components. Its check `SOURCE_PRESENT_UNTESTED` says only that the component exists in the checkout, **not** that it is complete, executed or physically verified.

| Component | Software-tier status | External production acceptance gate |
|---|---|---|
| Open ipQR verifier | synthetic Ed25519, revocation/witness/log policy | externally pinned anchors, independent operators and fresh revocation |
| Human Hub | synthetic consent, scope and signed audit trail | human authorization, identity and domain safety |
| Paper Console | ESC/POS preview and rate-limited queue | actual physical paper, optical re-scan and verified printer status |
| rGPU terminal | local WebCrypto and two-client WebSocket | authenticated remote peers and real GPU |
| iP.CiH capsule | signed bounded HTML capsule | user-consented launch and adversarial sandbox review |
| iMorphus | exact-pixel experimental color grid | camera calibration and optical error correction |
| Buddy audit | formal bounded arithmetic only | checked factual premises and human review |
| Twinions | model disagreement detection | independent factual arbitration and reliable witnesses |
| Twinions legal | document hash-chain and workflow; incomplete 18-slot definitions | qualified jurisdiction-specific counsel and court admissibility |
| iTelepathy | manual consent-gated typed messaging | BCI enrollment and real peer security |
| Tessera-G RTL + Arty A7 | Icarus, Verilator, Yosys; Vivado recipe | real timing-gated bitstream, board measurement and signed test witness |
| PoPC-PU RTL | bounded sign-request gate | actual hardware compute/sensor-binding, not just sign request |
| iStick | MCU candidate and host C++ logic | KiCad/ERC/DRC, controlled impedance PCB, firmware and manufacturing |
| INA226 | software power integration | calibrated physical shunt/time samples |
| MCP9808 | read-only I2C parsing | sensor reading plus calibrated origin |
| ATECC608 P-256 | signature adapter | actual secure-element key, slot config and attestation |
| DAGE | headless Z3/trace integration | real GPU/FPGA executing code |
| Regulatory and external trust | acceptance policy | independent security, privacy, legal and clinical evaluations |

The dedicated release runner executes the original `unified-i/ci/run_all.sh`, actual optical QR and ESC/POS smoke, iP.CiH WebCrypto, rGPU two-WebSocket TCP smoke, Tessera-G and PoPC RTL. It publishes log hashes tied to source commit, not invented test statuses.

**A SHA256 hash chain over a local SQLite or log file is only tamper-evident relative to an external pinned checkpoint. It is not an immutable chain of custody by itself.**
