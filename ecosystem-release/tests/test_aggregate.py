import json,zipfile
import pytest
from ecosystem_release.aggregate import aggregate,AggregateRejected
from ecosystem_release.evidence import make_record
from ecosystem_release.policy import release_gate_report,EXTERNAL_GATES,SOFTWARE_GATES

COMMIT="a"*40
GROUPS={
  "core":["SOURCE_INVENTORY","PYTHON_UNIT_TESTS"],
  "integration":["WEBCRYPTO_TESTS","SYNTHETIC_IPQR_END_TO_END","HTTP_WEBSOCKET_SMOKE","ITELEPATHY_TYPED_INTENT"],
  "rtl":["TESSERA_RTL_SIM","ARTY_BOARD_PRE_FLIGHT","POPC_RTL_SIM","STRICT_HDL_LINT","GENERIC_HDL_SYNTH"]}

def make_zip(tmp_path,profile,*,commit=COMMIT,rc=0,tamper=False):
    raw=b"real task output"
    entry=make_record(sequence=1,previous_hash="0"*64,name="task",
          argv=["python","-m","pytest"],returncode=rc,output_bytes=raw,
          elapsed_ms=5,commit_sha=commit)
    observed={g:{"status":entry["result"],"evidence_sha256":entry["log_sha256"]} for g in GROUPS[profile]}
    payload={"schema":"i-ecosystem-build-evidence/v1","profile":profile,
             "source_commit":commit,"result":entry["result"],"entries":[entry],
             "evidence_root_sha256":entry["entry_hash"],"release":release_gate_report(observed)}
    p=tmp_path/(profile+".zip")
    prefix="evidence/core/" if profile=="core" else "ecosystem-release/evidence/"+profile+"/"
    with zipfile.ZipFile(p,"w") as z:
        z.writestr(prefix+"acceptance.json",json.dumps(payload))
        z.writestr(prefix+"task.log",b"forgery" if tamper else raw)
    return p

def test_full_11_software_gates_only(tmp_path):
    files=[make_zip(tmp_path,p) for p in GROUPS]
    r=aggregate(files,expected_source_commit=COMMIT)
    assert r["software_gates_verified"]==len(SOFTWARE_GATES)==11
    assert r["external_gates_pending"]==len(EXTERNAL_GATES)==21
    assert r["software_status"]=="ACCEPT_SOFTWARE_INTEGRATION_ONLY"
    assert r["physical_acceptance"] is False
    assert r["production_ready"] is False

def test_duplicate_profile_rejected(tmp_path):
    a=make_zip(tmp_path,"core");b=make_zip(tmp_path,"rtl")
    with pytest.raises(AggregateRejected):aggregate([a,a,b])

def test_mixed_commits_rejected(tmp_path):
    files=[make_zip(tmp_path,"core"),make_zip(tmp_path,"integration",commit="b"*40),make_zip(tmp_path,"rtl")]
    with pytest.raises(AggregateRejected,match="mixed"):aggregate(files)

def test_external_expected_commit_rejected(tmp_path):
    files=[make_zip(tmp_path,p) for p in GROUPS]
    with pytest.raises(AggregateRejected,match="pin"):aggregate(files,expected_source_commit="b"*40)

def test_tampered_rtl_log_rejected(tmp_path):
    files=[make_zip(tmp_path,p,tamper=(p=="rtl")) for p in GROUPS]
    with pytest.raises(ValueError):aggregate(files)

def test_failed_tests_not_accepted(tmp_path):
    files=[make_zip(tmp_path,p,rc=(4 if p=="integration" else 0)) for p in GROUPS]
    with pytest.raises(AggregateRejected,match="failed"):aggregate(files)

def test_missing_archive_not_promoted():
    with pytest.raises(AggregateRejected):aggregate([])
