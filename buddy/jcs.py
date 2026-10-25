import hashlib
import json

def jcs(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()

def sha(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()
