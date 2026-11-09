from __future__ import annotations
import json
from pathlib import Path
from jsonschema import Draft202012Validator,ValidationError
import pytest
from unified_i.physical import record_report
from unified_i.codec import ClaimRecord,sha256

ROOT=Path(__file__).parents[1]

@pytest.mark.parametrize('name',('unified-claim-v1.schema.json','physical-gates-v1.schema.json'))
def test_draft_202012_is_valid(name):
 schema=json.loads((ROOT/'spec'/name).read_text())
 Draft202012Validator.check_schema(schema)

def test_real_gate_report_matches_schema():
 schema=json.loads((ROOT/'spec'/'physical-gates-v1.schema.json').read_text())
 Draft202012Validator(schema).validate(record_report())

def test_gate_upgrade_rejected_by_schema():
 schema=json.loads((ROOT/'spec'/'physical-gates-v1.schema.json').read_text())
 d=record_report();d['physical_acceptance']=True
 with pytest.raises(ValidationError):Draft202012Validator(schema).validate(d)

def test_record_schema_synthetic():
 schema=json.loads((ROOT/'spec'/'unified-claim-v1.schema.json').read_text())
 r=ClaimRecord(event_id='synthetic-1',subject='demo:bench',assertion_kind='INTEGER_LTE',verdict='PASS_BOUNDED_CLAIM',
               source_tier='SYNTHETIC',evidence_sha256=sha256(b'demo'),issuer_key_id='demo-key',sequence=1,
               issued_at=1800000000,expires_at=1800000060,limitations=('test only',),observed_micro_units=2,maximum_micro_units=3)
 Draft202012Validator(schema).validate(r.to_dict())

def test_claim_schema_unassessed():
 schema=json.loads((ROOT/'spec'/'unified-claim-v1.schema.json').read_text())
 r=ClaimRecord(event_id='synthetic-1',subject='demo:bench',assertion_kind='DECLARED_UNASSESSED',verdict='UNRESOLVED',
               source_tier='SYNTHETIC',evidence_sha256=sha256(b'demo'),issuer_key_id='demo-key',sequence=1,
               issued_at=1800000000,expires_at=1800000060,limitations=('test only',))
 Draft202012Validator(schema).validate(r.to_dict())
