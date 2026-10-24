import hashlib
import json
import subprocess
from pathlib import Path


def run_renderer() -> dict[str, str]:
    result = subprocess.run(
        ["./build/render_combo"], check=True, capture_output=True, text=True
    )
    return dict(line.split("=", 1) for line in result.stdout.strip().splitlines())


def test_ray_trace_is_repeatable_and_boundary_safe():
    first = run_renderer()
    second = run_renderer()
    assert first == second
    assert first["algorithm"] == "deterministic-ray-tracing"
    assert len(first["framebuffer_sha256"]) == 64
    assert len(first["process_receipt"]) == 64
    assert first["physical_gate"] == "ACTION_REQUIRED"


def test_render_receipt_matches_binary_output():
    observed = run_renderer()
    receipt = json.loads(Path("RENDER_RECEIPT.json").read_text())
    assert receipt["framebuffer_sha256"] == "sha256:" + observed["framebuffer_sha256"]
    assert receipt["process_receipt"] == "sha256:" + observed["process_receipt"]
    assert receipt["physical_gate"] == "ACTION_REQUIRED"
    assert receipt["energy"]["state"] == "ACTION_REQUIRED"
    assert receipt["energy"]["measured_joules"] is None
