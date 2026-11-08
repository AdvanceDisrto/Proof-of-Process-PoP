# Tessera-G open hardware boundary, v0.1

## What G means at this acceptance tier

The long-form architectural definition is `G = (H,C,F,M,N,I,S,P,D,T,V,Q,B,R)`.
It is a **planning taxonomy**, not evidence that all blocks exist.

| Layer | Actual accepted implementation |
|---|---|
| H / Host | Simple ready/valid append port and readback, not PCIe or AXI |
| C / Compute | Synthesizable per-node (two-parent) status propagation only |
| F / Fixed-function | Node status gate; no rasterizer, ROP, or shader execution |
| M / Memory | Small inferred RTL array, not DDR/HBM |
| N / Interconnect | No NoC, network transport, or TileLink implementation |
| I / ISA | None; command fields are not RV64 or SPIR-V instructions |
| S / Security | Fail-closed on unknown/invalid dependencies, but no secure boot or PUF |
| P / Programming | Python reference model plus typed status input |
| D / Driver | No Mesa/Vulkan driver |
| T / Toolchain | Icarus/Verilator/Yosys workflow; CPU Z3 remains external |
| V / Verification | Directed RTL TB, model comparison, randomized Python properties |
| Q / Quality | Verifiable build gates, no silicon characterization |
| B / Buildability | Synthesis-logic check only, not placed/routed or FPGA boot |
| R / Release | Draft PR and operator approval; no ASIC or chiplet |

### Important corrections to the draft architecture

1. A Merkle DAG cannot generally be traversed or authenticated in O(1) time.
   This prototype costs O(V+E) for ingest/propagation, with fixed two-parent
   comparisons per node. It does *not* verify SHA-256 hashes in hardware.
2. SMT, QF_LIA, SAT and UNSAT are formal solver concepts. The RTL does not
   implement Z3 or solve unconstrained SMT formulas. An external, independently
   checked formal statement must supply the local verdict; tampered inputs
   can defeat this untrusted interface.
3. Deterministic status propagation is useful for **blocking visualizations**
   of dependents. It does not make a human claim universally true/false or
   force all displays to be truthful.
4. An ATECC608C is a separate hardware secure element using ECDSA P-256.
   The RTL does not implement an equivalent PUF or provide zeroization.
5. Owning RTL does not establish absence of hidden firmware or manufacturing
   backdoors. It also does not eliminate EDA, FPGA vendor, package, foundry,
   driver, or board dependencies.
6. Verilator, Yosys and a passing CI simulation do not prove a working FPGA,
   calibrated sensor, trusted witness, board timing closure, or tapeout.
7. This change also upgrades the RunPod Rust/WGSL GPU smoke to preserve
   two-parent joins and explicitly distinguish unknown from refuted status.
   It has only CPU shader validation until an actual AMD Vulkan GPU run is evidenced.
8. Claims of 100x speed, 1 GHz clocks, physical tamper resistance, commercial
   compliance, patentability, or independently verified energy are NOT supported.

## Next accepted milestones

- Execute real Icarus/Verilator directed simulation and Yosys logic synthesis.
- Add an AXI-lite command / status bridge, clock-domain crossing if necessary,
  bounded buffers, tests for reset and memory hazards, and FPGA constraints.
- On operator-provided FPGA, generate a bitstream, program, and compare
  measured readbacks to software model with a pinned firmware/bitstream digest.
- Bind *trusted* external Z3 receipt + individually verified signatures to
  a hardware command packet (checksum alone is insufficient).
- Only then claim an FPGA prototype; a custom GPU requires far more work:
  ISA, compiler/backend, memory system, coherence, scheduling, rasterizer,
  graphics driver, perf tests, security analysis and formal verification.

No VM, Cloudflare page, RunPod pod, PR or AWS resource has been provisioned
or changed by RTL synthesis itself. No existing PR is merged without approval.
