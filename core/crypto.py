import hashlib,json
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def canonical(obj):
    # Deterministic JSON subset; intentionally not advertised as full RFC 8785.
    return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(b): return "sha256:"+hashlib.sha256(b).hexdigest()
def new_key(): return ed25519.Ed25519PrivateKey.generate()
def public_hex(k): return k.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
def sign(k,obj): return "ed25519:"+k.sign(canonical(obj)).hex()
def verify(pub_hex,obj,sig):
    try:
        ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(bytes.fromhex(sig.split(":",1)[1]),canonical(obj)); return True
    except Exception:return False
