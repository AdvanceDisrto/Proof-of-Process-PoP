"""Master-run receipt requires machine-readable, independently checkable test evidence."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.verify_master_run import verify

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "master_run_receipt.py"


def fixture_evidence(tmp_path):
    d = tmp_path / "run-001"
    d.mkdir()
    (d / "ibare.log").write_text("selftest pass\\n", encoding="utf-8")
    r = {
        "exitcode": 0,
        "summary": {"passed": 2, "total": 2},
        "tests": [
            {"nodeid": "tests/test_example.py::test_one", "outcome": "passed"},
            {"nodeid": "tests/test_example.py::test_two", "outcome": "passed"},
        ],
    }
    (d / "test_results.json").write_text(json.dumps(r), encoding="utf-8")
    return d


def build(d):
    return subprocess.run([sys.executable, str(BUILDER), str(d)],
                          capture_output=True, text=True)


def test_pytest_records_bound_to_master_mmr(tmp_path):
    d = fixture_evidence(tmp_path)
    assert build(d).returncode == 0
    rec = json.loads((d / "MASTER_RUN_RECEIPT.json").read_text())
    assert rec["test_summary"]["passed"] == 2
    assert rec["test_summary"]["failed"] == 0
    assert "test_results.json" in [x["file"] for x in rec["artifacts"]]
    assert verify(d)["verdict"] == "ACCEPT_LOCAL_ARTIFACT_INTEGRITY_ONLY"


def test_missing_report_fails_before_seal(tmp_path):
    d = fixture_evidence(tmp_path)
    (d / "test_results.json").unlink()
    r = build(d)
    assert r.returncode != 0
    assert "FAIL_CLOSED" in r.stderr
    assert not (d / "MASTER_RUN_RECEIPT.json").exists()


def test_failed_test_refused_even_with_zero_exitcode(tmp_path):
    d = fixture_evidence(tmp_path)
    report = json.loads((d / "test_results.json").read_text())
    report["tests"][0]["outcome"] = "failed"
    report["summary"] = {"failed": 1, "passed": 1, "total": 2}
    (d / "test_results.json").write_text(json.dumps(report))
    assert build(d).returncode != 0


def test_nonzero_pytest_exitcode_refused(tmp_path):
    d = fixture_evidence(tmp_path)
    report = json.loads((d / "test_results.json").read_text())
    report["exitcode"] = 1
    (d / "test_results.json").write_text(json.dumps(report))
    assert build(d).returncode != 0


def test_report_tamper_after_sealing_detected(tmp_path):
    d = fixture_evidence(tmp_path)
    assert build(d).returncode == 0
    (d / "test_results.json").write_text("{}")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        verify(d)


def test_master_root_tamper_detected(tmp_path):
    d = fixture_evidence(tmp_path)
    assert build(d).returncode == 0
    recp = d / "MASTER_RUN_RECEIPT.json"
    receipt = json.loads(recp.read_text())
    receipt["master_mmr_root"] = "sha256:" + "0" * 64
    recp.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="master MMR root mismatch"):
        verify(d)


def test_new_unlisted_artifact_rejected(tmp_path):
    d = fixture_evidence(tmp_path)
    assert build(d).returncode == 0
    (d / "added.log").write_text("unsealed")
    with pytest.raises(ValueError, match="unexpected artifact"):
        verify(d)


def test_master_summary_tamper_detected(tmp_path):
    d = fixture_evidence(tmp_path)
    assert build(d).returncode == 0
    recp = d / "MASTER_RUN_RECEIPT.json"
    receipt = json.loads(recp.read_text())
    receipt["test_summary"]["passed"] = 777
    recp.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="master test summary mismatch"):
        verify(d)
