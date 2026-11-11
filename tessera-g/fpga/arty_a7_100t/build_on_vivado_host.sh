#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v vivado >/dev/null 2>&1; then
  echo "TESSERA_ARTY_BITSTREAM=NOT_BUILT: vivado command unavailable on this machine" >&2
  exit 42
fi
mkdir -p "$HERE/output"
vivado -mode batch -nojournal -nolog -source "$HERE/build_bitstream.tcl" \
  | tee "$HERE/output/vivado_build.log"
BIT="$HERE/output/tessera_g_arty_a7_100t.bit"
test -s "$BIT" || { echo "TESSERA_ARTY_BITSTREAM=FAIL: missing" >&2; exit 3; }
sha256sum "$BIT" | tee "$HERE/output/bitstream.sha256"
echo "TESSERA_ARTY_BITSTREAM=BUILT_NOT_FLASHED"
