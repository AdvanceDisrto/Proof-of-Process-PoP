#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TESSERA="$(cd "$HERE/../.." && pwd)"
cd "$HERE"
command -v iverilog >/dev/null || { echo "IVERILOG=NOT_INSTALLED" >&2; exit 42; }
command -v vvp >/dev/null || { echo "VVP=NOT_INSTALLED" >&2; exit 42; }
command -v verilator >/dev/null || { echo "VERILATOR=NOT_INSTALLED" >&2; exit 42; }
command -v yosys >/dev/null || { echo "YOSYS=NOT_INSTALLED" >&2; exit 42; }
python3 ci/check_pins.py
mkdir -p evidence
iverilog -g2012 -Wall -s tb_tessera_g_arty_top -o evidence/arty_board_sim \
  "$TESSERA/rtl/tessera_g_dag_tile.sv" \
  tessera_g_arty_top.sv sim/tb_tessera_g_arty_top.sv
vvp evidence/arty_board_sim | tee evidence/arty_board_sim.log
grep -q 'TESSERA_ARTY_BOARD_SIM=PASS' evidence/arty_board_sim.log
verilator --lint-only -Wall --top-module tessera_g_arty_top \
  "$TESSERA/rtl/tessera_g_dag_tile.sv" tessera_g_arty_top.sv \
  > evidence/arty_verilator_lint.log 2>&1
echo "TESSERA_ARTY_VERILATOR_STRICT_LINT=PASS"
yosys -Q -T -p \
  "read_verilog -sv $TESSERA/rtl/tessera_g_dag_tile.sv tessera_g_arty_top.sv; synth -top tessera_g_arty_top; check -assert; stat" \
  > evidence/arty_yosys_generic_synth.log 2>&1
echo "TESSERA_ARTY_YOSYS_GENERIC_SYNTH=PASS (not a bitstream)"
echo "TESSERA_ARTY_BITSTREAM=NOT_BUILT (requires Vivado + licensed host)"
