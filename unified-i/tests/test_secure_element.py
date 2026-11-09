from __future__ import annotations
import pytest
from cryptography.hazmat.primitives.asymmetric import ec,utils
from cryptography.hazmat.primitives import hashes,serialization
from unified_i.secure_element import challenge,sign_through_callback,verify_p256_signature,HardwareSignerUnavailable

@pytest.fixture
def kp():
 key=ec.generate_private_key(ec.SECP256R1())
 pem=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
 return key,pem

@pytest.fixture
def params(kp):
 k,pem=kp
 return {"callback":lambda slot,digest:k.sign(digest,ec.ECDSA(utils.Prehashed(hashes.SHA256()))),
         "pinned_public_pem":pem,"device_slot":0,"receipt_digest_hex":"1"*64,
         "nonce_hex":"2"*32,"issued_at":1800000000,"expires_at":1800000030,"now":1800000010}

def test_p256_signature_valid_but_unattested(params):
 r=sign_through_callback(**params)
 assert r["cryptographic_signature_valid"] is True
 assert r["hardware_provenance_verified"] is False
 assert r["tpm_or_puf_claim"] is False

@pytest.mark.parametrize("field,value",[
 ("device_slot",-1),("device_slot",16),("device_slot",True),
 ("nonce_hex","bad"),("receipt_digest_hex","bad"),
 ("issued_at",1.1),("expires_at",1800000200),("now",1800000400),
 ("callback",None),("callback",lambda slot,dig:b'bad'),
 ])
def test_bad_params_fail_closed(params,field,value):
 params[field]=value
 with pytest.raises(HardwareSignerUnavailable):sign_through_callback(**params)

def test_wrong_public_key_rejected(params,kp):
 other=ec.generate_private_key(ec.SECP256R1())
 params["pinned_public_pem"]=other.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
 with pytest.raises(HardwareSignerUnavailable):sign_through_callback(**params)

def test_p256_signature_binding(kp):
 key,pem=kp
 d=challenge(receipt_digest_hex='1'*64,nonce_hex='2'*32,issued_at=1800000000,expires_at=1800000030)
 sig=key.sign(d,ec.ECDSA(utils.Prehashed(hashes.SHA256())))
 assert verify_p256_signature(digest=d,signature=sig,pinned_public_pem=pem)
 assert not verify_p256_signature(digest=b'\x00'*32,signature=sig,pinned_public_pem=pem)

def test_p256_raw64_signature(kp):
 key,pem=kp
 d=b'\x03'*32
 der=key.sign(d,ec.ECDSA(utils.Prehashed(hashes.SHA256())))
 r,s=utils.decode_dss_signature(der)
 raw=r.to_bytes(32,'big')+s.to_bytes(32,'big')
 assert verify_p256_signature(digest=d,signature=raw,pinned_public_pem=pem)

def test_expired_time_fails_closed(params):
 params["expires_at"]=params["issued_at"]
 with pytest.raises(HardwareSignerUnavailable):sign_through_callback(**params)
