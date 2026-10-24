from __future__ import annotations

import json
import subprocess
from pathlib import Path


def main() -> None:
    result = subprocess.run(
        ["./build/render_combo"], check=True, capture_output=True, text=True
    )
    observed = dict(line.split("=", 1) for line in result.stdout.strip().splitlines())
    receipt = {
        "spec": "innovulis-cpu-render/2.0",
        "algorithm": observed["algorithm"],
        "framebuffer_sha256": "sha256:" + observed["framebuffer_sha256"],
        "process_receipt": "sha256:" + observed["process_receipt"],
        "state": "VERIFIED_PROCESS",
        "physical_gate": "ACTION_REQUIRED",
        "energy": {
            "state": "ACTION_REQUIRED",
            "measured_joules": None,
            "reason": "No independently verified physical energy sensor evidence supplied.",
        },
        "proves": [
            "The hosted CPU ray tracer executed in CI.",
            "The framebuffer bytes were hashed by the iBare SHA-256 implementation.",
            "The deterministic manifest receipt was generated from the framebuffer hash.",
        ],
        "does_not_prove": [
            "Physical energy consumption or a per-instruction electrical footprint.",
            "TPM quote or hardware-rooted attestation.",
            "SIMD execution merely because optimization flags were requested.",
            "ASIC execution, RTL equivalence, fabrication, or foundry tape-out.",
            "That a cryptographic hash makes physical telemetry unforgeable.",
        ],
    }
    Path("RENDER_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    print(result.stdout, end="")
    print("render receipt generated: RENDER_RECEIPT.json")


if __name__ == "__main__":
    main()
