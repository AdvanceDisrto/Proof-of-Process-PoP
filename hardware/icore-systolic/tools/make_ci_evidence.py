#!/usr/bin/env python3
"""Produce evidence-bound CI receipt from actual RTL simulator and synthesis logs."""
import hashlib
import json
import os
import re
from pathlib import Path

sim = Path("systolic-simulation.log").read_bytes()
synth = Path("systolic-synthesis.log").read_bytes()
gowin = Path("systolic-gowin-mapping.log").read_bytes()
gowin_netlist = Path("icore-gowin-netlist.json").read_bytes()
simtext = sim.decode(errors="replace")
synthtext = synth.decode(errors="replace")
required = {
    "corner": 32,
    "skew": 16,
    "back_to_back": 4,
    "mid_pipeline_resets": 4,
    "randomized": 512,
    "deterministic_replays": 1000,
}
patterns = {
    "corner": r"^PASS corner_vectors=(\d+)$",
    "skew": r"^PASS skew_vectors=(\d+)$",
    "back_to_back": r"^PASS back_to_back_vectors=(\d+)$",
    "mid_pipeline_resets": r"^PASS mid_pipeline_resets=(\d+)$",
    "randomized": r"^PASS randomized_vectors=(\d+) seed=0x00091911$",
    "deterministic_replays": r"^PASS deterministic_replays=(\d+)$",
}
counts = {}
for name, regex in patterns.items():
    matches = re.findall(regex, simtext, flags=re.MULTILINE)
    if len(matches) != 1 or int(matches[0]) != required[name]:
        raise SystemExit("FAIL_EVIDENCE_COUNT_" + name)
    counts[name] = int(matches[0])
total = sum(counts.values())
expected = (
    f"ALL_SYSTOLIC_SIMULATION_TESTS_PASS total={total} "
    "skew_scheme=output_stationary array=2x2 tiles_per_matmul=1"
)
if total != 1568 or expected not in simtext:
    raise SystemExit("FAIL_SUMMARY_MISMATCH")
if "Found and reported 0 problems." not in synthtext or "Number of cells:" not in synthtext:
    raise SystemExit("FAIL_SYNTHESIS_EVIDENCE")
if "Found and reported 0 problems." not in gowin.decode(errors="replace"):
    raise SystemExit("FAIL_GOWIN_MAPPING_EVIDENCE")
if not gowin_netlist.strip():
    raise SystemExit("FAIL_GOWIN_NETLIST_MISSING")
paths = [
    "hardware/icore-systolic/rtl/icore_pe.sv",
    "hardware/icore-systolic/rtl/icore_systolic_2x2.sv",
    "hardware/icore-systolic/tb/tb_icore_systolic_2x2.sv",
]
body = {
    "schema": "ipqr/icore-rtl-ci-evidence/v0.3",
    "source": "github-actions-ci",
    "commit": os.getenv("GITHUB_SHA", "LOCAL_UNVERIFIED_COMMIT"),
    "architecture": {
        "type": "digital_systolic",
        "stationarity": "output_stationary",
        "array_dims": [2, 2],
        "matrix_dims": [2, 2],
        "tiles_per_matmul": 1,
        "data": "signed_int8_x_int8_int32",
        "skew_scheme": "row_i_at_tick_i_plus_k__column_j_at_tick_j_plus_k",
        "execution": "four_wavefront_mac_cycles_plus_controller_completion",
        "testbench_completion_wait_cycles": 4,
    },
    "verification": {
        "counts": counts,
        "total_checked_executions": total,
        "testbench_random_seed": "0x00091911",
        "verdict": "ACCEPT_RTL_SIMULATION",
    },
    "synthesis": {
        "tool": "yosys",
        "gowin_primitive_mapping": "PASS",
        "gowin_placement_and_routing": "NOT_RUN",
        "target": "generic",
        "structural_check": "PASS",
        "target_lut": None,
        "target_dsp": None,
        "timing_slack_ns": None,
        "timing_closed": False,
    },
    "evidence_sha256": {
        "simulation_log": hashlib.sha256(sim).hexdigest(),
        "synthesis_log": hashlib.sha256(synth).hexdigest(),
        "gowin_mapping_log": hashlib.sha256(gowin).hexdigest(),
        "gowin_unplaced_netlist": hashlib.sha256(gowin_netlist).hexdigest(),
        "rtl_and_testbench": {
            name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in paths
        },
    },
    "signed": False,
    "fpga_bitstream_sha256": None,
    "physical_execution_observed": False,
    "physical_gate": "ACTION_REQUIRED",
    "does_not_prove": [
        "FPGA-specific resources or timing closure",
        "Programmed FPGA, hardware identity, or physical execution",
        "Cryptographic independent attestation",
        "4x4 matmul or a general iISA decoder",
    ],
}
Path("icore-rtl-evidence.json").write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
print("ACCEPT_RTL_CI_EVIDENCE total_checked_executions=" + str(total))
