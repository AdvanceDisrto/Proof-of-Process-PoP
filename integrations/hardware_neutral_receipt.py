"""iRECEIPT hardware-neutral transport v1: CPU, GPU and edge records.

Standard-library hashing and externally supplied Ed25519 signing callback.
Device classes are observations, never hardware attestations.
Canonical JSON here is protocol-specific, NOT RFC 8785 JCS.
"""
from __future__ import annotations
import hashlib,json,re
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

DOMAIN=b"iRECEIPT/hardware-neutral/v1\x00"
DEVICE_CLASSES=frozenset({"CPU","GPU","NPU","MCU","MICROPROCESSOR"})
ALLOWED_OPERATIONS=frozenset({"compute_observation","inference_observation","sensor_observation"})
SHA_RE=re.compile(r"sha256:[0-9a-f]{64}\Z")
KEY_RE=re.compile(r"[0-9a-f]{64}\Z")
SIG_RE=re.compile(r"[0-9a-f]{128}\Z")

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")

def digest(data):
    return "sha256:"+hashlib.sha256(data).hexdigest()

def _valid_hash(value):
    return isinstance(value,str) and bool(SHA_RE.fullmatch(value))

def observation(*,device_class,operation,evidence_bytes,request_id,parent=None):
    """Construct unsigned observation; cannot establish real execution or identity."""
    if device_class not in DEVICE_CLASSES or operation not in ALLOWED_OPERATIONS:
        raise ValueError("UNSUPPORTED_DEVICE_OR_OPERATION")
    if not isinstance(evidence_bytes,bytes) or len(evidence_bytes)>8_388_608:
        raise ValueError("INVALID_EVIDENCE_BYTES")
    if not isinstance(request_id,str) or not 1<=len(request_id)<=128:
        raise ValueError("INVALID_REQUEST_ID")
    if parent is not None and not _valid_hash(parent):
        raise ValueError("INVALID_PARENT")
    return {"schema":"ipqr/hardware-neutral-observation/v1",
            "device_class_reported":device_class,"operation":operation,
            "request_id":request_id,"parent":parent,
            "evidence_hash":digest(evidence_bytes),"evidence_length":len(evidence_bytes)}

def sign(observation_body,signing_callback,public_key_hex):
    """Sign a domain-separated canonical body using externally supplied key custody."""
    _validate_body(observation_body)
    if not isinstance(public_key_hex,str) or not KEY_RE.fullmatch(public_key_hex):
        raise ValueError("INVALID_PUBLIC_KEY")
    message=DOMAIN+canonical(observation_body)
    signature=signing_callback(message)
    if not isinstance(signature,bytes) or len(signature)!=64:
        raise ValueError("INVALID_SIGNING_RESULT")
    result={"body":observation_body,"receipt_id":digest(message),
            "signature":{"algorithm":"Ed25519","public_key_hex":public_key_hex,
                         "signature_hex":signature.hex()},
            "external_anchor":None}
    if not verify(result,{public_key_hex}):
        raise ValueError("SIGNING_KEY_DOES_NOT_MATCH")
    return result

def _validate_body(b):
    if not isinstance(b,dict) or set(b)!={"schema","device_class_reported","operation",
                                         "request_id","parent","evidence_hash","evidence_length"}:
        raise ValueError("BODY_SHAPE")
    if b["schema"]!="ipqr/hardware-neutral-observation/v1":
        raise ValueError("BODY_SCHEMA")
    if b["device_class_reported"] not in DEVICE_CLASSES or b["operation"] not in ALLOWED_OPERATIONS:
        raise ValueError("DEVICE_OPERATION")
    if not isinstance(b["request_id"],str) or not 1<=len(b["request_id"])<=128:
        raise ValueError("REQUEST_ID")
    if b["parent"] is not None and not _valid_hash(b["parent"]):
        raise ValueError("PARENT")
    if not _valid_hash(b["evidence_hash"]):
        raise ValueError("EVIDENCE_HASH")
    if type(b["evidence_length"]) is not int or not 0<=b["evidence_length"]<=8_388_608:
        raise ValueError("EVIDENCE_LENGTH")

def verify(receipt,approved_public_keys,evidence_bytes=None):
    """Independently check signed integrity. Optional evidence bytes check.

    Does not imply identity, time, silicon type, execution, correctness or anchoring.
    """
    try:
        if not isinstance(receipt,dict) or set(receipt)!={"body","receipt_id","signature","external_anchor"}:
            return False
        if receipt["external_anchor"] is not None:
            return False # anchor status is verified by a different layer
        body=receipt["body"];_validate_body(body)
        sig=receipt["signature"]
        if not isinstance(sig,dict) or set(sig)!={"algorithm","public_key_hex","signature_hex"}:
            return False
        key=sig["public_key_hex"]
        if (sig["algorithm"]!="Ed25519" or not isinstance(key,str)
            or not KEY_RE.fullmatch(key) or key not in approved_public_keys
            or not isinstance(sig["signature_hex"],str)
            or not SIG_RE.fullmatch(sig["signature_hex"])):
            return False
        message=DOMAIN+canonical(body)
        if receipt["receipt_id"]!=digest(message):
            return False
        if evidence_bytes is not None:
            if not isinstance(evidence_bytes,bytes) or len(evidence_bytes)!=body["evidence_length"]:
                return False
            if digest(evidence_bytes)!=body["evidence_hash"]:
                return False
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)).verify(
            bytes.fromhex(sig["signature_hex"]),message)
        return True
    except (KeyError,ValueError,TypeError,OverflowError,InvalidSignature):
        return False

def export_for_edge(receipt):
    """Portable JSON; edge devices can use SHA256 and Ed25519 without Python."""
    if not isinstance(receipt,dict):
        raise ValueError("INVALID_RECEIPT")
    return canonical(receipt)

def hardware_capability_matrix():
    return {kind:{"format":"canonical-json-v1","hash":"SHA-256",
                   "signature":"Ed25519","benchmark":"NOT_MEASURED",
                   "hardware_attestation":"NOT_VERIFIED"} for kind in sorted(DEVICE_CLASSES)}
