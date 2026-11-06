# FABRICATION HOLD — REV0

**NO-GO for ordering as an assembled custom PCB.** This package deliberately does not claim KiCad DRC/ERC, valid Gerbers, assembly drawings, stackup, BOM source stock, CPL positions, or a tested custom board.

## Mandatory release checklist

- [ ] Approve host adapter mechanical connector: Pi Zero 40-pin, CM4 dual 100-pin, or separate x86/RISC-V adapter. Never treat connectors as interchangeable.
- [ ] Select real, orderable manufacturer part numbers and verify footprint pads and pin numbering against current datasheets.
- [ ] Choose ATECC608C P-256 evidence version and provisioning plan, or a separately verified Ed25519-capable secure device.
- [ ] Supply the exact shunt footprint, Kelvin geometry, resistor tolerance, power rating, ADC configuration and per-module current bounds.
- [ ] Size regulator, fuse, input protection, power planes and trace widths from load/temperature measurements rather than generic 1-mm assumptions.
- [ ] Design KiCad schematic, assign footprints and pin mappings; pass electrical rules check.
- [ ] Design 4-layer PCB and impedance calculation for **actual selected fab stackup**; pass DRC and routing review.
- [ ] Check E-Ink controller and board/display compatibility: dedicated BUSY GPIO, SPI command wiring, vendor power and level shifting.
- [ ] Independent review of all CSI/PCIe pairs if included. No high-speed interface allocated in Rev0.
- [ ] Generate **real** Gerber/Excellon, BOM and CPL from verified PCB CAD source; inspect in an independent Gerber viewer.
- [ ] Sign off board test points, power-up without SoM, isolation, I2C read-only scan, secure key provisioning, thermal testing.
- [ ] Preserve revisioned, signed manufacturing release; annotate exactly what physical evidence was produced.

Do not submit this engineering interface package directly as a JLCPCB/PCBWay board order. Do not claim USPTO reduction to practice is complete without counsel reviewing documented actual hardware evidence and application disclosure.
