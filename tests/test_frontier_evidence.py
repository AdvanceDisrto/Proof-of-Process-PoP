"""Deterministic transport mocks only; no live inference or signing claimed."""
import os
import unittest
from unittest.mock import patch
from integrations.frontier_evidence import InferenceBlocked, RunPodAsync, digest, generate

class InferenceTests(unittest.TestCase):
    def test_explicit_external_consent(self):
        with self.assertRaises(InferenceBlocked):
            generate("hi", "openai_api")
    def test_missing_key_fail_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(InferenceBlocked):
                generate("hi", "deepseek_api", allow_external=True)
    def test_unknown_provider(self):
        with self.assertRaises(InferenceBlocked):
            generate("hi", "imaginary", allow_external=True)
    def test_realistic_mock_metadata(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY":"test-placeholder"}):
            output = generate("A byte?", "openai_api", allow_external=True,
               transport=lambda url, payload, key: {
                   "model": "gpt-4o-mini", "id": "test-id",
                   "choices": [{"message": {"content": "8 bits"}}]})
        self.assertEqual(output["verification_state"], "UNVERIFIED_INFERENCE")
        self.assertEqual(output["source"], "api")
        self.assertEqual(output["output_sha256"], digest("8 bits"))
        self.assertIn("checkpoint_weights", output["capability_not_verified"])
        self.assertEqual(output["observation_sha256"], digest({k:v for k,v in output.items() if k!="observation_sha256"}))
    def test_local_no_false_attestation(self):
        output = generate("hello", "ollama_local", transport=lambda *args: {
            "choices": [{"message":{"content":"world"}}]})
        self.assertEqual(output["source"], "self-hosted-endpoint")
        self.assertEqual(output["ownership"], "checkpoint-unattested")
    def test_missing_text_rejected(self):
        with self.assertRaises(InferenceBlocked):
            generate("hey", "ollama_local", transport=lambda *args: {"choices":[]})

class BatchTests(unittest.TestCase):
    def worker(self, post=None, get=None):
        return RunPodAsync("ep_123", "placeholder", post or (lambda *args: {"id":"job-1"}),
                           get or (lambda *args: {"status":"COMPLETED", "output":["ok"]}))
    def test_no_authorization(self):
        with self.assertRaises(InferenceBlocked):
            self.worker().submit(["x"], "native-model")
    def test_submission_is_not_receipt(self):
        value = self.worker().submit(["x"], "native-model", authorized=True)
        self.assertEqual(value["phase"], "SUBMISSION_ACKNOWLEDGED")
        self.assertEqual(value["receipt_status"], "UNSIGNED_OBSERVATION")
    def test_completion_links_submission(self):
        w = self.worker()
        sub = w.submit(["x"], "native-model", authorized=True)
        result = w.poll(sub)
        self.assertEqual(result["submission_sha256"], digest(sub))
        self.assertEqual(result["output_sha256"], digest(["ok"]))
        self.assertEqual(result["verification_state"], "UNVERIFIED")
    def test_no_output_rejected(self):
        w = self.worker(get=lambda *args: {"status":"COMPLETED"})
        sub = w.submit(["x"], "m", authorized=True)
        with self.assertRaises(InferenceBlocked):
            w.poll(sub)
    def test_failure_has_no_output_hash(self):
        w = self.worker(get=lambda *args: {"status":"FAILED"})
        sub = w.submit(["x"], "m", authorized=True)
        result = w.poll(sub)
        self.assertIsNone(result["output_sha256"])
    def test_invalid_job_id(self):
        w = self.worker(post=lambda *args: {"id":"../../etc"})
        with self.assertRaises(InferenceBlocked):
            w.submit(["x"], "m", authorized=True)
    def test_missing_endpoint(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(InferenceBlocked):
                RunPodAsync()
    def test_unknown_state(self):
        w = self.worker(get=lambda *args: {"status":"MAGICALLY_VERIFIED"})
        sub = w.submit(["x"], "m", authorized=True)
        with self.assertRaises(InferenceBlocked):
            w.poll(sub)

if __name__ == "__main__":
    unittest.main()
