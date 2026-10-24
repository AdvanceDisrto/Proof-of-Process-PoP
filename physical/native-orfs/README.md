# Native ORFS SPU preflight

This lane is intentionally separate from hosted RTL/reference CI. It validates canonical source custody and the no-container physical-design boundary before an OpenROAD/ORFS run.

The preflight does not claim placement, routing, timing closure, DRC/LVS, real SRAM macros, fabricated silicon, measured power, HBM, UCIe, or networking.

Required promotion evidence remains external to this software repository. A successful preflight leaves:
- real20MiBSramProven=false
- tapeoutReady=false
- physical_gate=ACTION_REQUIRED
