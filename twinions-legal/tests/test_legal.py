import copy, json, os, subprocess, sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from twinions_legal import CaseBook,GATES,evaluate,compare_claims,sign_demo,verify_receipt
from twinions_legal.cli import demo,format_status
from twinions_legal.z3gate import check_workflow_constraints
from twinions_legal.web import app_for

@pytest.fixture
def book(tmp_path):
    b=CaseBook(tmp_path/'cases.sqlite')
    b.create('TEST-2026')
    yield b
    b.close()

def test_gate_template_is_exactly_18_and_unknown_names_are_not_invented():
    assert len(GATES)==18
    assert [x['gate'] for x in GATES]==list(range(1,19))
    assert {x['gate'] for x in GATES if x['definition_source']=='user_supplied'}=={1,2,5,7,8,14,18}
    assert len([x for x in GATES if x['definition_source']=='not_provided'])==11

@pytest.mark.parametrize('gate,name', [(1,'Intake'),(2,'Conflict check'),(5,'Favorable termination'),
    (7,'Lack of probable cause'),(8,'Malice / improper purpose'),(14,'Due process notice'),
    (18,'Due process reply logged')])
def test_known_names(gate,name):assert GATES[gate-1]['name']==name

def test_empty_case_failclosed(book):
    r=book.status('TEST-2026')
    assert r['outcome']=='EVIDENCE_REVIEW_REQUIRED'
    assert r['undefined_gates']==[3,4,6,9,10,11,12,13,15,16,17]
    assert r['missing_gates']==list(range(1,19))
    assert r['filing_authorization']=='NOT_GRANTED'
    assert book.verify_log()['valid'] is True

def test_case_id_validation(tmp_path):
    b=CaseBook(tmp_path/'x.db')
    try:
        for bad in ('../escape','x/y','', 'x'*65, 'AB\nC'):
            with pytest.raises(ValueError):b.create(bad)
    finally:b.close()

def test_duplicate_case_blocked(book):
    with pytest.raises(Exception):book.create('TEST-2026')

def test_no_evidence_cannot_claim_attached(book):
    with pytest.raises(ValueError):book.set_gate('TEST-2026',5,'EVIDENCE_ATTACHED','a'*64)

def test_no_unbound_hash(book):
    with pytest.raises(ValueError):book.set_gate('TEST-2026',1,'MISSING','a'*64)

@pytest.mark.parametrize('status',['EVIDENCE_ATTACHED','CONTESTED'])
def test_real_hash_and_gate(book,tmp_path,status):
    src=tmp_path/'synthetic_document.txt';src.write_bytes(b'SYNTHETIC EVIDENCE ONLY')
    h=book.add_evidence('TEST-2026',src,'mock docket')
    assert len(h)==64
    book.set_gate('TEST-2026',5,status,h)
    assert book.status('TEST-2026')['gate_states'][4]['status']==status
    assert book.verify_log()['valid']

def test_symlink_blocked(book,tmp_path):
    t=tmp_path/'t';t.write_text('test');link=tmp_path/'ln';link.symlink_to(t)
    with pytest.raises(ValueError):book.add_evidence('TEST-2026',link,'alias')

@pytest.mark.parametrize('bad',['','A\nB','x'*101])
def test_invalid_evidence_label(book,tmp_path,bad):
    t=tmp_path/'t';t.write_text('a')
    with pytest.raises(ValueError):book.add_evidence('TEST-2026',t,bad)

def test_cannot_record_notice_without_hashed_evidence(book):
    with pytest.raises(ValueError):book.record('TEST-2026','NOTICE_EVIDENCE','a'*64,'operator')

def test_notice_not_proof_of_delivery(book,tmp_path):
    t=tmp_path/'notice';t.write_text('synthetic');h=book.add_evidence('TEST-2026',t,'notice marker')
    book.record('TEST-2026','NOTICE_EVIDENCE',h,'operator label')
    s=book.status('TEST-2026')
    assert 'NOTICE_DOCUMENTATION_MISSING' not in s['reasons']
    assert 'GATE_DEFINITIONS_INCOMPLETE' in s['reasons']
    assert s['filing_authorization']=='NOT_GRANTED'

def test_conflicted_model_assertions_are_not_truth(book):
    r=compare_claims([{'source':'model-A','question_id':'Q1','answer':'benign'},
                      {'source':'model-B','question_id':'Q1','answer':'malignant'}])
    assert r['status']=='CONFLICT_DETECTED' and r['factual_verdict']=='UNDETERMINED'

def test_model_agreement_not_truth():
    r=compare_claims([{'source':'a','question_id':'Q','answer':'same'},
                      {'source':'b','question_id':'Q','answer':'SAME'}])
    assert r['status']=='NO_TEXTUAL_CONFLICT_DETECTED'
    assert r['factual_verdict']=='UNDETERMINED'

@pytest.mark.parametrize('bad',[[],[{}],[{'source':'a','question_id':'q','answer':'x','unsafe':'y'}]*2])
def test_model_bad_inputs_rejected(bad):
    with pytest.raises(ValueError):compare_claims(bad)

def test_signed_receipt_pinned_key(book):
    a=Ed25519PrivateKey.generate();b=Ed25519PrivateKey.generate()
    apub=a.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()
    bpub=b.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()
    receipt=sign_demo(book.status('TEST-2026'),a)
    assert verify_receipt(receipt,apub)
    assert not verify_receipt(receipt,bpub)
    altered=copy.deepcopy(receipt);altered['signed']['snapshot']['filing_authorization']='CERTIFIED'
    assert not verify_receipt(altered,apub)

def test_swapping_signature_blocked(book):
    priv=Ed25519PrivateKey.generate();pk=priv.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()
    x=sign_demo(book.status('TEST-2026'),priv)
    x['signature_b64']='?'*86
    assert not verify_receipt(x,pk)

def test_ledger_hash_tamper_detected(book):
    book.db.execute("UPDATE audit SET event_hash=? WHERE seq=1",('f'*64,));book.db.commit()
    assert book.verify_log()['valid'] is False

def test_ledger_event_tamper_detected(book):
    book.db.execute("UPDATE audit SET event_json=? WHERE seq=1",('{"foo":"bar"}',));book.db.commit()
    assert not book.verify_log()['valid']
    assert format_status(book,'TEST-2026')['outcome']=='AUDIT_CHAIN_INVALID'

def test_ledger_durable_reopen(tmp_path):
    p=tmp_path/'durable.db';b=CaseBook(p);b.create('X');tip=b.tip();b.close()
    b=CaseBook(p);assert b.verify_log()['valid'];assert b.tip()==tip;b.close()

def test_z3_narrow_workflow_sat():
    r=check_workflow_constraints(True,True,True,True,True)
    assert r['status']=='SAT' and r['release_gate']=='DRAFT_FOR_COUNSEL_ONLY'
    assert 'legal truth' in r['does_not_prove']

@pytest.mark.parametrize('which',range(5))
def test_z3_denies_missing_boolean(which):
    v=[True]*5;v[which]=False
    r=check_workflow_constraints(*v)
    assert r['status']=='UNSAT' and r['release_gate']=='BLOCKED'

def test_z3_requires_boolean():
    with pytest.raises(ValueError):check_workflow_constraints(1,True,True,True,True)

def test_demo_is_synthetic_and_verifiable(tmp_path):
    r=demo(tmp_path/'demo')
    assert r['local_demo']=='PASS' and r['result']=='EVIDENCE_REVIEW_REQUIRED'
    assert r['physical_hardware']=='NOT_CONNECTED'
    case=json.loads((tmp_path/'demo'/'synthetic_receipt.json').read_text())
    pub=(tmp_path/'demo'/'demo_public_key_hex.txt').read_text().strip()
    assert verify_receipt(case,pub)

def test_web_requires_token(book):
    with pytest.raises(ValueError):app_for(book.path,'short')

def test_web_api_unauthenticated_blocked(book):
    client=TestClient(app_for(book.path,'A'*32))
    r=client.get('/api/cases/TEST-2026')
    assert r.status_code==403
    r=client.get('/api/cases/TEST-2026',headers={'X-Operator-Token':'A'*32})
    assert r.status_code==200 and r.json()['filing_authorization']=='NOT_GRANTED'
    assert r.headers['Cache-Control']=='no-store'
    assert r.headers['Content-Security-Policy'].startswith("default-src 'none'")

def test_web_no_file_upload_or_mutation(book):
    c=TestClient(app_for(book.path,'A'*32))
    assert c.post('/api/cases/TEST-2026').status_code==405
    assert c.get('/').status_code==200
    assert 'legal' in c.get('/').text.lower()

def test_counsel_not_a_license_verification(book,tmp_path):
    t=tmp_path/'review.txt';t.write_text('synthetic');h=book.add_evidence('TEST-2026',t,'review')
    for kind in ('NOTICE_EVIDENCE','REPLY_EVIDENCE','COUNSEL_REVIEW_EVIDENCE'):
        book.record('TEST-2026',kind,h,'operator entered label')
    r=book.status('TEST-2026')
    assert r['outcome']=='EVIDENCE_REVIEW_REQUIRED'
    assert r['filing_authorization']=='NOT_GRANTED'

def test_cpp_manifest_fails_closed(tmp_path,book):
    result=format_status(book,'TEST-2026')
    manifest=tmp_path/'gate.tsv'
    manifest.write_text(''.join(f"{g['gate']}\t{g['status']}\t{'supplied' if g['definition_source']=='user_supplied' else 'undefined'}\t{g['evidence_hash'] or '-'}\n" for g in result['gate_states']))
    src=Path(__file__).resolve().parents[1]/'hardware/innovulis_istick.cpp'
    exe=tmp_path/'istick_host'
    subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-pedantic',str(src),'-o',str(exe)],check=True)
    good=subprocess.run([str(exe),str(manifest)],capture_output=True,text=True,check=True)
    assert json.loads(good.stdout)['filing_authority']=='NONE'
    broken=tmp_path/'broken.tsv';broken.write_text(manifest.read_text().replace('1\tNOT_REVIEWED','1\tPROVEN_TRUE'))
    bad=subprocess.run([str(exe),str(broken)],capture_output=True)
    assert bad.returncode!=0

def test_readiness_is_blocked(tmp_path):
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/'hardware'))
    from readiness import check
    result=check(root/'hardware/board_readiness.json')
    assert result['acceptance']=='BLOCKED_NO_FABRICABLE_PCB'
    assert 'mcu_or_i2c_host' in result['missing_prerequisites']
    assert not result['atecc_locked']
