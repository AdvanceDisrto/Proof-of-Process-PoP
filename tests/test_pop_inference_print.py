import unittest
from dataclasses import asdict
from unittest.mock import Mock

from core.crypto import new_key, public_hex
from integrations.frontier_evidence import generate
from integrations.pop_inference_bridge import sign_inference_observation
from integrations.ireceipt_thermal import (
    ReceiptRejected, verify_domain_envelope, paper_payload, render_58mm_text, print_escpos
)
from proof.parallel_pop import verify_domain, aggregate

class ProofReceiptTests(unittest.TestCase):
    def setUp(self):
        self.key = new_key()
        self.pub = public_hex(self.key)
        self.observation = generate("byte", "ollama_local", transport=lambda *a: {
            "model": "deepseek-r1:7b", "choices": [{"message": {"content": "8 bits"}}]
        })
        self.signed = sign_inference_observation(self.observation, self.key)
        self.envelope = asdict(self.signed)

    def test_real_core_signature_verifies(self):
        self.assertTrue(verify_domain(self.signed))

    def test_remains_action_required(self):
        self.assertEqual(self.signed.body["state"], "ACTION_REQUIRED")
        self.assertEqual(aggregate([self.signed])["body"]["state"], "INCOMPLETE")

    def test_signed_observation_not_checkpoint_attestation(self):
        self.assertIn("provider identity or checkpoint weights", self.signed.body["does_not_prove"])

    def test_reject_modified_observation(self):
        altered = dict(self.observation, output_sha256="sha256:" + "0"*64)
        with self.assertRaises(ValueError):
            sign_inference_observation(altered, self.key)

    def test_reject_fake_verified_observation(self):
        altered = dict(self.observation, verification_state="VERIFIED_PROCESS")
        with self.assertRaises(ValueError):
            sign_inference_observation(altered, self.key)

    def test_paper_payload_requires_trusted_key(self):
        with self.assertRaises(ReceiptRejected):
            paper_payload(self.envelope, set())

    def test_paper_payload_accepts_trusted_key(self):
        payload = paper_payload(self.envelope, {self.pub})
        self.assertEqual(payload["signature_integrity"], "VERIFIED_WITH_TRUSTED_PUBLIC_KEY")
        self.assertFalse(payload["physical_event_verified"])
        self.assertIn("PHYSICAL: NOT VERIFIED", render_58mm_text(payload))

    def test_tamper_detection(self):
        altered = asdict(self.signed)
        altered["body"]["state"] = "VERIFIED_PROCESS"
        with self.assertRaises(ReceiptRejected):
            verify_domain_envelope(altered, {self.pub})

    def test_qr_only_with_https(self):
        with self.assertRaises(ReceiptRejected):
            paper_payload(self.envelope, {self.pub}, "http://localhost/verify")
        payload = paper_payload(self.envelope, {self.pub}, "https://example.org/verify")
        self.assertIn("receipt_id=", payload["qr_content"])

    def test_no_print_without_approval(self):
        p = Mock()
        with self.assertRaises(ReceiptRejected):
            print_escpos(paper_payload(self.envelope, {self.pub}), p)
        p.text.assert_not_called()

    def test_approved_print_with_injected_hardware(self):
        p = Mock()
        print_escpos(paper_payload(self.envelope, {self.pub}), p, operator_approved=True)
        p.qr.assert_called_once()
        p.cut.assert_called_once()

if __name__ == "__main__":
    unittest.main()
