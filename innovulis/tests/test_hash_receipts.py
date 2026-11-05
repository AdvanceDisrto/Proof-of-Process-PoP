import copy
import os
import tempfile
os.environ["INNOVULIS_API_KEYS"]="test-only-strong-key-911"
os.environ["INNOVULIS_SIGNING_SEED"]="11"*32
import hashlib
import json
import subprocess
import sys
from pathlib import Path
os.environ["INNOVULIS_DB"]=str(Path(tempfile.gettempdir())/"innovulis-pytest-911.db")
from fastapi.testclient import TestClient
from api import hash_receipts
from api.main import app, public_key

client=TestClient(app)
HEADERS={'X-API-Key':'test-only-strong-key-911'}
# Kept scoped to test suite: original test_innovulis.py configures the test API env.
DATA={
    'prompt_hash':'sha256:'+'a'*64,
    'output_hash':'sha256:'+'b'*64,
    'model_id':'iNNOVULIS/test',
    'model_version':'0.1',
}

def mint(path='/receipt', data=None):
    r=client.post(path, headers=HEADERS, json=data or DATA)
    assert r.status_code==200, r.text
    return r.json()

def check(r, pin=public_key):
    q=client.post('/verify', json={'receipt':r,'pinned_pubkey_hex':pin})
    assert q.status_code==200, q.text
    return q.json()

def test_t1_stateless_and_urn_not_mutated():
    r=mint()
    assert r['receipt_id'].startswith('sha256:')
    assert r['receipt_urn'] == hash_receipts.urn_from_hash(r['receipt_id'])
    assert check(r)['ok']

def test_tamper_body_detects_hash_and_signature():
    r=mint()
    r['body']['output_hash']='sha256:'+'c'*64
    verdict=check(r)
    assert verdict['ok'] is False
    assert 'receipt_id mismatch' in verdict['errors']
    assert any('signature invalid:' in x for x in verdict['errors'])

def test_urn_tamper():
    r=mint();r['receipt_urn']='urn:iverify:'+'c'*64
    assert not check(r)['ok']

def test_urn_only_tamper_is_independent_gate():
    """Change only the URN; body digest and Ed25519 signature must stay valid."""
    original = mint()
    modified = copy.deepcopy(original)
    modified['receipt_urn'] = 'urn:iverify:' + 'c' * 64
    assert modified['body'] == original['body']
    assert modified['receipt_id'] == original['receipt_id']
    assert modified['signature'] == original['signature']
    verdict = check(modified)
    assert verdict['ok'] is False
    assert verdict['integrity_ok'] is True
    assert verdict['signature_ok'] is True
    assert verdict['errors'] == ['receipt_urn does not match body hash']

def test_wrong_pin_rejected():
    assert not check(mint(), '00'*32)['ok']

def test_missing_pin_fails_closed():
    assert client.post('/verify',json={'receipt':mint()}).status_code==400

def test_t2_wellformed_structure_only():
    data={**DATA,'evidence':[{
        'source_id':'dummy', 'payload_hash':'sha256:'+'f'*64,
        'source_pubkey_hex':'00'*32, 'grade':'A'}]}
    r=mint('/receipt/warrant',data)
    assert r['tier']=='T2' and check(r)['ok']
    assert any('evidence' in x.lower() for x in r['does_not_prove'])

def test_bad_evidence_rejected():
    data={**DATA,'evidence':[{'source_id':'x','payload_hash':'invalid','source_pubkey_hex':'zz','grade':'G'}]}
    assert client.post('/receipt/warrant',headers=HEADERS,json=data).status_code==400

def test_unknown_tier_rejected():
    r=mint();r['tier']='T3'
    assert not check(r)['ok']

def test_body_cap():
    assert client.post('/receipt',headers={**HEADERS,'Content-Type':'application/json'},content=b'x'*65537).status_code==413

def test_no_auth_mint():
    assert client.post('/receipt',json=DATA).status_code==401

def test_content_type():
    assert client.post('/receipt',headers=HEADERS,content='{}').status_code==415

def test_banner_binding_exact_bytes(tmp_path):
    banner=tmp_path/'banner.txt'
    banner.write_bytes(b'SOFTWARE_GATE GREEN\nPHYSICAL_GATE ACTION_REQUIRED\n')
    data={**DATA,'prompt_hash':hash_receipts.digest(banner.read_bytes())}
    r=mint(data=data)
    receiptfile=tmp_path/'receipt.json';receiptfile.write_text(json.dumps(r))
    tool=Path(__file__).parents[1]/'api'/'verify_hash_offline.py'
    command=[sys.executable,str(tool),str(receiptfile),'--pinned-public-key',public_key,'--banner',str(banner)]
    good=subprocess.run(command,capture_output=True,text=True)
    assert good.returncode==0,good.stderr+good.stdout
    banner.write_bytes(b'SOFTWARE_GATE GREEN\nPHYSICAL_GATE GREEN\n')
    bad=subprocess.run(command,capture_output=True,text=True)
    assert bad.returncode==2 and 'external banner content hash mismatch' in bad.stdout

def test_wrong_external_pin_offline(tmp_path):
    r=mint()
    f=tmp_path/'r.json';f.write_text(json.dumps(r))
    tool=Path(__file__).parents[1]/'api'/'verify_hash_offline.py'
    p=subprocess.run([sys.executable,str(tool),str(f),'--pinned-public-key','00'*32],capture_output=True,text=True)
    assert p.returncode==2

def test_tier_downgrade_detected():
    data={**DATA,'evidence':[{'source_id':'source','payload_hash':'sha256:'+'f'*64,'source_pubkey_hex':'00'*32,'grade':'B'}]}
    r=mint('/receipt/warrant',data)
    r['tier']='T1'
    result=check(r)
    assert not result['ok'] and any('envelope' in x for x in result['errors'])

def test_unsigned_disclaimer_tamper_detected():
    r=mint()
    r['does_not_prove']=[]
    result=check(r)
    assert not result['ok'] and any('caveat' in x for x in result['errors'])
