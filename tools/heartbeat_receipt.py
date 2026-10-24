#!/usr/bin/env python3
import hashlib,json,os,subprocess,time
from pathlib import Path
def run_check(name,cmd):
 start=time.time()
 try:
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=120);result="PASS" if r.returncode==0 else "FAIL";out=r.stdout[-500:];err=r.stderr[-500:]
 except subprocess.TimeoutExpired: result="TIMEOUT";out=err=""
 return {"check":name,"command":" ".join(cmd),"result":result,"duration_seconds":round(time.time()-start,3),"stdout_tail":out,"stderr_tail":err}
def emit_heartbeat(out_path,commit_sha,run_id):
 checks=[run_check("env_guard",["test","-f","requirements.txt"]),run_check("python_runtime",["python","-c","import sys; print(sys.version)"]),run_check("pytest_collect",["python","-m","pytest","tests/","-q","--collect-only"])]
 body={"spec":"innovulis-heartbeat-receipt/1.0","commit_sha":commit_sha,"run_id":run_id,"timestamp_utc":time.time(),"timestamp_source":"CI_RUNNER_CLOCK (wall clock; not cryptographically attested)","overall":"PASS" if all(c["result"]=="PASS" for c in checks) else "FAIL","checks":checks,"proves":["Repository prerequisites were checked.","Python executed.","The test suite collection command executed."],"does_not_prove":["That the full test suite passes.","That any AI model was invoked.","That edge infrastructure exists.","That physical energy was measured.","That the system is physically self-running."],"physical_gate":"ACTION_REQUIRED","the_central_rule":"The receipt can record reality; it cannot manufacture reality."}
 body["receipt_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest();p=Path(out_path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(body,indent=2)+"\n");return body
if __name__=="__main__":
 import sys
 r=emit_heartbeat(sys.argv[1] if len(sys.argv)>1 else "evidence/heartbeats/latest.json",os.environ.get("GITHUB_SHA","local"),os.environ.get("GITHUB_RUN_ID","local"));print(json.dumps(r,indent=2));raise SystemExit(0 if r["overall"]=="PASS" else 1)
