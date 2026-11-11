#!/usr/bin/env bash
# Deliberately programs SRAM (volatile). Does NOT overwrite persistent flash.
# Run only from a workstation physically connected to the matching Arty A7-100T.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIT="$HERE/output/tessera_g_arty_a7_100t.bit"
if [[ "${TESSERA_CONFIRM_PHYSICAL_BOARD:-}" != "ARTY_A7_100T_CONNECTED_AND_IDLE" ]]; then
  echo "PHYSICAL_FLASH=BLOCKED: set TESSERA_CONFIRM_PHYSICAL_BOARD=ARTY_A7_100T_CONNECTED_AND_IDLE after checking board owner/USB" >&2
  exit 41
fi
command -v openFPGALoader >/dev/null 2>&1 || {
  echo "PHYSICAL_FLASH=BLOCKED: openFPGALoader not installed" >&2; exit 42;
}
test -s "$BIT" || { echo "PHYSICAL_FLASH=BLOCKED: no real Vivado-generated bitstream" >&2; exit 43; }
sha256sum -c "$HERE/output/bitstream.sha256"
mkdir -p "$HERE/output"
echo "PHYSICAL_BOARD_DETECTION_START"
openFPGALoader -c digilent --detect | tee "$HERE/output/physical_board_detect.log"
# Device-specific -b configuration validates target type before SRAM programming.
openFPGALoader -b arty_a7_100t "$BIT" | tee "$HERE/output/sram_programming.log"
echo "TESSERA_ARTY_SRAM_LOAD=COMMAND_COMPLETED"
echo "PHYSICAL_DAG_ACCEPTANCE=PENDING_LED_AND_READBACK_WITNESS"
echo "Validate RGB0 green and four discrete LEDs. Record photo/serial/bitstream SHA separately."
