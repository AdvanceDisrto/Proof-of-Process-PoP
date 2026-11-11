"""Independent v1.0 offline verifier integration tests with synthetic keys only."""
import copy
from pathlib import Path
import tempfile
import time
import unittest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from paper_console.verification import IndependentReceiptGate,VerificationNotReady
from paper_console.escpos import PrintPolicy,render_receipt
from paper_console.p256_bridge import P256HardwareSigner,HardwareNotConnected,verify_p256_digest

try:
    from innovulis_receipt.issuer_demo import create_demo
    from innovulis_receipt.codec import encode_qr_text
    HAS_OPEN_VERIFIER=True
except ImportError:
    HAS_OPEN_VERIFIER=False


@unittest.skipUnless(HAS_OPEN_VERIFIER, "Requires bundled Open Receipt Verifier v1.0 wheel")
class TestRealVerifierIntegration(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.example=create_demo()
        self.packet=self.example['packet']
        self.t=self.example['demo_time']
        Path(self.temp.name,'sensor_demo_trace.txt').write_bytes(self.example['evidence'])
    def tearDown(self):self.temp.cleanup()
    def gate(self, **overrides):
        opts=dict(trust=self.example['trust'],revocations=self.example['revocations'],
            issuance_log=self.example['issuance_log'],
            independently_pinned_anchor_sha256=self.example['trust_sha256'],
            expected_subject='sensor:demo-unit-314',evidence_dir=self.temp.name)
        opts.update(overrides)
        return IndependentReceiptGate(**opts)
    def test_verified_live_signed(self):
        ev,res=self.gate().check(self.packet,now=self.t,carrier=encode_qr_text(self.packet))
        self.assertEqual(res['code'],'VERIFIED_DIGITAL_RECEIPT')
        self.assertEqual(ev.verification,'VERIFIED_DIGITAL_RECEIPT')
        self.assertEqual(ev.source_tier,'SIGNED_DIGITAL')
    def test_verified_refuted_receipt_does_not_show_green(self):
        demo=create_demo(at_time=self.t,verdict='REFUTED_FALSE',observed=90000,limit=50000)
        gate=self.gate(trust=demo['trust'],revocations=demo['revocations'],
                       issuance_log=demo['issuance_log'],independently_pinned_anchor_sha256=demo['trust_sha256'])
        event,_=gate.check(demo['packet'],now=self.t,carrier=encode_qr_text(demo['packet']))
        self.assertEqual(event.claim_verdict,'REFUTED_FALSE')
        self.assertEqual(event.verification,'VERIFIED_DIGITAL_RECEIPT')
        printout,_=render_receipt(event,policy=PrintPolicy(),include_qr=True)
        self.assertIn(b'DECLARED_FALSE',printout)
    def test_signature_mutation_rejected(self):
        packet=copy.deepcopy(self.packet)
        packet['issuer_signature']='00'*64
        ev,res=self.gate().check(packet,now=self.t)
        self.assertEqual(res['code'],'REJECTED')
        self.assertNotEqual(ev.verification,'VERIFIED_DIGITAL_RECEIPT')
    def test_wrong_subject_rejected(self):
        _,res=self.gate(expected_subject='wrong-object').check(self.packet,now=self.t)
        self.assertEqual(res['code'],'REJECTED')
    def test_evidence_bytes_missing_not_verifiable(self):
        _,res=self.gate(evidence_dir=None).check(self.packet,now=self.t)
        self.assertEqual(res['code'],'CRYPTOGRAPHIC_ATTESTATION_ONLY')
    def test_modified_sensor_bytes_rejected(self):
        Path(self.temp.name,'sensor_demo_trace.txt').write_text('tampered data')
        _,res=self.gate().check(self.packet,now=self.t)
        self.assertEqual(res['code'],'REJECTED')
    def test_expired_receipt_rejected(self):
        _,res=self.gate().check(self.packet,now=self.t+4000)
        self.assertEqual(res['code'],'REJECTED')
    def test_wrong_independent_anchor_rejected(self):
        # Verifier returns no subject/receipt metadata when independent anchor is wrong;
        # application refuses to mint an event from a structurally untrusted body.
        with self.assertRaises(VerificationNotReady):
            self.gate(independently_pinned_anchor_sha256='a'*64).check(self.packet,now=self.t)
    def test_signed_ipqr_raster_escpos_generated(self):
        ev,res=self.gate().check(self.packet,now=self.t,carrier=encode_qr_text(self.packet))
        data,meta=render_receipt(ev,policy=PrintPolicy())
        self.assertIn(b'\x1dv0\x00',data)
        self.assertTrue(meta['is_signed_payload_carried'])
        self.assertGreater(len(data),20000)


class TestP256Boundary(unittest.TestCase):
    def test_absent_hardware_fails_closed(self):
        dev=P256HardwareSigner(slot=0,device_id='not-connected')
        with self.assertRaises(HardwareNotConnected):dev.sign_claim_digest(b'\x99'*32)
    def test_ecdsa_p256_software_reference_only(self):
        software=ec.generate_private_key(ec.SECP256R1())
        pub=software.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        digest=b'\x11'*32
        sig=software.sign(digest,ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        self.assertTrue(verify_p256_digest(pub,digest,sig))
        self.assertFalse(verify_p256_digest(pub,b'\x00'*32,sig))
    def test_non_p256_rejected(self):
        software=ec.generate_private_key(ec.SECP384R1())
        pub=software.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        self.assertFalse(verify_p256_digest(pub,b'\x11'*32,b'\x00'*64))
    def test_hardware_callback_wrong_signature_denied(self):
        software=ec.generate_private_key(ec.SECP256R1())
        pub=software.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        dev=P256HardwareSigner(slot=0,device_id='test-only',public_key_pem=pub,sign_digest_callback=lambda slot,digest: b'\x00'*64)
        with self.assertRaises(HardwareNotConnected):dev.sign_claim_digest(b'\x11'*32)
