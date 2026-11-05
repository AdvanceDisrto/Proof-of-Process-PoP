"""Real Ed25519 signatures over local simulated observations; NOT iVerify API compatible.

Never equate a valid signature with verified orbital time or real sensor data.
"""
import hashlib,json,re
from datetime import datetime,timezone
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat

SHA_RE=re.compile(r'^sha256:[0-9a-f]{64}$')
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False,ensure_ascii=False).encode('utf8')
def sha(b):return 'sha256:'+hashlib.sha256(b).hexdigest()
def public_key_hex(sk):return sk.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()

def mint_observation(observation,sk=None):
    if not isinstance(observation,dict):raise ValueError('observation must be object')
    sk=sk or Ed25519PrivateKey.generate()
    body={'spec':'ors/synthetic-observation/0.1','issued_at_utc_untrusted':datetime.now(timezone.utc).isoformat(),
          'input':observation,'trust_basis':'local_software_generated_key',
          'does_not_prove':['sensor truth','actual orbital position','independent trusted time','Bitcoin anchoring','physical ring existence']}
    encoded=canonical(body)
    return {'body':body,'receipt_id':sha(encoded),'signature_hex':sk.sign(encoded).hex(),
            'public_key_hex':public_key_hex(sk),'signature_algorithm':'Ed25519'}

def verify(receipt,pinned_public_key_hex):
    errors=[]
    try:
        if not isinstance(receipt,dict):return {'ok':False,'errors':['malformed_receipt']}
        b=receipt['body'];pk=receipt['public_key_hex'];sig=receipt['signature_hex']
        if not isinstance(b,dict) or b.get('spec')!='ors/synthetic-observation/0.1':errors.append('schema_invalid')
        encoded=canonical(b)
        if receipt['receipt_id']!=sha(encoded):errors.append('body_hash_mismatch')
        if pk!=pinned_public_key_hex:errors.append('pin_mismatch')
        if receipt.get('signature_algorithm')!='Ed25519':errors.append('algorithm_mismatch')
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pinned_public_key_hex)).verify(bytes.fromhex(sig),encoded)
    except (ValueError,KeyError,TypeError,InvalidSignature,OverflowError):
        errors.append('signature_or_format_invalid')
    return {'ok':not errors,'errors':errors}
