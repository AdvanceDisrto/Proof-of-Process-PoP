"""Tests for CI DSL validation and externally trusted receipt gate."""
import json
import tempfile
import unittest
from pathlib import Path

from core.crypto import canonical, new_key, public_hex, sign, sha
from integrations.ci_oracle import OracleRejected, parse_intent, translate
from integrations.ci_sign_gate import verify_external_receipt
from integrations.ireceipt_thermal import ReceiptRejected

INTENT = {"project": "innovulis-pop", "steps": ["compile", "frontier_tests", "receipt_tests", "ci_tests", "sign_gate"]}

class OracleTests(unittest.TestCase):
    def test_validate_intent(self):
        self.assertEqual(parse_intent(json.dumps(INTENT)), INTENT)

    def test_bitbucket_pipeline(self):
        doc = json.loads(translate(INTENT, "bitbucket"))
        scripts = doc["pipelines"]["custom"]["verified-evidence"][0]["step"]["script"]
        self.assertTrue(scripts[-1].endswith("integrations.ci_sign_gate"))

    def test_woodpecker_pipeline(self):
        doc = json.loads(translate(INTENT, "woodpecker"))
        self.assertEqual(doc["steps"][-1]["name"], "sign_gate")

    def test_jenkins_pipeline(self):
        pipeline = translate(INTENT, "jenkins")
        self.assertIn("stage('sign_gate')", pipeline)
        self.assertIn("integrations.ci_sign_gate", pipeline)

    def test_reject_arbitrary_command(self):
        with self.assertRaises(OracleRejected):
            parse_intent(json.dumps({"project": "p", "steps": ["rm -rf /", "sign_gate"]}))

    def test_reject_missing_sign_gate(self):
        with self.assertRaises(OracleRejected):
            parse_intent(json.dumps({"project": "p", "steps": ["compile"]}))

    def test_reject_sign_gate_not_last(self):
        with self.assertRaises(OracleRejected):
            parse_intent(json.dumps({"project": "p", "steps": ["sign_gate", "compile"]}))

    def test_reject_unsafe_name(self):
        with self.assertRaises(OracleRejected):
            parse_intent(json.dumps({"project": "p; echo compromised", "steps": ["sign_gate"]}))

    def test_reject_duplicate(self):
        with self.assertRaises(OracleRejected):
            parse_intent(json.dumps({"project": "p", "steps": ["compile", "compile", "sign_gate"]}))

    def test_reject_unrecognized_target(self):
        with self.assertRaises(OracleRejected):
            translate(INTENT, "made-up-cicd")

    def test_signed_receipt_requires_pinned_key(self):
        key = new_key()
        body = {"state": "ACTION_REQUIRED", "signer": "ed25519:" + public_hex(key)}
        document = {"body": body, "receipt_id": sha(canonical(body)), "signature": sign(key, body)}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "receipt.json"
            p.write_text(json.dumps(document), encoding="utf-8")
            result = verify_external_receipt(str(p), public_hex(key))
            self.assertEqual(result["verification"], "SIGNATURE_INTEGRITY_ACCEPTED")
            self.assertEqual(result["signed_state"], "ACTION_REQUIRED")
            with self.assertRaises(ReceiptRejected):
                verify_external_receipt(str(p), public_hex(new_key()))

    def test_tampered_receipt_rejected(self):
        key = new_key()
        body = {"state": "ACTION_REQUIRED", "signer": "ed25519:" + public_hex(key)}
        document = {"body": body, "receipt_id": sha(canonical(body)), "signature": sign(key, body)}
        document["body"]["state"] = "VERIFIED_PROCESS"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "receipt.json"
            p.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(ReceiptRejected):
                verify_external_receipt(str(p), public_hex(key))

if __name__ == "__main__":
    unittest.main()
