"""No PHI, no live clinic. Real cryptographic and optical tests under demo keys."""
import copy, json, time
import pytest
from pathlib import Path
from PIL import Image, ImageOps
from fastapi.testclient import TestClient

from human_hub import HumanHub, HubRejected
from human_hub.web import create_app
from innovulis_receipt.codec import canonical, decode_qr_text
from innovulis_receipt.carrier import read_qr_image
from innovulis_receipt.engine import verify

@pytest.fixture
def hub(tmp_path):
    h=HumanHub(tmp_path/"hub.sqlite3")
    yield h
    h.close()

def demo(hub,obs=45000,limit=50000):
    return hub.create_synthetic_receipt(observed=obs,limit=limit,
                                        explicit_demo_consent=True)

def test_consent_required(hub):
    with pytest.raises(HubRejected):hub.create_synthetic_receipt()

@pytest.mark.parametrize("v",[True,False,None,45000.0,"45000"])
def test_strict_integer(hub,v):
    with pytest.raises(HubRejected):demo(hub,obs=v)

def test_true_under_synthetic_anchor(hub):
    r=demo(hub)
    assert r["issuer_claim"]=="PROVEN_TRUE"
    assert r["digital_receipt_authentic_under_synthetic_anchor"]
    assert not r["independent_real_world_verification"]

def test_refuted_under_synthetic_anchor(hub):
    r=demo(hub,60000)
    assert r["issuer_claim"]=="REFUTED_FALSE"
    assert hub.get_event(r["event_id"]).verification=="VERIFIED_DIGITAL_RECEIPT"

def test_unknown_event(hub):
    with pytest.raises(HubRejected):hub.get_event("missing")

def test_equal_limit_is_true(hub):
    assert demo(hub,50000)["issuer_claim"]=="PROVEN_TRUE"

def test_bad_timestamp_fails(hub):
    with pytest.raises(HubRejected):
        hub.create_synthetic_receipt(explicit_demo_consent=True,now=True)

def test_replay_fresh_nonce(hub):
    a=demo(hub);b=demo(hub)
    assert a["receipt_sha256"]!=b["receipt_sha256"]
    assert hub.store.integrity()["checked"]==2

def test_public_feed_redacts_signed_carrier(hub):
    demo(hub)
    feed=hub.read_feed()
    assert len(feed["events"])==1
    assert "ipqr1:" not in json.dumps(feed)
    assert feed["scope"]["patient_data"]=="NOT_ACCEPTED"

def test_signed_receipt_tamper_is_detected(tmp_path):
    d=HumanHub._fixture(45000,50000,int(time.time()))
    (tmp_path/"synthetic_bench_trace.txt").write_bytes(d["evidence"])
    kw=dict(expected_anchor_sha256=d["trust_sha256"],
            expected_subject=d["packet"]["receipt"]["subject"],
            evidence_dir=tmp_path)
    ok=verify(d["packet"],d["trust"],d["revocations"],d["issuance_log"],**kw)
    assert ok.verified
    tampered=copy.deepcopy(d["packet"])
    tampered["receipt"]["claim"]["observed"]=0
    assert not verify(tampered,d["trust"],d["revocations"],d["issuance_log"],**kw).verified

def test_missing_evidence_is_not_verified(tmp_path):
    d=HumanHub._fixture(45000,50000,int(time.time()))
    result=verify(d["packet"],d["trust"],d["revocations"],d["issuance_log"],
                  expected_anchor_sha256=d["trust_sha256"],
                  expected_subject=d["packet"]["receipt"]["subject"],evidence_dir=tmp_path)
    assert not result.verified

def test_mismatched_anchor_is_not_verified(tmp_path):
    d=HumanHub._fixture(45000,50000,int(time.time()))
    (tmp_path/"synthetic_bench_trace.txt").write_bytes(d["evidence"])
    result=verify(d["packet"],d["trust"],d["revocations"],d["issuance_log"],
                  expected_anchor_sha256="0"*64,
                  expected_subject=d["packet"]["receipt"]["subject"],evidence_dir=tmp_path)
    assert not result.verified

def test_wrong_subject_is_not_verified(tmp_path):
    d=HumanHub._fixture(45000,50000,int(time.time()))
    (tmp_path/"synthetic_bench_trace.txt").write_bytes(d["evidence"])
    result=verify(d["packet"],d["trust"],d["revocations"],d["issuance_log"],
                  expected_anchor_sha256=d["trust_sha256"],
                  expected_subject="demo:wrong",evidence_dir=tmp_path)
    assert not result.verified

def test_real_optical_qr_roundtrip(hub,tmp_path):
    r=demo(hub)
    image=tmp_path/"qr.png";image.write_bytes(hub.render_qr_png(r["event_id"]))
    scanned=read_qr_image(image)
    assert scanned["receipt"]["subject"]=="demo:equipment-bench-001"
    assert scanned["receipt"]["verdict"]=="PROVEN_TRUE"

def test_escpos_preview_explicitly_unprinted(hub):
    r=demo(hub)
    raw=hub.print_preview_bytes(r["event_id"])
    assert raw.startswith(b"\x1b@")
    assert b"SYNTHETIC DEMO ONLY" in raw
    assert b"NO PATIENT DATA" in raw
    assert b"\x1d\x76\x30\x00" in raw

def test_screen_and_escpos_same_receipt_pixels(hub,tmp_path):
    r=demo(hub)
    event=hub.get_event(r["event_id"])
    raw=hub.print_preview_bytes(r["event_id"])
    i=raw.index(b"\x1d\x76\x30\x00")
    w=raw[i+4]+256*raw[i+5]
    h=raw[i+6]+256*raw[i+7]
    bitmap=raw[i+8:i+8+w*h]
    assert len(bitmap)==w*h
    image=ImageOps.invert(Image.frombytes("1",(w*8,h),bitmap).convert("L"))
    p=tmp_path/"printed.png";image.save(p)
    scanned=read_qr_image(p)
    assert canonical(scanned)==canonical(decode_qr_text(event.carrier))

def test_review_must_be_opt_in(hub):
    r=demo(hub)
    with pytest.raises(HubRejected):hub.acknowledge_review(r["event_id"])

def test_ack_is_not_medical_approval(hub):
    r=demo(hub)
    ack=hub.acknowledge_review(r["event_id"],confirm_scope=True)
    assert not ack["is_professional_medical_approval"]
    assert hub.store.integrity()["checked"]==2

@pytest.fixture
def api(tmp_path):
    token="operator"+("x"*40)
    with TestClient(create_app(database=tmp_path/"web.sqlite3",operator_token=token)) as c:
        yield c,token

def test_health_discloses_nonclinical_scope(api):
    c,_=api
    r=c.get("/health")
    assert r.json()["clinical_ready"] is False
    assert r.json()["physical_acceptance"] is False

def test_all_receipt_routes_require_operator_token(api):
    c,t=api
    assert c.get("/api/feeds").status_code==403
    assert c.get("/api/qr/abc").status_code==403
    assert c.get("/api/print-preview/abc").status_code==403
    assert c.post("/api/demo",json={"explicit_demo_consent":True}).status_code==403

def test_api_rejects_patient_data_field(api):
    c,t=api
    r=c.post("/api/demo",headers={"X-I-Hub-Token":t},
             json={"explicit_demo_consent":True,"patient_name":"never record"})
    assert r.status_code==422

def test_api_demonstrates_refuted_without_clinical_claim(api):
    c,t=api
    h={"X-I-Hub-Token":t}
    r=c.post("/api/demo",headers=h,json={"explicit_demo_consent":True,"observed":70000,"limit":50000})
    assert r.status_code==200,r.text
    body=r.json()
    assert body["issuer_claim"]=="REFUTED_FALSE"
    assert body["scope"]["clinical_decision"]=="NOT_IMPLEMENTED"
    assert c.get("/api/qr/"+body["event_id"],headers=h).content.startswith(b"\x89PNG")
    assert c.get("/api/print-preview/"+body["event_id"],headers=h).headers["x-actual-printer-used"]=="false"
    feed=c.get("/api/feeds",headers=h).json()
    assert feed["journal"]["chain_ok"] and "ipqr1:" not in json.dumps(feed)

def test_api_review_is_ack_only(api):
    c,t=api
    h={"X-I-Hub-Token":t}
    r=c.post("/api/demo",headers=h,json={"explicit_demo_consent":True})
    eid=r.json()["event_id"]
    assert c.post("/api/review/"+eid,headers=h,json={"confirm_scope":False}).status_code==422
    ack=c.post("/api/review/"+eid,headers=h,json={"confirm_scope":True})
    assert ack.status_code==200
    assert not ack.json()["is_professional_medical_approval"]

def test_no_clinical_action_endpoint(api):
    c,t=api
    for ep in ("/api/diagnose","/api/patient","/api/prescribe"):
        assert c.post(ep,headers={"X-I-Hub-Token":t}).status_code==404

def test_index_has_no_remote_dependencies(api):
    c,_=api
    r=c.get("/")
    assert r.status_code==200
    assert "NON-CLINICAL" in r.text
    assert "https://" not in r.text
    assert "Content-Security-Policy" in r.headers
