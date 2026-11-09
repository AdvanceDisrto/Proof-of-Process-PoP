"""iP.CiH v0.1: bounded signed app capsule, never a hardware proof.

Trust anchor is supplied separately by the verifier, NEVER self-provided by a capsule.
Signing v1 uses canonical UTF-8 JSON bytes; verify before rendering anything.
"""
from __future__ import annotations
import base64, hashlib, json, secrets, time, zlib
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

PROTOCOL='ipcih/capsule/v1'
MAX_HTML=1536
MAX_WIRE=12000
MAX_LIFETIME=3600
APP_KIND='passive-local-canvas-v1'

class CapsuleRejected(ValueError):pass

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

def b64e(b):return base64.urlsafe_b64encode(b).decode('ascii').rstrip('=')

def b64d(x, max_len=MAX_WIRE):
    if type(x) is not str or len(x)>max_len*2 or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in x):raise CapsuleRejected('invalid base64url')
    try:
        b=base64.urlsafe_b64decode(x+'='*((-len(x))%4))
    except (ValueError,Exception) as exc:
        raise CapsuleRejected('base64 decoding failed') from exc
    if len(b)>max_len or b64e(b)!=x:raise CapsuleRejected('noncanonical or oversized base64')
    return b

def sha(data):return hashlib.sha256(data).hexdigest()

def make_app(label):
    # No user-controlled HTML or JS: label goes into a safe JSON string assigned textContent.
    if not isinstance(label,str) or not 1<=len(label)<=70 or any(ord(c)<32 for c in label):raise CapsuleRejected('invalid label')
    literal=json.dumps(label,ensure_ascii=True).replace("<",r"\u003c").replace(">",r"\u003e").replace("&",r"\u0026")
    app='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>iP.CiH</title><style>body{background:#07100e;color:#aafbdc;font:15px system-ui;text-align:center;padding:24px}canvas{width:270px;max-width:100%;border:1px solid #1b9}</style><h2>i&#8482; CAPSULE</h2><p id="claim"></p><p>VISUAL DEMO ONLY · NOT A PHYSICS ATTESTATION</p><canvas id="v" width="270" height="150"></canvas><script>document.getElementById('claim').textContent=LABEL;let c=document.getElementById('v'),x=c.getContext('2d'),i=0;function d(){x.fillStyle='#07100e';x.fillRect(0,0,270,150);x.strokeStyle='#5cf2c7';x.beginPath();for(let k=0;k<270;k++){let y=75+25*Math.sin(k/15-i);k?x.lineTo(k,y):x.moveTo(k,y)}x.stroke();i+=.06;requestAnimationFrame(d)}d()</script>'''
    return app.replace('LABEL',literal).encode('utf-8')

class Issuer:
    def __init__(self, private_key:ed25519.Ed25519PrivateKey, issuer_id='i-local-demo'):
        if not isinstance(private_key,ed25519.Ed25519PrivateKey):raise TypeError('Ed25519 key required')
        if not isinstance(issuer_id,str) or not 1<=len(issuer_id)<=70:raise ValueError('issuer id')
        self.key=private_key;self.issuer_id=issuer_id
    def public_raw(self):return self.key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    def public_fingerprint(self):return sha(self.public_raw())
    def issue(self,label,now=None,lifetime=300):
        now=int(time.time()) if now is None else now
        if type(now) is not int or type(lifetime) is not int or not 1<=lifetime<=MAX_LIFETIME:raise CapsuleRejected('bad time')
        html=make_app(label)
        if len(html)>MAX_HTML:raise CapsuleRejected('app too large')
        body={'v':PROTOCOL,'issuer':self.issuer_id,'issued_at':now,'expires_at':now+lifetime,
              'nonce':secrets.token_hex(12),'app_kind':APP_KIND,'app_sha256':sha(html),
              'app_b64':b64e(html),'claim':label,'evidence_tier':'SYNTHETIC_SOFTWARE',
              'does_not_prove':['truth of user-supplied claim','hardware-backed signature','measured joules','independent witness verification']}
        signed=canonical(body)
        return {'body':body,'signature':b64e(self.key.sign(signed))}

def verify(packet, pinned_public_raw, *, now=None):
    if type(pinned_public_raw) is not bytes or len(pinned_public_raw)!=32:raise CapsuleRejected('independently pinned 32-byte Ed25519 public key required')
    try:
        if type(packet) is not dict or set(packet)!={'body','signature'}:raise CapsuleRejected('bad envelope')
        body=packet['body']
        required={'v','issuer','issued_at','expires_at','nonce','app_kind','app_sha256','app_b64','claim','evidence_tier','does_not_prove'}
        if type(body) is not dict or set(body)!=required or body['v']!=PROTOCOL or body['app_kind']!=APP_KIND:raise CapsuleRejected('unsupported capsule')
        if type(body['nonce']) is not str or len(body['nonce'])!=24 or any(c not in '0123456789abcdef' for c in body['nonce']):raise CapsuleRejected('invalid nonce')
        if type(body['issued_at']) is not int or type(body['expires_at']) is not int or not 1<=body['expires_at']-body['issued_at']<=MAX_LIFETIME:raise CapsuleRejected('invalid lifetime')
        now=int(time.time()) if now is None else now
        if type(now) is not int or now>body['expires_at'] or now<body['issued_at']-5:raise CapsuleRejected('expired/not yet valid')
        if body['evidence_tier']!='SYNTHETIC_SOFTWARE':raise CapsuleRejected('invalid evidence tier')
        if not isinstance(body['does_not_prove'],list) or len(body['does_not_prove'])!=4:raise CapsuleRejected('bad limitations')
        # Authenticate the *whole* body before decoding/executing app bytes.
        raw=canonical(body)
        if len(raw)>MAX_WIRE:raise CapsuleRejected('oversized capsule')
        sig=b64d(packet['signature'],128)
        if len(sig)!=64:raise CapsuleRejected('bad signature length')
        ed25519.Ed25519PublicKey.from_public_bytes(pinned_public_raw).verify(sig,raw)
        html=b64d(body['app_b64'],MAX_HTML)
        if sha(html)!=body['app_sha256'] or html!=make_app(body['claim']):raise CapsuleRejected('app hash or template mismatch')
        if type(body['issuer']) is not str or not body['issuer']:raise CapsuleRejected('invalid issuer')
        return {'status':'VERIFIED_SIGNED_CAPSULE','issuer':body['issuer'],'app_html':html.decode('utf-8'),
                'app_sha256':sha(html),'fingerprint':sha(pinned_public_raw),'evidence_tier':'SYNTHETIC_SOFTWARE',
                'claim_truth':'NOT_EVALUATED'}
    except CapsuleRejected:raise
    except (ValueError,TypeError,KeyError,InvalidSignature,UnicodeError) as exc:raise CapsuleRejected('invalid capsule or signature') from exc

def encode_wire(packet):
    data=canonical(packet)
    if len(data)>MAX_WIRE:raise CapsuleRejected('wire oversized')
    compressed=zlib.compress(data,9)
    return 'ipcih1z:'+b64e(compressed)

def decode_wire(wire):
    if not isinstance(wire,str) or not wire.startswith('ipcih1z:'):raise CapsuleRejected('not ipcih carrier')
    compressed=b64d(wire[8:],MAX_WIRE)
    # Prevent zip-bomb on scanner; do not trust supplied compressed length.
    d=zlib.decompressobj()
    try:raw=d.decompress(compressed,MAX_WIRE+1)
    except zlib.error as exc:raise CapsuleRejected('corrupt compression') from exc
    if len(raw)>MAX_WIRE or not d.eof or d.unused_data or d.unconsumed_tail:raise CapsuleRejected('bad compressed payload')
    try:packet=json.loads(raw)
    except (ValueError,UnicodeError) as exc:raise CapsuleRejected('invalid packet JSON') from exc
    if canonical(packet)!=raw:raise CapsuleRejected('noncanonical packet JSON')
    return packet
