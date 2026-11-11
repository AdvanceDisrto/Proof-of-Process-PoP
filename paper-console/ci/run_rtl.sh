#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for cmd in iverilog vvp verilator yosys; do
  command -v "$cmd" >/dev/null || { echo "RTL_TEST=NOT_RUN missing=$cmd" >&2; exit 42; }
done
mkdir -p evidence/rtl
iverilog -g2012 -Wall -s tb_popc_gate -o evidence/rtl/popc.vvp rtl/popc_gate.sv rtl/tb_popc_gate.sv
vvp evidence/rtl/popc.vvp | tee evidence/rtl/icarus.log
grep -q 'POPC_GATE_SIM=PASS' evidence/rtl/icarus.log
verilator --lint-only --top-module popc_gate -Wall rtl/popc_gate.sv > evidence/rtl/verilator.log 2>&1
echo 'POPC_GATE_VERILATOR_STRICT_LINT=PASS'
yosys -Q -T -p 'read_verilog -sv rtl/popc_gate.sv; synth -top popc_gate; check -assert; stat' > evidence/rtl/yosys.log
printf '%s\n' 'POPC_GATE_YOSYS_GENERIC_SYNTH=PASS (not physical hardware)'
