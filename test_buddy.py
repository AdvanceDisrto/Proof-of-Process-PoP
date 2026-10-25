"""Buddy tests: identity, discovery disclosure, adaptation, provenance, tamper, handoff."""
from cryptography.hazmat.primitives.asymmetric import ed25519
from buddy import Buddy, verify_chain, verify_receipt

PHONE={"arch":"aarch64","cores":8,"memory_available_mb":1800,"python":"3.11","features":[],"has_wifi":True,"has_ethernet":False,"in_container":False,"simulated_class":"phone"}
SERVER={"arch":"x86_64","cores":32,"memory_available_mb":96000,"python":"3.12","features":["avx512f","avx2"],"has_wifi":False,"has_ethernet":True,"in_container":False,"simulated_class":"server"}
TASK={"seed":"t1","size":128,"data_size":16,"min_precision":"int8"}
SEED="test-seed"

def test_same_seed_same_identity():
    assert Buddy(SEED).id == Buddy(SEED).id

def test_different_seed_different_identity():
    assert Buddy(SEED).id != Buddy("other-seed").id

def test_device_override_is_disclosed():
    assert Buddy(SEED).arrive(PHONE)["runtime"]["simulated"] is True

def test_phone_quantizes_server_does_not():
    b=Buddy(SEED); assert b.arrive(PHONE)["precision"]=="int8"; assert b.arrive(SERVER)["precision"]=="fp64"

def test_output_differs_by_precision():
    b=Buddy(SEED); p=b.arrive(PHONE); s=b.arrive(SERVER)
    assert b.execute_on(p,TASK)["execution"]["output_hash"] != b.execute_on(s,TASK)["execution"]["output_hash"]

def test_chain_verifies_across_devices():
    b=Buddy(SEED)
    for x in (PHONE,SERVER): b.execute_on(b.arrive(x),TASK)
    v=verify_chain(b.state["receipts"]); assert v["ok"],v["errors"]
    assert len({r["buddy_id"] for r in b.state["receipts"]})==1

def test_tampered_receipt_fails():
    b=Buddy(SEED); r=b.execute_on(b.arrive(PHONE),TASK); r["execution"]["output"]["result"]=99999
    assert not verify_receipt(r)["ok"]

def test_handoff_preserves_state():
    b=Buddy(SEED); b.execute_on(b.arrive(PHONE),TASK); h=b.handoff(); b2=Buddy.from_handoff(h,SEED)
    assert b2.id==b.id and b2.state["seq"]==1 and len(b2.state["receipts"])==1

def test_handoff_rejects_wrong_seed():
    b=Buddy(SEED); b.execute_on(b.arrive(PHONE),TASK); h=b.handoff()
    try: Buddy.from_handoff(h,"wrong-seed"); assert False
    except ValueError: pass
