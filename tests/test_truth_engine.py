import json
import subprocess
from pathlib import Path

def test_truth_engine_fail_closed():
    exe = Path("build/truth_engine")
    assert exe.exists()
    out = subprocess.check_output([str(exe)], text=True)
    receipt = json.loads(out)
    assert receipt["execution_state"] == "VERIFIED_PROCESS"
    assert receipt["physical_gate"] == "ACTION_REQUIRED"
    assert receipt["hardware_telemetry_signature"] == "UNOBSERVED"
    assert receipt["epistemological_boundary"] == "SOFTWARE_KEYS_DO_NOT_PROVE_SILICON_MATRICES"
