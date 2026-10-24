import hashlib
from tools.inetty_verifier import build_receipt

PUB="00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"

def test_local_transport_route_passes_route_gate():
    h=hashlib.sha256(bytes.fromhex(PUB)).hexdigest()[:8]
    addr=f"200:{h[:4]}:{h[4:]}::1"
    r=build_receipt("did:iska:node:a",PUB,addr,"LoRa_868MHz",3,b"packet")
    assert r["verification"]["route_gate"]=="MEASURED_PASS"
    assert r["physical_gate"]=="ACTION_REQUIRED"

def test_central_transport_rejected():
    r=build_receipt("did:web:example",PUB,"192.168.1.5","AWS_DirectConnect",1,b"packet")
    assert r["verification"]["route_gate"]=="ACTION_REQUIRED"
    assert r["physical_gate"]=="ACTION_REQUIRED"

def test_merkle_receipt_is_hash_bound():
    r=build_receipt("did:iska:node:a",PUB,"200:abcd:1234::1","LoRa_868MHz",2,b"packet")
    assert r["receipt_sha256"].startswith("sha256:")
    assert len(r["receipt_sha256"])==71

def test_physical_gate_never_promoted():
    r=build_receipt("did:iska:node:a",PUB,"200:abcd:1234::1","LoRa_868MHz",2,b"packet")
    assert r["physical_gate"]=="ACTION_REQUIRED"
