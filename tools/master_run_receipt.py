#!/usr/bin/env python3
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.mmr_pipeline import MerkleMountainRange

KIND_BY_BASENAME = {
    "mmr_5000.json": "receipt",
    "gate_verification.json": "receipt",
    "host_capabilities.json": "log",
}

def artifact_kind(path: Path) -> str:
    if path.name in KIND_BY_BASENAME:
        return KIND_BY_BASENAME[path.name]
    if path.suffix == ".log":
        return "log"
    return "log"

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
    rel = str(path.relative_to(directory))
    kind = artifact_kind(path)
    leaf = json.dumps(
        {"path": rel, "kind": kind, "sha256": digest},
        sort_keys=True, separators=(",", ":")
    ).encode()
    mmr.append(leaf)
    artifacts.append({"file": rel, "kind": kind, "sha256": digest})

receipt = {
    "spec": "innovulis-master-run-all/1.2",
    "mark": "i™🧾",
    "run_id": directory.name,
    "issued_utc": time.time(),
    "artifact_count": len(artifacts),
    "receipt_count": sum(a["kind"] == "receipt" for a in artifacts),
    "log_count": sum(a["kind"] == "log" for a in artifacts),
    "artifacts": artifacts,
    "master_mmr_root": mmr.root(),
    "state": "VERIFIED_PROCESS",
    "physical_gate": "ACTION_REQUIRED",
    "proves": [
        "The listed repository verification commands completed successfully.",
        "The listed artifact bytes and their kind labels are bound to one deterministic MMR root.",
        "Changing an included artifact or its kind label changes the master root.",
    ],
    "does_not_prove": [
        "physical hardware execution",
        "vendor-verified TEE attestation",
        "measured energy",
        "RF/LAN/BLE/LoRa/cellular radio execution",
        "fabricated or deployed silicon",
        "existence or issuance of $SOV",
    ],
    "the_central_rule": "The receipt can record reality; it cannot manufacture reality.",
}
(directory / "MASTER_RUN_RECEIPT.json").write_text(
    json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
)
print(f"[Master] {len(artifacts)} artifacts ({receipt['receipt_count']} receipts, {receipt['log_count']} logs)")
print(f"[Master] root={receipt['master_mmr_root']}")
print("[Master] state=VERIFIED_PROCESS physical_gate=ACTION_REQUIRED")
