#!/usr/bin/env python3
"""iSovereign Local Runner (iSLR).

Runs the three former CircleCI proof jobs locally, records stdout/stderr hashes,
preserves every failure, and emits one fail-closed sovereign execution receipt.

This runner does not claim hardware attestation, physical deployment, or external
chain anchoring. A passing local command proves only that the declared command
completed successfully on the local execution environment.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "evidence" / "islr"
RECEIPT_PATH = ROOT / "ci_sovereign_receipt.json"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def git_value(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "UNAVAILABLE"
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


def run_command(name: str, argv: list[str], cwd: Path) -> dict[str, Any]:
    command = " ".join(argv)
    started = time.time()
    print(f"  -> {name}: {command}")

    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode
    except OSError as exc:
        stdout = ""
        stderr = f"{type(exc).__name__}: {exc}"
        exit_code = 127

    duration = round(time.time() - started, 3)
    state = "VERIFIED_PROCESS" if exit_code == 0 else "QUARANTINED"

    log_dir = OUT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace("/", "_").replace(" ", "_")
    (log_dir / f"{safe_name}.stdout.log").write_text(stdout, encoding="utf-8")
    (log_dir / f"{safe_name}.stderr.log").write_text(stderr, encoding="utf-8")

    if exit_code == 0:
        print("     PASS")
    else:
        print(f"     FAIL exit={exit_code}")
        if stderr.strip():
            print(stderr.rstrip())

    return {
        "name": name,
        "command": command,
        "cwd": str(cwd.relative_to(ROOT)),
        "exit_code": exit_code,
        "duration_seconds": duration,
        "stdout_sha256": sha256_text(stdout),
        "stderr_sha256": sha256_text(stderr),
        "state": state,
    }


def run_job(job_name: str, steps: list[tuple[str, list[str], Path]]) -> dict[str, Any]:
    results = []
    for name, argv, cwd in steps:
        results.append(run_command(name, argv, cwd))
    passed = all(step["exit_code"] == 0 for step in results)
    return {
        "job": job_name,
        "state": "VERIFIED_PROCESS" if passed else "QUARANTINED",
        "steps": results,
    }


def execute_sovereign_ci() -> int:
    print("=" * 78)
    print(" iSOVEREIGN LOCAL RUNNER (iSLR)")
    print(" Former CircleCI proof jobs executed on the local machine")
    print("=" * 78)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    jobs: dict[str, Any] = {}

    print("\n[1/3] compute-control-mcp")
    mcp = ROOT / "mcp" / "compute-control"
    jobs["compute_control_mcp"] = run_job(
        "compute-control-mcp",
        [
            ("mcp_npm_install", ["npm", "install"], mcp),
            ("mcp_itsc_compile", ["npm", "run", "compile:itsc"], mcp),
            ("mcp_tests", ["npm", "test"], mcp),
        ],
    )

    print("\n[2/3] control-plane-iproof")
    control = ROOT / "control-plane"
    jobs["control_plane_iproof"] = run_job(
        "control-plane-iproof",
        [
            ("control_npm_install", ["npm", "install"], control),
            ("control_build", ["npm", "run", "build"], control),
            ("control_tests", ["npm", "test"], control),
            (
                "iproof_schema_probe",
                ["node", "--import=tsx", "tools/iproof_probe.ts"],
                control,
            ),
            (
                "iproof_schema_validate",
                [sys.executable, "tools/validate_iproof.py", "evidence/islr/iproof-probe.json"],
                ROOT,
            ),
        ],
    )

    print("\n[3/3] root-pytest")
    jobs["root_pytest"] = run_job(
        "root-pytest",
        [
            (
                "root_python_dependencies",
                [sys.executable, "-m", "pip", "install", "--prefer-binary", "-r", "requirements.txt"],
                ROOT,
            ),
            ("root_native_build", ["make", "build-ibare", "build-truth"], ROOT),
            ("root_pytest", [sys.executable, "-m", "pytest", "-q"], ROOT),
        ],
    )

    all_passed = all(job["state"] == "VERIFIED_PROCESS" for job in jobs.values())
    final_state = "VERIFIED_PROCESS" if all_passed else "QUARANTINED"

    receipt: dict[str, Any] = {
        "protocol": "ISLR-CI-v1",
        "runner": "iSLR",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_branch": git_value("branch", "--show-current"),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "jobs": jobs,
        "state": final_state,
        "proves": [
            "The declared local commands were executed.",
            "Each command's exit status and output hashes were recorded.",
            "A passing job completed successfully in this local execution environment.",
        ],
        "does_not_prove": [
            "Remote CI execution.",
            "Hardware attestation or TEE identity.",
            "Physical network or subsea cable state.",
            "External blockchain anchoring.",
            "Global reproducibility on another machine.",
        ],
    }

    receipt_hash = sha256_text(canonical_json(receipt))
    receipt["receipt_hash"] = receipt_hash

    RECEIPT_PATH.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("\n" + "=" * 78)
    print(f" FINAL STATE: {final_state}")
    print(f" RECEIPT HASH: {receipt_hash}")
    print(f" SAVED TO: {RECEIPT_PATH}")
    print("=" * 78)

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(execute_sovereign_ci())
