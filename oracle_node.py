#!/usr/bin/env python3
"""Map Omniscope Node 1: The Oracle as an evidence-bounded software node."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from truth_process import (
    AICreationOracle,
    TruthLevel,
    TruthProcess,
    _fake_sha,
    _fake_ur1,
)


OUT = Path("artifacts/omniscope/oracle_node.json")


def build_receipts():
    tp = TruthProcess({"ai_creation": AICreationOracle()})
    claim = {
        "model_hash": _fake_sha("omniscope-node-1-model"),
        "policy_ur1": _fake_ur1("omniscope-node-1-policy"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    certified = tp.process("ai_creation", claim)
    declined = tp.process(
        "ai_creation",
        claim,
        external_verifier=lambda _: {
            "external_verified": False,
            "reason": "no external verifier configured",
        },
        external_policy_version="oracle-node/v1",
    )
    return certified, declined


def main() -> int:
    certified, declined = build_receipts()
    node = {
        "schema": "omniscope/oracle-node/v1",
        "node": "oracle",
        "mapped_at": datetime.now(timezone.utc).isoformat(),
        "layers": {
            "memory": {
                "role": "record and bind evidence",
                "state": "WARRANTED",
                "evidence": certified.evidence,
            },
            "mind": {
                "role": "produce a bounded AI creation claim",
                "state": "CERTIFIED",
                "receipt_hash": certified.receipt_hash,
            },
            "time": {
                "role": "external anchoring",
                "state": "ACTION_REQUIRED",
                "reason": declined.refusal_reason or declined.refusals_at_this_stage,
            },
        },
        "truth_ladder": {
            "reached_level": TruthLevel.CERTIFIED,
            "label": "CERTIFIED",
            "anchored_requires_external_verifier": True,
            "correspondence_available": False,
        },
        "does_not_claim": [
            "physical observation truth",
            "Bitcoin or Ethereum confirmation",
            "TEE attestation",
            "robotic actuation",
            "medical efficacy",
        ],
        "receipt_hash": "",
    }
    body = json.dumps(node, sort_keys=True, separators=(",", ":")).encode()
    node["receipt_hash"] = "sha256:" + hashlib.sha256(body).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(node, indent=2) + "\n")
    print(f"oracle node written: {OUT}")
    print(f"truth level: {node['truth_ladder']['label']}")
    print(f"receipt hash: {node['receipt_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
