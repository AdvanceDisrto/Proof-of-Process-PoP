import hashlib
import json

import pytest

from egi_brain import FabricPayload, EpidemicGenesisBrain


def canonical_source(raw: dict) -> str:
    return json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def test_missing_model_weights_fail_closed(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        EpidemicGenesisBrain(str(tmp_path / "missing.gguf"))


def test_payload_hash_and_inference_state(tmp_path) -> None:
    weights = tmp_path / "egi.gguf"
    weights.write_bytes(b"real-test-model-bytes")
    raw = {
        "origin_node_id": "test-node",
        "timestamp": "2026-10-25T00:00:00+00:00",
        "clinical_data": {"marker": "observed"},
        "omics_data": {"proteomic_mutation": "G12V"},
        "environmental_data": {"toxin_level": 85},
    }
    payload_hash = hashlib.sha256(canonical_source(raw).encode()).hexdigest()
    payload = FabricPayload(data_hash=payload_hash, **raw)

    brain = EpidemicGenesisBrain(str(weights))
    receipt = brain.analyze_fabric_data(payload)

    assert receipt.state == "UNVERIFIED_INFERENCE"
    assert receipt.physical_gate_required is True
    assert receipt.input_hash == payload_hash
    assert len(receipt.model_weights_hash) == 64
    assert brain.handoff_state(receipt)["materialization"] == "BLOCKED"


def test_tampered_payload_is_quarantined(tmp_path) -> None:
    weights = tmp_path / "egi.gguf"
    weights.write_bytes(b"real-test-model-bytes")
    raw = {
        "origin_node_id": "test-node",
        "timestamp": "2026-10-25T00:00:00+00:00",
        "clinical_data": {"marker": "observed"},
        "omics_data": {"proteomic_mutation": "G12V"},
        "environmental_data": {"toxin_level": 85},
    }
    payload_hash = hashlib.sha256(canonical_source(raw).encode()).hexdigest()
    raw["environmental_data"]["toxin_level"] = 86
    payload = FabricPayload(data_hash=payload_hash, **raw)

    with pytest.raises(ValueError, match="QUARANTINED"):
        EpidemicGenesisBrain(str(weights)).analyze_fabric_data(payload)
