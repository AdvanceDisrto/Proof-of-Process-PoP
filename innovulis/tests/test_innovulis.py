import copy
import os
import tempfile
from pathlib import Path
os.environ['INNOVULIS_API_KEYS']='test-only-strong-key-911'
os.environ['INNOVULIS_SIGNING_SEED']='11'*32
os.environ['INNOVULIS_DB']=str(Path(tempfile.gettempdir())/'innovulis-pytest-911.db')
from fastapi.testclient import TestClient
from api.main import app, public_key, verify_offline, canonical
from api import smoke
import numpy as np
import pytest

client=TestClient(app)
HDR={'X-API-Key':'test-only-strong-key-911'}

def test_health(): assert client.get('/health').json()['status']=='ok'
def test_missing_key(): assert client.post('/v1/mint',json={'claim':'x'}).status_code==401
def test_bad_digest(): assert client.post('/v1/mint',headers=HDR,json={'claim':'x','evidence':'sha256:xyz'}).status_code==422
def test_sign_pin_and_tamper():
 r=client.post('/v1/mint',headers=HDR,json={'claim':'claim','evidence':'evidence'}).json()
 assert verify_offline(r,public_key)[0]
 assert not verify_offline(r,'00'*32)[0]
 altered=copy.deepcopy(r);altered['payload']['claim']='altered'
 assert not verify_offline(altered,public_key)[0]
 assert client.get('/v1/receipt/'+r['receipt_id'],headers=HDR).json()==r

def test_model_endpoints_signed():
 for ep in ('/v1/spu/smoke','/v1/spu/empirical'):
  r=client.post(ep,headers=HDR,json={}).json()
  assert verify_offline(r,public_key)[0]
  assert r['payload']['physical_gate']=='ACTION_REQUIRED'

def test_status_honest():
 r=client.get('/v1/icore/status').json()
 assert r['physical_gate']['physical_execution']=='NOT_VERIFIED'

def test_cwa_all_truth_tables():
 for a in (0,1):
  assert smoke.boolean_not(a)==1-a
  for b in (0,1):
   assert smoke.boolean_and(a,b)==(a&b)
   assert smoke.boolean_xor(a,b)==(a^b)

def test_sign_preserving_matmul():
 a=np.array([[1,-2],[3,-4]],dtype=np.int8)
 b=np.array([[-7,8],[9,-10]],dtype=np.int8)
 assert np.array_equal(smoke.matmul_complex_field(a,b),a.astype(np.int64)@b.astype(np.int64))

def test_cwa_smoke():
 r=smoke.run_cwa_smoke()
 assert r['verdict']=='PASS'
 assert r['gates_passed']==r['gates_total']==7

def test_physics_assumption_bounds():
 a=smoke.estimate_enob(100000)
 b=smoke.estimate_enob(100000,nep_w_per_sqrt_hz=2e-12)
 assert b['model_effective_bits']>=a['model_effective_bits']
 assert smoke.estimate_power(tia_mw=5)['total_assumed_w']<smoke.estimate_power()['total_assumed_w']

def test_invalid_schema_fails():
 assert not verify_offline({'payload': {'schema':'random'},'signature':{}}, public_key)[0]

def test_canonical_deterministic():
 assert canonical({'b':1,'a':2})==canonical({'a':2,'b':1})

def test_independent_offline_verifier():
 from api.verify_offline import verify_receipt
 r=client.post('/v1/mint',headers=HDR,json={'claim':'independent offline test'}).json()
 assert verify_receipt(r,public_key)[0]
 assert not verify_receipt(r,'00'*32)[0]

# Full FastAPI integration tests added after reference-only 29-case baseline.
def test_fastapi_openapi_documents_all_public_and_spu_routes():
    response = client.get('/openapi.json')
    assert response.status_code == 200
    paths = set(response.json()['paths'])
    assert {'/health','/v1/keys','/v1/mint','/v1/verify',
            '/v1/receipt/{receipt_id}','/v1/spu/smoke',
            '/v1/spu/empirical','/v1/icore/status',
            '/receipt','/receipt/warrant','/verify','/pubkey'} <= paths

def test_spu_endpoints_are_not_accessible_without_authentication():
    for endpoint in ('/v1/spu/smoke','/v1/spu/empirical'):
        assert client.post(endpoint).status_code == 401

def test_receipt_fetch_requires_auth_and_handles_unknown_ids():
    r=client.post('/v1/mint',json={'claim':'verified lookup'},headers=HDR)
    assert r.status_code == 200
    rid=r.json()['receipt_id']
    assert client.get(f'/v1/receipt/{rid}').status_code == 401
    found=client.get(f'/v1/receipt/{rid}',headers=HDR)
    assert found.status_code == 200 and found.json() == r.json()
    assert client.get('/v1/receipt/unknown-id',headers=HDR).status_code == 404

def test_hash_only_receipt_rejects_non_json_and_large_body():
    request={'prompt_hash':'sha256:'+'a'*64,'output_hash':'sha256:'+'b'*64,
             'model_id':'iNNOVULIS','model_version':'v0.4.1'}
    assert client.post('/receipt',content='{}',headers={**HDR,'Content-Type':'text/plain'}).status_code == 415
    response=client.post('/receipt',content='x'*65537,headers={**HDR,'Content-Type':'application/json'})
    assert response.status_code == 413
    assert client.post('/receipt',json=request).status_code == 401

def test_hash_only_stateless_verify_requires_external_pin():
    body={'prompt_hash':'sha256:'+'a'*64,'output_hash':'sha256:'+'b'*64,
          'model_id':'iNNOVULIS','model_version':'v0.4.1'}
    minted=client.post('/receipt',json=body,headers=HDR)
    assert minted.status_code == 200
    receipt=minted.json()
    assert client.post('/verify',json={'receipt':receipt}).status_code == 400
    wrong=client.post('/verify',json={'receipt':receipt,'pinned_pubkey_hex':'00'*32})
    assert wrong.status_code == 200 and wrong.json()['ok'] is False
    correct=client.post('/verify',json={'receipt':receipt,'pinned_pubkey_hex':public_key})
    assert correct.status_code == 200 and correct.json()['ok'] is True
