# iNNOVULIS™ Physical Gate Readiness v0.2

**Purpose:** a safe, repeatable operator runbook for Paper Console, PoPC-PU, INA226, ATECC608C, FPGA and RunPod GPU. A passing GitHub Actions job means only the simulated software acceptance gate is green.

## 1. Inspect host without touching devices

From the repository root:

```sh
python -m pip install 'cryptography>=41' 'smbus2>=0.4'
python -m hardware.physical.gates readiness
```

Regardless of what device paths exist, `physical_acceptance` remains `ACTION_REQUIRED`.

## 2. INA226

With an INA226 physically wired to a Raspberry Pi and the load being monitored, and after independently validating electrical limits, shunt rating and 3.3V board compatibility:

```sh
python -m pip install -e ./paper-console
python -m hardware.physical.gates ina226 --approved --bus 1 --address 0x40 \
  --shunt-ohms <MEASURED_SHUNT_OHMS> \
  --device-id <OPERATOR_BOARD_ID> --calibration-id <ACTUAL_CALIBRATION_ID>
```

This read-only check requires manufacturer register `0xFE = 0x5449` and die register `0xFF = 0x2260` before taking two samples. Two samples allow a numerical trapezoidal joule estimate but are **not** adequate for precision metrology, independent calibration or authentication of the device. Manufacturer/die registers are not cryptographic authentication. If the board or driver is missing, the command fails instead of generating artificial samples.

Reference: Texas Instruments  [INA226 data sheet](https://www.ti.com/lit/ds/symlink/ina226.pdf) — manufacturer/die registers, shunt and bus ADC scaling. No mains power wiring is implied.

## 3. ATECC608C

A legitimate ATECC608C supports **ECDSA P-256**, not Ed25519. The real hardware signer must be independently provisioned and available as an **operator-approved external program**. The program accepts `--digest-hex <64 hex digits>` and outputs ECDSA signature hex (raw 64-byte r||s or DER), with no secret key export.

```sh
python -m hardware.physical.gates p256-challenge --approved \
  --binary /usr/local/bin/operator-reviewed-atecc608-signer \
  --trusted-pem /secure/verified-slot-public-key.pem
```

This challenge uses an unpredictable 32-byte nonce and independently verifies the returned signature against the pinned public key. **It cannot establish that the signing key is hardware protected.** A software emulator can also sign, so key provisioning and device identity require independent, recorded evidence. The probe never locks a configuration zone or writes keys.

Reference: [Microchip ATECC608C](https://www.microchip.com/en-us/product/atecc608c).

## 4. Printer, FPGA and RunPod

- The existing Paper Console code provides opt-in ESC/POS USB/serial/TCP sinks, but a successful write is **SENT_UNCONFIRMED** until the physical receipt is observed and its optical scan is independently verified using a separately pinned trust anchor. Do not send health/personally identifying data to an unattended printer.
- The Tessera-G Vivado Arty A7-100T program remains in `tessera-g/fpga/arty_a7_100t/`. The bitstream needs real licensed Vivado on the target host; physical FPGA acceptance needs on-board readback and independent observation, not a blinking demo LED alone.
- RunPod AMD hardware execution needs a connected RunPod account, actual compatible physical GPU, and verified device output. A CPU runner does not meet this criterion.
- The PoPC-PU RTL is a **sign-request logic gate**, not a PUF, a trusted power sensor, a cryptographic signer, a thermodynamics proof, or a printer ASIC.

## 5. What counts as acceptance

Every external gate requires device identification, accountable operator, observed action, software/firmware hashes, calibration evidence where applicable, and a signed record with an independent verifier. **Do not stamp `PASS` from simulated hardware data.**

This checklist is a reviewed proposal for actual bench work; it does not imply that a printer/FPGA/secure element was purchased or connected.
