#!/usr/bin/env python3
"""Executes real HTTP T1/T2 sign/verify, tamper, external banner binding and offline checks."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request

BASE=os.environ['BASE_URL']
OUT=Path(sys.argv[1])
OUT.mkdir(parents=True,exist_ok=True)
KEY=os.environ['INNOVULIS_API_KEYS'].split(',')[0]
PIN=os.environ['INNOVULIS_SIGNING_SEED']

def call(path,data=None, auth=False):
    headers={'Content-Type':'application/json'}
    if auth: headers['X-API-Key']=KEY
    req=urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers=headers,method='POST' if data is not None else 'GET')
    with urllib.request.urlopen(req,timeout=30) as res:
        return json.loads(res.read())

pk=call('/pubkey')['public_key_hex']
banner=(
    'iNNOVULIS iVERIFY + SPU\n'
    'API HTTP SMOKE: PASS\n'
    'RECEIPT SIGNATURE: PASS\n'
    'EXTERNAL BANNER BINDING: PASS\n'
    'SOFTWARE GATE: OBSERVATION_ONLY\n'
    'PHYSICAL GATE: ACTION_REQUIRED\n'
)
(OUT/'banner.txt').write_bytes(banner.encode('utf-8'))
h=lambda x:'sha256:'+hashlib.sha256(x).hexdigest()
data={'prompt_hash':h(banner.encode()),'output_hash':h(b'API HTTP SMOKE: PASS'),'model_id':'innovulis-smoke','model_version':'0.4'}
r=call('/receipt',data,auth=True)
(OUT/'hash-t1-receipt.json').write_text(json.dumps(r,indent=2))
valid=call('/verify',{'receipt':r,'pinned_pubkey_hex':pk})
assert valid['ok'],valid
assert r['receipt_urn']=='urn:iverify:'+r['receipt_id'][7:]
(OUT/'hash-valid.json').write_text(json.dumps(valid,indent=2))
r_bad=json.loads(json.dumps(r));r_bad['body']['output_hash']=h(b'MODIFIED')
tampered=call('/verify',{'receipt':r_bad,'pinned_pubkey_hex':pk})
assert not tampered['ok'] and any('signature invalid' in x for x in tampered['errors']) and 'receipt_id mismatch' in tampered['errors']
(OUT/'hash-tamper-rejection.json').write_text(json.dumps(tampered,indent=2))
assert not call('/verify',{'receipt':r,'pinned_pubkey_hex':'00'*32})['ok']
evidence=[{'source_id':'EXAMPLE_UNVERIFIED','payload_hash':h(b'not signed evidence'),'source_pubkey_hex':'00'*32,'grade':'A'}]
t2=call('/receipt/warrant',{**data,'evidence':evidence},auth=True)
assert call('/verify',{'receipt':t2,'pinned_pubkey_hex':pk})['ok']
(OUT/'hash-t2-structure-only.json').write_text(json.dumps(t2,indent=2))
tool=Path(__file__).parent/'api'/'verify_hash_offline.py'
p=subprocess.run([sys.executable,str(tool),str(OUT/'hash-t1-receipt.json'),'--pinned-public-key',pk,'--banner',str(OUT/'banner.txt')],capture_output=True,text=True)
assert p.returncode==0,(p.stdout,p.stderr)
(OUT/'offline-banner-verification.json').write_text(p.stdout)
# Alter external banner without altering receipt: content verifier must reject it.
badbanner=OUT/'banner-tampered.txt';badbanner.write_text(banner.replace('ACTION_REQUIRED','GREEN'))
p2=subprocess.run([sys.executable,str(tool),str(OUT/'hash-t1-receipt.json'),'--pinned-public-key',pk,'--banner',str(badbanner)],capture_output=True,text=True)
assert p2.returncode==2,(p2.stdout,p2.stderr)
(OUT/'offline-banner-tamper.json').write_text(p2.stdout)
print('PASS_HASH_RECEIPT_T1_HTTP')
print('PASS_HASH_RECEIPT_TAMPER_HASH_AND_SIGNATURE')
print('PASS_HASH_RECEIPT_T2_STRUCTURE_ONLY')
print('PASS_OFFLINE_PINNED_KEY_AND_FULL_BANNER')
print('PASS_EXTERNAL_BANNER_TAMPER_REJECTION')
