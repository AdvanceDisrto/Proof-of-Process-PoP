import asyncio
import hashlib
import json
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from integrations.qow_pop_bridge import validate_qow, qow_domain_receipt
from proof.parallel_pop import aggregate, verify_domain

def fixture():
    sk = Ed25519PrivateKey.generate()
    pub = sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    body = {"claim_id": "MATH_A", "verdict": "PROVEN_TRUE", "issuer_pubkey_hex": pub, "parent_hashes": []}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    return {"body": body, "receipt_hash": "sha256:" + hashlib.sha256(raw).hexdigest(), "signature": sk.sign(raw).hex()}, pub

def test_domain_uses_real_pop_merkle():
    receipt, pub = fixture()
    domain = asyncio.run(qow_domain_receipt(receipt, pub, lambda r: {"ok": True, "verdict": "PROVEN_TRUE"}))
    assert verify_domain(domain)
    assert aggregate([domain])["body"]["state"] == "VERIFIED_PROCESS"

def test_tamper_rejected():
    receipt, pub = fixture()
    receipt["body"]["claim_id"] = "CHANGED"
    with pytest.raises(ValueError):
        validate_qow(receipt, pub, lambda r: {"ok": True, "verdict": "PROVEN_TRUE"})

def test_pinned_key_rejected():
    receipt, pub = fixture()
    with pytest.raises(ValueError):
        validate_qow(receipt, "00" * 32, lambda r: {"ok": True, "verdict": "PROVEN_TRUE"})

def test_missing_recheck_fails_closed():
    receipt, pub = fixture()
    domain = asyncio.run(qow_domain_receipt(receipt, pub, None))
    assert aggregate([domain])["body"]["state"] == "INCOMPLETE"

def test_recheck_failure_fails_closed():
    receipt, pub = fixture()
    domain = asyncio.run(qow_domain_receipt(receipt, pub, lambda r: {"ok": False, "verdict": "PROVEN_TRUE"}))
    assert aggregate([domain])["body"]["state"] == "INCOMPLETE"
