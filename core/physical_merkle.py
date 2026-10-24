"""Fail-closed Merkle aggregation for hardware evidence receipts.

A structural blob-size heuristic is never accepted as cryptographic provenance.
Only receipts explicitly marked VERIFIED by an external/vendor verifier may enter
a physical-evidence Merkle tree.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    reason: str


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def verify_physical_receipt(receipt: dict[str, Any]) -> VerificationResult:
    if receipt.get("physical_gate") != "MEASURED_PASS":
        return VerificationResult(False, "physical_gate is not MEASURED_PASS")
    if receipt.get("attestation_verification") != "VERIFIED":
        return VerificationResult(False, "vendor attestation verification is absent")
    if receipt.get("evidence_origin") in {"SIMULATED", "MOCK", "SYNTHETIC"}:
        return VerificationResult(False, "simulated/mock evidence is prohibited")
    if not receipt.get("verifier_receipt_id"):
        return VerificationResult(False, "verifier receipt identity is absent")
    if not receipt.get("workload_hash"):
        return VerificationResult(False, "workload binding is absent")
    return VerificationResult(True, "verified")


def merkle_root(receipts: list[dict[str, Any]]) -> str | None:
    if not receipts:
        return None

    nodes: list[bytes] = []
    for receipt in receipts:
        result = verify_physical_receipt(receipt)
        if not result.valid:
            return None
        leaf = hashlib.sha256(b"i-pop-physical-leaf-v1:" + canonical_json(receipt)).digest()
        nodes.append(leaf)

    nodes.sort()
    while len(nodes) > 1:
        if len(nodes) % 2:
            nodes.append(nodes[-1])
        nodes = [
            hashlib.sha256(b"i-pop-physical-node-v1:" + nodes[i] + nodes[i + 1]).digest()
            for i in range(0, len(nodes), 2)
        ]
    return "sha256:" + nodes[0].hex()
