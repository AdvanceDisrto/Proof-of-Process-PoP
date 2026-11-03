# RunPod-only iRECEIPT GPU EiL probe — review candidate

This branch adds a deterministic CUDA arithmetic challenge and an independently
recomputed CPU result check. It never provisions, stops, deletes or resizes GPU
pods. Run **only on your existing authorized RunPod GPU pod**.

## On a connected RunPod CUDA pod

Install a CUDA-enabled PyTorch build compatible with your GPU and drivers using
the current official PyTorch installation instructions; do not copy an
untested CUDA wheel command into production. From a checkout of this commit:

```sh
export RUNPOD_POD_ID="<the existing pod ID from your trusted RunPod environment>"
# Fresh independent verifier challenge supplied out-of-band, hex 32-128 chars.
python -m integrations.runpod_eil_gpu observe --nonce "<fresh-hex-challenge>" --out runpod-gpu-observation.json
```

The process exits **2** if the RunPod pod ID or CUDA is missing, output differs
from an independent CPU reference, or the input is invalid. It exits **0**
only if the local Python process reports CUDA and its vector matches the
deterministic CPU reference.

Copy the JSON observation over an independently authenticated transfer route
and run on a separate CPU:

```sh
python -m integrations.runpod_eil_gpu verify --nonce "<same-fresh-hex-challenge>" --input runpod-gpu-observation.json
```

An `CHALLENGED_ARITHMETIC_MATCH` result **does not** authenticate RunPod or
the GPU, because the unsigned observation originates from the same process
that claims to have executed CUDA. Stronger evidence still requires a distinct
operator-attested signer, externally pinned production authority, tamper-resistant
execution telemetry, and an independent witness that actually observed the task.
No production LIVE root or secret is read or generated here.

## In this repository

GitHub Actions runs only CPU-negative tests and rejects missing
`RUNPOD_POD_ID`. CI never reports GPU execution success unless a separate
GPU-capable trusted runner is connected and verified.

The probe uses 4096 int64 values with a nonce-derived vector and GPU arithmetic.
It is **not** LLM inference, GPU performance benchmarking, physical-silicon
attestation, Bitcoin anchoring, ML-DSA, a production deployment or grid control.

No automatic fallback to another GPU provider, and no merge without approval.
