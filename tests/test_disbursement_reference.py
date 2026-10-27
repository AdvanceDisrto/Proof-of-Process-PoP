"""High consequence payout controls must not confer payment authority."""
import copy
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from federal.disbursement import REQUIRED_ROLES, canonical, duplicate_alert, verify_disbursement


def fixture():
    keys = {role: Ed25519PrivateKey.generate() for role in REQUIRED_ROLES}
    registry = {"protocol": "ITM-FED-TRUST-v1", "keys": {role: {
        "key_id": role + "-1",
        "public_key_hex": key.public_key().public_bytes(serialization.Encoding.Raw,
                serialization.PublicFormat.Raw).hex()
    } for role, key in keys.items()}}
    root = "sha256:" + "f" * 64
    body = {
        "protocol": "ITM-FED-DISBURSEMENT-v1", "agency": "HHS_CMS",
        "program": "Medicaid", "payment_id": "ab" * 16,
        "amount_cents": 450000, "intent_hash": root,
        "beneficiary_commitment": root, "service_commitment": root,
        "issued_at": 1000, "expires_at": 1100,
        "eligibility": {"decision": "ELIGIBLE", "evidence_root": root},
        "do_not_pay": {"decision": "CLEAR", "evidence_root": root},
        "service": {"decision": "EXTERNALLY_CORROBORATED", "evidence_root": root},
        "anchor": {"type": "OTS_BITCOIN", "status": "VERIFIED"},
    }
    bundle = {"body": body, "attestations": [{"role": role, "key_id": role + "-1",
             "signature_hex": key.sign(canonical(body)).hex()} for role,key in keys.items()]}
    return bundle, registry


def check(bundle, registry, *, seen=None, now=1050):
    return verify_disbursement(bundle,registry,now_unix=now,
                                consumed_payment_ids=set() if seen is None else seen)


def test_valid_signers_allow_integrity_only_not_money_or_anchor():
    b, t = fixture(); verdict = check(b,t)
    assert verdict.state == "EVIDENCE_CHECKS_PASS_SETTLEMENT_NOT_AUTHORIZED"
    assert not verdict.payment_authorized and not verdict.bitcoin_anchor_verified
    assert not verdict.bounty_authorized


def test_amount_tamper_fails_signature():
    b,t=fixture();b["body"]["amount_cents"]+=1
    assert check(b,t).state == "REJECTED"


def test_eligibility_claim_ineligible_fails_closed():
    b,t=fixture();b["body"]["eligibility"]["decision"]="INELIGIBLE"
    assert check(b,t).state == "REJECTED"


def test_unverified_service_fails_closed():
    b,t=fixture();b["body"]["service"]["decision"]="SELF_REPORTED"
    assert check(b,t).state == "REJECTED"


def test_missing_issuer_rejected():
    b,t=fixture();b["attestations"].pop()
    assert check(b,t).state == "REJECTED"


def test_substituted_untrusted_pubkey_rejected():
    b,t=fixture();t=copy.deepcopy(t);t["keys"]["provider"]["public_key_hex"]="c"*64
    assert check(b,t).state == "REJECTED"


def test_cross_role_key_reuse_rejected():
    b,t=fixture();t=copy.deepcopy(t)
    t["keys"]["provider"]["public_key_hex"]=t["keys"]["eligibility_verifier"]["public_key_hex"]
    assert check(b,t).state == "REJECTED"


def test_expired_receipt_fails():
    b,t=fixture();assert check(b,t,now=1200).state == "REJECTED"


def test_idempotency_fails_closed():
    b,t=fixture();assert check(b,t,seen={"ab"*16}).state == "REJECTED"


def test_float_amount_is_not_allowed():
    b,t=fixture();b["body"]["amount_cents"]=4500.5
    assert check(b,t).state == "REJECTED"


def test_duplicates_flag_investigation_not_confiscation():
    b,t=fixture();second=copy.deepcopy(b["body"]);second["payment_id"]="cd"*16
    alerts=duplicate_alert([b["body"],second]);assert len(alerts)==1
    assert alerts[0]["state"]=="AUDIT_REVIEW_REQUIRED" and not alerts[0]["automatic_forfeiture"]
