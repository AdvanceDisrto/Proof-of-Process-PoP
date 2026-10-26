#!/usr/bin/env python3
"""Dependency-free validator for the repository's iProof v1 instance shape.

This intentionally validates the exact constraints used by schemas/iproof-v1.schema.json.
It is not presented as a general-purpose JSON Schema implementation.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SHA256 = re.compile(r"^sha256:[a-f0-9]{64}$")
SIGNATURE = re.compile(r"^[a-f0-9]{128}$")


def fail(path: str, message: str) -> None:
    raise ValueError(f"{path}: {message}")


def require_keys(obj: dict[str, Any], required: set[str], allowed: set[str], path: str) -> None:
    missing = required - obj.keys()
    extra = set(obj) - allowed
    if missing:
        fail(path, f"missing required properties: {sorted(missing)}")
    if extra:
        fail(path, f"additional properties are forbidden: {sorted(extra)}")


def require_string(value: Any, path: str, min_length: int = 1) -> None:
    if not isinstance(value, str) or len(value) < min_length:
        fail(path, "must be a non-empty string")


def require_sha(value: Any, path: str) -> None:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        fail(path, "must match sha256:<64 lowercase hex characters>")


def validate_receipt(receipt: Any) -> None:
    if not isinstance(receipt, dict):
        fail("$", "must be an object")

    root_allowed = {
        "protocol", "evidence_id", "intent", "routing", "execution",
        "resources", "result", "reproduction", "signature",
    }
    require_keys(
        receipt,
        {"protocol", "evidence_id", "intent", "routing", "execution", "resources", "result", "reproduction"},
        root_allowed,
        "$",
    )
    if receipt["protocol"] != "IPROOF-v1":
        fail("$.protocol", "must equal IPROOF-v1")
    require_string(receipt["evidence_id"], "$.evidence_id")

    intent = receipt["intent"]
    if not isinstance(intent, dict):
        fail("$.intent", "must be an object")
    require_keys(intent, {"request_sha256", "intent_class"}, {"request_sha256", "intent_class"}, "$.intent")
    require_sha(intent["request_sha256"], "$.intent.request_sha256")
    require_string(intent["intent_class"], "$.intent.intent_class")

    routing = receipt["routing"]
    if not isinstance(routing, dict):
        fail("$.routing", "must be an object")
    routing_allowed = {"router_version", "action_id", "execution_class", "reason", "module_ids"}
    require_keys(routing, routing_allowed, routing_allowed, "$.routing")
    for key in ("router_version", "action_id", "reason"):
        require_string(routing[key], f"$.routing.{key}")
    if routing["execution_class"] not in {"INTELLIGENCE", "DETERMINISTIC", "HUMAN_REVIEW", "BLOCKED"}:
        fail("$.routing.execution_class", "invalid enum value")
    if not isinstance(routing["module_ids"], list) or not all(isinstance(x, str) and x for x in routing["module_ids"]):
        fail("$.routing.module_ids", "must be an array of non-empty strings")

    execution = receipt["execution"]
    if not isinstance(execution, dict):
        fail("$.execution", "must be an object")
    execution_allowed = {"artifact_id", "artifact_sha256", "runtime_version", "output_sha256", "completed_at"}
    require_keys(execution, execution_allowed, execution_allowed, "$.execution")
    require_string(execution["artifact_id"], "$.execution.artifact_id")
    require_sha(execution["artifact_sha256"], "$.execution.artifact_sha256")
    require_string(execution["runtime_version"], "$.execution.runtime_version")
    require_sha(execution["output_sha256"], "$.execution.output_sha256")
    require_string(execution["completed_at"], "$.execution.completed_at")
    try:
        datetime.fromisoformat(execution["completed_at"].replace("Z", "+00:00"))
    except ValueError:
        fail("$.execution.completed_at", "must be an ISO date-time")

    resources = receipt["resources"]
    if not isinstance(resources, dict):
        fail("$.resources", "must be an object")
    require_keys(resources, {"compute", "network", "storage"}, {"compute", "network", "storage"}, "$.resources")

    compute = resources["compute"]
    if not isinstance(compute, dict):
        fail("$.resources.compute", "must be an object")
    require_keys(compute, {"device", "driver", "memory_bytes"}, {"device", "driver", "memory_bytes"}, "$.resources.compute")
    require_string(compute["device"], "$.resources.compute.device", 0)
    require_string(compute["driver"], "$.resources.compute.driver", 0)
    if not isinstance(compute["memory_bytes"], int) or isinstance(compute["memory_bytes"], bool) or compute["memory_bytes"] < 0:
        fail("$.resources.compute.memory_bytes", "must be a non-negative integer")

    network = resources["network"]
    if not isinstance(network, dict):
        fail("$.resources.network", "must be an object")
    require_keys(network, {"mode"}, {"mode"}, "$.resources.network")
    require_string(network["mode"], "$.resources.network.mode", 0)

    storage = resources["storage"]
    if not isinstance(storage, dict):
        fail("$.resources.storage", "must be an object")
    require_keys(storage, {"artifact_bytes"}, {"artifact_bytes"}, "$.resources.storage")
    if not isinstance(storage["artifact_bytes"], int) or isinstance(storage["artifact_bytes"], bool) or storage["artifact_bytes"] < 0:
        fail("$.resources.storage.artifact_bytes", "must be a non-negative integer")

    result = receipt["result"]
    if not isinstance(result, dict):
        fail("$.result", "must be an object")
    result_allowed = {"status", "metrics"}
    require_keys(result, {"status"}, result_allowed, "$.result")
    if result["status"] not in {"PASS", "FAIL", "ACTION_REQUIRED", "QUARANTINED"}:
        fail("$.result.status", "invalid enum value")
    if "metrics" in result:
        metrics = result["metrics"]
        if not isinstance(metrics, dict):
            fail("$.result.metrics", "must be an object")
        for key, value in metrics.items():
            if not isinstance(key, str):
                fail("$.result.metrics", "property names must be strings")
            if not (isinstance(value, (int, float, str, bool)) or value is None):
                fail(f"$.result.metrics.{key}", "must be number, string, boolean, or null")

    reproduction = receipt["reproduction"]
    if not isinstance(reproduction, dict):
        fail("$.reproduction", "must be an object")
    reproduction_allowed = {"required", "command", "environment_hash", "expected_output_sha256"}
    require_keys(reproduction, reproduction_allowed, reproduction_allowed, "$.reproduction")
    if reproduction["required"] is not True:
        fail("$.reproduction.required", "must be true")
    require_string(reproduction["command"], "$.reproduction.command")
    require_sha(reproduction["environment_hash"], "$.reproduction.environment_hash")
    require_sha(reproduction["expected_output_sha256"], "$.reproduction.expected_output_sha256")

    if "signature" in receipt and (
        not isinstance(receipt["signature"], str) or not SIGNATURE.fullmatch(receipt["signature"])
    ):
        fail("$.signature", "must be 128 lowercase hexadecimal characters")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python tools/validate_iproof.py <receipt.json>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        validate_receipt(receipt)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"IPROOF_SCHEMA_FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"IPROOF_SCHEMA_PASS: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
