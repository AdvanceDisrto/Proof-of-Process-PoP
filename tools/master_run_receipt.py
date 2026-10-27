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
    "ilogic_derivation.json": "derivation",
    "envelope.json": "envelope",
    "cce_prototype_receipt.json": "receipt",
    "epistemic_tier_map.json": "log",
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

# A signed root over other artifacts is not evidence that tests passed.
# Require pytest's per-test JSON report and validate it before sealing.
report_path = directory / "test_results.json"
if not report_path.is_file():
    raise SystemExit("FAIL_CLOSED: missing test_results.json; refusing master receipt")
try:
    test_report = json.loads(report_path.read_text(encoding="utf-8"))
except (ValueError, OSError) as exc:
    raise SystemExit(f"FAIL_CLOSED: invalid pytest JSON report: {exc}") from exc

records = test_report.get("tests")
summary = test_report.get("summary")
if not isinstance(records, list) or not records or not isinstance(summary, dict):
    raise SystemExit("FAIL_CLOSED: pytest report has no per-test evidence")
if type(test_report.get("exitcode")) is not int or test_report["exitcode"] != 0:
    raise SystemExit("FAIL_CLOSED: pytest did not exit successfully")
counts = {"passed": 0, "skipped": 0, "xfailed": 0}
seen_nodes = set()
for record in records:
    if not isinstance(record, dict):
        raise SystemExit("FAIL_CLOSED: malformed per-test record")
    node = record.get("nodeid")
    outcome = record.get("outcome")
    if not isinstance(node, str) or not node or node in seen_nodes or outcome not in counts:
        raise SystemExit("FAIL_CLOSED: missing/duplicate test ID or non-accepting outcome")
    seen_nodes.add(node)
    counts[outcome] += 1
if counts["passed"] == 0 or summary.get("passed") != counts["passed"]:
    raise SystemExit("FAIL_CLOSED: pytest summary does not match passed records")
if summary.get("total") != len(records):
    raise SystemExit("FAIL_CLOSED: pytest summary does not match per-test count")
if any(summary.get(field, 0) for field in ("failed", "error", "errors", "xpassed")):
    raise SystemExit("FAIL_CLOSED: pytest reported failed tests or collection errors")
for field in ("skipped", "xfailed"):
    if summary.get(field, 0) != counts[field]:
        raise SystemExit("FAIL_CLOSED: skipped/expected-failure count mismatch")
test_summary = {
    "report_file": "test_results.json",
    "report_sha256": "sha256:" + hashlib.sha256(report_path.read_bytes()).hexdigest(),
    "passed": counts["passed"],
    "skipped": counts["skipped"],
    "xfailed": counts["xfailed"],
    "failed": 0,
    "total": len(records),
    "exitcode": test_report["exitcode"],
}

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
    "test_summary": test_summary,
    "receipt_count": sum(a["kind"] == "receipt" for a in artifacts),
    "log_count": sum(a["kind"] == "log" for a in artifacts),
    "derivation_count": sum(a["kind"] == "derivation" for a in artifacts),
    "envelope_count": sum(a["kind"] == "envelope" for a in artifacts),
    "artifacts": artifacts,
    "master_mmr_root": mmr.root(),
    "state": "VERIFIED_PROCESS",
    "physical_gate": "ACTION_REQUIRED",
    "proves": [
        "A machine-readable pytest report records each test outcome and exit code.",
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
