# Copyright 2026 AdvanceDisrto · Apache-2.0
from tools.gate import energy_is_measured, physical_gate, tee_quote_is_attested


def test_gate_rejects_presence():
    assert physical_gate("q", 1.0) == "ACTION_REQUIRED"
    assert physical_gate("anything", 0.0) == "ACTION_REQUIRED"
    assert physical_gate(None, None) == "ACTION_REQUIRED"
    assert not tee_quote_is_attested("q")
    assert not energy_is_measured(1.0)


def test_gate_rejects_untrusted_structure():
    assert physical_gate(
        {"vendor_chain": ["SELF_SIGNED"], "measurement": "x"},
        {"joules": 1.0, "source": "signed:lab"},
    ) == "ACTION_REQUIRED"
    assert physical_gate(
        {"vendor_chain": ["AMD_SEV_SNP_ROOT_CA"]},
        {"joules": 1.0, "source": "signed:lab"},
    ) == "ACTION_REQUIRED"
    assert physical_gate(
        {"vendor_chain": ["AMD_SEV_SNP_ROOT_CA"], "measurement": "x"},
        {"joules": 1.0, "source": "estimated"},
    ) == "ACTION_REQUIRED"


def test_gate_accepts_attested_objects():
    assert physical_gate(
        {"vendor_chain": ["AMD_SEV_SNP_ROOT_CA"], "measurement": "deadbeef"},
        {"joules": 1.0, "source": "signed:lab-a"},
    ) == "MEASURED_PASS"
