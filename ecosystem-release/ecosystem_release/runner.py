"""Allowlisted cross-component smoke execution. No commands supplied by a QR or user manifest."""
from __future__ import annotations
import os,sys,json,subprocess,time
from dataclasses import dataclass
from pathlib import Path
from .catalog import inventory
from .policy import release_gate_report,verify_policy_report
from .evidence import make_record,verify_chain,safe_atomic_json

@dataclass(frozen=True)
class Task:
    name:str
    profile:str
    argv:tuple[str,...]
    cwd:str
    required_paths:tuple[str,...]
    gates:tuple[str,...]
    timeout:int=180
    required_markers:tuple[bytes,...]=()

TASKS=(
 Task("python_unit","core",("{python}","-m","pytest","-q","ecosystem-release/tests"),".",
      ("ecosystem-release/tests/test_evidence.py",),("PYTHON_UNIT_TESTS",),120),
 Task("source_inventory","core",("{python}","-m","ecosystem_release","inventory","--repo",".","--strict"),".",
      ("unified-i/unified_i/bridge.py","ipcih-capsule/ipcih/core.py"),
      ("SOURCE_INVENTORY",),45,(b'"missing_components": 0',)),
 Task("integrated_synthetic","integration",("bash","unified-i/ci/run_all.sh"),".",
      ("unified-i/ci/run_all.sh","twinions-legal/twinions_legal/arbiter.py"),
      ("SYNTHETIC_IPQR_END_TO_END",),780,(b"UNIFIED_I_SOFTWARE_INTEGRATION=PASS",)),
 Task("signed_browser_crypto","integration",("node","--test","ipcih-capsule/tests/test_browser.mjs"),".",
      ("ipcih-capsule/tests/test_browser.mjs",),("WEBCRYPTO_TESTS",),120),
 Task("two_client_websocket","integration",("{python}","rgpu-terminal/ci/smoke_live.py"),".",
      ("rgpu-terminal/ci/smoke_live.py",),("HTTP_WEBSOCKET_SMOKE",),150,
      (b'"two_concurrent_websocket_clients": "PASS"',)),
 Task("tessera_rtl","rtl",("bash","tessera-g/ci/run_gate.sh"),".",
      ("tessera-g/ci/run_gate.sh",),
      ("TESSERA_RTL_SIM","STRICT_HDL_LINT","GENERIC_HDL_SYNTH"),360,
      (b"VERILATOR_STRICT_LINT=PASS",b"YOSYS_GENERIC_SYNTHESIS=PASS")),
 Task("popc_rtl","rtl",("bash","paper-console/ci/run_rtl.sh"),".",
      ("paper-console/ci/run_rtl.sh",),("POPC_RTL_SIM",),180,(b"POPC_GATE_SIM=PASS",)),
)

class SmokeError(RuntimeError):pass

def task_plan(profile):
    if profile not in ("core","integration","rtl","all"):
        raise SmokeError("profile not allowed")
    return tuple(t for t in TASKS if t.profile==profile or profile=="all")

def _command(task,root):
    cwd=(root/task.cwd).resolve()
    if not cwd.is_relative_to(root):raise SmokeError("task cwd escaped checkout")
    for p in task.required_paths:
        f=(root/p).resolve()
        if not f.is_relative_to(root) or not f.is_file():
            raise SmokeError("source missing for "+task.name+": "+p)
    return [sys.executable if a=="{python}" else a for a in task.argv],cwd

def run(profile,repo_root,out_dir,*,commit_sha=None):
    root=Path(repo_root).resolve()
    if not root.is_dir():raise SmokeError("repo path missing")
    out=Path(out_dir).resolve()
    if out==root or not out.is_relative_to(root):
        raise SmokeError("evidence must live inside checkout subfolder")
    out.mkdir(parents=True,exist_ok=True)
    entries=[];logs={};observed={};success=True
    for t in task_plan(profile):
        argv,cwd=_command(t,root)
        env=os.environ.copy()
        env["PYTHONPATH"]=os.pathsep.join((
            str(root/"ecosystem-release"),str(root/"unified-i"),str(root/"paper-console"),
            str(root/"paper-console/integrations"),str(root/"human-hub"),
            str(root/"ipcih-capsule"),str(root/"twinions-legal"),str(root/"rgpu-terminal"),
            env.get("PYTHONPATH","")))
        env["INNOVULIS_PHYSICAL_ACCEPTANCE"]="PENDING"
        start=time.monotonic()
        try:
            process=subprocess.run(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                   timeout=t.timeout,check=False)
            output=process.stdout[:2_000_000]
            code=process.returncode
        except subprocess.TimeoutExpired as exc:
            output=(exc.stdout or b"")[:1_900_000]+b"\nSMOKE_TIMEOUT_FAIL_CLOSED\n"
            code=124
        if code==0 and any(marker not in output for marker in t.required_markers):
            output+=b"\nREQUIRED_SUCCESS_MARKER_MISSING\n"
            code=90
        logs[t.name]=output
        (out/(t.name+".log")).write_bytes(output)
        prev=entries[-1]["entry_hash"] if entries else "0"*64
        entry=make_record(sequence=len(entries)+1,previous_hash=prev,name=t.name,
                          argv=argv,returncode=code,output_bytes=output,
                          elapsed_ms=int((time.monotonic()-start)*1000),
                          commit_sha=commit_sha)
        entries.append(entry)
        for gate in t.gates:
            observed[gate]={"status":entry["result"],"evidence_sha256":entry["log_sha256"]}
        if code!=0:success=False
    assert verify_chain(entries,logs)
    result={"schema":"i-ecosystem-build-evidence/v1","profile":profile,
            "result":"PASS_SOFTWARE_ONLY" if success else "FAIL",
            "source_commit":commit_sha,"task_count":len(entries),"entries":entries,
            "evidence_root_sha256":entries[-1]["entry_hash"] if entries else "0"*64,
            "inventory":inventory(root),"release":release_gate_report(observed),
            "untrusted_local_signature":None,
            "limitations":["Hashes are not immutable absent externally pinned root.",
                            "No device, printer, sensor, witness, clinical or legal authentication.",
                            "Software green never implies physical acceptance."]}
    safe_atomic_json(out/"acceptance.json",result)
    return result

def verify_disk(folder):
    out=Path(folder)
    obj=json.loads((out/"acceptance.json").read_text())
    entries=obj["entries"]
    logs={x["name"]:(out/(x["name"]+".log")).read_bytes() for x in entries}
    verify_chain(entries,logs)
    verify_policy_report(obj["release"])
    if obj["evidence_root_sha256"]!=(entries[-1]["entry_hash"] if entries else "0"*64):
        raise SmokeError("wrong evidence root")
    expected="PASS_SOFTWARE_ONLY" if all(x["result"]=="PASS_SOFTWARE_ONLY" for x in entries) else "FAIL"
    if obj["result"]!=expected:raise SmokeError("wrong final status")
    return {"verified_local_integrity":True,"tasks":len(entries),
            "result":obj["result"],"evidence_root_sha256":obj["evidence_root_sha256"],
            "trust_note":"not externally anchored or physical/clinical/legal evidence"}
