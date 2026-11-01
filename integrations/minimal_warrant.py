"""Minimal T1 signed receipt and policy-based T2 evidence warrant. No JCS/RFC8785 claim."""
import hashlib,json,time
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")
def sha(data): return "sha256:"+hashlib.sha256(data).hexdigest()
def pub(key): return key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
def mint(claim,key):
    body={"schema":"ipqr/t1/1","claim":claim,"declared_time_ns":time.time_ns()}
    data=canonical(body)
    return {"body":body,"receipt_id":sha(data),"signature":key.sign(data).hex(),"public_key":pub(key),"external_anchor":None}
def verify_t1(receipt, trusted_pubkeys):
    try:
        data=canonical(receipt["body"]); key=receipt["public_key"]
        if key not in trusted_pubkeys or sha(data)!=receipt["receipt_id"] or receipt.get("external_anchor") is not None:return False
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)).verify(bytes.fromhex(receipt["signature"]),data)
        return True
    except (KeyError,ValueError,TypeError,OverflowError,InvalidSignature):return False
GRADES={"U":-1,"D":0,"C":1,"B":2,"A":3}
def sign_evidence(payload, source_id, claimed_grade, source_key):
    if claimed_grade not in GRADES or claimed_grade=="U":raise ValueError("Invalid evidence grade")
    body={"evidence_hash":sha(payload),"source_id":source_id,"claimed_grade":claimed_grade}
    return {"body":body,"signature":source_key.sign(canonical(body)).hex(),"source_pubkey":pub(source_key)}
def verify_warrant(receipt,claim_type,evidence_bytes,evidence_record,policy):
    if not verify_t1(receipt,set(policy.get("trusted_claimants",[]))):
        return {"tier":"REJECTED","reason":"claimant trust/signature"}
    try:
        source=evidence_record["source_pubkey"];body=evidence_record["body"]
        if source not in policy["trusted_source_pubkeys"]:raise ValueError("untrusted source")
        if body["evidence_hash"]!=sha(evidence_bytes):raise ValueError("evidence hash mismatch")
        grade=body["claimed_grade"];minimum=policy["min_grade_by_claim_type"][claim_type]
        ceiling=policy["max_grade_by_source_pubkey"][source]
        if GRADES[grade]<GRADES[minimum] or GRADES[grade]>GRADES[ceiling]:raise ValueError("grade outside policy")
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(source)).verify(bytes.fromhex(evidence_record["signature"]),canonical(body))
        if receipt["body"]["claim"].get("evidence_hash")!=sha(evidence_bytes):raise ValueError("claim evidence link mismatch")
        return {"tier":"T2_WARRANT","declared_grade":grade,"semantic_correctness":"NOT_VERIFIED"}
    except (KeyError,ValueError,TypeError,OverflowError,InvalidSignature):
        return {"tier":"REJECTED","reason":"source signature/evidence/policy"}
