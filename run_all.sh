#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

RUN_ID="${GITHUB_RUN_ID:-local-$(date -u +%Y%m%dT%H%M%SZ)}"
OUT="evidence/run-all/$RUN_ID"
mkdir -p "$OUT"

log_step() {
  local name="$1"; shift
  echo
  echo "======================================================================"
  echo "RUN-ALL :: $name"
  echo "======================================================================"
  "$@" 2>&1 | tee "$OUT/$name.log"
}

echo "======================================================================"
echo "i™ MONOREPO — RUN ALL INTEGRATED PROOF-OF-PROCESS SURFACES"
echo "======================================================================"
echo "run_id=$RUN_ID"
echo "physical_gate=ACTION_REQUIRED"
echo "rule=The receipt can record reality; it cannot manufacture reality."

python3 -m pip install --quiet -r requirements.txt

log_step ibare make test-ibare
log_step platform_architecture make test-platform-architecture
log_step render make test-render
log_step polyglot make test-polyglot
log_step iska make test-iska
log_step imcp make test-imcp
log_step ledger make test-ledger
log_step tee_scrape make test-tee-scrape
log_step antimatter make test-antimatter
log_step antimatter_tiered make test-am-tiered
log_step ambient make test-ambient
log_step omnipresent make test-omnipresent
log_step buddy_liveness make test-buddy-liveness
log_step inetty make test-inetty
log_step mmr make test-mmr

log_step pytest_all python3 -m pytest -q

python3 - <<'PY' > "$OUT/host_capabilities.json"
import json, platform, os
print(json.dumps({
    "spec": "innovulis-run-all-host-capabilities/1.0",
    "machine": platform.machine(),
    "system": platform.system(),
    "tee_devices": {
        "amd_sev_snp": os.path.exists("/dev/sev-guest"),
        "intel_tdx": os.path.exists("/dev/tdx-guest"),
        "intel_sgx": os.path.exists("/dev/sgx_enclave"),
    },
    "physical_gate": "ACTION_REQUIRED",
    "does_not_prove": [
        "hardware attestation", "TEE execution", "measured energy",
        "physical radio execution"
    ],
}, indent=2))
PY

python3 tools/mmr_pipeline.py 5000 "$OUT/mmr_5000.json"
python3 tools/master_run_receipt.py "$OUT"

echo
echo "======================================================================"
echo "RUN-ALL COMPLETE"
echo "======================================================================"
python3 - <<PY
import json
from pathlib import Path
r=json.loads(Path("$OUT/MASTER_RUN_RECEIPT.json").read_text())
print("artifacts:       ", r["artifact_count"])
print("master_mmr_root: ", r["master_mmr_root"])
print("state:            ", r["state"])
print("physical_gate:   ", r["physical_gate"])
print("run_id:           ", r["run_id"])
PY
