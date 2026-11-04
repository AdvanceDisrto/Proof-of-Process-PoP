#!/usr/bin/env python3
"""Fail-closed AMD Instinct GPU observation. No mock hardware acceptance.
Run only on an authenticated, trusted ROCm runner; signatures alone do not attest hardware.
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def read_cmd(name, args, timeout=12):
    executable = shutil.which(name)
    if not executable:
        return {"available": False, "returncode": None, "output": "NOT_INSTALLED"}
    try:
        p = subprocess.run([executable, *args], capture_output=True, text=True, timeout=timeout, check=False)
        return {"available": True, "returncode": p.returncode, "output": (p.stdout + p.stderr)[-12000:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": True, "returncode": None, "output": type(exc).__name__}

def gpu_observation():
    observed = {"amd_smi": read_cmd("amd-smi", ["list"]), "rocminfo": read_cmd("rocminfo", [])}
    observed["kfd_device"] = Path("/dev/kfd").exists()
    observed["dri_device"] = Path("/dev/dri").exists()
    return observed

def active_matmul():
    try:
        import torch
        result = {"torch_version": torch.__version__, "hip_version": torch.version.hip,
                  "cuda_available": torch.cuda.is_available(), "device_count": torch.cuda.device_count()}
        if not torch.version.hip or not torch.cuda.is_available() or torch.cuda.device_count() < 1:
            result["error"] = "ROCM_CUDA_BACKEND_UNAVAILABLE"
            return result
        name = torch.cuda.get_device_name(0)
        result["device_name"] = name
        result["device_properties"] = str(torch.cuda.get_device_properties(0))
        if not any(x in name.upper() for x in ("MI210", "MI250", "MI300", "MI325", "MI350", "MI355", "INSTINCT")):
            result["error"] = "NOT_RECOGNIZED_AS_AMD_INSTINCT"
            return result
        torch.manual_seed(20261103)
        x = torch.randn((256, 256), dtype=torch.float32, device="cuda")
        y = torch.randn((256, 256), dtype=torch.float32, device="cuda")
        start = time.perf_counter()
        out = x @ y
        torch.cuda.synchronize()
        result["elapsed_seconds"] = time.perf_counter() - start
        ref = x.cpu() @ y.cpu()
        result["max_absolute_error"] = float((out.cpu() - ref).abs().max().item())
        result["numerically_correct"] = bool(torch.allclose(out.cpu(), ref, atol=1e-3, rtol=1e-3))
        return result
    except Exception as exc:
        return {"error": type(exc).__name__, "detail": str(exc)[:300]}

def sign_if_configured(body):
    key_text = os.environ.get("IGPU_ED25519_KEY_B64")
    if not key_text:
        return {"mode": "UNSIGNED", "reason": "NO_PINNED_SIGNING_KEY_CONFIGURED"}
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    key_bytes = base64.b64decode(key_text, validate=True)
    if len(key_bytes) != 32:
        raise ValueError("ED25519_PRIVATE_KEY_SEED_MUST_BE_32_BYTES")
    key = Ed25519PrivateKey.from_private_bytes(key_bytes)
    pub = key.public_key().public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    return {"mode": "ED25519_SOFTWARE", "public_key": pub.hex(),
            "signature": key.sign(canonical(body)).hex(),
            "key_trust": "OUT_OF_BAND_PIN_REQUIRED"}

def verify_receipt(receipt, expected_pubkey, expected_nonce=None):
    if not expected_pubkey or len(expected_pubkey) != 64:
        return False
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        body = receipt["body"]
        sig = receipt["signing"]
        if body.get("schema") != "i/amd-instinct-gpu/v1":
            return False
        if expected_nonce is not None and not hmac.compare_digest(str(body.get("nonce", "")), expected_nonce):
            return False
        if sig["mode"] != "ED25519_SOFTWARE" or sig["public_key"] != expected_pubkey:
            return False
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(expected_pubkey)).verify(bytes.fromhex(sig["signature"]), canonical(body))
        return hashlib.sha256(canonical(body)).hexdigest() == receipt["body_sha256"]
    except Exception:
        return False

def probe(nonce):
    passive = gpu_observation()
    active = active_matmul()
    accepted = bool(passive["kfd_device"] and passive["dri_device"] and
                    passive["amd_smi"]["available"] and passive["amd_smi"]["returncode"] == 0 and
                    passive["rocminfo"]["available"] and passive["rocminfo"]["returncode"] == 0 and
                    active.get("numerically_correct") is True and not active.get("error"))
    return {"schema": "i/amd-instinct-gpu/v1", "nonce": nonce, "observed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "host_os": platform.platform(), "passive": passive, "active": active,
            "verdict": "ACCEPT_AMD_INSTINCT_SOFTWARE_GPU_GATE" if accepted else "GPU_NOT_VERIFIED",
            "physical_gate": "ACTION_REQUIRED", "does_not_prove": [
                "Independent silicon identity or hardware attestation",
                "Performance guarantee, thermal stability, or prolonged stress-test health",
                "That the host or its signing key is uncompromised",
                "Evidence of an AMD GPU when this job ran on a CPU-only host"]}

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("probe")
    p.add_argument("--nonce", required=True)
    p.add_argument("--out", required=True)
    v = sub.add_parser("verify")
    v.add_argument("receipt")
    v.add_argument("--pinned-public-key", required=True)
    v.add_argument("--expected-nonce", required=True)
    args = parser.parse_args()
    if args.command == "verify":
        receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        ok = verify_receipt(receipt, args.pinned_public_key, args.expected_nonce)
        accepted = ok and receipt["body"].get("verdict") == "ACCEPT_AMD_INSTINCT_SOFTWARE_GPU_GATE"
        print("ACCEPT_SIGNED_SOFTWARE_GPU_OBSERVATION" if accepted else ("VALID_SIGNATURE_GPU_NOT_VERIFIED" if ok else "REJECT_SIGNATURE_KEY_OR_NONCE"))
        return 0 if accepted else 2
    if len(args.nonce) < 32:
        parser.error("--nonce must be at least 32 characters and externally generated")
    body = probe(args.nonce)
    try:
        sig = sign_if_configured(body)
    except Exception as exc:
        print("SIGNING_FAILURE:" + type(exc).__name__, file=sys.stderr)
        return 2
    receipt = {"body": body, "body_sha256": hashlib.sha256(canonical(body)).hexdigest(), "signing": sig}
    Path(args.out).write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    signed = sig["mode"] == "ED25519_SOFTWARE"
    accepted = body["verdict"] == "ACCEPT_AMD_INSTINCT_SOFTWARE_GPU_GATE" and signed
    print(json.dumps({"verdict": body["verdict"], "signature": sig["mode"], "receipt": args.out,
                      "gate_passed": accepted, "hardware_attestation": False}))
    return 0 if accepted else 2

if __name__ == "__main__":
    raise SystemExit(main())
