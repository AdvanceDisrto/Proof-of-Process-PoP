#!/usr/bin/env python3
import json,os,sys,urllib.request
from pathlib import Path
def build_payload(r):
 failing=[s["stage"] for s in r["stages"] if s["result"]!="PASS"];mark="PASS" if r["overall_result"]=="PASS" else "FAIL"
 return {"content":f"i™ PoP — {r['workflow']}\nRun: {r['run_id']} · Commit: {r['commit_sha'][:8]}\nResult: {mark} · Stages: {r['stage_count']}\nFailing: {', '.join(failing) if failing else 'none'}\nphysical_gate: ACTION_REQUIRED — CI evidence is not hardware measurement."}
def fire(url,payload):
 req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json","User-Agent":"ipop-ci/1.0"});return urllib.request.urlopen(req,timeout=10).status
def main(path):
 r=json.loads(Path(path).read_text());url=os.environ.get("IPOP_NOTIFY_WEBHOOK")
 if not url: print("[Notify] webhook not configured; receipt remains source of truth.");return 0
 try: print(f"[Notify] fired (status {fire(url,build_payload(r))})");return 0
 except Exception as e: print(f"[Notify] failed: {e}",file=sys.stderr);return 1
if __name__=="__main__": sys.exit(main(sys.argv[1]) if len(sys.argv)==2 else 2)
