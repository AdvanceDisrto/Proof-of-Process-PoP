"""Opt-in standalone HTTP relay (no default listening, no external forwarding).

Start manually after provisioning independent signing key and out-of-band pinned trust
registry. Output is always a cryptographic *evaluation*, not payment authorization.
"""
from __future__ import annotations
import hmac
import json
import os
import stat
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, Request, HTTPException
from .quorum import VerificationError, canonical, evaluate, issue_relay_receipt, validate_registry

MAX_REQUEST = 16 * 1024

def _load_json_reject_duplicates(raw: bytes):
    def pairs(items):
        obj = {}
        for k,v in items:
            if k in obj: raise VerificationError('duplicate JSON object key')
            obj[k] = v
        return obj
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(VerificationError('nonfinite JSON')))

def _load_key(path: str) -> Ed25519PrivateKey:
    f=Path(path)
    mode=stat.S_IMODE(f.stat().st_mode)
    if mode & 0o077: raise RuntimeError('relay key file must not be readable by group/others')
    blob=f.read_bytes()
    if len(blob)!=32: raise RuntimeError('expected raw 32-byte Ed25519 machine key')
    return Ed25519PrivateKey.from_private_bytes(blob)

def create_app(registry: dict, pinned_sha256: str, relay_key: Ed25519PrivateKey, bearer_token: str, now_fn=None) -> FastAPI:
    """Create an API under explicit local configuration, fail-closed on invalid config."""
    validate_registry(registry, pinned_sha256)
    if not isinstance(bearer_token,str) or len(bearer_token)<32:
        raise RuntimeError('independent random bearer token required (>=32 characters)')
    app=FastAPI(title='iNNOVULIS Juror Receipt Relay -- NO ACTUATION',version='0.1.0')
    @app.get('/healthz')
    def health():return {'ready':True,'scope':'LOCAL_REVIEW_ONLY'}
    @app.post('/v1/quorum')
    async def quorum(request:Request):
        auth=request.headers.get('authorization','')
        if not hmac.compare_digest(auth,'Bearer '+bearer_token):
            raise HTTPException(status_code=401,detail='UNAUTHORIZED')
        if request.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':
            raise HTTPException(status_code=415,detail='EXPECTED_JSON')
        body=await request.body()
        if len(body)>MAX_REQUEST:raise HTTPException(status_code=413,detail='OVERSIZE')
        try:
            batch=_load_json_reject_duplicates(body)
            evaluation=evaluate(batch,registry,pinned_sha256,now=now_fn() if now_fn else None)
            return issue_relay_receipt(evaluation,relay_key)
        except (ValueError,TypeError,UnicodeDecodeError) as exc:
            raise HTTPException(status_code=422,detail='RECEIPT_REJECTED') from exc
    return app

def from_environment():
    needed=['RELAY_REGISTRY_FILE','RELAY_REGISTRY_SHA256_PIN','RELAY_KEY_FILE','RELAY_BEARER_TOKEN']
    missing=[k for k in needed if not os.environ.get(k)]
    if missing: raise RuntimeError('Missing externally provisioned config: '+','.join(missing))
    registry=_load_json_reject_duplicates(Path(os.environ['RELAY_REGISTRY_FILE']).read_bytes())
    return create_app(registry,os.environ['RELAY_REGISTRY_SHA256_PIN'],_load_key(os.environ['RELAY_KEY_FILE']),os.environ['RELAY_BEARER_TOKEN'])

def main():
    import uvicorn
    # Explicit opt-in only, bind loopback by default. No env credentials are printed.
    host=os.environ.get('RELAY_BIND_HOST','127.0.0.1')
    if host not in ('127.0.0.1','::1') and os.environ.get('RELAY_EXPLICIT_NONLOCAL_OPT_IN') != 'YES':
        raise RuntimeError('Non-local relay bind requires explicit opt-in and external network protections')
    uvicorn.run(from_environment(),host=host,port=9843,access_log=False)

if __name__=='__main__':main()

