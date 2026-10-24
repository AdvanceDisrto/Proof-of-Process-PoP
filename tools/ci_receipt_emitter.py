#!/usr/bin/env python3
import hashlib,json,time
from pathlib import Path
def _hash(body): return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def emit_stage_receipt(stage_name,result,started_at,ended_at,commit_sha,run_id,extra=None,out_dir="evidence/ci_receipts"):
    if ended_at < started_at: raise ValueError("ended_at must be >= started_at")
    body={"spec":"innovulis-ci-stage-receipt/1.0","stage":stage_name,"result":result,"started_utc":started_at,"ended_utc":ended_at,"duration_seconds":round(ended_at-started_at,3),"timestamp_source":"CI_RUNNER_CLOCK (GitHub Actions, wall clock; not cryptographically attested)","commit_sha":commit_sha,"run_id":run_id,"extra":extra or {},"physical_gate":"ACTION_REQUIRED","proves":[f"The '{stage_name}' stage result was recorded as {result}.","The timestamps were reported by the CI runner wall clock."],"does_not_prove":["That the CI runner clock is cryptographically attested.","That any physical hardware measurement was taken.","That the underlying code is correct beyond the checks represented by the stage."]}
    body["receipt_sha256"]=_hash(body); p=Path(out_dir)/f"{stage_name.replace('/','_')}__{run_id}.json";p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(body,indent=2)+"\n");return body
def emit_run_summary(stages,commit_sha,run_id,workflow_name,out_dir="evidence/ci_receipts"):
    overall="PASS" if stages and all(s["result"]=="PASS" for s in stages) else "FAIL"
    body={"spec":"innovulis-ci-workflow-receipt/1.0","workflow":workflow_name,"run_id":run_id,"commit_sha":commit_sha,"overall_result":overall,"stage_count":len(stages),"stages":[{"stage":s["stage"],"result":s["result"],"duration_seconds":s["duration_seconds"],"receipt_sha256":s["receipt_sha256"]} for s in stages],"timestamp_source":"CI_RUNNER_CLOCK (GitHub Actions, wall clock; not cryptographically attested)","generated_utc":time.time(),"physical_gate":"ACTION_REQUIRED","the_central_rule":"The receipt can record reality; it cannot manufacture reality."}
    body["workflow_receipt_sha256"]=_hash(body);p=Path(out_dir)/f"workflow__{workflow_name.replace('/','_')}__{run_id}.json";p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(body,indent=2)+"\n");return body
if __name__=="__main__":
 import argparse
 p=argparse.ArgumentParser();p.add_argument("--stage",required=True);p.add_argument("--result",required=True,choices=["PASS","FAIL","SKIP"]);p.add_argument("--started-at",type=float,required=True);p.add_argument("--ended-at",type=float,required=True);p.add_argument("--commit",required=True);p.add_argument("--run-id",required=True);p.add_argument("--out-dir",default="evidence/ci_receipts");a=p.parse_args();emit_stage_receipt(a.stage,a.result,a.started_at,a.ended_at,a.commit,a.run_id,out_dir=a.out_dir)
