import json
from pathlib import Path
import pytest
from ecosystem_release.policy import release_gate_report,SOFTWARE_GATES,EXTERNAL_GATES

ROOT=Path(__file__).resolve().parents[1]

def test_contract_schema_is_valid():
    from jsonschema import Draft202012Validator
    s=json.loads((ROOT/"spec/release-gates-v1.schema.json").read_text())
    Draft202012Validator.check_schema(s)
    Draft202012Validator(s).validate(release_gate_report())

def test_physical_upgrade_is_rejected_by_schema():
    from jsonschema import Draft202012Validator,ValidationError
    s=json.loads((ROOT/"spec/release-gates-v1.schema.json").read_text())
    r=release_gate_report()
    r["physical_acceptance"]=True
    with pytest.raises(ValidationError):Draft202012Validator(s).validate(r)

def test_32_gates_accounted_for():
    assert len(SOFTWARE_GATES)==11
    assert len(EXTERNAL_GATES)==21
    assert set(SOFTWARE_GATES).isdisjoint(EXTERNAL_GATES)
