# iCore™ Digital Systolic RTL — v0.3 Coverage Gate

The implementation is a **2×2 output-stationary digital systolic array**,
not a 4×4 array, a tiled 4×4 implementation, a weight-stationary core,
an FPGA design with verified timing, or fabricated/photonic hardware.

The compute engine multiplies signed INT8 2×2 matrices and accumulates each
result in signed INT32. There is one 2×2 tile per 2×2 multiplication; it
does **not** implement an arbitrary matrix-size tiling scheduler.

## Dataflow and skew

For output cell C[i,j], the two products are A[i,k] × B[k,j] for k=0,1.
A[i,k] enters from the west at wavefront tick i+k; B[k,j] enters from
the north at tick j+k. Registered PE outputs propagate to eastern and
southern neighbors. Each output PE accumulates its own INT32 partial sum.

```
           B column 0   B column 1
               ↓            ↓
A row 0 →   PE(0,0)  →   PE(0,1)
               ↓            ↓
A row 1 →   PE(1,0)  →   PE(1,1)
```

The first nonzero product at the farthest PE arrives later than at PE(0,0);
the controller's existing testbench observes `done` after four counted
negative-edge waits following its start setup; that is an interface-specific
schedule, not a universal `2N-1` hardware theorem.

## v0.3 deterministic regression

Actual Icarus simulation compares all four INT32 cells against an
independently calculated integer reference for:

| Test category | Count | Description |
| --- | ---: | --- |
| Corner / structured | 32 | Zero, identity, extrema, signed edge patterns and bounded structured patterns |
| Skew-specific | 16 | Single-hot A, single-hot B, paired corner/diagonal impulses |
| Immediate post-completion restart | 4 | Reassert start at the earliest following accepting clock edge, without reset |
| Interrupted wavefront reset + clean restart | 4 | Four different reset phases |
| Seeded random | 512 | Fixed LCG seed `0x00091911`; full INT8 signed range |
| Bit-exact deterministic replay | 1000 | Repeated fixed vector compared against captured 128-bit result |
| **Total checked operations** | **1568** | One extra uncounted replay baseline also executes |

This is a coverage **count**, not a claim that every possible category or
all 2^(64) matrix-input pairs have been covered.

## Reproduce

```bash
iverilog -g2012 -Wall -s tb_icore_systolic_2x2 -o /tmp/icore-systolic \
  rtl/icore_pe.sv rtl/icore_systolic_2x2.sv tb/tb_icore_systolic_2x2.sv
vvp /tmp/icore-systolic | tee systolic-simulation.log
yosys -Q -T -l systolic-synthesis.log -p \
  'read_verilog -sv rtl/icore_pe.sv rtl/icore_systolic_2x2.sv; hierarchy -check -top icore_systolic_2x2; proc; opt; check -assert; synth -top icore_systolic_2x2; stat'
```

GitHub CI executes these steps from the repository root. It also writes
`icore-rtl-evidence.json`, binding exact RTL/testbench bytes and logs through
SHA-256 hashes, with `physical_gate=ACTION_REQUIRED`.

## Next: actual FPGA implementation

A board-specific wrapper (clock/reset, UART/host control, I/O), pin map,
FPGA technology mapping, placement-and-route, clock timing, bitstream
generation and real board programming are **not** established by this CI.

A bitstream hash is provenance for a file, not evidence by itself that an
FPGA was programmed or operated correctly. Hardware acceptance requires
a captured observation from the programmed board plus independently
checked results and appropriate witness/identity controls.
