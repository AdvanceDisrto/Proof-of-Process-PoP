"""Compose exactly three successful software-only CI job artifacts from the same source revision.

This is a digest check and release policy, not a remote runner attestation.
"""
from __future__ import annotations
import json,zipfile
from pathlib import Path
from .policy import SOFTWARE_GATES,EXTERNAL_GATES,release_gate_report,verify_policy_report
from .evidence import canonical,digest,verify_chain,EvidenceRejected

class AggregateRejected(EvidenceRejected):pass

def read_ci_archive(path):
    path=Path(path)
    with zipfile.ZipFile(path) as archive:
        matches=[n for n in archive.namelist() if n.endswith("/acceptance.json") and
                 (n.startswith("ecosystem-release/evidence/") or n.startswith("evidence/core/"))]
        if len(matches)!=1:raise AggregateRejected("expected one release acceptance record")
        prefix=matches[0].rsplit("/",1)[0]+"/"
        data=json.loads(archive.read(matches[0]))
        if data.get("schema")!="i-ecosystem-build-evidence/v1":
            raise AggregateRejected("unknown transcript schema")
        entries=data.get("entries")
        if type(entries) is not list or not entries:raise AggregateRejected("missing job entries")
        logs={e["name"]:archive.read(prefix+e["name"]+".log") for e in entries}
        verify_chain(entries,logs)
        if data.get("result")!="PASS_SOFTWARE_ONLY" or any(e["returncode"]!=0 for e in entries):
            raise AggregateRejected("failed CI job")
        if data.get("evidence_root_sha256")!=entries[-1]["entry_hash"]:
            raise AggregateRejected("evidence root mismatch")
        release=data["release"]
        if release.get("physical_acceptance") is not False or release.get("production_ready") is not False:
            raise AggregateRejected("unauthorized physical promotion")
        for gate in EXTERNAL_GATES:
            if release["gates"].get(gate)!={"status":"PENDING_INDEPENDENT_EVIDENCE","evidence_sha256":None}:
                raise AggregateRejected("external gate upgraded: "+gate)
        return {"profile":data["profile"],"source_commit":data["source_commit"],
                "root":data["evidence_root_sha256"],"archive_sha256":digest(path.read_bytes()),
                "tasks":len(entries),
                "software_gates":{k:v for k,v in release["gates"].items()
                                  if k in SOFTWARE_GATES and v["status"]!="NOT_RUN"}}

def aggregate(paths,expected_source_commit=None):
    if type(paths) is not list or len(paths)!=3:
        raise AggregateRejected("exactly three CI archives required")
    records=[read_ci_archive(p) for p in paths]
    if {r["profile"] for r in records}!={"core","integration","rtl"}:
        raise AggregateRejected("missing or repeated profile")
    commits={r["source_commit"] for r in records}
    if len(commits)!=1 or None in commits:
        raise AggregateRejected("mixed or missing source commits")
    commit=next(iter(commits))
    if expected_source_commit is not None and commit!=expected_source_commit:
        raise AggregateRejected("independent source commit pin mismatch")
    observed={}
    for row in records:
        for gate,entry in row["software_gates"].items():
            if gate in observed:raise AggregateRejected("duplicate software gate")
            if entry["status"]!="PASS_SOFTWARE_ONLY":raise AggregateRejected("nonpassing software gate")
            observed[gate]=entry
    if set(observed)!=set(SOFTWARE_GATES):
        raise AggregateRejected("incomplete 11-gate software acceptance")
    policy=release_gate_report(observed)
    if policy["software_only_release_candidate"] is not True or verify_policy_report(policy) is not True:
        raise AggregateRejected("software policy mismatch")
    parts=[{"profile":r["profile"],"transcript_root":r["root"],
            "artifact_sha256":r["archive_sha256"],"tasks":r["tasks"]}
            for r in sorted(records,key=lambda x:x["profile"])]
    result={"schema":"i-ecosystem-composite-acceptance/v1",
            "software_status":"ACCEPT_SOFTWARE_INTEGRATION_ONLY",
            "source_commit":commit,"parts":parts,
            "software_gates_verified":len(observed),
            "external_gates_pending":len(EXTERNAL_GATES),
            "physical_acceptance":False,"production_ready":False,
            "legal_certification":False,"clinical_approval":False,
            "limitations":["GitHub archives need independent provenance verification.",
                           "Hash chain root requires an externally pinned/signed timestamp for rollback resistance.",
                           "No clinical, physical, manufacturing or legal claim."]}
    result["bundle_root_sha256"]=digest(canonical(result))
    return result
