#!/usr/bin/env bash
set -euo pipefail
make test-e2e
cat E2E_REALITY_MANIFEST.json
