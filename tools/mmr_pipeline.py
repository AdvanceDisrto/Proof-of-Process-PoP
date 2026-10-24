#!/usr/bin/env python3
# Copyright 2026 AdvanceDisrto · Apache-2.0
"""Honest Class 5000 MMR pipeline.

Synthetic receipts are data fixtures, not evidence of physical execution.
The MMR implementation is append-only and peak-bagged.
"""
import hashlib
import json
import secrets
import time
from dataclasses import asdict, dataclass
from pathlib import Path


def jcs(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def sha_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_bytes(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


@dataclass
class ProcessTaskReceipt:
    task_id: int
    classification: int
    component_name: str
    hardware_enclave_timestamp: int
    input_state_hash: str
    output_state_hash: str
    runtime_signature: str


def synthesize_receipt(task_id: int) -> ProcessTaskReceipt:
    """Create a deterministic synthetic receipt; no hardware execution occurs."""
    classification = min(5000, ((task_id - 1) // 1000 + 1) * 1000)
    seed = f"task::{task_id}"
    digest = sha_hex(seed.encode())
    runtime_sig = "synthetic-ed25519:" + sha_hex((seed + ":runtime-signature").encode())
    return ProcessTaskReceipt(
        task_id=task_id,
        classification=classification,
        component_name=f"synthetic_component_{task_id:04d}",
        hardware_enclave_timestamp=1_792_843_800_000_000_000 + task_id,
        input_state_hash="sha256:" + sha_hex((seed + ":in").encode()),
        output_state_hash="sha256:" + sha_hex((seed + ":out").encode()),
        runtime_signature=runtime_sig,
    )


class MerkleMountainRange:
    """Append-only MMR using binary peaks and deterministic right-to-left bagging."""

    def __init__(self):
        self.peaks: list[tuple[int, bytes]] = []
        self.leaves: list[bytes] = []

    def append(self, leaf_bytes: bytes) -> None:
        self.leaves.append(leaf_bytes)
        peak = (0, sha_bytes(leaf_bytes))
        while self.peaks and self.peaks[-1][0] == peak[0]:
            height, previous = self.peaks.pop()
            peak = (height + 1, sha_bytes(previous + peak[1]))
        self.peaks.append(peak)

    def root(self) -> str:
        if not self.peaks:
            return "sha256:" + sha_hex(b"")
        acc = self.peaks[-1][1]
        for _, peak in reversed(self.peaks[:-1]):
            acc = sha_bytes(peak + acc)
        return "sha256:" + acc.hex()

    def peaks_snapshot(self) -> list[dict]:
        return [{"height": height, "hash": "sha256:" + peak.hex()} for height, peak in self.peaks]


def run_pipeline(task_count: int, out_path: str) -> dict:
    if task_count < 1:
        raise ValueError("task_count must be >= 1")

    receipts = [synthesize_receipt(i + 1) for i in range(task_count)]
    by_class = {}
    for receipt in receipts:
        by_class[str(receipt.classification)] = by_class.get(str(receipt.classification), 0) + 1

    mmr = MerkleMountainRange()
    start = time.perf_counter()
    for receipt in receipts:
        mmr.append(jcs(asdict(receipt)))
    elapsed_ms = (time.perf_counter() - start) * 1000
    root = mmr.root()
    peaks = mmr.peaks_snapshot()

    verifier = MerkleMountainRange()
    for receipt in receipts:
        verifier.append(jcs(asdict(receipt)))
    if verifier.root() != root:
        raise AssertionError("MMR is not deterministic")

    tampered = list(receipts)
    original = tampered[0]
    tampered[0] = ProcessTaskReceipt(
        task_id=original.task_id,
        classification=original.classification,
        component_name=original.component_name,
        hardware_enclave_timestamp=original.hardware_enclave_timestamp,
        input_state_hash=original.input_state_hash,
        output_state_hash="sha256:" + "0" * 64,
        runtime_signature=original.runtime_signature,
    )
    tamper_mmr = MerkleMountainRange()
    for receipt in tampered:
        tamper_mmr.append(jcs(asdict(receipt)))
    if tamper_mmr.root() == root:
        raise AssertionError("tamper was not detected")

    receipt = {
        "spec": "innovulis-mmr-pipeline/1.0",
        "mark": "i Process Architecture · Class 5000",
        "created_utc": time.time(),
        "task_count": task_count,
        "classes_represented": by_class,
        "mmr_root": root,
        "mmr_peaks": peaks,
        "append_duration_ms": round(elapsed_ms, 3),
        "input_status": "SYNTHETIC_RECEIPTS",
        "state": "VERIFIED_PROCESS",
        "physical_gate": "ACTION_REQUIRED",
        "proves": [
            "The implemented MMR accepts arbitrary positive leaf counts.",
            "Identical synthetic receipt bytes produce the identical root.",
            "Changing a leaf changes the resulting root.",
            "Peak bagging produces a compact root from the append-only leaf sequence."
        ],
        "does_not_prove": [
            "That any task executed on real hardware.",
            "That RF, routing, AI, workflow, ZK, PPoV, or settlement operations occurred.",
            "That any receipt has a real hardware-enclave signature.",
            "That $SOV exists, was issued, or was settled."
        ],
        "the_central_rule": "The receipt can record reality; it cannot manufacture reality."
    }
    destination = Path(out_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    output = sys.argv[2] if len(sys.argv) > 2 else "evidence/mmr_5000.json"
    result = run_pipeline(count, output)
    print(f"[MMR] leaves={result['task_count']} peaks={len(result['mmr_peaks'])}")
    print(f"[MMR] root={result['mmr_root']}")
    print(f"[State] {result['state']} · physical_gate={result['physical_gate']}")
