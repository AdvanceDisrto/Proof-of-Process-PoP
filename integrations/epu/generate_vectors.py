"""Deterministic, PUBLIC-KEY software-only fixtures; no authentic meter evidence."""
import copy
import json
from pathlib import Path
from epu.core import sign, PENDING, sha, sample_store_hash
from tests.fixtures import make_case, METER_SK, LAB_SK, JOB, START, EPU_ID, TRUSTED_POLICY


def dump(v):
    return json.dumps(v,indent=2,ensure_ascii=False,sort_keys=True)+'\n'


def main():
    reg,cal,ex,alloc,art,trust=make_case()
    vector={'registration':reg,'calibration':cal,'execution':ex,'allocation':alloc,'artifacts':art}
    vector_stale={}
    rg,c,e,a,arts,_=make_case(expired=True)
    vector_stale={'registration':rg,'calibration':c,'execution':e,'allocation':a,'artifacts':arts}
    notmetered=copy.deepcopy(vector)
    notmetered['calibration']=None
    notmetered['execution']['attribution_method']='ESTIMATED_FROM_UTIL'
    notmetered['execution']['consumption']={'status':'NOT_MEASURED','joules':None}
    notmetered['execution']['measurement']={}
    notmetered['execution']=sign(notmetered['execution'],METER_SK)
    negative={}
    t=copy.deepcopy(vector);t['calibration']['lab_accreditation']='SELF_REPORTED';t['calibration']=sign(t['calibration'],LAB_SK)
    # Must rebind registration to new certificate; this is a *fully signed attack fixture*.
    t['registration']['calibration']['certificate_hash']=sha(__import__('epu.core',fromlist=['jcs']).jcs({k:v for k,v in t['calibration'].items() if k!='signature'}))
    t['registration']=sign(t['registration'],METER_SK)
    negative['T1_SELF_REPORTED']=t
    t=copy.deepcopy(vector_stale);t['execution']['consumption']['status']='METERED';t['execution']=sign(t['execution'],METER_SK)
    negative['T2_EXPIRED_BUT_CLAIMED_CURRENT']=t
    t=copy.deepcopy(vector);t['execution']['attribution_method']='ESTIMATED_FROM_UTIL';t['execution']=sign(t['execution'],METER_SK)
    negative['T3_ESTIMATED_AS_METERED']=t
    t=copy.deepcopy(vector);t['execution']['attribution_method']='DIFFERENTIAL';t['execution']=sign(t['execution'],METER_SK)
    negative['T4_DIFFERENTIAL_NO_BASELINE']=t
    t=copy.deepcopy(vector);t['execution']['job_id']='JOB_B_REPLAY';t['execution']=sign(t['execution'],METER_SK)
    negative['T5_WRONG_JOB']=t
    t=copy.deepcopy(vector);t['artifacts']={}
    negative['T6_NO_RAW_SAMPLES']=t
    t=copy.deepcopy(vector);t['execution']['consumption']['status']='CLAIMED';t['execution']=sign(t['execution'],METER_SK)
    negative['EXTRA_CLAIMED']=t
    t=copy.deepcopy(vector);t['execution']['measurement']['joules_integrated']='0.023000000';t['execution']=sign(t['execution'],METER_SK)
    negative['EXTRA_FAKE_JOULES']=t
    trusted_demo={'job_id':trust.job_id,'job_start_ts':trust.job_start_ts,'meter_pubkey':trust.meter_pubkey,'lab_pubkey':trust.lab_pubkey,'expected_meter_id':trust.expected_meter_id,'allocation_policy':TRUSTED_POLICY,'physically_inspected':False}
    out={'notice':'SYNTHETIC TEST FIXTURES ONLY — NO PHYSICAL METER OR CERTIFICATION VERIFIED',
        'cih_status':PENDING,'trusted_demo_config':trusted_demo,
        'positive':{'METERED_SOFTWARE_FIXTURE':vector,'EXPIRED_SOFTWARE_FIXTURE':vector_stale,'NOT_MEASURED':notmetered},
        'negative':negative,'expected_negative_codes':{
          'T1_SELF_REPORTED':'T1_T3_NOT_MEASURED_REQUIRED','T2_EXPIRED_BUT_CLAIMED_CURRENT':'T2_CALIBRATION_STATE_MISMATCH',
          'T3_ESTIMATED_AS_METERED':'T1_T3_NOT_MEASURED_REQUIRED','T4_DIFFERENTIAL_NO_BASELINE':'T4_DIFFERENTIAL_BASELINE_REQUIRED',
          'T5_WRONG_JOB':'T5_JOB_REPLAY','T6_NO_RAW_SAMPLES':'T6_RAW_SAMPLES_UNRECOVERABLE',
          'EXTRA_CLAIMED':'CLAIMED_STATUS_FORBIDDEN','EXTRA_FAKE_JOULES':'MEASURED_JOULES_RECOMPUTE_FAILED'}}
    Path('build').mkdir(exist_ok=True)
    Path('build/test_vectors.json').write_text(dump(out),encoding='utf-8')
    print('Generated PUBLIC synthetic signed vectors; NONE are physical meter claims')

if __name__=='__main__':main()
