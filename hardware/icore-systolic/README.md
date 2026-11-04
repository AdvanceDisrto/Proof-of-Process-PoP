# iCore iISA v0.2 — 2×2 output-stationary systolic digital core

A 2×2 PE wavefront that computes signed INT8 matrix multiplication with INT32 accumulators. Each PE receives its A operand from the west and B operand from the north, forwarding registered values east/south. Matrices are latched on `start`. The controller injects skewed edge streams for a fixed 2×2 shape and reports `done` after the pipeline drains.

Scope boundaries: **Output-stationary**, not weight-stationary; no opcode decoding, FPGA bitstream, board programming, hardware attestation, or optical logic. These require further engineering.

To simulate:
```sh
iverilog -g2012 -s tb_icore_systolic_2x2 -o /tmp/a rtl/icore_pe.sv rtl/icore_systolic_2x2.sv tb/tb_icore_systolic_2x2.sv
vvp /tmp/a
```

The testbench covers six fixed/replay/reset matrix invocations plus 256 seeded random cases, mathematical reference comparison, start-while-busy rejection, input latching, and reset abort.
