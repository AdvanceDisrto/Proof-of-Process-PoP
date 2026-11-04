# iCore™ iISA-0.1: Verified RTL Milestone

This repository contains a synthesizable **sequential** fixed-point 4×4 signed
INT8 × signed INT8 → INT32 matrix multiplier. It is **not** yet a systolic array,
an iISA instruction decoder, a cryptographic accelerator, or a photonic device.

## Verified interface and schedule

- Row-major flattened A/B input; inputs are latched on `start` when idle.
- 64 MAC positive clock edges per operation. Current testbench observes
  `done` after **63 counted negative-edge waits** from the initial setup edge.
- `start` while `busy` does not queue/restart; asynchronous input changes
  after start do not alter the stored operation.
- Active-low synchronous reset clears the output and interrupts a running MAC.
- Signed full 16-bit product is sign-extended into INT32 accumulator.
  INT32 is sufficient for all 4 products of signed INT8 inputs.

## Reproduce

```bash
iverilog -g2012 -s tb_icore_matmul -o /tmp/icore-sim \
  rtl/icore_matmul.sv tb/tb_icore_matmul.sv
vvp /tmp/icore-sim
yosys -Q -T -l synthesis.log -p \
  'read_verilog -sv rtl/icore_matmul.sv; hierarchy -check -top icore_matmul; proc; opt; check -assert; synth -top icore_matmul; stat'
```

The testbench checks cases 0–5 (including extrema), a deterministic replay,
reset at MAC step 17, start-while-busy isolation, strict cycle accounting and
**1000 reproducible seeded random cases** against an independent integer
matrix-multiplication reference: **1007 operation vectors** in total.

## Evidence boundary / next gates

1. RTL simulation: actual Icarus run must print
   `ALL_RTL_SIMULATION_TESTS_PASS vectors=1007 expected_cycles=63`.
2. Generic synthesis: actual Yosys `check -assert` must pass. Generic gate
   cell counts are **not** FPGA timing, LUT/DSP usage or power estimates.
3. Target-specific mapping and place-and-route: select a real FPGA board and
   verify its exact part, pin map, clock constraint and available memory/DSP.
4. Physical FPGA: load the bitstream on the actual device, capture UART/PCIe
   results, compare with independent reference and record an observation that
   binds the actual programmed bitstream hash to observed outputs.
5. Independent witness/identity checks: required to elevate any receipt above
   software process evidence.

A bitstream hash identifies a file; by itself it does **not** prove the file
was loaded into physical hardware or that a real FPGA executed the computation.
**PHYSICAL_GATE: ACTION_REQUIRED** until measured physical evidence exists.
