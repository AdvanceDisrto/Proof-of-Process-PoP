import copy
import hashlib
import json
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from innovulis.ci.receipt_core import sign_receipt,verify,sha,pubraw

@pytest.fixture()
def kit():
    key=ed25519.Ed25519PrivateKey.generate()
    b=b"Full banner\\nPHYSICAL_GATE=ACTION_REQUIRED\\n"
    r=sign_receipt(key,sha(b),sha(b"summary"),"iNNOVULIS/self-claim","0.4.1")
    return key,b,r

def test_valid_pinned_receipt(kit):
    key,b,r=kit
    assert verify(r,pubraw(key))["ok"]

def test_external_banner_tamper_independent(kit):
    key,b,r=kit
    v=verify(r,pubraw(key),banner=b.replace(b"ACTION_REQUIRED",b"GREEN"))
    assert not v["ok"] and v["integrity_ok"] and v["signature_ok"] and v["urn_ok"]
    assert v["errors"]==["banner_hash_mismatch"]

def test_urn_only_tamper_independent(kit):
    key,b,r=kit
    r["receipt_urn"]="urn:iverify:"+"f"*64
    v=verify(r,pubraw(key))
    assert not v["ok"] and v["integrity_ok"] and v["signature_ok"]
    assert v["errors"]==["receipt_urn does not match body hash"]

def test_signature_only_mutation(kit):
    key,b,r=kit
    r["signature"]="00"*64
    v=verify(r,pubraw(key))
    assert not v["ok"] and v["integrity_ok"] and v["urn_ok"] and not v["signature_ok"]

def test_wrong_trusted_pin(kit):
    key,b,r=kit
    other=pubraw(ed25519.Ed25519PrivateKey.generate())
    assert not verify(r,other)["ok"]

def test_t2_structure_not_source_auth(kit):
    key,b,r=kit
    r2=sign_receipt(key,sha(b),sha(b"summary"),"iNNOVULIS/self-claim","0.4.1",
        evidence=[{"source_id":"placeholder","payload_hash":"sha256:"+"f"*64}])
    v=verify(r2,pubraw(key))
    assert v["ok"] and r2["body"]["tier"]=="T2"
    assert "does not verify evidence source signatures" in r2["body"]["does_not_prove"]

def test_t2_downgrade_is_signed(kit):
    key,b,r=kit
    r2=sign_receipt(key,sha(b),sha(b"summary"),"iNNOVULIS/self-claim","0.4.1",
        evidence=[{"source_id":"placeholder","payload_hash":"sha256:"+"f"*64}])
    r2["body"]["tier"]="T1"
    v=verify(r2,pubraw(key))
    assert not v["ok"] and not v["integrity_ok"] and not v["signature_ok"]

# Twenty-two mutated-body examples are individual independently executed pytest cases.
@pytest.mark.parametrize("field,new_value",[
    ("prompt_hash","sha256:"+"a"*64),
    ("output_hash","sha256:"+"b"*64),
    ("model_id","untrusted"),
    ("model_version","0.0.0"),
    ("timestamp_utc","1970-01-01T00:00:00Z"),
    ("nonce","spoofed"),
    ("spec","forged/spec"),
    ("tier","T2"),
    ("does_not_prove",[]),
    ("prompt_hash",None),
    ("output_hash",None),
    ("model_id",None),
    ("model_version",None),
    ("timestamp_utc",None),
    ("nonce",None),
    ("spec",None),
    ("tier",None),
    ("does_not_prove",None),
    ("prompt_hash",""),
    ("output_hash",""),
    ("model_id",""),
    ("model_version",""),
])
def test_mutated_signed_field_fails(kit,field,new_value):
    key,b,r=kit
    r["body"][field]=new_value
    v=verify(r,pubraw(key))
    assert not v["ok"]
    assert not v["integrity_ok"]
    assert not v["signature_ok"]
