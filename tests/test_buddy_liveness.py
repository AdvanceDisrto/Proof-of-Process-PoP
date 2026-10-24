import json
from cryptography.hazmat.primitives.asymmetric import ed25519
from tools.buddy_liveness_proof import make_beacon,verify_beacon,make_ack,verify_ack,merkle_root,verify_receipt,classify_tier,run_self_test

def test_beacon_roundtrip():
    k=ed25519.Ed25519PrivateKey.generate(); assert verify_beacon(make_beacon(k,"hello world","test-model"))

def test_beacon_tamper_fails():
    k=ed25519.Ed25519PrivateKey.generate(); b=make_beacon(k,"hello","test-model"); b["body"]["resp"]="sha256:"+"0"*64; assert not verify_beacon(b)

def test_ack_binds_to_beacon():
    kb,kw=ed25519.Ed25519PrivateKey.generate(),ed25519.Ed25519PrivateKey.generate()
    b1,b2=make_beacon(kb,"hi","m"),make_beacon(kb,"different","m")
    a=make_ack(kw,b1); assert verify_ack(a); assert a["body"]["observed"]!=make_ack(kw,b2)["body"]["observed"]

def test_merkle_root_deterministic():
    assert merkle_root([{"x":1},{"y":2}])==merkle_root([{"x":1},{"y":2}])

def test_tier_classification():
    ips={"127.0.0.1","192.168.1.41"}
    assert classify_tier("127.0.0.1","127.0.0.1",ips)=="T0.5"
    assert classify_tier("192.168.1.41","192.168.1.42",ips)=="T1"

def test_receipt_verifies_and_gate_is_locked():
    kb,kw=ed25519.Ed25519PrivateKey.generate(),ed25519.Ed25519PrivateKey.generate(); b=make_beacon(kb,"hi","m"); a=make_ack(kw,b)
    r={"beacon":b,"witness_ack":a,"merkle_root":merkle_root([b,a]),"physical_gate":"ACTION_REQUIRED"}
    assert verify_receipt(r)["ok"] and r["physical_gate"]=="ACTION_REQUIRED"

def test_self_test_passes(tmp_path):
    assert run_self_test(str(tmp_path/"buddy.json"))==0
    assert json.loads((tmp_path/"buddy.json").read_text())["state"]=="VERIFIED_PROCESS"
