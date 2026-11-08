"""ATECC608(C)-compatible ECDSA P-256 public verification boundary, never fake signing.

A real secure-element signing adapter must sign the 32-byte SHA-256 digest
using a configured device slot and return authentic DER or 64-byte raw (r||s).
The device firmware, key authorization, provenance, and certificate chain need
independent setup. Ed25519 software keys are NOT equivalent to ATECC608 P256.
"""
from __future__ import annotations
import hashlib
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

class HardwareNotConnected(RuntimeError):pass


class P256HardwareSigner:
    def __init__(self,*,slot,device_id,sign_digest_callback=None,public_key_pem=None):
        if type(slot) is not int or not 0 <= slot <= 15 or not device_id:
            raise ValueError("physical device and programmed slot identity required")
        self.slot=slot;self.device_id=device_id;self._cb=sign_digest_callback
        self._pub=public_key_pem

    def sign_claim_digest(self,claim_sha256:bytes)->dict:
        if len(claim_sha256)!=32:raise ValueError("expected SHA256 digest exactly")
        if self._cb is None or self._pub is None:
            raise HardwareNotConnected("ATECC device I2C signer not configured; cannot synthesize a signature")
        raw=self._cb(self.slot,claim_sha256)
        if type(raw) is not bytes:
            raise HardwareNotConnected("device did not provide real signature bytes")
        if not verify_p256_digest(self._pub,claim_sha256,raw):
            raise HardwareNotConnected("hardware signature failed independent ECDSA P256 verification")
        return {"algorithm":"ECDSA_P256_SHA256", "device_id_unattested":self.device_id,
                "slot":self.slot,"digest_sha256":claim_sha256.hex(),
                "signature_hex":raw.hex(),
                "warning":"Signature authenticity doesn't prove signer hardware provenance, sensor accuracy or independent clock"}


def verify_p256_digest(public_key_pem,digest:bytes,signature:bytes):
    if type(digest) is not bytes or len(digest)!=32:return False
    try:
        key=serialization.load_pem_public_key(public_key_pem)
        if not isinstance(key,ec.EllipticCurvePublicKey) or not isinstance(key.curve,ec.SECP256R1):return False
        if len(signature)==64:
            r=int.from_bytes(signature[:32],"big");s=int.from_bytes(signature[32:],"big")
            signature=utils.encode_dss_signature(r,s)
        key.verify(signature,digest,ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        return True
    except (ValueError,TypeError,InvalidSignature):
        return False
