import json
import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from innovulis.api import Settings, make_app
from innovulis.simulate import simulate
from alil.router import canonical, SOURCE_DOMAIN, pub_hex, sha256, load_json, MACHINE_DOMAIN

TOKEN = "integration-demo-token-not-production-123456"

@pytest.fixture
def seeded(tmp_path):
    result = simulate(tmp_path / "demo")
    settings = Settings(tmp_path / "demo" / "runtime", result["machine_public_key_ed25519"], TOKEN)
    return TestClient(make_app(settings)), result, settings

def auth(): return {"Authorization": "Bearer " + TOKEN}

def test_unconfigured_endpoint_fails_closed():
    from innovulis.api import app
    assert TestClient(app).get('/v1/health').status_code == 503

def test_health_never_claims_real_world_proof(seeded):
    client,_,_=seeded
    data=client.get('/v1/health').json()
    assert data['status']=='API_PROCESS_RUNNING'
    assert data['hardware_attested'] is False
    assert data['receipts_verified'] is False
    assert data['settlement_enabled'] is False

def test_chain_requires_authorization(seeded):
    client,_,_=seeded
    assert client.get('/v1/chain/status').status_code == 401
    assert client.get('/v1/chain/status',headers={'Authorization':'Bearer wrong'}).status_code==401

def test_chain_externally_pinned_key_verifies(seeded):
    client,_,_=seeded
    result=client.get('/v1/chain/status',headers=auth())
    assert result.status_code==200
    assert result.json()['receipt_count']==1
    assert result.json()['underlying_events_verified'] is False
    assert result.headers['cache-control']=='no-store'

def test_get_receipt_has_verified_root(seeded):
    client,_,_=seeded
    result=client.get('/v1/receipts/1',headers=auth())
    assert result.status_code==200
    assert result.json()['event']['underlying_real_world_event_verified'] is False
    assert len(result.headers['x-verified-local-root'])==64

def test_receipt_cannot_claim_physical_event(seeded):
    client,_,_=seeded
    receipt=client.get('/v1/receipts/1',headers=auth()).json()
    verified=client.post('/v1/receipts/verify',json={'receipt':receipt},headers=auth())
    assert verified.status_code==200
    assert verified.json()['financial_or_physical_actions_authorized'] is False
    assert verified.json()['external_anchor_verified'] is False

def test_tampered_submission_is_rejected(seeded):
    client,_,_=seeded
    receipt=client.get('/v1/receipts/1',headers=auth()).json()
    receipt['event']['physical_actuation_authorized']=True
    response=client.post('/v1/receipts/verify',json={'receipt':receipt},headers=auth())
    assert response.status_code==409

def test_tampered_store_halts_verification(seeded):
    client,_,settings=seeded
    f=settings.root/'records'/'000000000001.json'
    receipt=load_json(f.read_bytes())
    receipt['event']['settlement_authorized']=True
    f.write_bytes(canonical(receipt))
    assert client.get('/v1/chain/status',headers=auth()).status_code==409
    assert client.get('/v1/receipts/1',headers=auth()).status_code==409

def test_no_records_does_not_claim_verified(tmp_path):
    machine=Ed25519PrivateKey.generate()
    app=make_app(Settings(tmp_path/'empty',pub_hex(machine),TOKEN))
    assert TestClient(app).get('/v1/chain/status',headers=auth()).status_code==409

def test_ingress_disabled_by_default(seeded):
    client,_,_=seeded
    assert client.post('/v1/intake',content=b'{}',headers={**auth(),'Content-Type':'application/json'}).status_code==403

def test_ingress_accepts_only_queue_when_opted_in(seeded):
    _,_,settings=seeded
    client=TestClient(make_app(Settings(settings.root,settings.machine_public_key_hex,TOKEN,True)))
    response=client.post('/v1/intake',content=b'{"note":"pending"}',headers={**auth(),'Content-Type':'application/json'})
    assert response.status_code==202
    assert response.json()['status']=='QUEUED_UNVERIFIED'
    assert response.json()['machine_signed'] is False
    inbox=list((settings.root/'inbox').glob('api-*.json'))
    assert len(inbox)==1 and b'pending' in inbox[0].read_bytes()

def test_ingress_rejects_duplicate_json_keys(seeded):
    _,_,settings=seeded
    client=TestClient(make_app(Settings(settings.root,settings.machine_public_key_hex,TOKEN,True)))
    response=client.post('/v1/intake',content=b'{"receipt":1,"receipt":2}',headers={**auth(),'Content-Type':'application/json'})
    assert response.status_code==422

def test_ingress_rejects_excessive_body(seeded):
    _,_,settings=seeded
    client=TestClient(make_app(Settings(settings.root,settings.machine_public_key_hex,TOKEN,True)))
    response=client.post('/v1/intake',content=b'{' + b' '*1000002 + b'}',headers={**auth(),'Content-Type':'application/json'})
    assert response.status_code==413

def test_incorrect_content_type(seeded):
    _,_,settings=seeded
    client=TestClient(make_app(Settings(settings.root,settings.machine_public_key_hex,TOKEN,True)))
    response=client.post('/v1/intake',content=b'{}',headers={**auth(),'Content-Type':'text/plain'})
    assert response.status_code==415

def test_no_out_of_band_pin_fails_fast(tmp_path):
    with pytest.raises(ValueError,match='public key'):
        make_app(Settings(tmp_path,'not-a-key',TOKEN))
    with pytest.raises(ValueError,match='Token'):
        Settings(tmp_path,'a'*64,'short')

def test_demo_cannot_overwrite(tmp_path):
    simulate(tmp_path/'demo')
    with pytest.raises(FileExistsError): simulate(tmp_path/'demo')


def test_causal_confounder_pattern_is_not_certainty(seeded):
    client,_,_=seeded
    r=client.post('/v1/causal/inspect',json={'edges':[['z','x'],['z','y'],['x','y']], 'x':'x','y':'y','z':'z'},headers=auth())
    assert r.status_code==200
    assert r.json()['patterns']['confounder_shape'] is True
    assert r.json()['hidden_confounding_ruled_out'] is False


def test_collider_does_not_imply_safe_adjustment(seeded):
    client,_,_=seeded
    r=client.post('/v1/causal/inspect',json={'edges':[['x','z'],['y','z']], 'x':'x','y':'y','z':'z'},headers=auth())
    assert r.status_code==200
    assert r.json()['patterns']['collider_shape'] is True
    assert r.json()['causal_effect_identified'] is False


def test_mediator_candidate_shape(seeded):
    client,_,_=seeded
    r=client.post('/v1/causal/inspect',json={'edges':[['x','z'],['z','y']], 'x':'x','y':'y','z':'z'},headers=auth())
    assert r.status_code==200
    assert r.json()['patterns']['mediator_shape'] is True


def test_candidate_instrument_not_proven(seeded):
    client,_,_=seeded
    r=client.post('/v1/causal/inspect',json={'edges':[['z','x'],['x','y']], 'x':'x','y':'y','z':'z'},headers=auth())
    assert r.status_code==200
    assert r.json()['patterns']['instrument_candidate_shape'] is True
    assert r.json()['instrument_assumptions_proven'] is False


def test_cycles_are_rejected(seeded):
    client,_,_=seeded
    r=client.post('/v1/causal/inspect',json={'edges':[['x','y'],['y','x']], 'x':'x','y':'y','z':'z'},headers=auth())
    assert r.status_code==422


def test_causal_endpoint_requires_auth(seeded):
    client,_,_=seeded
    assert client.post('/v1/causal/inspect',json={'edges':[],'x':'x','y':'y','z':'z'}).status_code==401
