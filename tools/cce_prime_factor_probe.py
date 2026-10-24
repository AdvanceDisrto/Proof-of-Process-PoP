"""Project Euler #3 CCE probe: mechanism execution against harness-held truth.

This receipt verifies a generated trial-division mechanism at the software
process layer. It does not establish model novelty, consciousness, TEE
isolation, or physical attestation.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROBLEM = "Find the largest prime factor of the number 600851475143."
EXPECTED = "6857"
METHOD_ID = "trial-division-v1"
METHOD_SOURCE = """def solve(n=600851475143):
    factor = 2
    last_factor = 1
    while n > 1:
        if n % factor == 0:
            last_factor = factor
            n = n // factor
        else:
            factor += 1
    return last_factor

print(solve())
"""

def sha256_text(value):
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()

def run_probe(timeout_seconds=5):
    with tempfile.TemporaryDirectory(prefix="cce-prime-") as td:
        path = Path(td) / "method.py"
        path.write_text(METHOD_SOURCE)
        started = time.time_ns()
        try:
            cp = subprocess.run(
                [sys.executable, "-I", str(path)],
                cwd=td,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                env={"PATH": ""},
            )
            stdout = cp.stdout.strip()
            stderr = cp.stderr
            exit_code = cp.returncode
        except subprocess.TimeoutExpired:
            stdout, stderr, exit_code = "", "TIMEOUT", -1
        duration_ns = time.time_ns() - started

    expected_hash = sha256_text(EXPECTED)
    actual_hash = sha256_text(stdout)
    success = exit_code == 0 and stderr == "" and actual_hash == expected_hash
    return {
        "spec": "innovulis-epistemic-genesis/1.0",
        "context": {
            "problem_hash": sha256_text(PROBLEM),
            "ground_truth_provenance": "ci_harness_constant_not_passed_to_method",
        },
        "synthesis": {
            "method_id": METHOD_ID,
            "language": "python",
            "source_code_hash": sha256_text(METHOD_SOURCE),
        },
        "execution": {
            "sandbox_id": "github-actions-python-isolated-mode",
            "stdout": stdout,
            "stdout_hash": actual_hash,
            "stderr_hash": sha256_text(stderr),
            "exit_code": exit_code,
            "duration_ns": duration_ns,
            "constraints": {
                "timeout_seconds": timeout_seconds,
                "python_isolated_mode": True,
                "network_passed_to_method": False,
                "kernel_isolation": False,
            },
        },
        "validation": {
            "success": success,
            "expected_hash": expected_hash,
            "actual_hash": actual_hash,
        },
        "ilogic": {
            "truth_axis": "ESTABLISHED" if success else "REFUTED",
            "attestation_axis": "UNATTESTED",
            "tier": "VERIFIED_PROCESS" if success else "REFUTED",
            "physical_gate": "ACTION_REQUIRED",
        },
        "claims": {
            "mechanism_executed_and_matched_harness_truth": success,
            "method_was_invented_not_retrieved": "UNATTESTED",
            "consciousness_or_agi": "NOT_ESTABLISHED",
            "physical_tee_isolation": "ACTION_REQUIRED",
        },
        "physical_gate": "ACTION_REQUIRED",
    }

def verify_receipt(receipt):
    errors = []
    ex, val = receipt["execution"], receipt["validation"]
    derived = (
        ex["exit_code"] == 0
        and ex["stderr_hash"] == sha256_text("")
        and ex["stdout_hash"] == val["expected_hash"]
        and val["actual_hash"] == ex["stdout_hash"]
    )
    if derived != val["success"]:
        errors.append("validation_mismatch")
    if receipt["ilogic"]["truth_axis"] != ("ESTABLISHED" if derived else "REFUTED"):
        errors.append("truth_axis_mismatch")
    if receipt["ilogic"]["tier"] != ("VERIFIED_PROCESS" if derived else "REFUTED"):
        errors.append("tier_mismatch")
    if receipt["ilogic"]["attestation_axis"] != "UNATTESTED":
        errors.append("attestation_mismatch")
    if receipt["physical_gate"] != "ACTION_REQUIRED":
        errors.append("physical_gate_mismatch")
    return errors

if __name__ == "__main__":
    receipt = run_probe()
    errors = verify_receipt(receipt)
    if errors:
        raise SystemExit("verification failed: " + ",".join(errors))
    print(json.dumps(receipt, indent=2, sort_keys=True))
