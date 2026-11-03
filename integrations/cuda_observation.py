"""Read-only CUDA arithmetic observation for future real GPU hardware runs.

No automatic CUDA fallback to CPU. An output hash and device name are runtime
assertions, not remote attestation, independent witnessing, or proof of silicon.
Run manually with an existing GPU host: python -m integrations.cuda_observation
"""
from __future__ import annotations
import json,sys
from integrations.hardware_neutral_receipt import canonical,digest

N = 4096
SCHEMA="ipqr/cuda-arithmetic-observation/v1"

def expected_output_bytes():
    return canonical([i*3+7 for i in range(N)])

def verify_cuda_observation(data):
    """Verify reproducible arithmetic only, NOT physical GPU identity."""
    if not isinstance(data,dict) or set(data)!={"schema","scope","cuda_available",
            "device_name_reported","task","output_hash","elements","external_anchor",
            "production_trust","physical_gpu_attestation"}:
        return {"verdict":"BLOCKED","reason":"RECORD_STRUCTURE"}
    if (data["schema"]!=SCHEMA or data["scope"]!="UNATTESTED_CUDA_RUNTIME_REPORT"
        or data["cuda_available"] is not True or not isinstance(data["device_name_reported"],str)
        or not data["device_name_reported"] or data["task"]!="int64_linear_transform_x3_plus_7"
        or type(data["elements"]) is not int or data["elements"]!=N
        or data["external_anchor"] is not None or data["production_trust"]!="UNVERIFIED"
        or data["physical_gpu_attestation"] is not None):
        return {"verdict":"BLOCKED","reason":"UNTRUSTED_OR_MISLABELED_GPU_OBSERVATION"}
    if data["output_hash"]!=digest(expected_output_bytes()):
        return {"verdict":"BLOCKED","reason":"CPU_RECOMPUTATION_MISMATCH"}
    return {"verdict":"ARITHMETIC_RECOMPUTED",
            "hardware_proven":False,"source":"UNATTESTED_RUNTIME_CLAIM",
            "production_trust":"UNVERIFIED"}

def run_cuda():
    try:
        import torch
    except ImportError:
        return {"verdict":"BLOCKED","reason":"PYTORCH_MISSING"}
    if not torch.cuda.is_available():
        return {"verdict":"BLOCKED","reason":"CUDA_UNAVAILABLE"}
    try:
        device="cuda:0"
        with torch.no_grad():
            input_tensor=torch.arange(N,device=device,dtype=torch.int64)
            output=input_tensor*3+7
            torch.cuda.synchronize()
            output_bytes=canonical(output.cpu().tolist())
        result={"schema":SCHEMA,"scope":"UNATTESTED_CUDA_RUNTIME_REPORT",
                "cuda_available":True,
                "device_name_reported":torch.cuda.get_device_name(0),
                "task":"int64_linear_transform_x3_plus_7","elements":N,
                "output_hash":digest(output_bytes),"external_anchor":None,
                "production_trust":"UNVERIFIED","physical_gpu_attestation":None}
        # Fail if host cannot independently reproduce deterministic output.
        check=verify_cuda_observation(result)
        if check["verdict"]!="ARITHMETIC_RECOMPUTED":
            return {"verdict":"BLOCKED","reason":"OUTPUT_MISMATCH"}
        return result
    except (RuntimeError,ValueError,TypeError,AttributeError) as exc:
        return {"verdict":"BLOCKED","reason":"CUDA_PROBE_FAILURE:"+type(exc).__name__}

if __name__=="__main__":
    data=run_cuda()
    print(json.dumps(data,sort_keys=True))
    sys.exit(0 if data.get("schema")==SCHEMA else 2)
