"""Independently check bundled GitHub-run output hashes, not physical authenticity."""
from __future__ import annotations
import json,sys,zipfile
from pathlib import Path
from ecosystem_release.evidence import verify_chain,EvidenceRejected
from ecosystem_release.policy import EXTERNAL_GATES

def check(path):
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist()
        matches=[n for n in names if n.endswith("/acceptance.json") and
                 (n.startswith("ecosystem-release/evidence/") or n.startswith("evidence/core/"))]
        if len(matches)!=1:raise EvidenceRejected("one release acceptance record required")
        prefix=matches[0].rsplit("/",1)[0]+"/"
        report=json.loads(archive.read(matches[0]))
        entries=report["entries"]
        logs={e["name"]:archive.read(prefix+e["name"]+".log") for e in entries}
        verify_chain(entries,logs)
        if report["result"]!="PASS_SOFTWARE_ONLY" or any(e["returncode"] for e in entries):
            raise EvidenceRejected("failed or incomplete CI profile")
        if report["evidence_root_sha256"]!=entries[-1]["entry_hash"]:
            raise EvidenceRejected("wrong root")
        gates=report["release"]["gates"]
        for gate in EXTERNAL_GATES:
            if gates[gate]["status"]!="PENDING_INDEPENDENT_EVIDENCE":
                raise EvidenceRejected("forged external gate: "+gate)
        if report["release"]["production_ready"] is not False or report["release"]["physical_acceptance"] is not False:
            raise EvidenceRejected("improperly promoted release")
        return {"artifact":Path(path).name,"profile":report["profile"],
                "tasks":len(entries),"root":report["evidence_root_sha256"],
                "external_gates_pending":len(EXTERNAL_GATES),
                "note":"internally self-consistent only, not externally attested"}

if __name__=="__main__":
    print(json.dumps([check(p) for p in sys.argv[1:]],indent=2))
