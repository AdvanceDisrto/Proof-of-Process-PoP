from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
import numpy as np
from fastapi.testclient import TestClient
from paper_console.codec import Event, InvalidEvent, sha256
from paper_console.store import EventStore
from paper_console.escpos import PrintPolicy, PrintBlocked, DryRunPrinter, PrintScheduler, render_receipt, ApprovedTcpPrinter
from paper_console.energy import PowerSample, JouleIntegrator, INA226
from paper_console.math_receipt import compute_covariance_svd
from paper_console.atlas import ingest_atlas,atlas_event,AtlasDataError,cable_transit_observation
from paper_console.popc import GateInputs,popc_admission
from paper_console.service import create_app
from paper_console.cli import run_demo

NOW=int(time.time())


def evt(i='12345',**changes):
    base=dict(event_id='test-'+i,occurred_at=NOW, track='claim',subject='test:unit-01',
              claim_verdict='UNRESOLVED', verification='NOT_CHECKED',details={'proof':'none'},
              source_tier='DEMO',source_ref='demo fixture',receipt_sha256=None,carrier=None,observed_joules=None)
    base.update(changes)
    return Event(**base)


class TestEvent(unittest.TestCase):
    def test_canonical_hash_order(self):self.assertEqual(sha256({'x':1,'y':2}),sha256({'y':2,'x':1}))
    def test_reject_too_short_id(self):
        with self.assertRaises(InvalidEvent):evt(event_id='a')
    def test_reject_unknown_verdict(self):
        with self.assertRaises(InvalidEvent):evt(claim_verdict='THE_TRUTH')
    def test_reject_spoofed_verified_status(self):
        with self.assertRaises(InvalidEvent):evt(verification='VERIFIED_DIGITAL_RECEIPT')
    def test_accept_signed_verified_typed_only(self):
        e=evt(verification='VERIFIED_DIGITAL_RECEIPT',source_tier='SIGNED_DIGITAL',receipt_sha256='b'*64)
        self.assertEqual(e.verification,'VERIFIED_DIGITAL_RECEIPT')
    def test_carrier_rejects_unsiged_string(self):
        with self.assertRaises(InvalidEvent):evt(carrier='https://attack.invalid')
    def test_reject_nan(self):
        with self.assertRaises(ValueError):evt(details={'x':float('nan')})
    def test_reject_negative_joules(self):
        with self.assertRaises(InvalidEvent):evt(observed_joules=-1)
    def test_reject_oversized(self):
        with self.assertRaises(InvalidEvent):evt(details={'x':'a'*9000})


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'db.sqlite3'
        self.store=EventStore(self.path)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_append_integrity(self):
        self.store.append(evt('10000'));self.store.append(evt('20000'))
        self.assertTrue(self.store.integrity()['chain_ok'])
        self.assertEqual(self.store.integrity()['checked'],2)
    def test_duplicate_is_idempotent(self):
        self.store.append(evt('10000'));r=self.store.append(evt('10000'))
        self.assertTrue(r['duplicate']);self.assertEqual(self.store.stats()['total_events'],1)
    def test_id_collision_rejected(self):
        self.store.append(evt('10000'))
        with self.assertRaises(InvalidEvent):self.store.append(evt('10000',subject='other'))
    def test_chain_detects_tampering(self):
        self.store.append(evt('10000'));self.store.db.execute("UPDATE events SET json='{}' WHERE seq=1")
        self.assertFalse(self.store.integrity()['chain_ok'])
    def test_queue_exactly_once(self):
        e=evt();self.store.append(e);self.store.queue(e.event_id);self.store.queue(e.event_id)
        self.assertEqual(self.store.stats()['queued_prints'],1)
    def test_spool_restart_hold(self):
        e=evt();self.store.append(e);self.store.queue(e.event_id)
        self.assertIsNotNone(self.store.next_print())
        self.store.close();self.store=EventStore(self.path)
        self.store.recover_claimed_as_hold()
        self.assertIsNone(self.store.next_print())
    def test_history_on_reject(self):
        self.store.append(evt('10000',claim_verdict='REFUTED_FALSE',verification='REJECTED'))
        self.assertEqual(self.store.stats()['refuted_claims'],1)
        self.assertEqual(self.store.stats()['verified_digital_receipts'],0)
    def test_joules_separate_sources(self):
        self.store.append(evt('10000',observed_joules=4.2))
        self.store.append(evt('20000',observed_joules=0.4,source_tier='INA226_CALIBRATED_UNATTESTED'))
        self.assertEqual(self.store.stats()['joules_meter_derived_unattested'],0.4)
        self.assertEqual(self.store.stats()['joules_other_reported_unverified'],4.2)
    def test_missing_queue_event(self):
        with self.assertRaises(KeyError):self.store.queue('missing')


class TestPrint(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=EventStore(Path(self.tmp.name)/'db')
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def verified(self,id='12345',carrier=None):
        return evt(id,verification='VERIFIED_DIGITAL_RECEIPT',source_tier='SIGNED_DIGITAL',
                   receipt_sha256='a'*64,claim_verdict='REFUTED_FALSE',carrier=carrier)
    def test_policy_min_rate(self):
        with self.assertRaises(ValueError):PrintPolicy(minimum_interval_seconds=1)
    def test_unverified_print_qr_denied(self):
        with self.assertRaises(PrintBlocked):render_receipt(evt(),policy=PrintPolicy(),include_qr=True)
    def test_untrusted_carrier_denied(self):
        with self.assertRaises(PrintBlocked):render_receipt(self.verified(),policy=PrintPolicy())
    def test_metadata_explicit_untrusted(self):
        x,meta=render_receipt(evt(),policy=PrintPolicy(),include_qr=False)
        self.assertIn(b'UNTRUSTED PAPER',x);self.assertFalse(meta['is_signed_payload_carried'])
    def test_injecting_control_byte_in_subject_fails(self):
        with self.assertRaises(InvalidEvent):evt(subject='x\x1b@')
    def test_print_budget(self):
        self.store.append(evt())
        sched=PrintScheduler(self.store,DryRunPrinter(Path(self.tmp.name)/'o.bin'),mode='manual')
        self.store.queue('test-12345');self.store.finish_print if False else None
        self.store.db.execute("INSERT INTO print_history(event_id,printed_at,body_sha256) VALUES (?,?,?)",('history',NOW,'b'*64))
        self.assertEqual(sched.process_once(now=NOW+1)['status'],'RATE_LIMITED')
    def test_hour_budget(self):
        sched=PrintScheduler(self.store,DryRunPrinter(Path(self.tmp.name)/'o.bin'),policy=PrintPolicy(maximum_per_hour=1),mode='manual')
        self.store.db.execute("INSERT INTO print_history(event_id,printed_at,body_sha256) VALUES (?,?,?)",('history',NOW-10,'b'*64))
        self.assertEqual(sched.process_once(now=NOW)['status'],'HOURLY_BUDGET_EXCEEDED')
    def test_physical_printer_must_be_approved(self):
        with self.assertRaises(PrintBlocked):ApprovedTcpPrinter('192.168.4.33')
    def test_public_network_printer_denied(self):
        with self.assertRaises(PrintBlocked):ApprovedTcpPrinter('8.8.8.8',operator_approved=True)
    def test_exception_requires_verified(self):
        s=PrintScheduler(self.store,DryRunPrinter(Path(self.tmp.name)/'o.bin'),mode='exception')
        e=evt('11111',claim_verdict='REFUTED_FALSE',verification='REJECTED')
        self.store.append(e);self.assertFalse(s.consider(e))
    def test_exception_buffers_verified_refuted(self):
        s=PrintScheduler(self.store,DryRunPrinter(Path(self.tmp.name)/'o.bin'),mode='exception')
        e=self.verified();self.store.append(e);self.assertTrue(s.consider(e))
        # No carrier available; avoid silently printing a hash alone as a signed receipt.
        self.assertEqual(s.process_once(now=NOW)['status'],'HOLD')
    def test_dry_run_file_is_not_hardware(self):
        path=Path(self.tmp.name)/'dryrun.escpos'
        count=DryRunPrinter(path).write(b'abc')
        self.assertEqual(count,3);self.assertEqual(path.read_bytes(),b'abc')
    def test_qr_real_raster(self):
        e=self.verified(carrier='ipqr1:'+ 'a'*100)
        data,m=render_receipt(e,policy=PrintPolicy(),include_qr=True)
        self.assertTrue(m['is_signed_payload_carried'])
        self.assertIn(b'\x1dv0\x00',data)
    def test_qr_excess_density_fails_closed(self):
        e=self.verified(carrier='ipqr1:'+ 'a'*10000)
        with self.assertRaises(PrintBlocked):render_receipt(e,policy=PrintPolicy(paper_width_pixels=384))


class TestPhysicsMath(unittest.TestCase):
    def test_real_numpy_svd(self):
        x=np.random.default_rng(0).normal(size=(16,16))
        r=compute_covariance_svd(x)
        self.assertLess(r['reconstruction_residual'],1e-8)
        self.assertEqual(r['patches'],16)
    def test_svd_repeat_hash(self):
        x=np.ones((16,16))
        self.assertEqual(compute_covariance_svd(x)['covariance_f64le_sha256'],compute_covariance_svd(x)['covariance_f64le_sha256'])
    def test_svd_nonfinite_denied(self):
        with self.assertRaises(ValueError):compute_covariance_svd(np.full((8,8),np.nan))
    def test_svd_irregular_patch_denied(self):
        with self.assertRaises(ValueError):compute_covariance_svd(np.ones((9,8)))
    def test_svd_too_few_patches_denied(self):
        with self.assertRaises(ValueError):compute_covariance_svd(np.ones((4,4)))
    def sample(self,t,p):
        return PowerSample(t,p,5,p/5,'meter-x','INA226_UNATTESTED','cal-001')
    def test_integration_trapezoid(self):
        e=JouleIntegrator();e.add(self.sample(1,4));e.add(self.sample(3,8))
        self.assertEqual(e.receipt()['joules_estimate'],12)
    def test_missing_second_sample_denied(self):
        e=JouleIntegrator();e.add(self.sample(1,4))
        with self.assertRaises(ValueError):e.receipt()
    def test_backward_time_denied(self):
        e=JouleIntegrator();e.add(self.sample(2,4))
        with self.assertRaises(ValueError):e.add(self.sample(1,4))
    def test_sampling_gap_denied(self):
        e=JouleIntegrator();e.add(self.sample(1,4))
        with self.assertRaises(ValueError):e.add(self.sample(100,4))
    def test_change_calibration_denied(self):
        e=JouleIntegrator();e.add(self.sample(1,4))
        bad=PowerSample(2,3,5,.6,'meter-x','INA226_UNATTESTED','different')
        with self.assertRaises(ValueError):e.add(bad)
    def test_meter_negative_denied(self):
        with self.assertRaises(ValueError):self.sample(1,-1)
    def test_mocked_registers_are_not_attested(self):
        class Bus:
            def read_word_data(self, addr,reg):
                raw=1600 if reg==2 else 400
                return ((raw&0xff)<<8)|(raw>>8)
        dev=INA226(bus_number=1,address=0x40,shunt_ohms=.01,calibration_id='cal',device_id='fake',bus=Bus())
        s=dev.sample(monotonic_seconds=2)
        self.assertEqual(s.source,'INA226_UNATTESTED')
        self.assertAlmostEqual(s.volts,2.0)
        self.assertAlmostEqual(s.amps,.1)
        self.assertAlmostEqual(s.watts,.2)
    def test_malformed_meter_address(self):
        with self.assertRaises(ValueError):INA226(bus_number=1,address=0x20,shunt_ohms=.01,calibration_id='cal',device_id='x',bus=object())
    def test_popc_all_flags_true_is_only_request_eligible(self):
        i=GateInputs(*([True]*8));r=popc_admission(i,'a'*64)
        self.assertTrue(r['admit_to_signer']);self.assertEqual(r['status'],'SIGN_REQUEST_ELIGIBLE_UNATTESTED')
    def test_popc_any_one_false_denies(self):
        for bit in range(8):
            flags=[True]*8;flags[bit]=False
            self.assertFalse(popc_admission(GateInputs(*flags),'a'*64)['admit_to_signer'])
    def test_popc_zero_digest_denied(self):
        self.assertFalse(popc_admission(GateInputs(*([True]*8)),'0'*64)['admit_to_signer'])
    def test_popc_invalid_hash_denied(self):
        with self.assertRaises(ValueError):popc_admission(GateInputs(*([True]*8)),'xyz')


class TestAtlas(unittest.TestCase):
    def setUp(self):self.fixture=Path(__file__).resolve().parents[1]/'data/atlas_example.json'
    def test_reference_dataset_explicit_unverified(self):
        x=ingest_atlas(self.fixture)
        self.assertEqual(x['count'],4)
        self.assertEqual({e['source_tier'] for e in x['entities']},{'DATASET_UNVERIFIED'})
    def test_atlas_event_is_unresolved(self):
        x=ingest_atlas(self.fixture);e=atlas_event(x['entities'][0],x['source_sha256'],NOW)
        self.assertEqual(e.claim_verdict,'UNRESOLVED');self.assertEqual(e.verification,'NOT_CHECKED')
    def test_atlas_duplicates_denied(self):
        doc=json.loads(self.fixture.read_text());doc['entities'].append(copy.deepcopy(doc['entities'][0]))
        with tempfile.NamedTemporaryFile(mode='w',delete=False) as f:
            json.dump(doc,f);name=f.name
        try:
            with self.assertRaises(AtlasDataError):ingest_atlas(name)
        finally:os.unlink(name)
    def test_atlas_source_required(self):
        doc=json.loads(self.fixture.read_text());doc['provenance']['license']=''
        with tempfile.NamedTemporaryFile(mode='w',delete=False) as f:json.dump(doc,f);name=f.name
        try:
            with self.assertRaises(AtlasDataError):ingest_atlas(name)
        finally:os.unlink(name)
    def test_cable_route_cannot_be_inferred(self):
        v=cable_transit_observation(origin='NYC',destination='London',declared_route='MAREA')
        self.assertEqual(v['cable_route_status'],'UNOBSERVED')
    def test_operator_route_cannot_gain_verification(self):
        v=cable_transit_observation(origin='NYC',destination='London',declared_route='MAREA',source_id='demo')
        self.assertEqual(v['cable_route_status'],'THIRD_PARTY_CLAIM_UNVERIFIED')
    def test_demo_outputs_do_not_claim_signatures(self):
        with tempfile.TemporaryDirectory() as d:
            z=run_demo(d)
            self.assertEqual(z['count'],7)
            self.assertEqual(z['hardware_energy'],'NOT_CONNECTED')
            self.assertTrue(z['integrity']['chain_ok'])


class TestWeb(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.app=create_app(db_path=Path(self.tmp.name)/'web.db',operator_token='Z'*40)
        self.client=TestClient(self.app)
    def tearDown(self):self.client.close();self.app.state.store.close();self.tmp.cleanup()
    def test_health(self):
        self.assertEqual(self.client.get('/health').json()['printer'],'DISABLED_UNLESS_CONFIGURED')
    def test_dashboard_loaded(self):
        self.assertIn('PAPER CONSOLE',self.client.get('/').text)
    def test_public_ingest_denied(self):
        self.assertEqual(self.client.post('/api/ingest',json=evt().as_dict()).status_code,403)
    def test_verified_self_assertion_denied(self):
        payload=evt().as_dict();payload['verification']='VERIFIED_DIGITAL_RECEIPT';payload['source_tier']='SIGNED_DIGITAL';payload['receipt_sha256']='a'*64
        self.assertEqual(self.client.post('/api/ingest',headers={'x-i-operator-token':'Z'*40},json=payload).status_code,422)
    def test_public_blob_denied(self):
        payload=evt().as_dict();payload['carrier']='ipqr1:abcd'
        self.assertEqual(self.client.post('/api/ingest',headers={'x-i-operator-token':'Z'*40},json=payload).status_code,422)
    def test_operator_ingest_unverified(self):
        payload=evt().as_dict();res=self.client.post('/api/ingest',headers={'x-i-operator-token':'Z'*40},json=payload)
        self.assertEqual(res.status_code,200)
        self.assertEqual(self.client.get('/api/stats').json()['verified_digital_receipts'],0)
    def test_operator_duplicate_idempotent(self):
        data=evt().as_dict();h={'x-i-operator-token':'Z'*40}
        self.assertFalse(self.client.post('/api/ingest',headers=h,json=data).json()['duplicate'])
        self.assertTrue(self.client.post('/api/ingest',headers=h,json=data).json()['duplicate'])
    def test_token_mismatch_denied(self):
        self.assertEqual(self.client.post('/api/ingest',headers={'x-i-operator-token':'Y'*40},json=evt().as_dict()).status_code,403)
    def test_future_time_denied(self):
        data=evt().as_dict();data['occurred_at']=NOW+100000
        self.assertEqual(self.client.post('/api/ingest',headers={'x-i-operator-token':'Z'*40},json=data).status_code,422)
