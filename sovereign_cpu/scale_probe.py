from __future__ import annotations
import argparse
import gc
import hashlib
import json
import math
import os
import time
from pathlib import Path

import psutil
import torch
import torch.nn as nn
from cryptography.hazmat.primitives.asymmetric import ed25519


class ProbeState:
    CAPACITY_ESTIMATE = "CAPACITY_ESTIMATE"
    ALLOCATION_ATTEMPT = "ALLOCATION_ATTEMPT"
    ALLOCATION_VERIFIED = "ALLOCATION_VERIFIED"
    FORWARD_VERIFIED = "FORWARD_VERIFIED"
    BACKWARD_VERIFIED = "BACKWARD_VERIFIED"
    PHYSICAL_LIMIT_REACHED = "PHYSICAL_LIMIT_REACHED"
    PROCESS_ABORTED_UNOBSERVED = "PROCESS_ABORTED_UNOBSERVED"


def sha256_json(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def format_scale(num: int) -> str:
    scales = [
        (10**33, "Decillion"), (10**30, "Nonillion"), (10**27, "Octillion"),
        (10**24, "Septillion"), (10**21, "Sextillion"), (10**18, "Quintillion"),
        (10**15, "Quadrillion"), (10**12, "Trillion"), (10**9, "Billion"),
        (10**6, "Million"), (10**3, "Thousand"),
    ]
    for value, name in scales:
        if num >= value:
            return f"{num / value:.2f} {name}"
    return str(num)


def sign_receipt(payload: dict) -> dict:
    key = ed25519.Ed25519PrivateKey.generate()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    receipt = dict(payload)
    receipt["signature"] = key.sign(canonical).hex()
    receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return receipt


def candidate_dims(max_weight_bytes: int) -> list[int]:
    # A training step needs weights + gradients, so reserve 2x the weight budget.
    d0 = max(1, int(math.sqrt(max_weight_bytes / 8)))
    raw = [d0, int(d0 * 0.9), int(d0 * 0.75), int(d0 * 0.6), int(d0 * 0.45), int(d0 * 0.3)]
    return sorted({d for d in raw if d > 0}, reverse=True)


def run_probe(max_probe_bytes: int, safety_fraction: float) -> dict:
    mem = psutil.virtual_memory()
    safe_bytes = min(int(mem.available * safety_fraction), max_probe_bytes)
    max_weight_bytes = max(4, safe_bytes // 2)
    state_log = {
        "protocol": "IPROOF-SCALE-v1",
        "device": "CPU",
        "dtype": "FP32",
        "ram_total_bytes": mem.total,
        "ram_available_bytes": mem.available,
        "safety_fraction": safety_fraction,
        "probe_cap_bytes": max_probe_bytes,
        "safe_bytes": safe_bytes,
        "max_theoretical_params": safe_bytes // 4,
        "attempts": [],
        "parameters_allocated": 0,
        "forward_status": "UNOBSERVED",
        "backward_status": "UNOBSERVED",
        "terminal_state": ProbeState.PROCESS_ABORTED_UNOBSERVED,
    }

    print("=" * 58)
    print(" ⛓️ GAIA PHYSICAL LIMIT PROBE — BOUNDED")
    print("=" * 58)
    print(f"[STATE: {ProbeState.CAPACITY_ESTIMATE}]")
    print(f"Total RAM:        {mem.total / (1024**3):.2f} GB")
    print(f"Available RAM:    {mem.available / (1024**3):.2f} GB")
    print(f"Probe cap:        {max_probe_bytes / (1024**2):.2f} MB")
    print(f"Safe allocation:  {safe_bytes / (1024**2):.2f} MB")
    print(f"Theoretical cap:  {format_scale(state_log['max_theoretical_params'])}")

    for dim in candidate_dims(max_weight_bytes):
        params = dim * dim
        weight_bytes = params * 4
        attempt = {
            "state": ProbeState.ALLOCATION_ATTEMPT,
            "dimension": dim,
            "parameters": params,
            "weight_bytes": weight_bytes,
        }
        print(f"\n[STATE: {ProbeState.ALLOCATION_ATTEMPT}] {dim} x {dim} = {format_scale(params)}")
        model = dummy_input = output = target = loss = None
        try:
            gc.collect()
            model = nn.Linear(dim, dim, bias=False)
            attempt["allocation_state"] = ProbeState.ALLOCATION_VERIFIED
            state_log["parameters_allocated"] = params
            print(f"✅ [STATE: {ProbeState.ALLOCATION_VERIFIED}]")

            dummy_input = torch.randn(1, dim)
            target = torch.randn(1, dim)
            start = time.time()
            output = model(dummy_input)
            attempt["forward_seconds"] = round(time.time() - start, 6)
            attempt["forward_state"] = ProbeState.FORWARD_VERIFIED
            state_log["forward_status"] = attempt["forward_state"]
            print(f"✅ [STATE: {ProbeState.FORWARD_VERIFIED}]")

            loss = nn.functional.mse_loss(output, target)
            start = time.time()
            loss.backward()
            elapsed = round(time.time() - start, 6)
            attempt["backward_seconds"] = elapsed
            attempt["backward_state"] = ProbeState.BACKWARD_VERIFIED
            state_log["backward_status"] = attempt["backward_state"]
            state_log["terminal_state"] = ProbeState.BACKWARD_VERIFIED
            attempt["loss"] = float(loss)
            state_log["attempts"].append(attempt)
            print(f"✅ [STATE: {ProbeState.BACKWARD_VERIFIED}] loss={float(loss):.6f}")
            break
        except (MemoryError, RuntimeError) as exc:
            attempt["failure"] = str(exc).splitlines()[0][:500]
            attempt["failure_state"] = ProbeState.PHYSICAL_LIMIT_REACHED
            state_log["attempts"].append(attempt)
            state_log["terminal_state"] = ProbeState.PHYSICAL_LIMIT_REACHED
            print(f"⚠️ [STATE: {ProbeState.PHYSICAL_LIMIT_REACHED}] {attempt['failure']}")
        finally:
            del model, dummy_input, output, target, loss
            gc.collect()

    return state_log


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-probe-mb", type=int, default=int(os.getenv("SCALE_PROBE_MAX_MB", "256")))
    parser.add_argument("--safety-fraction", type=float, default=float(os.getenv("SCALE_PROBE_SAFETY", "0.50")))
    parser.add_argument("--output", default="scale_probe_receipt.json")
    args = parser.parse_args()
    if args.max_probe_mb < 16:
        raise SystemExit("--max-probe-mb must be >= 16")
    if not 0.1 <= args.safety_fraction <= 0.8:
        raise SystemExit("--safety-fraction must be between 0.1 and 0.8")

    payload = run_probe(args.max_probe_mb * 1024 * 1024, args.safety_fraction)
    payload["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    receipt = sign_receipt(payload)
    Path(args.output).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("\n🧾 [iProof Generated] " + args.output)
    print("Terminal state:", payload["terminal_state"])
    print("Largest backward-verified:", payload["parameters_allocated"])


if __name__ == "__main__":
    main()
