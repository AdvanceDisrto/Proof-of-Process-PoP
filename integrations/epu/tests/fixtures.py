import copy
from epu.core import *

METER_SK=SigningKey(bytes([0x42])*32)  # PUBLIC SOFTWARE TEST KEY, NOT HARDWARE ROOT
LAB_SK=SigningKey(bytes([0x43])*32)
JOB='JOB_A_2026_11_23'
START='2026-11-23T00:00:00Z'
END='2026-11-23T00:00:00.420Z'
EPU_ID='sha256:'+('a4'*32)
TRUSTED_POLICY={'bounded_domain_kw':[0,30],'available_kw':15,'num_jobs':3}


def allocation():
    req=[8,5,7]; actual=[8,5,2]
    proof={'method':'Z3_FIXED_ASSIGNMENT_COUNTEREXAMPLE_UNSAT_V1','policy':TRUSTED_POLICY,'requests_kw':req,'allocated_kw':actual}
    return {'status':'VERIFIED','bounded_domain_kw':[0,30], 'available_kw':15,'requests_kw':req,'allocated_kw':actual,
        'constraints_hash':sha(jcs(TRUSTED_POLICY)),'proof_hash':sha(jcs(proof))}


def make_case(method='DEDICATED_CIRCUIT',expired=False,lab_accreditation='ISO17025'):
    raw={'unit':'mW','samples':[[0,'1000'],[210,'1000'],[420,'1000']]}
    rawhash=sample_store_hash(raw)
    samples={rawhash:raw}
    cert=sign({'protocol':'ITM-EPU-CALIBRATION-v1','epu_id':EPU_ID,
        'calibrated_at':'2025-01-01T00:00:00Z' if expired else '2026-10-01T00:00:00Z',
        'interval_days':365,'lab_accreditation':lab_accreditation,'cert_id':'TEST_FIXTURE_CERT'},LAB_SK)
    certhash=sha(jcs({k:v for k,v in cert.items() if k!='signature'}))
    reg=sign({'protocol':'ITM-EPU-REGISTRATION-v1','epu_id':EPU_ID,
        'meter_class':'SMART_PDU','manufacturer':'SYNTHETIC_TEST_ONLY',
        'serial':'TEST-DO-NOT-DEPLOY','accuracy_spec_pct':'1.0','sample_rate_hz':5,
        'dedicated_job_circuit':True,'calibration':{'certificate_hash':certhash}},METER_SK)
    value='0.420000000'
    base=None
    if method=='DIFFERENTIAL':
        idle={'unit':'mW','samples':[[0,'100'],[210,'100'],[420,'100']]}
        baselinehash=sample_store_hash(idle)
        samples[baselinehash]=idle
        base={'baseline_samples_hash':baselinehash,'joules_idle_per_ms':'0.000100000'}
        value='0.378000000'
    cons={'status':'METERED_STALE' if expired else 'METERED','joules':value}
    execution={'protocol':'ITM-EPU-EXECUTION-v1','job_id':JOB,'epu_id':EPU_ID,
        'attribution_method':method,'window':{'start_ts':START,'end_ts':END,'duration_ms':420},
        'measurement':{'joules_integrated':value,'sample_count':3,'sample_rate_hz':5,'raw_samples_hash':rawhash},
        'uncertainty':{'accuracy_pct':'1.0','attribution_error_pct':'10.0' if method=='DIFFERENTIAL' else '1.0','combined_joules_1sigma':'0.080' if method=='DIFFERENTIAL' else '0.005'},
        'consumption':cons,'derivation':{'status':'NONE'}}
    if base: execution['baseline']=base
    if method=='RAPL_PER_JOB':execution['job_scope_hash']=sha(b'trusted-cgroup-scope')
    execution=sign(execution,METER_SK)
    trust=VerifierTrust(JOB,START,bytes(METER_SK.verify_key).hex(),bytes(LAB_SK.verify_key).hex(),EPU_ID,TRUSTED_POLICY,
        expected_scope_hash=sha(b'trusted-cgroup-scope'))
    return reg,cert,execution,allocation(),samples,trust


def signed_execution_modified(execution,**updates):
    v=copy.deepcopy(execution)
    for k,value in updates.items():v[k]=value
    return sign(v,METER_SK)
