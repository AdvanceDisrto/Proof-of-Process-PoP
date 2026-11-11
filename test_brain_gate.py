#!/usr/bin/env python3
"""BrainGate software acceptance harness — no API keys, no hardware proof."""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from unittest.mock import patch
from brain_registry import build_dispatcher

NO_EXTERNAL_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "CLOUDFLARE_API_TOKEN", "IZETTA_MODEL_PATH")


def run_gate_tests() -> dict:
    # Isolate this test from stored provider keys; it makes no model calls.
    with patch.dict(os.environ, {key: "" for key in NO_EXTERNAL_KEYS}, clear=False):
        dispatcher = build_dispatcher()
        coverage = dispatcher.coverage()
        assert coverage["total_brains"] == 21
        assert coverage["by_kind"] == {
            "deterministic": 4, "head": 6, "router": 1, "oracle": 6, "external_llm": 4
        }
        assert not coverage["external_ready"]

        # Actual dispatcher takes a text string, not a request dictionary.
        attempt = dispatcher.brains["Calculator"].handler({"text": "add 40 and 2"})
        assert attempt.produced and attempt.output["result"] == 42
        math = dispatcher.dispatch("add 40 and 2")
        assert math.brain == "Calculator" and math.gate_verdict == "ACCEPT"
        assert math.confidence == 1.0

        # This is a software routing/refusal test, NOT a medical decision.
        human = dispatcher.dispatch("What disease does the patient have?", forced="OracleHumanReview")
        assert human.brain == "OracleHumanReview"
        assert human.gate_verdict == "ACCEPT-REFUSAL"
        assert "diagnose" in human.refusals
        assert human.confidence == 0

        # External credential unavailable: refuses without performing remote inference.
        external = dispatcher.dispatch("Write a poem", forced="Claude")
        assert external.brain == "Claude"
        assert external.gate_verdict == "ACCEPT-REFUSAL"
        assert external.connection_status == "not_connected"
        assert external.confidence == 0

        chain = dispatcher.verify_chain()
        assert chain["ok"] and chain["count"] == 3
        result = {
            "tier": "EXECUTED_SOFTWARE_HARNESS",
            "registered": coverage["total_brains"],
            "local_rule_based": 17,
            "external_declared": 4,
            "math_output": attempt.output,
            "receipts": [asdict(x) for x in (math, human, external)],
            "chain": chain,
            "does_not_prove": [
                "external LLM execution", "real hardware execution",
                "physical facts", "mathematical proof of no hallucinations",
                "cryptographic signature", "network consensus",
            ],
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        dispatcher.chain[0].claims = ["tampered"]
        assert dispatcher.verify_chain()["ok"] is False
        print("BRAIN_GATE_ACCEPTANCE_PASS: 3 receipts, intact chain, altered claim detected")
        return result


if __name__ == "__main__":
    run_gate_tests()
