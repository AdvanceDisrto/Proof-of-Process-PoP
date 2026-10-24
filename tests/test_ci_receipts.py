import time
from tools.ci_receipt_emitter import emit_stage_receipt,emit_run_summary
def test_stage_receipt_has_sha(tmp_path):
 r=emit_stage_receipt("unit-tests","PASS",1000,1001.5,"abc","111",out_dir=str(tmp_path));assert len(r["receipt_sha256"])==64;assert r["physical_gate"]=="ACTION_REQUIRED";assert "CI_RUNNER_CLOCK" in r["timestamp_source"]
def test_stage_receipt_is_canonical(tmp_path):
 a=dict(stage_name="d",result="PASS",started_at=1000,ended_at=1001,commit_sha="abc",run_id="1",out_dir=str(tmp_path));assert emit_stage_receipt(**a)["receipt_sha256"]==emit_stage_receipt(**a)["receipt_sha256"]
def test_duration(tmp_path): assert emit_stage_receipt("x","PASS",1000,1002.5,"a","1",out_dir=str(tmp_path))["duration_seconds"]==2.5
def test_summary(tmp_path):
 a=emit_stage_receipt("a","PASS",1,2,"x","1",out_dir=str(tmp_path));b=emit_stage_receipt("b","PASS",1,2,"x","1",out_dir=str(tmp_path));w=emit_run_summary([a,b],"x","1","T",out_dir=str(tmp_path));assert w["overall_result"]=="PASS" and w["physical_gate"]=="ACTION_REQUIRED"
def test_summary_fail(tmp_path):
 a=emit_stage_receipt("a","FAIL",1,2,"x","1",out_dir=str(tmp_path));assert emit_run_summary([a],"x","1","T",out_dir=str(tmp_path))["overall_result"]=="FAIL"
def test_boundary(tmp_path):
 r=emit_stage_receipt("a","PASS",1,2,"x","1",out_dir=str(tmp_path));assert "physical hardware measurement" in " ".join(r["does_not_prove"]).lower()
