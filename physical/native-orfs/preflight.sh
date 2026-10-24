#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
test -f "$root/rtl/ispu10240/SHA256SUMS.v1.5"
test -f "$root/rtl/ispu10240/SPU_Sovereign_10240_Lock.sv"
test -f "$root/materialization/topology.pending.json"
if grep -RniE 'docker|podman|tapeoutReady[[:space:]]*=[[:space:]]*true|real20MiBSramProven[[:space:]]*=[[:space:]]*true' "$root/physical/native-orfs" --exclude=README.md --exclude=preflight.sh; then
  echo "FAIL: native ORFS boundary violation"
  exit 1
fi
echo "NATIVE_ORFS_PREFLIGHT=PASS"
echo "real20MiBSramProven=false"
echo "tapeoutReady=false"
echo "physical_gate=ACTION_REQUIRED"
