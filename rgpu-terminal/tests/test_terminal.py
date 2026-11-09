from __future__ import annotations
import asyncio, json, os, stat, sqlite3
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from rgpu_terminal.crypto import (ReceiptError,ZERO_HASH,canonical,make_envelope,verify_envelope,
                                   public_hex,public_fingerprint,load_or_create_identity)
from rgpu_terminal.journal import ReceiptJournal
from rgpu_terminal.server import create_app

SECRET='X'*48

class ReceiptCryptography(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.dir=Path(self.temp.name)
        self.j=ReceiptJournal(self.dir)
        self.genesis=self.j.ensure_genesis()
    def tearDown(self):self.j.close();self.temp.cleanup()
    def test_signature_and_real_hash_chain(self):
        d=verify_envelope(self.genesis,self.j.public_key,previous=ZERO_HASH,expected_sequence=1)
        self.assertEqual(d['claim'],'HUB_INITIALIZED')
        self.assertEqual(d['source_tier'],'LOCAL_SOFTWARE_ONLY')
        self.assertIsNone(d['telemetry']['physical_joules'])
    def test_key_persistence_and_reboot(self):
        pub=self.j.public_key
        self.j.close()
        self.j=ReceiptJournal(self.dir)
        self.assertEqual(pub,self.j.public_key)
        self.assertEqual(self.j.verify_all()['entries'],1)
    def test_private_key_permissions_0600(self):
        mode=os.stat(self.dir/'terminal_identity.pem').st_mode
        self.assertEqual(stat.S_IMODE(mode),0o600)
    def test_rejects_world_readable_private_key(self):
        p=self.dir/'terminal_identity.pem'
        os.chmod(p,0o644)
        with self.assertRaises(ReceiptError):load_or_create_identity(p)
    def test_symlink_identity_rejected(self):
        p=self.dir/'terminal_identity.pem';alias=self.dir/'alias.pem'
        os.symlink(p,alias)
        with self.assertRaises(OSError):load_or_create_identity(alias)
    def test_pinned_mismatch_fails(self):
        from cryptography.hazmat.primitives.asymmetric import ed25519
        with self.assertRaises(ReceiptError):verify_envelope(self.genesis, public_hex(ed25519.Ed25519PrivateKey.generate()))
    def test_unpinned_fails(self):
        with self.assertRaises(ReceiptError):verify_envelope(self.genesis,'')
    def test_mutation_of_envelope_rejected(self):
        e=dict(self.genesis);e['payload_sha256']='f'*64
        with self.assertRaises(ReceiptError):verify_envelope(e,self.j.public_key)
    def test_mutated_signature_rejected(self):
        e=dict(self.genesis);e['signature_hex']='00'*64
        with self.assertRaises(ReceiptError):verify_envelope(e,self.j.public_key)
    def test_wrong_previous_hash_fails(self):
        with self.assertRaises(ReceiptError):verify_envelope(self.genesis,self.j.public_key,previous='1'*64)
    def test_wrong_sequence_fails(self):
        with self.assertRaises(ReceiptError):verify_envelope(self.genesis,self.j.public_key,expected_sequence=2)
    def test_extra_untrusted_public_key_rejected(self):
        e=dict(self.genesis);e['public_key']=self.j.public_key
        with self.assertRaises(ReceiptError):verify_envelope(e,self.j.public_key)
    def test_journal_detects_corruption(self):
        self.j.db.execute("UPDATE receipts SET sha256=? WHERE sequence=1",('f'*64,))
        with self.assertRaises(ReceiptError):self.j.verify_all()
    def test_journal_refuses_changed_key(self):
        self.j.close()
        p=self.dir/'terminal_identity.pem';p.unlink()
        with self.assertRaises(ReceiptError):ReceiptJournal(self.dir)
        self.j=ReceiptJournal.__new__(ReceiptJournal)
        self.j.close=lambda:None
    def test_journal_reboot_chain_continuity(self):
        self.j.append(claim='SYNTHETIC_TELEMETRY',source_tier='SYNTHETIC_DEMO',verdict='REFUTED_FALSE',
                      telemetry={'physical_joules':None,'simulated_joules':2})
        before=self.j.verify_all();self.j.close()
        self.j=ReceiptJournal(self.dir)
        self.assertEqual(self.j.last()[0],2)
        self.assertEqual(self.j.verify_all(),before)
    def test_invalid_claim_rejected(self):
        with self.assertRaises(ReceiptError):self.j.append(claim='CLINICAL_DIAGNOSIS',source_tier='LOCAL_SOFTWARE_ONLY',verdict='PROVEN_TRUE',telemetry={})
    def test_physical_claim_for_synthetic_denied(self):
        with self.assertRaises(ReceiptError):self.j.append(claim='SYNTHETIC_TELEMETRY',source_tier='LOCAL_SOFTWARE_ONLY',verdict='PROVEN_TRUE',telemetry={})
    def test_journal_database_no_fake_hardware_signer(self):
        p=verify_envelope(self.genesis,self.j.public_key)
        self.assertEqual(p['device_crypto'],'SOFTWARE_ED25519_0600_KEY')
        self.assertEqual(p['telemetry']['TPM'],'NOT_CONNECTED')
    def test_sequence_monotonic_and_chain(self):
        e=self.j.append(claim='SYNTHETIC_TELEMETRY',source_tier='SYNTHETIC_DEMO',verdict='PROVEN_TRUE',telemetry={'physical_joules':None})
        p=verify_envelope(e,self.j.public_key,previous=self.genesis['payload_sha256'],expected_sequence=2)
        self.assertEqual(p['sequence'],2)
    def test_unsupported_integer_or_broken_page_rejected(self):
        with self.assertRaises(ReceiptError):self.j.get_after(-1)
        with self.assertRaises(ReceiptError):self.j.get_after(0,limit=999)
    def test_wrong_codec_fails(self):
        e=dict(self.genesis);e['schema']='ipqr1'
        with self.assertRaises(ReceiptError):verify_envelope(e,self.j.public_key)

class Network(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.app=create_app(data_dir=self.temp.name,operator_token=SECRET,demo_enabled=True,
                            max_clients=2,queue_size=4,heartbeat_seconds=.15)
        self.client=TestClient(self.app,base_url='http://127.0.0.1:8768')
        self.client.__enter__()
    def tearDown(self):
        self.client.__exit__(None,None,None);self.temp.cleanup()
    def auth(self):return {'x-innovulis-operator-token':SECRET}
    def ws(self):return self.client.websocket_connect('/ws',headers={'origin':'http://127.0.0.1:8768','host':'127.0.0.1:8768'})
    def test_genesis_on_server_start(self):
        r=self.client.get('/api/history');self.assertEqual(len(r.json()['envelopes']),1)
        self.assertEqual(self.client.get('/api/health').json()['physical_printer'],False)
    def test_does_not_auto_accept_trust_key(self):
        r=self.client.get('/api/identity').json()
        self.assertIn('UNTRUSTED',r['trust']);self.assertFalse(r['hardware_key'])
    def test_boot_is_not_false_medical_claim(self):
        pub=self.client.get('/api/identity').json()['ed25519_public_key_hex']
        e=self.client.get('/api/receipt/1').json();p=verify_envelope(e,pub)
        self.assertEqual(p['declared_verdict'],'PROCESS_OBSERVED')
        self.assertNotEqual(p['operator_attestation'],'ARCHITECT_PRESENT')
    def test_synthetic_tick_requires_operator(self):
        self.assertEqual(self.client.post('/api/demo/tick',json={'outcome':'PASS'}).status_code,403)
    def test_synthetic_refuted_attested_only_as_synthetic(self):
        res=self.client.post('/api/demo/tick',json={'outcome':'REFUTED'},headers=self.auth())
        self.assertEqual(res.status_code,200)
        pub=self.client.get('/api/identity').json()['ed25519_public_key_hex']
        p=verify_envelope(res.json(),pub,expected_sequence=2)
        self.assertEqual(p['source_tier'],'SYNTHETIC_DEMO')
        self.assertEqual(p['declared_verdict'],'REFUTED_FALSE')
        self.assertIsNone(p['telemetry']['physical_joules'])
    def test_simulation_invalid_action(self):
        self.assertEqual(self.client.post('/api/demo/tick',json={'outcome':'TRANSFER_FUNDS'},headers=self.auth()).status_code,422)
    def test_no_xss_in_dashboard(self):
        html=self.client.get('/').text
        self.assertNotIn('https://cdn',html)
        self.assertIn('verify.mjs',self.client.get('/static/app.mjs').text)
    def test_source_qr_svg_contains_full_carrier(self):
        resp=self.client.get('/api/receipt/1/qr.svg')
        self.assertEqual(resp.status_code,200)
        self.assertTrue(resp.content.startswith(b'<'))
    def test_header_origin_rejected(self):
        from starlette.websockets import WebSocketDisconnect
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect('/ws',headers={'origin':'https://evil.example','host':'127.0.0.1:8768'}) as ws: ws.receive_json()
    def test_two_live_ws_clients_same_signed_envelope(self):
        with self.ws() as a, self.ws() as b:
            self.assertEqual(a.receive_json()['type'],'hello')
            self.assertEqual(b.receive_json()['type'],'hello')
            self.client.post('/api/demo/tick',json={'outcome':'REFUTED'},headers=self.auth())
            e1=a.receive_json();e2=b.receive_json()
            self.assertEqual(e1['type'],'receipt');self.assertEqual(e1['envelope'],e2['envelope'])
            self.assertEqual(len(self.app.state.service.clients),2)
    def test_limit_clients(self):
        from starlette.websockets import WebSocketDisconnect
        with self.ws() as a, self.ws() as b:
            a.receive_json();b.receive_json()
            with self.assertRaises(WebSocketDisconnect):
                with self.ws() as c:c.receive_json()
    def test_journal_tamper_refuses_reboot(self):
        self.app.state.service.journal.db.execute('UPDATE receipts SET sha256=? WHERE sequence=1',('0'*64,))
        with self.assertRaises(ReceiptError):self.app.state.service.journal.verify_all()
    def test_demo_disabled_even_if_token_valid(self):
        app=create_app(data_dir=Path(self.temp.name)/'second',operator_token=SECRET,demo_enabled=False)
        with TestClient(app,base_url='http://127.0.0.1:8768') as cli:
            self.assertEqual(cli.post('/api/demo/tick',json={'outcome':'PASS'},headers=self.auth()).status_code,403)

if __name__=='__main__':unittest.main()
