#!/usr/bin/env python3
"""Real HTTP smoke against the separately launched uvicorn process."""
import copy
import json
import os
import sys
from pathlib import Path
import urllib.error
import urllib.request

base=os.environ['BASE_URL']
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
auth={'X-API-Key':os.environ['INNOVULIS_API_KEYS'].split(',')[0]}

def request(path, data=None, headers=None, method=None):
    h=dict(headers or {})
    if data is not None:
        data=json.dumps(data).encode()
        h['Content-Type']='application/json'
    req=urllib.request.Request(base+path, data=data,headers=h,method=method)
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read())

def save(name,val):
    (out/name).write_text(json.dumps(val,indent=2,sort_keys=True)+'\n')

health=request('/health');assert health['status']=='ok';save('health.json',health)
key=request('/v1/keys');pin=key['public_key_hex'];save('public-key.json',key)
try:
    request('/v1/mint', {'claim':'blocked'})
    raise AssertionError('unauthorized request accepted')
except urllib.error.HTTPError as e: assert e.code==401
mint=request('/v1/mint', {'claim':'1 byte has 8 bits','evidence':'reference text'},auth)
save('mint.json',mint)
verified=request('/v1/verify',{'receipt':mint,'pinned_pubkey_hex':pin})
assert verified['valid'];save('mint-verification.json',verified)
retrieved=request('/v1/receipt/'+mint['receipt_id'],headers=auth)
assert retrieved==mint
altered=copy.deepcopy(mint);altered['payload']['claim']='1 byte has 9 bits'
rejected=request('/v1/verify',{'receipt':altered,'pinned_pubkey_hex':pin})
assert not rejected['valid'];save('tamper-rejection.json',rejected)
wrong_pin=request('/v1/verify',{'receipt':mint,'pinned_pubkey_hex':'0'*64})
assert not wrong_pin['valid'];save('wrong-key-rejection.json',wrong_pin)
spu=request('/v1/spu/smoke',{},auth)
assert spu['payload']['result']['verdict']=='PASS';save('spu-cwa-receipt.json',spu)
assert request('/v1/verify',{'receipt':spu,'pinned_pubkey_hex':pin})['valid']
physics=request('/v1/spu/empirical',{},auth)
assert physics['payload']['result']['verdict']=='MODEL_COMPUTED_NOT_MEASURED';save('spu-model-receipt.json',physics)
assert request('/v1/verify',{'receipt':physics,'pinned_pubkey_hex':pin})['valid']
from verify_offline import verify_receipt
assert all(verify_receipt(r,pin)[0] for r in [mint,spu,physics])
icore=request('/v1/icore/status');assert icore['physical_gate']['verdict']=='ACTION_REQUIRED';save('icore-status.json',icore)
print(json.dumps({'result':'ALL_HTTP_SMOKES_PASS','health':'PASS','auth_required':'PASS',
 'mint_verify':'PASS','tamper':'REJECTED','untrusted_key':'REJECTED',
 'spu_cwa':f"{spu['payload']['result']['gates_passed']}/{spu['payload']['result']['gates_total']}",
 'spu_model':'CPU_PARAMETER_MODEL','icore_physical':'ACTION_REQUIRED',
 'receipt_ids':[mint['receipt_id'],spu['receipt_id'],physics['receipt_id']]},indent=2))
