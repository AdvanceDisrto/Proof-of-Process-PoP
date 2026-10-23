"""Signed iDr root primitives. A hash detects tampering; a trusted signature supplies authority."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519

def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha256(obj): return "sha256:"+hashlib.sha256(canonical(obj)).hexdigest()

def sign_root(manifest,key):
    body=dict(manifest); body.pop("iDr_root_id",None); body.pop("iDr_signature",None)
    body["iDr_root_id"]=sha256(body)
    body["iDr_signature"]="ed25519:"+key.sign(canonical(body)).hex()
    return body

def verify_root(data,trusted_public_key_hex):
    body=dict(data); sig=body.pop("iDr_signature",None); claimed=body.pop("iDr_root_id",None)
    if not sig or not claimed or claimed!=sha256(body): return False,"root hash mismatch"
    try:
        pub=ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(trusted_public_key_hex))
        pub.verify(bytes.fromhex(sig.split(":",1)[1]),canonical({**body,"iDr_root_id":claimed}))
    except Exception: return False,"genesis signature invalid"
    return True,"ok"

def load_and_verify(path,trusted_public_key_hex):
    data=json.loads(Path(path).read_text()); ok,reason=verify_root(data,trusted_public_key_hex)
    if not ok: raise ValueError("iDr verification failed: "+reason)
    return data
