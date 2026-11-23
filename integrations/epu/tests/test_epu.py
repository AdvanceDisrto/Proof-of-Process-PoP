import copy
import pytest
from epu.core import *
from .fixtures import make_case, signed_execution_modified, allocation, METER_SK, JOB, START


def expect(code, callable_):
    with pytest.raises(Reject) as caught:callable_()
    assert caught.value.code==code


def test_baseline_classification_is_simulation_not_physical():
    reg,cal,ex,alloc,art,tr=make_case()
    v=verify_epu(reg,cal,ex,alloc,art,tr)
    assert v['effective_consumption_status']=='METERED'
    assert v['joules_integrated']=='0.420000000'
    assert not v['billing_eligible'] and not v['physical_ground_truth_verified']
    assert v['cih_status']==PENDING


def test_t1_self_report_not_metered():
    reg,cal,ex,alloc,art,tr=make_case(lab_accreditation='SELF_REPORTED')
    expect('T1_T3_NOT_MEASURED_REQUIRED',lambda: verify_epu(reg,cal,ex,alloc,art,tr))
    ex2=copy.deepcopy(ex);ex2['attribution_method']='ESTIMATED_FROM_UTIL';ex2['consumption']={'status':'NOT_MEASURED','joules':None};ex2=sign(ex2,METER_SK)
    r=verify_epu(reg,cal,ex2,alloc,art,tr)
    assert r['effective_consumption_status']=='NOT_MEASURED'


def test_t2_expiry_downgrade():
    reg,cal,ex,alloc,art,tr=make_case(expired=True)
    assert verify_epu(reg,cal,ex,alloc,art,tr)['effective_consumption_status']=='METERED_STALE'
    ex2=copy.deepcopy(ex);ex2['consumption']['status']='METERED';ex2=sign(ex2,METER_SK)
    expect('T2_CALIBRATION_STATE_MISMATCH',lambda: verify_epu(reg,cal,ex2,alloc,art,tr))


def test_t3_estimate_not_metered():
    reg,cal,ex,alloc,art,tr=make_case()
    ex['attribution_method']='ESTIMATED_FROM_UTIL';ex=sign(ex,METER_SK)
    expect('T1_T3_NOT_MEASURED_REQUIRED',lambda: verify_epu(reg,cal,ex,alloc,art,tr))
    ex['consumption']={'status':'NOT_MEASURED','joules':None};ex=sign(ex,METER_SK)
    assert verify_epu(reg,cal,ex,alloc,art,tr)['effective_consumption_status']=='NOT_MEASURED'


def test_t4_differential_requires_baseline_and_uncertainty():
    reg,cal,ex,alloc,art,tr=make_case(method='DIFFERENTIAL')
    assert verify_epu(reg,cal,ex,alloc,art,tr)['joules_integrated']=='0.378000000'
    del ex['baseline'];ex=sign(ex,METER_SK)
    expect('T4_DIFFERENTIAL_BASELINE_REQUIRED',lambda: verify_epu(reg,cal,ex,alloc,art,tr))


def test_t5_job_replay():
    reg,cal,ex,alloc,art,tr=make_case()
    expect('T5_JOB_REPLAY',lambda: verify_epu(reg,cal,ex,alloc,art,VerifierTrust('JOB_B',tr.job_start_ts,tr.meter_pubkey,tr.lab_pubkey,tr.expected_meter_id,tr.allocation_policy)))
    ex['job_id']='JOB_B';expect('SIGNATURE_INVALID',lambda: verify_epu(reg,cal,ex,alloc,art,tr))


def test_t6_raw_samples_must_resolve_and_rehash():
    reg,cal,ex,alloc,art,tr=make_case()
    expect('T6_RAW_SAMPLES_UNRECOVERABLE',lambda: verify_epu(reg,cal,ex,alloc,{},tr))
    broken=copy.deepcopy(art)
    k=next(iter(broken));broken[k]['samples'][0][1]='1300'
    expect('T6_RAW_SAMPLES_TAMPERED',lambda: verify_epu(reg,cal,ex,alloc,broken,tr))


def test_no_claimed_status():
    reg,cal,ex,alloc,art,tr=make_case()
    ex['consumption']['status']='CLAIMED';ex=sign(ex,METER_SK)
    expect('CLAIMED_STATUS_FORBIDDEN',lambda: verify_epu(reg,cal,ex,alloc,art,tr))


def test_unsigned_allocation_hash_strings_are_not_proofs():
    reg,cal,ex,alloc,art,tr=make_case()
    alloc['proof_hash']=sha(b'i swear this was checked')
    expect('ALLOCATION_EVIDENCE_HASH_MISMATCH',lambda:verify_epu(reg,cal,ex,alloc,art,tr))


def test_domain_bound_must_match_out_of_band_policy():
    reg,cal,ex,alloc,art,tr=make_case()
    alloc['bounded_domain_kw']=[0,50]
    expect('POLICY_BOUND_MISMATCH',lambda:verify_epu(reg,cal,ex,alloc,art,tr))


def test_priority_violation():
    reg,cal,ex,alloc,art,tr=make_case()
    alloc['allocated_kw']=[8,4,3]
    expect('PRIORITY_ALLOCATION_MISMATCH',lambda:verify_epu(reg,cal,ex,alloc,art,tr))


def test_meter_replay_or_wrong_trust_root():
    reg,cal,ex,alloc,art,tr=make_case()
    wrong=VerifierTrust(tr.job_id,tr.job_start_ts,'00'*32,tr.lab_pubkey,tr.expected_meter_id,tr.allocation_policy)
    expect('UNTRUSTED_SIGNER',lambda:verify_epu(reg,cal,ex,alloc,art,wrong))


def test_calibration_certificate_tamper():
    reg,cal,ex,alloc,art,tr=make_case()
    cal['calibrated_at']='2026-11-22T00:00:00Z'
    expect('SIGNATURE_INVALID',lambda:verify_epu(reg,cal,ex,alloc,art,tr))


def test_joules_recomputed_not_trusted():
    reg,cal,ex,alloc,art,tr=make_case()
    ex['measurement']['joules_integrated']='0.023000000';ex=sign(ex,METER_SK)
    expect('MEASURED_JOULES_RECOMPUTE_FAILED',lambda:verify_epu(reg,cal,ex,alloc,art,tr))


def test_rapl_scoping_is_mandatory():
    reg,cal,ex,alloc,art,tr=make_case(method='RAPL_PER_JOB')
    assert verify_epu(reg,cal,ex,alloc,art,tr)['effective_consumption_status']=='METERED'
    ex.pop('job_scope_hash');ex=sign(ex,METER_SK)
    expect('RAPL_SCOPE_NOT_VERIFIED',lambda:verify_epu(reg,cal,ex,alloc,art,tr))


def test_no_circuit_claim_without_dedication():
    reg,cal,ex,alloc,art,tr=make_case()
    reg['dedicated_job_circuit']=False;reg=sign(reg,METER_SK)
    expect('CIRCUIT_NOT_DEDICATED',lambda:verify_epu(reg,cal,ex,alloc,art,tr))


def test_wrong_duration():
    reg,cal,ex,alloc,art,tr=make_case()
    ex['window']['duration_ms']=421;ex=sign(ex,METER_SK)
    expect('DURATION_MISMATCH',lambda:verify_epu(reg,cal,ex,alloc,art,tr))


def pi_tau_fixture(pi='101100',tick=42,nonce='verifier-challenge-1',output='101000'):
    return sign({'protocol':'ITM-PI-TAU-V1','pi':pi,'tau':tick,'nonce':nonce,'output_pi':output,
                'delta':[int(a!=b) for a,b in zip(pi,output)]},METER_SK)


def test_pi_tau_1_honest():
    receipt=pi_tau_fixture();used=set()
    assert verify_pi_tau(receipt,ExpectedPiTau('101100',42,'verifier-challenge-1'),bytes(METER_SK.verify_key).hex(),used)=='VERIFIED_CONTRACT_AND_DELTA'


def test_pi_tau_2_one_bit_flip():
    r=pi_tau_fixture();assert r['delta']==[0,0,0,1,0,0]
    # A delta altered after signing fails crypto; a re-signed false delta fails recomputation.
    r['delta']=[0]*6;r=sign(r,METER_SK)
    expect('BIT_DELTA_MISMATCH',lambda:verify_pi_tau(r,ExpectedPiTau('101100',42,'verifier-challenge-1'),bytes(METER_SK.verify_key).hex(),set()))


def test_pi_tau_3_rogue_prover_pi_rejected():
    r=pi_tau_fixture(pi='000000',output='000000')
    expect('PI_CONTRACT_MISMATCH',lambda:verify_pi_tau(r,ExpectedPiTau('101100',42,'verifier-challenge-1'),bytes(METER_SK.verify_key).hex(),set()))


def test_pi_tau_4_rogue_tick_rejected():
    r=pi_tau_fixture(tick=41)
    expect('TAU_CHALLENGE_MISMATCH',lambda:verify_pi_tau(r,ExpectedPiTau('101100',42,'verifier-challenge-1'),bytes(METER_SK.verify_key).hex(),set()))


def test_pi_tau_5_replay():
    r=pi_tau_fixture();used=set();ctx=ExpectedPiTau('101100',42,'verifier-challenge-1')
    verify_pi_tau(r,ctx,bytes(METER_SK.verify_key).hex(),used)
    expect('REPLAYED_CHALLENGE',lambda:verify_pi_tau(r,ctx,bytes(METER_SK.verify_key).hex(),used))


def test_pi_tau_6_ops_provisioning_failure_not_attack():
    r=pi_tau_fixture()
    expect('CONFIG_MISSING_PI_TAU',lambda:verify_pi_tau(r,None,bytes(METER_SK.verify_key).hex(),set()))
    expect('PI_CONTRACT_MISMATCH',lambda:verify_pi_tau(r,ExpectedPiTau('000000',42,'verifier-challenge-1'),bytes(METER_SK.verify_key).hex(),set()))


def test_schema_validates_baseline_and_blocks_claimed():
    import json
    from pathlib import Path
    from jsonschema import Draft202012Validator
    from generate_vectors import main
    main()
    vectors=json.loads(Path('build/test_vectors.json').read_text())
    schema=json.loads(Path('energy_receipt.schema.json').read_text())
    validator=Draft202012Validator(schema)
    assert not list(validator.iter_errors(vectors['positive']['METERED_SOFTWARE_FIXTURE']))
    assert list(validator.iter_errors(vectors['negative']['EXTRA_CLAIMED']))
    assert list(validator.iter_errors(vectors['negative']['T4_DIFFERENTIAL_NO_BASELINE']))
