#!/usr/bin/env python3
"""Emit an evidence-bounded Omniscope AI node descriptor from the latest run receipt.

The descriptor maps only what the existing certification pipeline actually
executed. It deliberately refuses claims about general AI capability,
truth, physical actuation, or external notarization that the local run cannot
prove.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ARTIFACTS = Path("artifacts/omniscope")
ARTIFACTS.mkdir(parents=True, exist_ok=True)
RUN_RECEIPT = Path("run_all_receipt.json")


def _receipt_is_fresh(data: dict, max_age: int = 600) -> bool:
    if data.get("schema") != "run_all/v1":
        return False
    raw = data.get("ts")
    if not raw:
        return False
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return time.time() - ts.timestamp() < max_age
    except (TypeError, ValueError, OverflowError):
        return False


def run_pipeline() -> dict | None:
    """Use a fresh receipt, otherwise execute the existing run_all pipeline."""
    if RUN_RECEIPT.exists():
        try:
            data = json.loads(RUN_RECEIPT.read_text())
            if _receipt_is_fresh(data):
                print(f"  using cached {RUN_RECEIPT}")
                return data
        except (OSError, json.JSONDecodeError):
            pass

    print("  running run_all.py ...")
    result = subprocess.run(
        [sys.executable, "run_all.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout[-2000:])
    if result.returncode != 0:
        print(f"  run_all.py exited {result.returncode}", file=sys.stderr)
    if not RUN_RECEIPT.exists():
        print(f"  ✗ {RUN_RECEIPT} was not produced", file=sys.stderr)
        return None
    try:
        return json.loads(RUN_RECEIPT.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  ✗ invalid {RUN_RECEIPT}: {exc}", file=sys.stderr)
        return None


def descriptor(receipt: dict) -> dict:
    sections = receipt.get("sections", {})
    total_passed = receipt.get("total_passed", 0)
    total_failed = receipt.get("total_failed", 0)
    verdict = receipt.get("hfr_as_verdict") or {}

    node = {
        "schema": "omniscope/node/v1",
        "node": "artificial_intelligence",
        "node_version": "0.1.0",
        "mapped_at": datetime.now(timezone.utc).isoformat(),
        "coverage_scope": (
            "The certification subsystem of AI. Bounded, executed, "
            "evidence-backed claims emitted by certified heads. NOT general "
            "AI capability, training quality, or reasoning ability."
        ),
        "coverage_fraction": "small (single-digit percent of the field named 'AI')",
        "not_mapped": [
            "model capability and benchmark performance",
            "training data provenance and corpus legality",
            "generalization, reasoning, and emergent behavior",
            "alignment, interpretability, and hidden capabilities",
            "anything the 11 certified heads did not execute",
        ],
        "layers": {
            "L1_omni_edge": {
                "name": "sensory array",
                "actual_source": "the certified heads",
                "mechanism": "each head emits a bounded claim via CertificationGate",
                "integrity_gate": "CertificationGate.evaluate",
                "quarantine_policy": "REFUSED -> Decision_Record, never a UR-1",
                "emitted_this_run": sections.get("heads", {}),
            },
            "L2_omni_memory": {
                "name": "global namespace",
                "actual_source": "append-only receipt and anchorage stores plus in-process audit",
                "mechanism": (
                    "heads write receipts; anchors write registry entries; "
                    "decisions write audit records"
                ),
                "what_it_does_not_store": (
                    "model weights, training sets, or user intent beyond "
                    "what a head executed"
                ),
                "verified_this_run": sections.get("anchorage", {}),
            },
            "L3_omni_observer": {
                "name": "cross-head aggregation",
                "actual_source": "QuorumHead",
                "mechanism": (
                    "aggregates witness UR-1s, verifies Ed25519 signatures, "
                    "and deduplicates canonical public keys"
                ),
                "what_it_does_not_do": (
                    "does NOT emit truth_bearing=True; emits quorum_verified "
                    "scoped to quorum"
                ),
                "anchor_binding": (
                    "requires anchor evidence to bind to the claim hash"
                ),
                "emitted_this_run": sections.get("heads", {}),
            },
            "L4_omni_time": {
                "name": "temporal anchor",
                "actual_source": "AnchorHead + configured anchor backend",
                "mechanism": (
                    "commits claim hashes to an append-only registry; "
                    "artifact digests remain recomputable"
                ),
                "what_this_proves": (
                    "the artifact was recorded by this host at the stated "
                    "process time and that the internal registry chain is intact"
                ),
                "what_this_does_not_prove": (
                    "external notarization or Bitcoin inclusion unless an "
                    "external verifier explicitly supplied evidence"
                ),
                "emitted_this_run": sections.get("anchorage", {}),
            },
            "L5_omni_gate": {
                "name": "actuation",
                "actual_source": "HFR-AS routing verdict",
                "mechanism": (
                    "routes experts, measures FLOPs, and emits a scoped receipt"
                ),
                "verdict_this_run": verdict.get("verdict", "NOT_RUN"),
                "what_this_does_not_do": (
                    "does NOT actuate physical systems, synthesize compounds, "
                    "or authorize FDA, satellite, or drone operations"
                ),
            },
        },
        "run": {
            "receipt_hash": receipt.get("receipt_hash"),
            "ts": receipt.get("ts"),
            "total_passed": total_passed,
            "total_failed": total_failed,
            "status": "PASS" if total_failed == 0 else "FAIL",
        },
        "claims_supported": [
            "an enumerated set of bounded claims was executed this run",
            "certified claims carry evidence hashes",
            "refusals are recorded as Decision_Records, not certificates",
            "revocations preserve original certificates",
            "anchor registries can be checked for internal consistency",
            "quorum attestation verifies distinct canonical public keys",
            "FLOPs-per-token is reported for HFR-AS and flat routing",
        ],
        "claims_refused": [
            "that any certified claim is true outside its declared scope",
            "that an anchor is externally notarized without external evidence",
            "that N keys represent N people",
            "that HFR-AS beats flat routing at smoke scale",
            "that the universe is being mapped",
            "that any physical actuation occurred",
            "that the run was executed in the author's environment",
            "that is_generator_agent=False proves gate independence",
        ],
        "omniscope_notes": {
            "kept": [
                "QUARANTINED / PENDING / VERIFIED taxonomy",
                "distributed receipt and anchorage stores",
                "refusal to claim completeness",
            ],
            "refused": [
                "totality of existence as a reachable set",
                "deterministic pre-validated truths from an LLM-backed database",
                "multi-chain quorum as proof that an observation was true",
                "robotic actuators plus FDA webhooks as cure synthesis",
                "the universe observes itself as a technical claim",
            ],
        },
    }

    body = json.dumps(node, sort_keys=True, separators=(",", ":")).encode()
    node["descriptor_hash"] = "sha256:" + hashlib.sha256(body).hexdigest()
    return node


def main() -> int:
    print("=" * 72)
    print("  OMNISCOPE — AI NODE DESCRIPTOR")
    print("=" * 72)
    receipt = run_pipeline()
    if receipt is None:
        return 1
    node = descriptor(receipt)
    out = ARTIFACTS / "ai_node.json"
    out.write_text(json.dumps(node, indent=2) + "\n")
    print(f"  ✓ written: {out}")
    print(f"  descriptor_hash: {node['descriptor_hash']}")
    print(f"  run status:      {node['run']['status']}")
    print(f"  layers populated: {len(node['layers'])}/5")
    return 0


if __name__ == "__main__":
    sys.exit(main())
