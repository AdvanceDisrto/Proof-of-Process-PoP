"""RunPod-only CUDA execution observer and offline independent result verifier.

This does NOT attest physical silicon, cloud ownership, production signer or
external truth. Local observation is unsigned and fail-closed without CUDA.
The observer never provisions/deletes pods, manages keys, or controls machinery.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import pathlib
import re
import sys

SCHEMA = "ipqr/runpod-gpu-execution-observation/v1"
COUNT = 4096
PIN_RE = re.compile(r"[a-f0-9]{32,128}\Z")

def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",",":"), ensure_ascii=True, allow_nan=False).encode()

def sha(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()

def expected_vector(nonce):
    """Deterministic reference also computed by independent CPU verifier."""
    seed = int.from_bytes(hashlib.sha256(nonce.encode("ascii")).digest()[:4], "big")
    return [((i * 17) + seed) % 2147483647 for i in range(COUNT)]

def observe(nonce):
    if not isinstance(nonce, str) or not PIN_RE.fullmatch(nonce):
        return {"verdict":"BLOCKED","reason":"INVALID_FRESH_CHALLENGE"}
    # Caller must execute in RunPod environment; env values are only assertions.
    pod_id = os.environ.get("RUNPOD_POD_ID", "")
    if not pod_id:
        return {"verdict":"BLOCKED","reason":"RUNPOD_POD_ID_MISSING"}
    try:
        import torch
    except ImportError:
        return {"verdict":"BLOCKED","reason":"PYTORCH_MISSING"}
    if not torch.cuda.is_available():
        return {"verdict":"BLOCKED","reason":"CUDA_UNAVAILABLE"}
    try:
        device = "cuda:0"
        seed = int.from_bytes(hashlib.sha256(nonce.encode("ascii")).digest()[:4], "big")
        with torch.no_grad():
            indices = torch.arange(COUNT, device=device, dtype=torch.int64)
            result = (indices * 17 + seed) % 2147483647
            torch.cuda.synchronize()
            vector = result.cpu().tolist()
        data = encoded(vector)
        observation = {
            "schema": SCHEMA,
            "verdict": "CUDA_RUNTIME_OBSERVATION",
            "nonce":nonce,
            "provider_reported": "RUNPOD",
            "pod_id_reported":pod_id,
            "hardware_reported":torch.cuda.get_device_name(0),
            "cuda_runtime_reported":str(torch.version.cuda),
            "operation":"int64_challenged_vector_v1",
            "count":COUNT,
            "output_sha256":sha(data),
            "expected_sha256":sha(encoded(expected_vector(nonce))),
            "production_trust":"UNVERIFIED",
            "hardware_attestation":None,
            "external_anchor":None,
            "independent_witness":None
        }
        if observation["output_sha256"]!=observation["expected_sha256"]:
            return {"verdict":"BLOCKED","reason":"GPU_CPU_MISMATCH"}
        return observation
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
        return {"verdict":"BLOCKED","reason":"GPU_PROBE_EXCEPTION_"+type(exc).__name__}

def verify(observation,nonce):
    """Recompute expected output independently on CPU, not a hardware attestation."""
    fail = lambda reason:{"verdict":"BLOCKED","reason":reason}
    if not isinstance(observation,dict) or set(observation)!={
        "schema","verdict","nonce","provider_reported","pod_id_reported",
        "hardware_reported","cuda_runtime_reported","operation","count",
        "output_sha256","expected_sha256","production_trust",
        "hardware_attestation","external_anchor","independent_witness"
    }: return fail("UNEXPECTED_FIELDS")
    if not isinstance(nonce,str) or not PIN_RE.fullmatch(nonce):
        return fail("INVALID_CHALLENGE")
    if (observation["schema"]!=SCHEMA or observation["verdict"]!="CUDA_RUNTIME_OBSERVATION"
        or observation["nonce"]!=nonce or observation["provider_reported"]!="RUNPOD"
        or not isinstance(observation["pod_id_reported"],str) or not observation["pod_id_reported"]
        or not isinstance(observation["hardware_reported"],str) or not observation["hardware_reported"]
        or observation["operation"]!="int64_challenged_vector_v1"
        or type(observation["count"]) is not int or observation["count"]!=COUNT
        or observation["production_trust"]!="UNVERIFIED"
        or observation["hardware_attestation"] is not None
        or observation["external_anchor"] is not None
        or observation["independent_witness"] is not None):
        return fail("POLICY_OR_HARDWARE_ASSERTION")
    reference = sha(encoded(expected_vector(nonce)))
    if observation["output_sha256"]!=reference or observation["expected_sha256"]!=reference:
        return fail("CPU_RECOMPUTATION_MISMATCH")
    return {"verdict":"CHALLENGED_ARITHMETIC_MATCH",
            "scope":"UNSIGNED_RUNTIME_REPORT_ONLY",
            "provider_authenticated":False,
            "gpu_hardware_attested":False,
            "production_trust":"UNVERIFIED",
            "challenge":nonce,"output_sha256":reference}

def main(argv=None):
    parser=argparse.ArgumentParser()
    subs=parser.add_subparsers(dest="mode",required=True)
    produce=subs.add_parser("observe"); produce.add_argument("--nonce",required=True); produce.add_argument("--out",required=True)
    check=subs.add_parser("verify"); check.add_argument("--nonce",required=True); check.add_argument("--input",required=True)
    args=parser.parse_args(argv)
    if args.mode=="observe":
        output=observe(args.nonce)
        pathlib.Path(args.out).write_bytes(encoded(output)+b"\n")
        print(json.dumps({"verdict":output["verdict"],"artifact":args.out},sort_keys=True))
        return 0 if output.get("verdict")=="CUDA_RUNTIME_OBSERVATION" else 2
    try:
        data=json.loads(pathlib.Path(args.input).read_bytes())
        output=verify(data,args.nonce)
    except (OSError,ValueError,TypeError):
        output={"verdict":"BLOCKED","reason":"INPUT_READ_OR_PARSE_ERROR"}
    print(json.dumps(output,sort_keys=True))
    return 0 if output["verdict"]=="CHALLENGED_ARITHMETIC_MATCH" else 2

if __name__=="__main__":
    sys.exit(main())
