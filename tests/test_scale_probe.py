from pathlib import Path
import json
import subprocess
import sys

def test_scale_probe_bounded_and_receipt(tmp_path):
    out=tmp_path/"receipt.json"
    p=subprocess.run(
        [sys.executable,"-m","sovereign_cpu.scale_probe","--max-probe-mb","32","--output",str(out)],
        capture_output=True,text=True,check=True,timeout=120,
    )
    assert "GAIA PHYSICAL LIMIT PROBE" in p.stdout
    receipt=json.loads(out.read_text())
    assert receipt["protocol"]=="IPROOF-SCALE-v1"
    assert receipt["device"]=="CPU"
    assert receipt["probe_cap_bytes"]==32*1024*1024
    assert receipt["terminal_state"] in {"BACKWARD_VERIFIED","PHYSICAL_LIMIT_REACHED","PROCESS_ABORTED_UNOBSERVED"}
    assert receipt["signature"]
    assert receipt["receipt_hash"]
