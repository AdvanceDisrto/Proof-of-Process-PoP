#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/evidence"
mkdir -p "$OUT"
command -v g++ >/dev/null || { echo 'C++ compiler missing' >&2; exit 42; }
g++ -std=c++20 -O2 -Wall -Wextra -Werror -pedantic "$ROOT/hardware/istick_host_readonly.cpp" -o "$OUT/istick_host_selftest"
"$OUT/istick_host_selftest" --self-test | tee "$OUT/cpp_gate.log"
if command -v openscad >/dev/null; then
  openscad -o "$OUT/enclosure_preliminary.stl" "$ROOT/hardware/enclosure_PRELIMINARY.scad" > "$OUT/openscad.log" 2>&1
  test -s "$OUT/enclosure_preliminary.stl"
  echo 'ENCLOSURE_STL_RENDER=PASS CONCEPT_ONLY_NOT_FIT_VERIFIED'
else
  echo 'ENCLOSURE_STL_RENDER=SKIPPED_OPENSCAD_NOT_INSTALLED'
fi
if bash "$ROOT/hardware/PROVISIONING_HOLD.sh" >/dev/null 2>&1; then
  echo 'FATAL: irreversible provisioning was not safely blocked' >&2; exit 1
fi
echo 'IRREVERSIBLE_PROVISIONING=BLOCKED_AS_REQUIRED'
