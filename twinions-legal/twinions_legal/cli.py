"""Command line for local legal evidence organization. No automatic filing."""
from __future__ import annotations
import argparse, json, secrets
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from .ledger import CaseBook, canonical
from .crypto import sign_demo, verify_receipt
from .arbiter import compare_claims
from .z3gate import check_workflow_constraints


def format_status(book:CaseBook,cid:str)->dict:
    book._ensure(cid)
    # Validate the full journal BEFORE parsing its events. A corrupted/malformed
    # event must never crash the UI into falsely reporting healthy evidence.
    audit=book.verify_log()
    if not audit['valid']:
        return {'case_id':cid,'outcome':'AUDIT_CHAIN_INVALID',
                'filing_authorization':'NOT_GRANTED',
                'legal_merits_verdict':'NOT_DETERMINED',
                'journal_check':audit,'gate_states':[],
                'missing_gates':[],'undefined_gates':[],
                'reasons':['AUDIT_CHAIN_INVALID']}
    data=book.status(cid)
    data['journal_check']=audit
    states=data['gate_states']
    gate=check_workflow_constraints(
        all(s['definition_source']=='user_supplied' for s in states),
        all(s['status']=='EVIDENCE_ATTACHED' for s in states),
        'NOTICE_EVIDENCE' in {e['action'] for e in book.audit_events(cid)},
        'REPLY_EVIDENCE' in {e['action'] for e in book.audit_events(cid)},
        'COUNSEL_REVIEW_EVIDENCE' in {e['action'] for e in book.audit_events(cid)})
    data['workflow_z3']=gate
    return data


def demo(folder:Path)->dict:
    folder.mkdir(parents=True,exist_ok=True)
    book=CaseBook(folder/'synthetic_case.db')
    try:
        book.create('SYNTHETIC-001')
        document=folder/'synthetic_docket.txt'
        document.write_text('SYNTHETIC DEMONSTRATION ONLY. This is not a docket or certified court document.\n')
        h=book.add_evidence('SYNTHETIC-001',document,'synthetic docket marker')
        book.set_gate('SYNTHETIC-001',1,'EVIDENCE_ATTACHED',h)
        book.set_gate('SYNTHETIC-001',5,'MISSING')
        book.set_gate('SYNTHETIC-001',8,'CONTESTED',h)
        book.record('SYNTHETIC-001','NOTICE_EVIDENCE',h,'synthetic user label')
        status=format_status(book,'SYNTHETIC-001')
        priv=Ed25519PrivateKey.generate()
        public_hex=priv.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()
        signed=sign_demo(status,priv)
        assert verify_receipt(signed,public_hex)
        (folder/'synthetic_receipt.json').write_bytes(canonical(signed)+b'\n')
        (folder/'demo_public_key_hex.txt').write_text(public_hex+'\n')
        (folder/'synthetic_status.json').write_bytes(canonical(status)+b'\n')
        return {'local_demo':'PASS','software_signature':'PASS',
                'journal_check':status['journal_check']['valid'],
                'workflow_z3':status['workflow_z3'],
                'result':status['outcome'],'physical_hardware':'NOT_CONNECTED',
                'legal_filing_authority':'NONE'}
    finally:book.close()


def main(argv=None):
    parser=argparse.ArgumentParser(prog='twinions-legal',description='iNNOVULIS evidence organization, NOT legal adjudication')
    sub=parser.add_subparsers(dest='action',required=True)
    for action in ('create','attach','gate','record','status','log-check','receipt-demo','model-compare','cpp-export','report','demo','serve'):
        sub.add_parser(action)
    # use parse_known_args so subcommands remain simple and explicit.
    p=sub.choices['create'];p.add_argument('--db',required=True);p.add_argument('--case',required=True)
    p=sub.choices['attach'];p.add_argument('--db',required=True);p.add_argument('--case',required=True);p.add_argument('--file',required=True);p.add_argument('--label',required=True)
    p=sub.choices['gate'];p.add_argument('--db',required=True);p.add_argument('--case',required=True);p.add_argument('--number',type=int,required=True);p.add_argument('--status',required=True);p.add_argument('--evidence-hash')
    p=sub.choices['record'];p.add_argument('--db',required=True);p.add_argument('--case',required=True);p.add_argument('--kind',required=True);p.add_argument('--evidence-hash',required=True);p.add_argument('--actor-label',required=True)
    p=sub.choices['status'];p.add_argument('--db',required=True);p.add_argument('--case',required=True)
    p=sub.choices['log-check'];p.add_argument('--db',required=True)
    p=sub.choices['receipt-demo'];p.add_argument('--db',required=True);p.add_argument('--case',required=True);p.add_argument('--out',required=True)
    p=sub.choices['model-compare'];p.add_argument('--input',required=True)
    p=sub.choices['cpp-export'];p.add_argument('--db',required=True);p.add_argument('--case',required=True);p.add_argument('--out',required=True)
    p=sub.choices['report'];p.add_argument('--db',required=True);p.add_argument('--case',required=True);p.add_argument('--out',required=True)
    p=sub.choices['demo'];p.add_argument('--out',required=True)
    p=sub.choices['serve'];p.add_argument('--db',required=True);p.add_argument('--port',type=int,default=8776)
    args=parser.parse_args(argv)
    if args.action=='demo':value=demo(Path(args.out))
    elif args.action=='model-compare':value=compare_claims(json.loads(Path(args.input).read_text()))
    elif args.action=='serve':
        from .web import run
        run(args.db,args.port);return
    else:
        book=CaseBook(args.db)
        try:
            if args.action=='create':book.create(args.case);value={'created':args.case}
            elif args.action=='attach':value={'sha256':book.add_evidence(args.case,args.file,args.label)}
            elif args.action=='gate':book.set_gate(args.case,args.number,args.status,args.evidence_hash);value={'set_gate':args.number}
            elif args.action=='record':book.record(args.case,args.kind,args.evidence_hash,args.actor_label);value={'recorded':args.kind}
            elif args.action=='status':value=format_status(book,args.case)
            elif args.action=='log-check':value=book.verify_log()
            elif args.action=='cpp-export':
                snapshot=format_status(book,args.case)
                dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_text(''.join(f"{g['gate']}\t{g['status']}\t{'supplied' if g['definition_source']=='user_supplied' else 'undefined'}\t{g['evidence_hash'] or '-'}\n" for g in snapshot['gate_states']))
                value={'host_manifest':str(dest),'hardware_execution':False,'legal_merits':'NOT_DETERMINED'}
            elif args.action=='report':
                from .report import printable_report
                value={'html_preview':str(printable_report(book,args.case,Path(args.out))),
                       'not_certified_for_filing':True,'physical_printer_connected':False}
            elif args.action=='receipt-demo':
                snapshot=format_status(book,args.case)
                private=Ed25519PrivateKey.generate()
                pub=private.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()
                receipt=sign_demo(snapshot,private)
                assert verify_receipt(receipt,pub)
                dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(canonical(receipt)+b'\n')
                (dest.parent/(dest.stem+'_public_hex.txt')).write_text(pub+'\n')
                value={'demo_receipt_file':str(dest),'software_key_only':True,'legal_filing_authority':'NONE'}
        finally:book.close()
    print(json.dumps(value,indent=2,sort_keys=True))

if __name__=='__main__': main()
