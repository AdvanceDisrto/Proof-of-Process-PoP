from copy import deepcopy
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from threshold.quorum import (VerificationError, canonical, evaluate, issue_relay_receipt,
    sha256, signing_bytes, verify_relay_receipt)

NOW=1793100000
R='sha256:'+'a'*64
P='sha256:'+'b'*64
NONCE='9'*32

@pytest.fixture()
def example():
    keys={f'juror-{c}':Ed25519PrivateKey.generate() for c in 'abc'}
    registry={'protocol':'ITM-JUROR-REGISTRY-v1','policy_sha256':P,
              'jurors':{k:v.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex() for k,v in keys.items()}}
    pin=sha256(canonical(registry))
    def att(k,decision='APPROVE'):
        obj={'juror':k,'receipt_sha256':R,'policy_sha256':P,'request_nonce':NONCE,
             'decision':decision,'issued_at':NOW-30,'expires_at':NOW+30}
        obj['signature_hex']=keys[k].sign(signing_bytes(obj)).hex()
        return obj
    batch={'protocol':'ITM-JUROR-QUORUM-BATCH-v1','receipt_sha256':R,'policy_sha256':P,
           'request_nonce':NONCE, 'attestations':[att('juror-a'),att('juror-b')]}
    return keys,registry,pin,att,batch

def run(e):
    _,r,p,_,batch=e
    return evaluate(batch,r,p,now=NOW)

def test_two_independent_approvals_and_no_execution(example):
    result=run(example)
    assert result['state']=='QUORUM_APPROVED'
    assert result['threshold']==2 and result['total_jurors']==3
    assert result['actuation_authorized'] is False and result['settlement_authorized'] is False

def test_one_is_not_a_quorum(example):
    example[-1]['attestations'].pop()
    assert run(example)['state']=='ACTION_REQUIRED'

def test_signed_reject_vetoes_otherwise_two_approvals(example):
    example[-1]['attestations'].append(example[-2]('juror-c','REJECT'))
    assert run(example)['state']=='REFUTED_BY_SIGNED_REJECTION'

def test_duplicate_vote(example):
    example[-1]['attestations'][1]=deepcopy(example[-1]['attestations'][0])
    with pytest.raises(VerificationError,match='duplicate'):run(example)

def test_payload_mutation(example):
    example[-1]['attestations'][0]['decision']='REJECT'
    with pytest.raises(VerificationError,match='BAD_SIGNATURE'):run(example)

def test_substituted_source_key_even_same_name(example):
    example[1]['jurors']['juror-a']=Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()
    with pytest.raises(VerificationError,match='PIN_MISMATCH'):run(example)

def test_wrong_out_of_band_pin(example):
    e=list(example);e[2]='sha256:'+'0'*64
    with pytest.raises(VerificationError,match='PIN_MISMATCH'):run(e)

def test_duplicate_public_keys(example):
    example[1]['jurors']['juror-b']=example[1]['jurors']['juror-a']
    example=list(example);example[2]=sha256(canonical(example[1]))
    with pytest.raises(VerificationError,match='duplicate'):run(example)

def test_replayed_nonce_or_receipt(example):
    example[-1]['request_nonce']='c'*32
    with pytest.raises(VerificationError,match='cross-batch'):run(example)

def test_expiry(example):
    with pytest.raises(VerificationError,match='expired'):evaluate(example[-1],example[1],example[2],now=NOW+31)

def test_future_time(example):
    with pytest.raises(VerificationError,match='future'):evaluate(example[-1],example[1],example[2],now=NOW-50)

def test_rogue_juror(example):
    example[-1]['attestations'][0]['juror']='forged'
    with pytest.raises(VerificationError,match='unrecognized'):run(example)

def test_no_float_canonicalization():
    with pytest.raises(VerificationError,match='unsupported'):canonical({'f':0.32})

def test_invalid_registry_role_count(example):
    example[1]['jurors'].pop('juror-c')
    with pytest.raises(VerificationError,match='exactly three'):run(example)

def test_relay_receipt_verify_and_tamper(example):
    relay=Ed25519PrivateKey.generate()
    pub=relay.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()
    signed=issue_relay_receipt(run(example),relay)
    assert verify_relay_receipt(signed,pub) is True
    signed['evaluation']['state']='QUORUM_APPROVED_REVOKED'
    with pytest.raises(VerificationError,match='INVALID_RELAY_SIGNATURE'):verify_relay_receipt(signed,pub)

def test_explicit_policy_mismatch(example):
    example[-1]['policy_sha256']='sha256:'+'c'*64
    with pytest.raises(VerificationError,match='policy mismatch'):run(example)

def test_reject_overlong_ttl_even_signed(example):
    a=example[-2]('juror-a');a['expires_at']=NOW+601
    a['signature_hex']=example[0]['juror-a'].sign(signing_bytes({k:v for k,v in a.items() if k!='signature_hex'})).hex()
    example[-1]['attestations'][0]=a
    with pytest.raises(VerificationError,match='overlong'):run(example)

