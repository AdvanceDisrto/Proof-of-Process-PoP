#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r cih_api/requirements-dev.txt
.venv/bin/python -m pytest -q cih_api/test_app.py
echo "Tests passed; starting loopback-only CIH API on http://127.0.0.1:8000"
echo "No pretend PROVEN_TRUE path. Signing & Auth0 require configured secrets."
exec .venv/bin/python -m uvicorn cih_api.app:app --host 127.0.0.1 --port 8000
