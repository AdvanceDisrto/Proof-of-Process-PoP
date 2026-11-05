import copy
from datetime import datetime,timezone
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from ors.service import app
from ors.trust import issue,verify,digest,meter_utility,mint_energy,match_energy,guardian_evaluate,decision_authorized

@pytest.fixture
def keys():return Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate()

def test_u_r_verified(keys):
    a,_,_=keys
    r=meter_utility(a,'consumer','ENERGY','4.5','kWh',digest({'trace':'demo'}),'event-1')
    assert verify(r,r['signature']['public_key_hex'])['ok']
    assert r['payload']['trust_basis'].startswith('software_reported')

def test_u_r_wrong_pin(keys):
    a,b,_=keys
    r=meter_utility(a,'c','GPU_SECONDS',2,'s',digest({'trace':3}),'e')
    assert not verify(r, __import__('ors.trust',fromlist=['public_hex']).public_hex(b))['ok']

def test_tamper_all_signed_fields(keys):
    a,_,_=keys
    r=meter_utility(a,'c','GPU_SECONDS',2,'s',digest({'trace':3}),'e')
    for change in (lambda q:q['payload']['resource'].update(quantity='999'),lambda q:q.update(payload_hash='sha256:'+'0'*64),lambda q:q['signature'].update(value='00'*64)):
        x=copy.deepcopy(r);change(x);assert not verify(x,r['signature']['public_key_hex'])['ok']

def test_invalid_quantities(keys):
    a,_,_=keys
    for q in (0,-1,float('nan'),float('inf'),'NaN',True):
        with pytest.raises(ValueError):meter_utility(a,'c','ENERGY',q,'kWh',digest({'x':1}),'id')

def test_invalid_evidence(keys):
    with pytest.raises(ValueError):meter_utility(keys[0],'c','ENERGY',1,'kWh','bad','id')

def test_energy_window(keys):
    a,_,_=keys
    r=mint_energy(a,'m','SOLAR',5,'2026-11-05T12:00:00Z','2026-11-05T13:00:00Z','ev')
    assert verify(r,r['signature']['public_key_hex'])['ok']
    with pytest.raises(ValueError):mint_energy(a,'m','SOLAR',5,'2026-11-05T13:00:00Z','2026-11-05T12:00:00Z','ev')

def _valid_pair(keys):
    gen,cons,_=keys
    e=mint_energy(gen,'meter','SOLAR',10,'2026-11-05T12:00:00Z','2026-11-05T13:00:00Z','e1')
    u=meter_utility(cons,'consumer','ENERGY',5,'kWh',digest({'device':'load'}),'c1')
    # Issue properly signed test observation with deliberately controlled time in the window
    body={**u['payload'],'issued_at_utc_untrusted':'2026-11-05T12:30:00+00:00'}
    u=issue('ipqr/utility-receipt/v1',body,cons)
    return e,u

def test_accounting_match_signed(keys):
    a,b,c=keys;e,u=_valid_pair(keys); ledger=set()
    r=match_energy(c,e,u,e['signature']['public_key_hex'],u['signature']['public_key_hex'],ledger)
    assert verify(r,r['signature']['public_key_hex'])['ok']
    assert r['payload']['offset_kg_co2']=='NOT_ASSERTED'
    assert r['payload']['claim_type']=='SIMULATED_TIME_WINDOW_MATCH_NOT_CARBON_CREDIT'
    with pytest.raises(ValueError,match='duplicate'):match_energy(c,e,u,e['signature']['public_key_hex'],u['signature']['public_key_hex'],ledger)

def test_accounting_rejects_more_than_generated(keys):
    e,u=_valid_pair(keys); c=keys[1]
    body=copy.deepcopy(u['payload']);body['resource']['quantity']='11'
    u2=issue('ipqr/utility-receipt/v1',body,c)
    with pytest.raises(ValueError,match='exceeds'):match_energy(keys[2],e,u2,e['signature']['public_key_hex'],u2['signature']['public_key_hex'])

def test_accounting_rejects_bad_signature(keys):
    e,u=_valid_pair(keys);u['payload']['resource']['quantity']='7'
    with pytest.raises(ValueError,match='signature'):match_energy(keys[2],e,u,e['signature']['public_key_hex'],u['signature']['public_key_hex'])

def test_no_untrusted_guardian_approval(keys):
    g,_,_=keys
    r=guardian_evaluate(g,'DROP TABLE foo','p','disallow destructive operations',True,'demo','test')
    assert verify(r,r['signature']['public_key_hex'])['ok']
    assert not decision_authorized(r,r['signature']['public_key_hex'],'DROP TABLE foo','disallow destructive operations',{r['signature']['public_key_hex']})

def test_guardian_api_fails_closed(keys,monkeypatch):
    monkeypatch.delenv('INNOVULIS_TRUSTED_GUARDIAN_KEYS',raising=False)
    g=keys[0];r=guardian_evaluate(g,'x','p','policy',True,'demo','reason')
    client=TestClient(app)
    resp=client.post('/v1/trust/guardian-check',json={'receipt':r,'pinned_public_key_hex':r['signature']['public_key_hex'],'proposal':'x','policy_text':'policy'})
    assert resp.status_code==200 and resp.json()['authorized'] is False

def test_api_verify(keys):
    k=keys[0];r=meter_utility(k,'c','GPU_SECONDS',5,'s',digest({'trace':'x'}),'one')
    client=TestClient(app)
    resp=client.post('/v1/trust/verify',json={'receipt':r,'pinned_public_key_hex':r['signature']['public_key_hex']})
    assert resp.status_code==200 and resp.json()['ok']

def test_api_frontend():
    c=TestClient(app)
    assert c.get('/').status_code==200
    assert b'iNNOVULIS Proof Fabric' in c.get('/').content
    assert c.get('/static/input.css').status_code==200

def test_missing_scope_rejected(keys):
    a=keys[0]
    with pytest.raises(ValueError):issue('ipqr/utility-receipt/v1',{'does_not_prove':[]},a)

def test_unknown_spec_rejected(keys):
    with pytest.raises(ValueError):issue('other',{'does_not_prove':['scope']},keys[0])
