from tools.ambient_harvester_verifier import *
def base(**k): d={"barometric_m2":.01,"teg_cm2":1.,"radiative_cm2":0.,"piezo_cm2":0.};d.update(k);return d
def test_beverly(): assert classify(base(),1e-6,0)["verdict"]=="BEVERLY_CLASS_RUNNING"
def test_motor(): assert classify(base(barometric_m2=1,teg_cm2=1000,radiative_cm2=1000,piezo_cm2=1000),100000,0)["verdict"]=="CANNOT_SELF_RUN"
def test_gate(): assert emit_receipt("/tmp/a.json",base(),1e-6,0)["physical_gate"]=="ACTION_REQUIRED"
def test_superconductor_blocked(): assert next(p for p in emit_receipt("/tmp/b.json",base(),1e-6,0)["pillars"] if "SUPERCONDUCTOR" in p["id"])["gate"]=="ACTION_REQUIRED"
