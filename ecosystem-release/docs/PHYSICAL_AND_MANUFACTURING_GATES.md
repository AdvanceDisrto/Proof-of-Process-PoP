# Physical hardware acceptance and actual manufacturing work still required

**Not fabricated, provisioned, calibrated, programmed, operated, printed or field-tested in this PR.**

## USB iStick PCB

- CH340E is **only a USB-to-UART converter** and cannot execute the host C++ or directly master I2C. Choose a genuinely USB-capable MCU with documented boot policy, clock, firmware loading and I2C peripherals; or select and validate an appropriate USB-to-I2C bridge.
- Approve exact ATECC608 family variant and datasheet, key slots and certificate chain. Never claim ECDSA P-256 signature proves a physically unclonable function or that truth follows from a signature.
- Prepare actual KiCad schematic + ERC, 4-layer PCB + DRC, vendor stackup and **measured/design-checked 90Ω differential USB impedance**, decoupling, USB-C CC resistors where appropriate, 3.3V supply, USB ESD/thermal/rated currents.
- Verify shunt placement and calibration for INA226; MCP9808 is temperature only. Collect raw registers with device identity and an independent calibrated reference.
- Generate and inspect real Gerber X2, drill, fab drawing, BOM with chosen MPN, centroid/CPL, enclosure STL and mechanical tests. A text blueprint is **not** a manufacturable board.
- Provision physical ATECC slot keys only after an operator-approved irreversible-action runbook and secure recovery policy; all CI workflows must block lock/fuse operations.

## FPGA and printer

- Reproduce target FPGA place/route/timing and generate the **actual** .bit or .fs file in an authorized toolchain. Flash on the actual target board with operator consent and record JTAG identity, firmware hash, readback, clock/voltage and failure behavior.
- Use calibrated instrumented compute/sensor pairing; don't infer an algorithm's validity from energy consumed. Observe PCB thermals and monitor equipment for sustained use.
- Make an authenticated subject-bound ipQR with independently pinned key and fresh revocation; print on a real printer and optically scan the physical paper on a separate device. Compare decoded bytes to original and record cutter/paper-out errors.

No gate may be marked physically accepted by a GitHub-hosted Ubuntu runner. An independent review workflow must be designed once credible physical evidence exists.
