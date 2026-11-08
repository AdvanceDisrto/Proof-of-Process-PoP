# iNNOVULIS™ Tessera-G — single-tile hardware status propagator v0.1

**Executable RTL component, not a finished sovereign GPU.**

This enhancement adds a small synthesizable SystemVerilog accelerator for the
**dependency-status** operation underlying DAGE. It handles one- or two-parent
append-only directed acyclic graphs. It enforces topological order,
propagates blocked/refuted/unknown states, rejects duplicate and future parents,
and provides register-style readback and overflow detection.

Node status codes: `0 EMPTY`, `1 ACCEPTED`, `2 REFUTED`, `3 DEPENDENCY_BLOCKED`,
`4 UNDETERMINED`, `5 INVALID_TOPOLOGY`.

### Engineering gate

On Ubuntu/Debian with Python 3, Icarus Verilog, Verilator and Yosys installed:

```bash
bash ci/run_gate.sh
```

The gate runs Python unit/property tests, a real HDL simulator testbench,
compares all committed RTL states to an independent Python reference model,
lints Verilog and invokes Yosys logic synthesis. The GitHub Actions workflow
runs the same gates headlessly and publishes the trace as a CI artifact.

**Integration**: the model exports **two-parent** statuses and dependency depth
to the upgraded `tools/runpod_gpu_probe` GPU shader. The same pull request
extends the Rust/WGSL structure with two-parent gates and adds a headless
Naga WGSL parser/validator test. CPU Z3 remains separate from GPU status propagation.

This RTL **does not** execute Z3, SHA-256, cryptographic signatures, RISC-V,
Vulkan, or physical sensor measurements, and is not a completed FPGA or ASIC.
See `docs/TESSERA_G_TRUST_BOUNDARIES.md`.
