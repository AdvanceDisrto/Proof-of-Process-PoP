from pathlib import Path
import json,pytest
from ecosystem_release.catalog import COMPONENTS,inventory
from ecosystem_release.evidence import make_record,verify_chain,safe_atomic_json,EvidenceRejected,digest,canonical
from ecosystem_release.policy import (release_gate_report,verify_policy_report,SOFTWARE_GATES,EXTERNAL_GATES,PolicyViolation)
from ecosystem_release.runner import Task,task_plan,run,verify_disk,SmokeError
from ecosystem_release import runner
H="a"*64

def sample(previous="0"*64,seq=1,name="sample",raw=b"ok",rc=0):
    return make_record(sequence=seq,previous_hash=previous,name=name,
        argv=["python","test.py"],returncode=rc,output_bytes=raw,
        elapsed_ms=2,commit_sha="b"*40)

def test_catalog_unique():
    assert len(COMPONENTS)>=20
    assert len({x.ident for x in COMPONENTS})==len(COMPONENTS)

def test_catalog_relative():
    assert all(not Path(x.path).is_absolute() and ".." not in Path(x.path).parts for x in COMPONENTS)
    assert all(x.path and x.scope and x.remaining_gate for x in COMPONENTS)

def test_inventory_source_is_not_execution(tmp_path):
    f=tmp_path/COMPONENTS[0].path
    f.parent.mkdir(parents=True);f.write_text("hello")
    report=inventory(tmp_path)
    assert report["source_present"]==1
    assert report["components"][0]["acceptance"]=="SOURCE_PRESENT_UNTESTED"

def test_inventory_symlink_fail(tmp_path):
    target=tmp_path/"target";target.write_text("code")
    f=tmp_path/COMPONENTS[0].path;f.parent.mkdir(parents=True)
    f.symlink_to(target)
    assert inventory(tmp_path)["source_present"]==0

@pytest.mark.parametrize("value",[True,None,0,-1,1.0,"1",{},[]])
def test_invalid_sequence(value):
    with pytest.raises(EvidenceRejected):
        make_record(sequence=value,previous_hash="0"*64,name="sample",
            argv=["python"],returncode=0,output_bytes=b"hi",elapsed_ms=0)

@pytest.mark.parametrize("name",["", "x", "White Space", "../bad", "NOTLOWER", "a"*65])
def test_invalid_log_name(name):
    with pytest.raises(EvidenceRejected):
        make_record(sequence=1,previous_hash="0"*64,name=name,
            argv=["test"],returncode=0,output_bytes=b"hi",elapsed_ms=0)

def test_sha_known_answer():
    assert digest(b"abc")=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

def test_valid_two_entry_chain():
    a=sample(name="first",raw=b"a")
    b=sample(previous=a["entry_hash"],seq=2,name="second",raw=b"b")
    assert verify_chain([a,b],{"first":b"a","second":b"b"})

def test_missing_log():
    with pytest.raises(EvidenceRejected):verify_chain([sample()],{})

def test_changed_log():
    with pytest.raises(EvidenceRejected):verify_chain([sample()],{"sample":b"changed"})

def test_changed_entry():
    a=sample();a["returncode"]=43
    with pytest.raises(EvidenceRejected):verify_chain([a],{"sample":b"ok"})

def test_changed_link():
    a=sample(name="first",raw=b"a")
    b=sample(seq=2,name="second",raw=b"b")
    with pytest.raises(EvidenceRejected):
        verify_chain([a,b],{"first":b"a","second":b"b"})

def test_seq_replay():
    a=sample(name="first",raw=b"a")
    b=sample(previous=a["entry_hash"],seq=1,name="second",raw=b"b")
    with pytest.raises(EvidenceRejected):
        verify_chain([a,b],{"first":b"a","second":b"b"})

def test_forged_pass():
    r=sample(rc=42);r["result"]="PASS_SOFTWARE_ONLY"
    r["entry_hash"]=digest(canonical({k:v for k,v in r.items() if k!="entry_hash"}))
    with pytest.raises(EvidenceRejected,match="result"):
        verify_chain([r],{"sample":b"ok"})

def test_failed_command_stays_failed():
    assert sample(rc=31)["result"]=="FAIL"

def test_invalid_source_commit():
    with pytest.raises(EvidenceRejected):
        make_record(sequence=1,previous_hash="0"*64,name="sample",argv=["x"],
            returncode=0,output_bytes=b"",elapsed_ms=1,commit_sha="bad")

def test_log_bound():
    with pytest.raises(EvidenceRejected):
        make_record(sequence=1,previous_hash="0"*64,name="sample",argv=["x"],
            returncode=0,output_bytes=b"x"*5000001,elapsed_ms=1)

def test_safe_write(tmp_path):
    p=tmp_path/"dir"/"report.json"
    safe_atomic_json(p,{"pass":False})
    assert json.loads(p.read_text())["pass"] is False
    assert p.stat().st_mode & 0o077 == 0

def test_distinct_gates():
    assert len(EXTERNAL_GATES)>=20
    assert set(SOFTWARE_GATES).isdisjoint(EXTERNAL_GATES)

def test_policy_baseline():
    r=release_gate_report()
    assert verify_policy_report(r)
    assert not r["physical_acceptance"] and not r["production_ready"]

@pytest.mark.parametrize("gate",EXTERNAL_GATES)
def test_no_external_gates_from_software(gate):
    with pytest.raises(PolicyViolation):
        release_gate_report({gate:{"status":"PASS_SOFTWARE_ONLY","evidence_sha256":H}})

@pytest.mark.parametrize("bad",[
    {"status":"PASSED","evidence_sha256":H},
    {"status":"PASS_SOFTWARE_ONLY","evidence_sha256":"a"},
    {"status":"PASS_SOFTWARE_ONLY","evidence_sha256":"A"*64},
    {"status":"PASS_SOFTWARE_ONLY","evidence_sha256":None},
    {"status":"PASS_SOFTWARE_ONLY"},
    {"status":True,"evidence_sha256":H},
])
def test_invalid_software_gate(bad):
    with pytest.raises(PolicyViolation):
        release_gate_report({"PYTHON_UNIT_TESTS":bad})

def test_all_software_does_not_mean_production():
    r=release_gate_report({k:{"status":"PASS_SOFTWARE_ONLY","evidence_sha256":H} for k in SOFTWARE_GATES})
    assert r["software_only_release_candidate"]
    assert r["physical_acceptance"] is False
    assert r["production_ready"] is False
    assert verify_policy_report(r)

@pytest.mark.parametrize("flag",["physical_acceptance","production_ready","clinical_approval","legal_certification"])
def test_tamper_acceptance(flag):
    r=release_gate_report();r[flag]=True
    with pytest.raises(PolicyViolation):verify_policy_report(r)

def test_tamper_external_gate():
    r=release_gate_report()
    r["gates"]["FPGA_PROGRAMMED_OBSERVED"]["status"]="PASSED"
    with pytest.raises(PolicyViolation):verify_policy_report(r)

def test_tamper_candidate_summary():
    r=release_gate_report();r["software_only_release_candidate"]=True
    with pytest.raises(PolicyViolation):verify_policy_report(r)

def test_unknown_gate():
    with pytest.raises(PolicyViolation):
        release_gate_report({"NEW_GATE":{"status":"PASS_SOFTWARE_ONLY","evidence_sha256":H}})

@pytest.mark.parametrize("profile",["core","integration","rtl","all"])
def test_allowlisted_plan(profile):
    jobs=task_plan(profile)
    assert jobs and all(j.argv for j in jobs)

def test_reject_hardware_profile():
    with pytest.raises(SmokeError):task_plan("hardware")

def test_real_runner_and_tamper(tmp_path,monkeypatch):
    root=tmp_path/"checkout";root.mkdir()
    (root/"source.py").write_text("pass")
    job=Task("smoketest","core",("{python}","-c","print('TEST_OK')"),".",("source.py",),
             ("PYTHON_UNIT_TESTS",),required_markers=(b"TEST_OK",))
    monkeypatch.setattr(runner,"TASKS",(job,))
    out=root/"evidence"
    obj=run("core",root,out)
    assert obj["result"]=="PASS_SOFTWARE_ONLY"
    assert verify_disk(out)["verified_local_integrity"]
    (out/"smoketest.log").write_text("HACK")
    with pytest.raises(EvidenceRejected):verify_disk(out)

def test_no_silent_marker_success(tmp_path,monkeypatch):
    root=tmp_path/"checkout";root.mkdir()
    (root/"source.py").write_text("pass")
    job=Task("test_marker","core",("{python}","-c","print('wrong')"),".",
             ("source.py",),("PYTHON_UNIT_TESTS",),required_markers=(b"PASS",))
    monkeypatch.setattr(runner,"TASKS",(job,))
    assert run("core",root,root/"ev")["result"]=="FAIL"

def test_subprocess_failure_is_fail(tmp_path,monkeypatch):
    root=tmp_path/"checkout";root.mkdir()
    (root/"source.py").write_text("pass")
    job=Task("test_failure","core",("{python}","-c","import sys;sys.exit(7)"),".",
             ("source.py",),("PYTHON_UNIT_TESTS",))
    monkeypatch.setattr(runner,"TASKS",(job,))
    assert run("core",root,root/"ev")["result"]=="FAIL"

def test_missing_source_fail(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,"TASKS",(Task("missing","core",("{python}",),".",
                  ("not_found",),("PYTHON_UNIT_TESTS",)),))
    with pytest.raises(SmokeError):run("core",tmp_path,tmp_path/"ev")

def test_no_repo_overwrite(tmp_path):
    with pytest.raises(SmokeError):run("core",tmp_path,tmp_path)
