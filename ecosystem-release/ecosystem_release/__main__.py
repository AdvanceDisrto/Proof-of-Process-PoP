"""i™ deterministic source inventory, smoke and evidence verification CLI."""
from __future__ import annotations
import argparse,json,sys
from .catalog import inventory
from .policy import release_gate_report
from .runner import task_plan,run,verify_disk

def main(argv=None):
    p=argparse.ArgumentParser(prog="ecosystem-release")
    sp=p.add_subparsers(dest="cmd",required=True)
    i=sp.add_parser("inventory");i.add_argument("--repo",default=".");i.add_argument("--strict",action="store_true")
    pl=sp.add_parser("plan");pl.add_argument("--profile",choices=("core","integration","rtl","all"),default="core")
    r=sp.add_parser("run");r.add_argument("--repo",default=".")
    r.add_argument("--profile",choices=("core","integration","rtl","all"),default="core")
    r.add_argument("--out",default="ecosystem-release/evidence/ci");r.add_argument("--commit")
    v=sp.add_parser("verify");v.add_argument("evidence_dir")
    sp.add_parser("policy")
    a=p.parse_args(argv)
    if a.cmd=="inventory":
        value=inventory(a.repo)
        missing=value["total_components"]-value["source_present"]
        value["missing_components"]=missing
        print(json.dumps(value,sort_keys=True,indent=2))
        return 0 if missing==0 or not a.strict else 3
    if a.cmd=="plan":
        print(json.dumps([{"name":t.name,"argv":list(t.argv),"profile":t.profile,
            "gates":list(t.gates)} for t in task_plan(a.profile)],indent=2))
        return 0
    if a.cmd=="run":
        record=run(a.profile,a.repo,a.out,commit_sha=a.commit)
        print(json.dumps({"result":record["result"],"tasks":record["task_count"],
            "evidence_root_sha256":record["evidence_root_sha256"],"physical_acceptance":False},indent=2))
        return 0 if record["result"]=="PASS_SOFTWARE_ONLY" else 1
    if a.cmd=="verify":
        print(json.dumps(verify_disk(a.evidence_dir),indent=2));return 0
    if a.cmd=="policy":
        print(json.dumps(release_gate_report(),indent=2));return 0
    return 2

if __name__=="__main__":sys.exit(main())
