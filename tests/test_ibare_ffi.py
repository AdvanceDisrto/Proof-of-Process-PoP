from pathlib import Path

import pytest

from polyglot.ffi_bridge import IBareBridge

LIB = Path("build/libibare.so")


@pytest.mark.skipif(not LIB.exists(), reason="build/libibare.so not built")
def test_ffi_receipt_is_deterministic_and_boundary_safe():
    bridge = IBareBridge(LIB)
    first = bridge.receipt(b"AI Inference Result", 1778035000)
    second = bridge.receipt(b"AI Inference Result", 1778035000)
    assert first["receipt_hash"] == second["receipt_hash"]
    assert first["payload_hash"] == (
        "sha256:5c3e67c897872dc814d3b0cca7f93551"
        "c42e8dc184940ec50e3eca0d64ca740e"
    )
    assert first["physical_gate"] == "ACTION_REQUIRED"
    assert "TPM quote or hardware-rooted attestation" in first["does_not_prove"]
