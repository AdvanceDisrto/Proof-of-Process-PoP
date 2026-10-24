#!/usr/bin/env python3
import json,os,sys,time,urllib.request
from datetime import datetime,timezone
REPO=os.environ.get("GITHUB_REPO","AdvanceDisrto/Proof-of-Process-PoP");TOKEN=os.environ.get("GITHUB_TOKEN","")
WORKFLOWS=["i™ Unified Proof of Process CI","i™ Parallel Proof CI","TEE Scrape Simulation","Antimatter Simulation","Ambient Harvester Verifier","Omnipresent Mesh Verifier","Antimatter Tiered Evidence","CI Observability"]
def api(path):
 h={"Accept":"application/vnd.github+json","User-Agent":"ipop-monitor/1.0"}; 
 if TOKEN:h["Authorization"]=f"Bearer {TOKEN}"
 with urllib.request.urlopen(urllib.request.Request(f"https://api.github.com/repos/{REPO}{path}",headers=h),timeout=10) as r:return json.load(r)
def fetch_latest_runs():
 latest={}
 for r in api("/actions/runs?per_page=50")["workflow_runs"]: latest.setdefault(r["name"],r)
 return [latest.get(w) for w in WORKFLOWS]
def render(runs):
 lines=["="*72,f"i™ PoP — LIVE STATUS · {datetime.now(timezone.utc).isoformat()}","="*72]
 for r in runs:
  if not r: continue
  s=r.get("conclusion") or r.get("status");lines.append(f"  {r['name'][:38]:<40} {s or 'pending':<12} {r['created_at'][:19]}")
 lines+=["="*72,"physical_gate: ACTION_REQUIRED — CI confirms software checks, not hardware."]
 return "\n".join(lines)
def main():
 while True:
  try: print("\033[2J\033[H"+render(fetch_latest_runs()))
  except Exception as e: print(f"[Monitor] error: {e}",file=sys.stderr)
  time.sleep(10)
if __name__=="__main__":main()
