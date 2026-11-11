from __future__ import annotations
import json
from pathlib import Path
import pytest
from unified_i.bridge import run_synthetic_closed_loop
from unified_i.arbiter import audit_free_text,bounded_integer_verdict,twinions_compare,UnsupportedClaim


def test_end_to_end_3_actual_modules(tmp_path):
 result=run_synthetic_closed_loop(tmp_path)
 assert result["sqlite_journal"]["checked"]==3
 assert result["false_claim_receipt"]=="AUTHENTIC_REFUTED_BOUNDED_DEMO"
 assert result["escpos"]=="BYTES_RENDERED_NOT_PHYSICALLY_PRINTED"
 assert result["root_of_trust"]=="EPHEMERAL_SOFTWARE_NOT_HARDWARE"
 assert result["hardware_gates"]["physical_acceptance"] is False
 assert (tmp_path/"signed_ipqr_synthetic.png").stat().st_size>1000
 assert (tmp_path/"synthetic_unprinted.escpos").stat().st_size>1000
 assert (tmp_path/"imorphus_exact_pixels.png").stat().st_size>1000
 assert json.loads((tmp_path/"acceptance.json").read_text())["twinions_factual_truth"]=="UNDETERMINED"

@pytest.mark.parametrize("lhs,rhs,expected",[(2,2,"PASS_BOUNDED_CLAIM"),(3,2,"REFUTED_BOUNDED_CLAIM"),(-1,0,"PASS_BOUNDED_CLAIM"),(0,-1,"REFUTED_BOUNDED_CLAIM")])
def test_bounded_claim(lhs,rhs,expected):
 r=bounded_integer_verdict(lhs,rhs)
 assert r["status"]==expected and r["factual_truth"]=="NOT_ESTABLISHED"

@pytest.mark.parametrize("observed,maximum",[(True,1),(2.0,3),(10**15,0),(0,"2"),(None,0)])
def test_out_of_scope_arithmetic(observed,maximum):
 with pytest.raises(UnsupportedClaim):bounded_integer_verdict(observed,maximum)

@pytest.mark.parametrize("claim",["The tumor is benign","the court issued a verdict","Z3 proved all AI outputs","The secure element has a PUF"])
def test_free_text_unresolved(claim):
 assert audit_free_text(claim)["status"]=="UNRESOLVED"

def test_conflicting_models_do_not_authorize_diagnosis():
 result=twinions_compare([{'source':'A','question_id':'q','answer':'benign'},{'source':'B','question_id':'q','answer':'malignant'}])
 assert result['status']=='CONFLICT_DETECTED'
 assert result['factual_verdict']=='UNDETERMINED'

def test_agreeing_models_not_truth():
 result=twinions_compare([{'source':'A','question_id':'q','answer':'yes'},{'source':'B','question_id':'q','answer':'YES'}])
 assert result['status']=='NO_TEXTUAL_CONFLICT_DETECTED'
 assert result['factual_verdict']=='UNDETERMINED'
