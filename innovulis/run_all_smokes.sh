#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-18765}"
OUT="${OUTPUT_DIR:-${ROOT}/evidence}"
mkdir -p "$OUT"
export INNOVULIS_API_KEYS="${INNOVULIS_API_KEYS:-$(python3 -c 'import secrets; print(secrets.token_hex(24))')}"
export INNOVULIS_SIGNING_SEED="${INNOVULIS_SIGNING_SEED:-$(python3 -c 'import secrets; print(secrets.token_hex(32))')}"
export INNOVULIS_DB="${INNOVULIS_DB:-${OUT}/receipts.db}"
export PYTHONPATH="${ROOT}/api${PYTHONPATH:+:$PYTHONPATH}"
export BASE_URL="http://127.0.0.1:${PORT}"
uvicorn main:app --host 127.0.0.1 --port "$PORT" >"$OUT/server.log" 2>&1 &
PID=$!
trap 'kill "$PID" 2>/dev/null || true; wait "$PID" 2>/dev/null || true' EXIT
python3 - <<'PY'
import os,time,urllib.request
url=os.environ['BASE_URL']+'/health'
for i in range(90):
 try:
  with urllib.request.urlopen(url,timeout=1) as r:
   assert r.status==200
  break
 except Exception: time.sleep(.2)
else: raise SystemExit('API_STARTUP_FAILED')
PY
python3 "${ROOT}/smoke_client.py" "$OUT"
python3 "${ROOT}/smoke_hash_client.py" "$OUT"
python3 -m pytest -q "$ROOT/tests" | tee "$OUT/pytest.log"
echo "ALL_SOFTWARE_SMOKES_PASSED (photonic/FPGA physical gate not executed)"
