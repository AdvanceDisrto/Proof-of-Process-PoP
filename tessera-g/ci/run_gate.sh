#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
python3 -m unittest discover -s model -p 'test_*.py' -v
mkdir -p evidence
if ! command -v iverilog >/dev/null || ! command -v vvp >/dev/null; then
  echo 'TESSERA_G_RTL=NOT_RUN: iverilog/vvp missing' | tee evidence/rtl_status.log
  exit 42
fi
iverilog -g2012 -Wall -s tb_tessera_g -o evidence/tessera-g-sim rtl/tessera_g_dag_tile.sv sim/tb_tessera_g.sv
vvp evidence/tessera-g-sim | tee evidence/rtl_trace.log
python3 ci/compare_rtl_trace.py evidence/rtl_trace.log
if command -v verilator >/dev/null; then
  verilator --lint-only --top-module tessera_g_dag_tile -Wall rtl/tessera_g_dag_tile.sv > evidence/verilator_lint.log 2>&1
  echo 'VERILATOR_STRICT_LINT=PASS (all RTL warnings treated as failure)'
else
  echo 'VERILATOR_LINT=NOT_RUN' | tee evidence/verilator_lint.log
fi
if command -v yosys >/dev/null; then
  yosys -Q -T -p 'read_verilog -sv rtl/tessera_g_dag_tile.sv; synth -top tessera_g_dag_tile; check -assert; stat' > evidence/yosys_synthesis.log
  echo 'YOSYS_GENERIC_SYNTHESIS=PASS (generic logic, NOT FPGA bitstream or ASIC tapeout)'
else
  echo 'YOSYS_SYNTHESIS_LOGIC=NOT_RUN' | tee evidence/yosys_synthesis.log
fi
