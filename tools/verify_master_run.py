#!/usr/bin/env python3
"""Independently re-hash a run-all evidence directory and check pytest evidence.

Checks integrity of a LOCAL, UNSIGNED artifact commitment. Not a hardware quote,
signature-chain verifier, or authority for claims contained in the artifacts.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.mmr_pipeline import MerkleMountainRange


def verify(directory: Path) -> dict:
    directory = directory.resolve()
    receipt_file = directory / "MASTER_RUN_RECEIPT.json"
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    if receipt.get("spec") != "innovulis-master-run-all/1.2":
        raise ValueError("unexpected master receipt spec")
    if receipt.get("physical_gate") != "ACTION_REQUIRED":
        raise ValueError("unsubstantiated physical gate promotion")
    listed = receipt.get("artifacts")
    if not isinstance(listed, list) or not listed:
        raise ValueError("no listed artifacts")

    actual = sorted(str(p.relative_to(directory)) for p in directory.rglob("*")
                    if p.is_file() and p.name != "MASTER_RUN_RECEIPT.json")
    recorded = [x["file"] for x in listed]
    if recorded != actual or len(recorded) != len(set(recorded)):
        raise ValueError("missing, duplicate, or unexpected artifact")
    if receipt.get("artifact_count") != len(actual):
        raise ValueError("artifact count mismatch")
    mmr = MerkleMountainRange()
    for item in listed:
        path = directory / item["file"]
        data = path.read_bytes()
        digest = "sha256:" + hashlib.sha256(data).hexdigest()
        if item.get("sha256") != digest:
            raise ValueError("artifact hash mismatch: " + item["file"])
        leaf = json.dumps({"path": item["file"], "kind": item["kind"], "sha256": digest},
                          sort_keys=True, separators=(",", ":")).encode()
        mmr.append(leaf)
    if receipt.get("master_mmr_root") != mmr.root():
        raise ValueError("master MMR root mismatch")

    summary = receipt.get("test_summary")
    if not isinstance(summary, dict) or summary.get("report_file") != "test_results.json":
        raise ValueError("no pinned pytest report")
    raw = (directory / "test_results.json").read_bytes()
    if summary.get("report_sha256") != "sha256:" + hashlib.sha256(raw).hexdigest():
        raise ValueError("pytest report hash mismatch")
    report = json.loads(raw)
    tests = report.get("tests")
    if not isinstance(tests, list) or not tests or report.get("exitcode") != 0:
        raise ValueError("invalid test execution evidence")
    counts = {kind: sum(t.get("outcome") == kind for t in tests)
              for kind in ("passed", "skipped", "xfailed")}
    if (sum(counts.values()) != len(tests) or counts["passed"] == 0
            or len({t.get("nodeid") for t in tests}) != len(tests)
            or any(not isinstance(t.get("nodeid"), str) or not t["nodeid"] for t in tests)
            or report.get("summary", {}).get("total") != len(tests)
            or report["summary"].get("passed") != counts["passed"]
            or any(report["summary"].get(x, 0) for x in ("failed", "error", "errors", "xpassed"))):
        raise ValueError("failed, inconsistent, or forged per-test report")
    for field in ("skipped", "xfailed"):
        if report["summary"].get(field, 0) != counts[field]:
            raise ValueError("pytest non-pass counts mismatch")
    for field in ("passed", "skipped", "xfailed"):
        if summary.get(field) != counts[field]:
            raise ValueError("master test summary mismatch: " + field)
    if summary.get("failed") != 0 or summary.get("exitcode") != 0 or summary.get("total") != len(tests):
        raise ValueError("master test totals invalid")

    return {
        "verdict": "ACCEPT_LOCAL_ARTIFACT_INTEGRITY_ONLY",
        "artifact_count": len(actual),
        "test_summary": summary,
        "master_mmr_root": mmr.root(),
        "physical_gate": "ACTION_REQUIRED",
        "signature_verified": False,
        "hardware_attested": False,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tools/verify_master_run.py <artifact-directory>")
    try:
        print(json.dumps(verify(Path(sys.argv[1])), indent=2))
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"verdict": "REJECT", "reason": str(exc)}), file=sys.stderr)
        raise SystemExit(2) from exc
