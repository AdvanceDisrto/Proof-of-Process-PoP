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
        "sha256:614ec72c3a45e92e74236d110e741a67"
        "bfde80a86b30a61a5b79418a09677850"
    )
    assert first["physical_gate"] == "ACTION_REQUIRED"
    assert "TPM quote or hardware-rooted attestation" in first["does_not_prove"]
