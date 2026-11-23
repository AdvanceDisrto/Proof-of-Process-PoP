#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m pytest -q tests
python generate_vectors.py
python verify_vectors.py
python -m compileall -q epu tests
printf 'EPU_T1_T6_PI_TAU_PYTHON_VERIFICATION_PASS\n'
