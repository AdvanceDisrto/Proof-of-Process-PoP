from __future__ import annotations
import copy
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from unified_i.codec import ClaimRecord,canonical,sha256,ContractError
from unified_i.signing import sign,verify,SignatureRejected,public_hex

@pytest.fixture
def claim():
 return ClaimRecord(event_id="demo:001",subject="demo:bench-001",assertion_kind="INTEGER_LTE",verdict="PASS_BOUNDED_CLAIM",source_tier="SYNTHETIC",
                    evidence_sha256=sha256(b"synthetic"),issuer_key_id="operator-key-001",sequence=1,issued_at=1800000000,expires_at=1800000300,
                    limitations=("synthetic-only","not-hardware"),observed_micro_units=3000,maximum_micro_units=4000)
@pytest.fixture
def signer():return ed25519.Ed25519PrivateKey.generate()

def check(packet,key,now=1800000001,subject="demo:bench-001",min_seq=1):
 return verify(packet,pinned_public_key_hex=public_hex(key),pinned_key_id="operator-key-001",now=now,expected_subject=subject,minimum_sequence=min_seq)

def test_valid(claim,signer):
 r=check(sign(claim,signer),signer)
 assert r.verdict=="PASS_BOUNDED_CLAIM" and r.source_tier=="SYNTHETIC"

def test_encoding_is_deterministic():
 assert canonical({"b":2,"a":1})==b'{"a":1,"b":2}'
 assert sha256(b"a") == __import__("hashlib").sha256(b"a").hexdigest()

@pytest.mark.parametrize("field,value",[
 ("event_id","bad event"),("issuer_key_id","X"),("subject",""),
 ("assertion_kind","LLM_TRUE"),("verdict","PROVEN_TRUE"),
 ("source_tier","SILICON_PUF_PROVEN"),("evidence_sha256","abc"),
 ("sequence",True),("sequence",0),("sequence",-1),
 ("issued_at",2.7),("expires_at",1800000000),("expires_at",1800200000),
 ("limitations",()),("limitations",("bad\n",)),("observed_micro_units",True),
 ("maximum_micro_units",1e15),("observed_micro_units",5000),
 ])
def test_reject_bad_claim_fields(claim,field,value):
 d=claim.to_dict();d[field]=value
 with pytest.raises(ContractError): ClaimRecord(**{**d,"limitations":tuple(d["limitations"])})

@pytest.mark.parametrize("field,value",[
 ("schema","unknown/v1"),("algorithm","RSA_UNVERIFIED"),
 ("signer_scope","HARDWARE_PUF_PROVEN"),("signature","f"*128),
 ("signature","0"*128),("signature","x")])
def test_bad_packet_fields(claim,signer,field,value):
 p=sign(claim,signer);p[field]=value
 with pytest.raises(SignatureRejected):check(p,signer)

@pytest.mark.parametrize("field,value",[
 ("subject","demo:other"),("evidence_sha256","0"*64),
 ("maximum_micro_units",1234),("source_tier","HARDWARE_UNATTESTED"),
 ("issued_at",1800000100),("sequence",2),
 ("limitations",["other"])])
def test_tamper_signed_body(claim,signer,field,value):
 p=sign(claim,signer);p["body"][field]=value
 with pytest.raises(SignatureRejected):check(p,signer)

def test_unpinned_wrong_key(claim,signer):
 with pytest.raises(SignatureRejected):check(sign(claim,signer),ed25519.Ed25519PrivateKey.generate())

def test_expired_and_not_yet_valid(claim,signer):
 p=sign(claim,signer)
 for now in [1799999999,1800000301]:
  with pytest.raises(SignatureRejected):check(p,signer,now=now)

def test_wrong_subject(claim,signer):
 with pytest.raises(SignatureRejected):check(sign(claim,signer),signer,subject="demo:other")

def test_replay_floor(claim,signer):
 with pytest.raises(SignatureRejected):check(sign(claim,signer),signer,min_seq=2)

def test_unassessed_must_unresolved(claim):
 d=claim.to_dict();d.update(assertion_kind="DECLARED_UNASSESSED",observed_micro_units=None,maximum_micro_units=None,verdict="PASS_BOUNDED_CLAIM")
 with pytest.raises(ContractError):ClaimRecord(**{**d,"limitations":tuple(d['limitations'])})

def test_nan_fails():
 with pytest.raises(ValueError):canonical({"bad":float("nan")})
