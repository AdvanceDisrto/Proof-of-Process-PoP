"""iNNOVULIS receipt CI reference: hash-only, no inference or hardware attestation.
This is a SMALL CI reference, not the separately packaged FastAPI v0.4.1 release.
Canonicalization is Python JSON, NOT RFC 8785 JCS.
"""
import hashlib, json, re, secrets, time
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("utf-8")
def sha(data):
    return "sha256:"+hashlib.sha256(data).hexdigest()
def sha_tag(s):
    return isinstance(s,str) and re.fullmatch(r"sha256:[0-9a-f]{64}",s) is not None
def urn(h):
    return "urn:iverify:"+h.removeprefix("sha256:")
def pubraw(priv):
    return priv.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
def sign_receipt(priv,prompt_hash,output_hash,model_id,model_version,evidence=None):
    if not (sha_tag(prompt_hash) and sha_tag(output_hash)):
        raise ValueError("invalid input hash")
    if not isinstance(model_id,str) or not model_id or not isinstance(model_version,str) or not model_version:
        raise ValueError("model metadata required")
    tier="T2" if evidence is not None else "T1"
    if tier=="T2" and (not isinstance(evidence,list) or not evidence):
        raise ValueError("T2 evidence required")
    disclaimers=["does not prove prompt/output correspond to actual execution",
                 "does not prove model identity or correctness",
                 "does not prove signing key custody"]
    if tier=="T2":
        disclaimers.append("does not verify evidence source signatures")
    body={"spec":"iverify/receipt/1.0","tier":tier,
          "prompt_hash":prompt_hash,"output_hash":output_hash,
          "model_id":model_id,"model_version":model_version,
          "timestamp_utc":"2026-11-04T00:00:00Z",
          "nonce":secrets.token_hex(16),
          "does_not_prove":disclaimers}
    if tier=="T2":
        for e in evidence:
            if not isinstance(e,dict) or not sha_tag(e.get("payload_hash")):
                raise ValueError("malformed evidence")
        body["evidence"]=evidence
    b=canonical(body); rid=sha(b)
    return {"receipt_id":rid,"receipt_urn":urn(rid),"body":body,
            "signature":priv.sign(b).hex(),"public_key_hex":pubraw(priv)}
def verify(receipt,pin,banner=None):
    result={"ok":False,"integrity_ok":False,"signature_ok":False,
            "urn_ok":False,"banner_hash_ok":None,"trust_basis":"external_pin",
            "errors":[]}
    err=result["errors"]
    if not isinstance(receipt,dict) or not isinstance(pin,str) or not re.fullmatch(r"[0-9a-f]{64}",pin):
        err.append("malformed receipt or missing trusted pin");return result
    try:
        body=receipt["body"]
        if not isinstance(body,dict):raise ValueError("body must be object")
        encoded=canonical(body)
        actual=sha(encoded)
        result["integrity_ok"]=actual==receipt.get("receipt_id")
        if not result["integrity_ok"]:err.append("receipt_id mismatch")
        result["urn_ok"]=receipt.get("receipt_urn")==urn(actual)
        if not result["urn_ok"]:err.append("receipt_urn does not match body hash")
        if receipt.get("public_key_hex")!=pin:
            err.append("signing public key does not match pinned key")
        else:
            try:
                ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(pin)).verify(bytes.fromhex(receipt["signature"]),encoded)
                result["signature_ok"]=True
            except (InvalidSignature,ValueError,KeyError,TypeError):
                err.append("signature invalid: InvalidSignature")
        if body.get("tier") not in ("T1","T2") or body.get("spec")!="iverify/receipt/1.0":
            err.append("unsupported schema or tier")
        if body.get("tier")=="T2":
            es=body.get("evidence")
            if not isinstance(es,list) or not es or any(not isinstance(x,dict) or not sha_tag(x.get("payload_hash")) for x in es):
                err.append("malformed T2 evidence")
        if banner is not None:
            result["banner_hash_ok"]=sha(banner)==body.get("prompt_hash")
            if not result["banner_hash_ok"]:err.append("banner_hash_mismatch")
    except (KeyError,TypeError,ValueError,OverflowError) as e:
        err.append("malformed receipt")
    result["ok"]=not err
    return result
