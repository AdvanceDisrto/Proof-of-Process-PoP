# iCore iISA-0.1 RTL engineering milestone

Synthesizable fixed-point sequential 4×4 signed INT8 matrix multiplication with INT32 accumulation.
64 MAC clock cycles, operand latching, reset abort, busy/done handshake and no vendor-specific IP.

## Local commands
```bash
iverilog -g2012 -s tb_icore_matmul -o /tmp/icore_sim rtl/icore_matmul.sv tb/tb_icore_matmul.sv
vvp /tmp/icore_sim
yosys -Q -T -l synthesis.log -p 'read_verilog -sv rtl/icore_matmul.sv; hierarchy -check -top icore_matmul; proc; opt; check -assert; synth -top icore_matmul; stat'
```

CI runs actual Icarus Verilog simulation and Yosys synthesis. This is not FPGA placement/routing, board testing, photonic computing, on-chip signing, or fabricated silicon. These latter milestones remain unverified.
