import json
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient
from threshold.quorum import sha256, canonical, signing_bytes, verify_relay_receipt
from threshold.server import create_app

NOW=1793100000

def config():
    keys={f'juror-{c}':Ed25519PrivateKey.generate() for c in 'abc'}
    policy='sha256:'+'1'*64
    registry={'protocol':'ITM-JUROR-REGISTRY-v1','policy_sha256':policy,'jurors':{k:v.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex() for k,v in keys.items()}}
    pin=sha256(canonical(registry))
    relay=Ed25519PrivateKey.generate()
    token='PRIVATE_TEST_BEARER_TOKEN_AAAAAAA_123456'
    app=create_app(registry,pin,relay,token,now_fn=lambda:NOW)
    batch={'protocol':'ITM-JUROR-QUORUM-BATCH-v1','receipt_sha256':'sha256:'+'2'*64,'policy_sha256':policy,'request_nonce':'3'*32,'attestations':[]}
    for k in ('juror-a','juror-b'):
        a={'juror':k,'receipt_sha256':batch['receipt_sha256'],'policy_sha256':policy,'request_nonce':'3'*32,'decision':'APPROVE','issued_at':NOW-5,'expires_at':NOW+5}
        a['signature_hex']=keys[k].sign(signing_bytes(a)).hex();batch['attestations'].append(a)
    return app,batch,token,relay

def test_http_requires_bearer():
    app,batch,token,relay=config()
    with TestClient(app) as c:
        assert c.post('/v1/quorum',json=batch).status_code==401
        assert c.post('/v1/quorum',json=batch,headers={'Authorization':'Bearer wrong'}).status_code==401
        res=c.post('/v1/quorum',json=batch,headers={'Authorization':'Bearer '+token})
        assert res.status_code==200
        obj=res.json();assert obj['evaluation']['state']=='QUORUM_APPROVED'
        pub=relay.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()
        assert verify_relay_receipt(obj,pub)

def test_http_json_only_and_tamper_failure():
    app,batch,token,relay=config();h={'Authorization':'Bearer '+token}
    with TestClient(app) as c:
        assert c.post('/v1/quorum',content='text',headers=h).status_code==415
        batch['attestations'][0]['decision']='REJECT'
        assert c.post('/v1/quorum',json=batch,headers=h).status_code==422

def test_http_duplicate_fields_and_large_request():
    app,batch,token,relay=config();h={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
    with TestClient(app) as c:
        assert c.post('/v1/quorum',content=b'{"protocol":"X","protocol":"Y"}',headers=h).status_code==422
        assert c.post('/v1/quorum',content=b' '*17000,headers=h).status_code==413

def test_cannot_create_http_server_without_external_pin():
    app,batch,token,relay=config()
    with pytest.raises((RuntimeError,ValueError)):
        create_app({},'sha256:'+'0'*64,relay,token)

