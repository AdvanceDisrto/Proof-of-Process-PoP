# iStick — Electrical and Manufacturing Hold Specification

**State: CANDIDATE ARCHITECTURE, NOT FAB-READY. DO NOT ORDER BASED ON THESE FILES.**

## Correct the original CH340E design

CH340E is a USB-to-UART converter, not a CPU capable of running Z3/C++ or directly hosting an I²C master. A reference USB-native MCU with native I²C support is necessary. This candidate uses the *family* RP2040, **not** a frozen board revision or a validated pin assignment. Full formal logic and Z3 run on the connected Linux host, not on the tiny MCU or secure element.

## Draft electrical connections

| Net | Participants | Policy |
|---|---|---|
| USB 5 V VBUS | USB connector → protected regulator | Cannot directly feed 3.3V MCU/sensors |
| USB D+/D− | USB connector → ESD protection → native USB2 controller | Calculate actual differential impedance for fab stack-up; not guaranteed by 4-layer count |
| 3.3V | regulator → MCU, sensor, ATECC | Check current, brownout, noise, operating limits |
| SDA/SCL | native I²C MCU pins ↔ MCP9808 and secure element | 3.3V pulled high; calculate pull-ups from bus capacitance |
| GND | all components and USB return | Check layout and EMC; plane != attack-proof shield |

The candidate JSON is audited for required named connections and miswired VBUS. It is **not a KiCad netlist** and does not assign any real package pins. Missing USB-C CC pull-downs, boot flash, RP2040 crystal/clocks, polarity, exact secure-element address and placement must be resolved from board-specific vendor documentation before ERC.

## Fabrication release criteria (all pending)

1. Freeze parts with supplier datasheets, footprint, pin mappings, lifecycle, supply chain risk and test fixtures.
2. Complete KiCad **schematic** with USB-C CC resistors, ESD diodes, regulator/load calculations, clock source, flash, reset/boot strap, I²C pull-ups, test points and safe power sequencing.
3. Run electrical rule check (ERC), documenting all exceptions.
4. Obtain exact fabrication stack-up and compute 90Ω USB differential pair geometry (trace width, separation, dielectric; validate the MCU's USB2 requirements). 6/6 mil is not a guarantee of impedance.
5. Route four layers, return paths, power distribution, sensor analog ground/noise constraints, decoupling near IC pins; run DRC and impedance checks.
6. Complete BOM, pick/place (CPL), assembly drawings, mask, silkscreen, drill drawing; generate and validate **real** Gerbers, Excellon drills and IPC-356/test-net data as required.
7. Prototype, current-limit power-on, device enumeration, I²C ID scan, calibration, range tests, ESD and stability, secure-element signing, recovery testing, repeatable UART/USB protocol framing.
8. Threat test USB bad-device cases, DFU/firmware signing and rollback, power and voltage/fault injection, physical tamper and manufacturing trust.
9. Mechanical check physical enclosure STL against the fabricated assembly and connector dimensions; test tolerances and environmental/ESD requirements. OpenSCAD output is a concept only.
10. **Separate, explicitly approved irreversible provisioning**: select key slot map, nonce/serial lifecycle, test challenge/signature, design rework/brick recovery, require two-person signoff. No automated zone lock in this repo.

## Anti-counterfeit caveat

A unique silicon serial and protected private key can support provenance if the public-key identity is itself authenticated. They do not by themselves establish a silicon PUF, defend against every glitch/power analysis attack or authenticate unprotected I²C sensor output.

## New-design secure element

Microchip lists ATECC608A as **Not Recommended for New Designs** (NRND) and recommends ATECC608B variants. Obtain current lifecycle, package and provisioning docs before choosing a final SKU. The part is an ECDSA P-256 device; it does not generate Ed25519 signatures.
