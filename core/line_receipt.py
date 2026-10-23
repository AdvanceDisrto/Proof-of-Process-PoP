from __future__ import annotations
import hashlib,json,secrets
from cryptography.hazmat.primitives.asymmetric import ed25519

def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def digest(obj): return "sha256:"+hashlib.sha256(canonical(obj)).hexdigest()

def create_human_receipt(*,execution_id,workflow_key,intent_hash,decision,actor,signer):
    body={"spec":"innovulis-line-receipt/1.2","execution_id":execution_id,"workflow_key":workflow_key,"intent_hash":intent_hash,"human_decision":decision,"human_id":actor,"nonce":secrets.token_hex(16),"proves":["the signer approved this exact intent hash"],"does_not_prove":["uncoerced consent","physical execution","external provider truth"]}
    body["human_signature"]="ed25519:"+signer.sign(canonical(body)).hex()
    return {"body":body,"receipt_id":digest(body)}

def verify_human_receipt(receipt,public_key_hex):
    body=receipt["body"]; sig=body["human_signature"]; unsigned=dict(body); unsigned.pop("human_signature",None)
    if receipt["receipt_id"]!=digest(body): return False
    try:
        ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex)).verify(bytes.fromhex(sig.split(":",1)[1]),canonical(unsigned)); return True
    except Exception: return False
