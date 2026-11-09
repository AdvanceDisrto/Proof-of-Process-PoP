#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="$REPO/unified-i:$REPO/paper-console:$REPO/paper-console/integrations:$REPO/human-hub:$REPO/ipcih:$REPO/twinions-legal:${PYTHONPATH:-}"
cd "$REPO"
mkdir -p unified-i/evidence
python -m pytest -q --import-mode=importlib unified-i/tests paper-console/tests human-hub/tests twinions-legal/tests --disable-warnings | tee unified-i/evidence/integrated_python_tests.log
(cd ipcih && python -m pytest -q tests --disable-warnings) | tee unified-i/evidence/ipcih_python_tests.log
python -m unified_i smoke-synthetic --out unified-i/evidence/synthetic-smoke > unified-i/evidence/closed_loop_stdout.json
python unified-i/ci/smoke_http_live.py | tee unified-i/evidence/live_http_smoke.json
bash unified-i/ci/smoke_hardware.sh | tee unified-i/evidence/hardware_host_smoke.log
python -m unified_i audit-board unified-i/hardware/istick_reference.json | tee unified-i/evidence/board_candidate_audit.json
node --test ipcih/tests/test_browser.mjs | tee unified-i/evidence/ipcih_webcrypto_tests.log
printf '%s\n' 'UNIFIED_I_SOFTWARE_INTEGRATION=PASS (NO PHYSICAL ACCEPTANCE)'
