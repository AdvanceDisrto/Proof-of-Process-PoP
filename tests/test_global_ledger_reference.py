from copy import deepcopy

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from global_ledger.transaction import REQUIRED_ROLES, assess_transfer
from federal.disbursement import canonical


def sample():
    keys = {role: Ed25519PrivateKey.generate() for role in REQUIRED_ROLES}
    registry = {
        "protocol": "ITM-GLOBAL-TRUST-v1",
        "keys": {role: {
            "key_id": role + "-01",
            "public_key_hex": sk.public_key().public_bytes(
                serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
        } for role,sk in keys.items()}
    }
    digest="sha256:"+"a"*64
    body = {
        "protocol": "ITM-GLOBAL-LEDGER-v1",
        "transaction_id": "a1"*16, "amount_minor": 500000000,
        "currency": "USD", "issued_at": 1000,"expires_at":1100,
        "sender_commitment": digest, "receiver_commitment":digest,
        "purpose_hash":digest,
        "kyc": {"decision":"PASS","evidence_root":digest},
        "aml": {"decision":"PASS","evidence_root":digest},
        "sanctions": {"decision":"CLEAR","evidence_root":digest},
        "anchor": {"type":"OTS_BITCOIN","status":"VERIFIED","txid":"fake"},
    }
    bundle = {"body":body,"attestations":[{"role":role,"key_id":role+"-01",
              "signature_hex":key.sign(canonical(body)).hex()} for role,key in keys.items()]}
    return bundle,registry


def check(b,t,seen=None,now=1050):
    return assess_transfer(b,t,now_unix=now,seen_ids=seen or set())


def test_valid_local_signatures_do_not_authorize_transfer():
    b,t=sample()
    d=check(b,t)
    assert d.state=="SIGNED_EVIDENCE_CHECKS_PASS_SETTLEMENT_BLOCKED"
    assert not d.payout_permitted
    assert not d.anchor_verified
    assert not d.sanctions_live_query_performed


def test_fake_bitcoin_anchor_does_not_certify():
    b,t=sample()
    d=check(b,t)
    assert not d.anchor_verified


def test_changed_amount_fails():
    b,t=sample();b["body"]["amount_minor"]+=1
    assert check(b,t).state=="REJECTED"


def test_aml_claim_failed_rejects():
    b,t=sample();b["body"]["aml"]["decision"]="FAIL"
    assert check(b,t).state=="REJECTED"


def test_signer_removed_rejects():
    b,t=sample();b["attestations"].pop()
    assert check(b,t).state=="REJECTED"


def test_signer_reuse_rejects():
    b,t=sample();t=deepcopy(t)
    t["keys"]["payer"]["public_key_hex"]=t["keys"]["payee"]["public_key_hex"]
    assert check(b,t).state=="REJECTED"


def test_untrusted_key_substitution_rejects():
    b,t=sample();t=deepcopy(t)
    t["keys"]["payer"]["public_key_hex"]="f"*64
    assert check(b,t).state=="REJECTED"


def test_negative_amount_or_float_rejects():
    for amount in [-100,1.5,0]:
        b,t=sample();b["body"]["amount_minor"]=amount
        assert check(b,t).state=="REJECTED"


def test_replay_rejects():
    b,t=sample();assert check(b,t,seen={"a1"*16}).state=="REJECTED"


def test_expired_rejects():
    b,t=sample();assert check(b,t,now=2000).state=="REJECTED"


def test_currency_rejects():
    b,t=sample();b["body"]["currency"]="US-D"
    assert check(b,t).state=="REJECTED"
