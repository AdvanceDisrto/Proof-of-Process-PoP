#!/usr/bin/env python3
import base64
import copy
import hashlib
import json
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from brain_registry import build_dispatcher, _canon, _sha
from buddy_receipt_v2 import (SCHEMA,GENESIS, SignedBrainDispatcher,canon,check_receipt,
    validate_receipt,make_demo)

HERE = Path(__file__).resolve().parent


class SignedV2Tests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.signer = SignedBrainDispatcher(self.private)

    def test_preserve_legacy_v1_receipt_confidence(self):
        legacy = build_dispatcher().dispatch('add 40 and 2')
        self.assertEqual(legacy.schema,'bitwitness/brain/receipt/v1')
        self.assertEqual(legacy.confidence,1.0)
        self.assertEqual(legacy.receipt_hash,_sha(_canon({k:v for k,v in vars(legacy).items() if k!='receipt_hash'})))
        self.assertFalse('signature' in vars(legacy))

    def test_signed_v2_math_refusal_external(self):
        a=self.signer.dispatch('add 40 and 2')
        b=self.signer.dispatch('diagnose patient',forced='OracleHumanReview')
        c=self.signer.dispatch('external text',forced='Claude')
        self.assertEqual([x['gate_verdict'] for x in (a,b,c)],['ACCEPT','ACCEPT-REFUSAL','ACCEPT-REFUSAL'])
        self.assertEqual([x['kind'] for x in (a,b,c)],['head','oracle','external_llm'])
        self.assertEqual(b['prev_hash'],a['receipt_hash'])
        self.assertEqual(c['prev_hash'],b['receipt_hash'])
        self.assertTrue(self.signer.verify_chain()['ok'])
        for r in (a,b,c):
            self.assertTrue(check_receipt(r,self.signer.public_key))
            self.assertEqual(r['schema'],SCHEMA)
            self.assertNotIn('confidence',r)
        self.assertEqual(len(a['signature']),88)
        self.assertEqual(len(a['signer_pubkey']),44)

    def test_fake_claim_and_fake_signature_refuted(self):
        source=self.signer.dispatch('add 40 and 2')
        changed=copy.deepcopy(source)
        changed['claims']=['machine is certified']
        self.assertFalse(check_receipt(changed,self.signer.public_key))
        changed=copy.deepcopy(source)
        changed['signature']=base64.b64encode(b'\0'*64).decode('ascii')
        self.assertFalse(check_receipt(changed,self.signer.public_key))

    def test_untrusted_public_key_cannot_verify(self):
        source=self.signer.dispatch('add 40 and 2')
        other=SignedBrainDispatcher(Ed25519PrivateKey.generate())
        self.assertFalse(check_receipt(source,other.public_key))

    def test_schema_extra_field_and_legacy_version_rejected(self):
        source=self.signer.dispatch('add 40 and 2')
        changed=copy.deepcopy(source);changed['confidence']=1.0
        self.assertFalse(check_receipt(changed,self.signer.public_key))
        changed=copy.deepcopy(source);changed['schema']='bitwitness/brain/receipt/v1'
        self.assertFalse(check_receipt(changed,self.signer.public_key))

    def test_legacy_v1_append_refuses_tampered_tail(self):
        d=build_dispatcher()
        r=d.dispatch('add 40 and 2')
        r.claims.append('new fake claim')
        with self.assertRaisesRegex(ValueError, 'EXISTING_BRAIN_CHAIN_REFUTED'):
            d.dispatch('add 1 and 2')
        self.assertEqual(len(d.chain),1)

    def test_chain_fork_refused_before_signing(self):
        receipt=self.signer.dispatch('add 40 and 2')
        self.signer.chain[-1]['claims']=['tampered']
        with self.assertRaisesRegex(RuntimeError,'CHAIN_FORK_OR_TAMPER'):
            self.signer.dispatch('add 2 and 3')
        self.assertEqual(len(self.signer.chain),1)

    def test_timestamp_utc_ms_and_invalid_ts_rejected(self):
        a=self.signer.dispatch('add 40 and 2')
        self.assertRegex(a['ts'],r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')
        wrong=copy.deepcopy(a);wrong['ts']='2026-11-11 01:00:00'
        self.assertFalse(check_receipt(wrong,self.signer.public_key))

    def test_no_number_profile_and_surrogate_refuses(self):
        with self.assertRaisesRegex(ValueError,'PROHIBITS_NUMBERS'):
            canon({'confidence':0.5})
        with self.assertRaisesRegex(ValueError,'INVALID_UNICODE_SURROGATE'):
            canon({'claim':'\ud800'})

    def test_json_schema_matches_all_actual_v2(self):
        try: import jsonschema
        except ImportError: self.skipTest('Optional jsonschema package absent')
        schema=json.loads((HERE/'buddy_receipt_v2.schema.json').read_text(encoding='utf-8'))
        jsonschema.Draft202012Validator.check_schema(schema)
        for text in ['add 40 and 2','hello no route','compute 64-bit word']:
            r=self.signer.dispatch(text)
            jsonschema.validate(r,schema)
        wrong=self.signer.dispatch('add 10 and 5').copy();wrong['confidence']=0.9
        with self.assertRaises(jsonschema.ValidationError):jsonschema.validate(wrong,schema)

    def test_utf16_unicode_order_matches_js_vector(self):
        specimen={'\ue000':'private-use','😇':'astral-key','text':'café 日本語 🧾 \u2028\u2029 " \\ \t\n'}
        source=canon(specimen)
        self.assertLess(source.index('😇'.encode()),source.index('\ue000'.encode()))
        (HERE/'canonical-vectors.json').write_text(json.dumps({
            'unicode_data':specimen,'unicode_canon_sha256':hashlib.sha256(source).hexdigest(),
            'unicode_canon_b64':base64.b64encode(source).decode(),
            'million_char_sha256':hashlib.sha256(canon({'long':'x'*1_000_000})).hexdigest(),
        },ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':unittest.main(verbosity=2)
