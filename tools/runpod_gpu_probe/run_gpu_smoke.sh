#!/usr/bin/env bash
# Execute ONLY on an operator-chosen, already-running RunPod pod with a PHYSICAL AMD GPU.
set -euo pipefail
for utility in cargo rustc pkg-config vulkaninfo; do
  if ! command -v "$utility" >/dev/null 2>&1; then
    echo "RUNPOD_GPU_GATE=BLOCKED missing_dependency=$utility" >&2
    exit 42
  fi
done
if ! pkg-config --exists z3; then
  echo "RUNPOD_GPU_GATE=BLOCKED missing_dependency=libz3-dev" >&2
  exit 43
fi
echo "RUNPOD_GPU_GATE=GPU_WORKLOAD_START"
vulkaninfo --summary | head -80
echo "RUNPOD_GPU_GATE=CARGO_TEST"
cargo test --manifest-path tools/runpod_gpu_probe/Cargo.toml --release
echo "RUNPOD_GPU_GATE=REAL_AMD_VULKAN_COMPUTE"
cargo run --manifest-path tools/runpod_gpu_probe/Cargo.toml --release -- --gpu-smoke
echo "RUNPOD_GPU_GATE=PASS (physical AMD Vulkan compute and Z3 software path only)"
