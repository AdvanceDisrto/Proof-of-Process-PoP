#!/usr/bin/env python3
"""Create an evidence seal for a generated MMR receipt.

The seal records artifact integrity and CI provenance. A SHA-256 digest is an
integrity fingerprint, not a signature and not proof of physical execution.
"""
import hashlib
import json
import sys
from pathlib import Path

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: mmr_artifact_seal.py <artifact> <run_id> <output>")
    artifact = Path(sys.argv[1])
    run_id = str(sys.argv[2])
    output = Path(sys.argv[3])
    receipt = json.loads(artifact.read_text(encoding="utf-8"))
    seal = {
        "spec": "innovulis-mmr-artifact-seal/1.1",
        "repository": "AdvanceDisrto/Proof-of-Process-PoP",
        "ci_run": run_id,
        "artifact_evidence": {
            "name": artifact.name,
            "size_bytes": artifact.stat().st_size,
            "sha256": sha256_file(artifact)
        },
        "layer_evaluation": {
            "Class_5000_MMR": {
                "state": receipt["state"],
                "task_count": receipt["task_count"],
                "input_status": receipt["input_status"]
            },
            "Rust_Architecture": {
                "state": "SPECIFIED_ONLY"
            },
            "Physical_Hardware": {
                "state": receipt["physical_gate"]
            }
        },
        "proves": [
            "The generated MMR receipt has the recorded SHA-256 integrity fingerprint.",
            "The CI workflow produced the referenced receipt artifact.",
            "The implemented MMR produced a deterministic root and detected leaf tampering."
        ],
        "does_not_prove": [
            "Physical hardware execution.",
            "RF, LoRa, cellular, ZK, PPoV, or settlement execution.",
            "That SHA-256 is a digital signature.",
            "That a compiler target or ISA feature flag executed on physical silicon."
        ],
        "state": receipt["state"],
        "physical_gate": receipt["physical_gate"],
        "the_central_rule": "The receipt can record reality; it cannot manufacture reality."
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(seal, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
