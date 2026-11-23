import json
from pathlib import Path
from epu.core import VerifierTrust, verify_epu, Reject


def run():
    allv=json.loads(Path('build/test_vectors.json').read_text())
    tr=VerifierTrust(**allv['trusted_demo_config'])
    for name,v in allv['positive'].items():
        r=verify_epu(v['registration'],v['calibration'],v['execution'],v['allocation'],v['artifacts'],tr)
        expected={'METERED_SOFTWARE_FIXTURE':'METERED','EXPIRED_SOFTWARE_FIXTURE':'METERED_STALE','NOT_MEASURED':'NOT_MEASURED'}[name]
        assert r['effective_consumption_status']==expected and not r['billing_eligible'],name
        print('PASS',name,r['effective_consumption_status'],'BILLING_BLOCKED')
    for name,v in allv['negative'].items():
        try:
            verify_epu(v['registration'],v['calibration'],v['execution'],v['allocation'],v['artifacts'],tr)
        except Reject as e:
            assert e.code==allv['expected_negative_codes'][name],(name,e.code)
            print('PASS rejected',name,e.code)
        else:
            raise AssertionError('FAIL accepted negative vector '+name)
    print('EPU_CROSS_LANGUAGE_SIGNED_VECTORS_PYTHON_PASS')

if __name__=='__main__':run()
