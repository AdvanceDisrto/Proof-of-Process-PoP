# STRMKRD Modular Trust Node — REV0 Engineering Prototype

**Status: ENGINEERING PROTOTYPE, NOT FABRICATION READY.**

This is an implementable low-voltage **carrier/adapter interface specification and Linux sensor bring-up** to advance the physical gates. It is **not** a routed production PCB, not a silicon photonics chip, and not a validated manufacturer Gerber/CPL release.

## Rev0 scope and modular interface

- **HOST adapter**: 3.3 V logic, 40-pin Raspberry Pi-style expansion **on an existing host dev board** (Pi Zero 2 W or Pi CM4 IO board). x86, CM4/CM5, RISC-V, and future optical iSPU require **separate host adapter boards**; they are not pin-compatible modules.
- **TRUST/SENSE card**: I2C 0x18 MCP9808 temperature sensor; I2C 0x40 (or strapped 0x41) INA226 current/voltage/power monitor with Kelvin shunt in the **LOAD power conductor**; reserved I2C 0x60 secure element connection (P-256 ECDSA ATECC608C-compatible, NOT Ed25519).
- **OPTICAL adapter**: 3.3 V SPI display via existing, vendor-matched E-Ink breakout, not an unverified 24-pin bare display FPC; no printed-camera acceptance yet.
- **SPU expansion**: mechanical and electrical interface **TBD**; no fabricated PIC and no claim that PCIe signals may use arbitrary SPI/I2C pinouts.
- **POWER boundary**: use certified development board supply. The 5 V load monitor is wired **in series with the load after power conversion**, never with INA226 IN+ / IN− as the main load path; the sense pins only Kelvin-monitor the shunt. Do **not** feed 12 V into 3.3 V logic.

## Physical architecture

```
Certified 5V source -- fuse/ESD -- 2mOhm high-side SHUNT -- monitored 5V LOAD
                                     |           |
                                   IN+         IN-     (Kelvin sensing)
                                      INA226 ---> I2C
MCP9808 ---------------------------------------> I2C 3V3 logic (host adapter)
ATECC608C (unprovisioned, P-256) --------------> I2C (reserved, NOT signing yet)
E-Ink vendor breakout -------------------------> SPI host adapter
HOST: Pi Zero / CM4 IO / other approved HOST ADAPTER ---> Linux Z3/QoW/PoP
FUTURE iSPU daughtercard: defined after SPU interface electrical spec
```

## Manufacture gate

See `BOM_rev0.csv`, `NETS_rev0.csv`, and `MANUFACTURING_HOLD.md`. These are design-controlled **engineering inputs** and not fabricator-upload-ready BOM and pick-and-place coordinates. Gerbers, validated KiCad `.kicad_sch`, routed `.kicad_pcb`, DRC/ERC results, stackup impedance specification, selected parts availability, enclosure, and thermal/power budgets remain open.

## Linux bring-up (requires actual hardware)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r hardware/strmkrd-node/requirements-hardware.txt
python hardware/strmkrd-node/bringup.py --self-test
# Only on a real Linux host, after physically checking power and wiring:
python hardware/strmkrd-node/bringup.py --hardware --bus 1 --ina-address 0x40
```

To stream observations continuously from the physical device with a scoped Z3 range check (still **unsigned and unauthenticated**):

```bash
python hardware/strmkrd-node/observer.py --bus 1 --ina-address 0x40 --once
# systemd uses observer.py without --once, with bounded 60s intervals
```

Grant the dedicated service account membership in the existing Linux `i2c` group before enabling systemd; ensure `/dev/i2c-1` exists, the modules have 3.3V-safe I/O, and that no kernel hwmon driver already owns the INA226 address. The host must have a Python virtual environment, the linked requirements, and the service file's paths must match the installation.

The hardware command only performs register reads and, with explicit `--calibrate-ina`, programs the INA226 calibration register. It emits an **UNAUTHENTICATED** observation that must not be promoted into the PoP/QoW signer until actual device provisioning, witness identity, signature-verified envelopes, and persistent anti-replay are built.

## Architecture discrepancies resolved

- Raspberry Pi CM4/CM5 use two 100-pin board-to-board connectors; **CM4S** is the legacy SO-DIMM variant. An Intel x86 SoM is **not** pin-compatible with CM4 merely because its connector resembles SO-DIMM.
- ATECC608B is **not recommended for new designs**; Microchip recommends ATECC608C. Neither is a native Ed25519 signer; use a dedicated **ECDSA-P256** evidence profile if physically deployed.
- INA226 reads power in watts. Joules require time integration, calibrated shunt, bounded sampling error and independently documented meter coverage.
- The current ipQR decoder accepts a registered source PNG; a real printed-phone capture remains unverified.
- Optical SPU mesh, photons-per-operation, near-zero entropy and hardware sign-at-origin are research objectives, not measured results.

## Sources

- Raspberry Pi CM docs: https://www.raspberrypi.com/documentation/computers/compute-module.html
- Microchip ATECC608C migration: https://onlinedocs.microchip.com/oxy/GUID-37C348DA-53FC-45CB-A3A3-9163D81C42E4-en-US-2/GUID-E20D34E2-217D-4EEB-B6F6-AFB01A712367.html
- TI INA226: https://www.ti.com/product/INA226
- MCP9808: https://www.microchip.com/en-us/product/MCP9808
