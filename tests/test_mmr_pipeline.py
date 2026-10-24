# Copyright 2026 AdvanceDisrto · Apache-2.0
import hashlib
import json
from dataclasses import asdict

from tools.mmr_pipeline import MerkleMountainRange, run_pipeline, synthesize_receipt


def encode(receipt):
    return json.dumps(asdict(receipt), sort_keys=True, separators=(",", ":")).encode()


def test_mmr_empty_root():
    assert MerkleMountainRange().root() == "sha256:" + hashlib.sha256(b"").hexdigest()


def test_mmr_single_leaf():
    mmr = MerkleMountainRange()
    mmr.append(b"leaf")
    assert mmr.root().startswith("sha256:")


def test_mmr_deterministic():
    left, right = MerkleMountainRange(), MerkleMountainRange()
    for i in range(10):
        leaf = encode(synthesize_receipt(i + 1))
        left.append(leaf)
        right.append(leaf)
    assert left.root() == right.root()


def test_mmr_tamper_changes_root():
    baseline = encode(synthesize_receipt(1))
    tampered = baseline.replace(b'"output_state_hash"', b'"OUTPUT_state_hash"')
    left, right = MerkleMountainRange(), MerkleMountainRange()
    left.append(baseline)
    right.append(tampered)
    assert left.root() != right.root()


def test_mmr_peak_counts():
    mmr = MerkleMountainRange()
    for i in range(8):
        mmr.append(f"leaf-{i}".encode())
    assert len(mmr.peaks) == 1
    for i in range(8, 11):
        mmr.append(f"leaf-{i}".encode())
    assert len(mmr.peaks) == 3


def test_pipeline_5000(tmp_path):
    result = run_pipeline(5000, str(tmp_path / "receipt.json"))
    assert result["task_count"] == 5000
    assert result["classes_represented"] == {"1000":1000,"2000":1000,"3000":1000,"4000":1000,"5000":1000}
    assert len(result["mmr_peaks"]) == 5
    assert result["state"] == "VERIFIED_PROCESS"
    assert result["physical_gate"] == "ACTION_REQUIRED"


def test_pipeline_10000_gate_stays_locked(tmp_path):
    result = run_pipeline(10000, str(tmp_path / "receipt.json"))
    assert result["task_count"] == 10000
    assert result["physical_gate"] == "ACTION_REQUIRED"
