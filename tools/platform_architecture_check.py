#!/usr/bin/env python3
"""Validate the software architecture contract across x86_64 and AArch64.

This test identifies the host ISA exposed to the process. It does not attest
physical silicon, virtualization state, accelerator execution, or ISA feature
execution.
"""
import json
import platform
from pathlib import Path

MATRIX = Path("schemas/platform_architecture_matrix.json")
ALIASES = {
    "x86_64": "x86_64",
    "AMD64": "x86_64",
    "amd64": "x86_64",
    "aarch64": "aarch64",
    "arm64": "aarch64",
    "ARM64": "aarch64",
}

matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
host = ALIASES.get(platform.machine(), platform.machine())
supported = set(matrix["architectures"])
if host not in supported:
    raise SystemExit(f"UNSUPPORTED_HOST_ARCHITECTURE:{platform.machine()}")

print(f"host_architecture={host}")
print("portable_contract=C11/Python3.12/SHA-256/deterministic-JSON")
print("physical_execution_claim=ACTION_REQUIRED")
print("platform_architecture=VERIFIED_PROCESS")
