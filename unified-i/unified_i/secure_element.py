"""ATECC608 family P-256 cryptographic contract, WITHOUT hardware provenance.

Transport is an injected signer callback. The caller must separately attest that
it is the physical chip, and independently pin the chip's real public key.
"""
from __future__ import annotations
import hashlib, secrets, time
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec,utils
from cryptography.exceptions import InvalidSignature
from .codec import canonical,sha256

DOMAIN=b"iNNOVULIS/hardware-signing-challenge/v1\x00"

class HardwareSignerUnavailable(RuntimeError):pass


def challenge(*,receipt_digest_hex:str,nonce_hex:str,issued_at:int,expires_at:int)->bytes:
    if type(receipt_digest_hex) is not str or type(nonce_hex) is not str:
        raise HardwareSignerUnavailable("hashes must be hex strings")
    if len(receipt_digest_hex)!=64 or len(nonce_hex)!=32:
        raise HardwareSignerUnavailable("invalid digest/nonce width")
    try:
        dg=bytes.fromhex(receipt_digest_hex);n=bytes.fromhex(nonce_hex)
    except ValueError as exc:
        raise HardwareSignerUnavailable("invalid hex") from exc
    if type(issued_at) is not int or type(expires_at) is not int or not 0<expires_at-issued_at<=120:
        raise HardwareSignerUnavailable("challenge lifetime must be <=120 sec")
    return hashlib.sha256(DOMAIN+canonical({"receipt_sha256":receipt_digest_hex,"nonce":nonce_hex,
                                           "issued_at":issued_at,"expires_at":expires_at})).digest()


def verify_p256_signature(*,digest:bytes,signature:bytes,pinned_public_pem:bytes)->bool:
    if type(digest) is not bytes or len(digest)!=32 or type(signature) is not bytes:
        return False
    try:
        pub=serialization.load_pem_public_key(pinned_public_pem)
        if not isinstance(pub,ec.EllipticCurvePublicKey) or not isinstance(pub.curve,ec.SECP256R1):
            return False
        if len(signature)==64:
            r=int.from_bytes(signature[:32],"big")
            s=int.from_bytes(signature[32:],"big")
            signature=utils.encode_dss_signature(r,s)
        pub.verify(signature,digest,ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        return True
    except (ValueError,TypeError,InvalidSignature):return False


def sign_through_callback(*,callback,device_slot:int,pinned_public_pem:bytes,
                          receipt_digest_hex:str,nonce_hex:str,issued_at:int,expires_at:int,now:int):
    if type(device_slot) is not int or not 0<=device_slot<=15:
        raise HardwareSignerUnavailable("invalid secure-element slot")
    if callback is None or not callable(callback):
        raise HardwareSignerUnavailable("no secure-element callback connected")
    if type(now) is not int or not issued_at<=now<=expires_at:
        raise HardwareSignerUnavailable("expired/replayed signing challenge")
    digest=challenge(receipt_digest_hex=receipt_digest_hex,nonce_hex=nonce_hex,
                     issued_at=issued_at,expires_at=expires_at)
    sig=callback(device_slot,digest)
    if not verify_p256_signature(digest=digest,signature=sig,pinned_public_pem=pinned_public_pem):
        raise HardwareSignerUnavailable("signature did not validate against independent pinned key")
    return {"algorithm":"ECDSA_P256_SHA256","signature_hex":sig.hex(),
            "digest_hex":digest.hex(),"device_slot":device_slot,
            "cryptographic_signature_valid":True,
            "hardware_provenance_verified":False,
            "tpm_or_puf_claim":False,
            "source_tier":"CALLBACK_UNATTESTED_NEVER_AUTO_PHYSICAL",
            "limits":"A software callback can impersonate a hardware signer; separate attestation required"}
