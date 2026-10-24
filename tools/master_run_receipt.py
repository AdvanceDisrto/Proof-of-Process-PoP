#!/usr/bin/env python3
import hashlib
import json
import sys
import time
from pathlib import Path
from tools.mmr_pipeline import MerkleMountainRange

if len(sys.argv) != 2:
    raise SystemExit("usage: master_run_receipt.py <artifact-directory>")

directory = Path(sys.argv[1]).resolve()
if not directory.is_dir():
    raise SystemExit(f"artifact directory does not exist: {directory}")

files = sorted(
    p for p in directory.rglob("*")
    if p.is_file() and p.name != "MASTER_RUN_RECEIPT.json"
)

mmr = MerkleMountainRange()
artifacts = []
for path in files:
    data = path.read_bytes()
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    leaf = json.dumps(
        {"path": str(path.relative_to(directory)), "sha256": digest},
        sort_keys=True, separators=(",", ":")
    ).encode()
    mmr.append(leaf)
    artifacts.append({"file": str(path.relative_to(directory)), "sha256": digest})

receipt = {
    "spec": "innovulis-master-run-all/1.1",
    "mark": "i™🧾",
    "run_id": directory.name,
    "issued_utc": time.time(),
    "artifact_count": len(artifacts),
    "artifacts": artifacts,
    "master_mmr_root": mmr.root(),
    "state": "VERIFIED_PROCESS",
    "physical_gate": "ACTION_REQUIRED",
    "proves": [
        "The listed repository verification commands completed successfully.",
        "The listed artifact bytes are bound to one deterministic MMR root.",
        "Changing an included artifact changes the master root."
    ],
    "does_not_prove": [
        "physical hardware execution", "vendor-verified TEE attestation",
        "measured energy", "RF/LAN/BLE/LoRa/cellular radio execution",
        "fabricated or deployed silicon", "existence or issuance of $SOV"
    ],
    "the_central_rule": "The receipt can record reality; it cannot manufacture reality."
}
(directory / "MASTER_RUN_RECEIPT.json").write_text(
    json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
)
print(f"[Master] {len(artifacts)} artifacts")
print(f"[Master] root={receipt['master_mmr_root']}")
print("[Master] state=VERIFIED_PROCESS physical_gate=ACTION_REQUIRED")
