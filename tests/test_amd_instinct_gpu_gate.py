import unittest
from unittest.mock import patch
from integrations import amd_instinct_gpu_gate as gate

class AMDGateTests(unittest.TestCase):
    def test_canonical_deterministic(self):
        self.assertEqual(gate.canonical({"b": 2, "a": 1}), b'{"a":1,"b":2}')

    def test_invalid_no_gpu_fails_closed(self):
        with patch.object(gate, "gpu_observation", return_value={
            "kfd_device": False, "dri_device": False, "amd_smi": {"available": False},
            "rocminfo": {"available": False}}), patch.object(
                gate, "active_matmul", return_value={"cuda_available": False}):
            self.assertEqual(gate.probe("a"*32)["verdict"], "GPU_NOT_VERIFIED")

    def test_signature_requires_pinned_pubkey(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        import base64, hashlib
        raw = bytes(range(32))
        with patch.dict("os.environ", {"IGPU_ED25519_KEY_B64": base64.b64encode(raw).decode()}):
            body = {"schema": "i/amd-instinct-gpu/v1", "nonce": "x"*32, "verdict": "GPU_NOT_VERIFIED"}
            signing = gate.sign_if_configured(body)
        receipt = {"body": body, "signing": signing, "body_sha256": hashlib.sha256(gate.canonical(body)).hexdigest()}
        self.assertTrue(gate.verify_receipt(receipt, signing["public_key"]))
        self.assertFalse(gate.verify_receipt(receipt, "0"*64))
        self.assertTrue(gate.verify_receipt(receipt, signing["public_key"], "x"*32))
        self.assertFalse(gate.verify_receipt(receipt, signing["public_key"], "y"*32))
        receipt["body"]["verdict"] = "ACCEPT_AMD_INSTINCT_SOFTWARE_GPU_GATE"
        self.assertFalse(gate.verify_receipt(receipt, signing["public_key"]))

    def test_mock_gpu_accepted_only_as_software_gate(self):
        observation = {"kfd_device": True, "dri_device": True,
                       "amd_smi": {"available": True, "returncode": 0},
                       "rocminfo": {"available": True, "returncode": 0}}
        with patch.object(gate, "gpu_observation", return_value=observation), patch.object(
                gate, "active_matmul", return_value={"numerically_correct": True, "device_name": "MI300X"}):
            body = gate.probe("a"*32)
        self.assertEqual(body["verdict"], "ACCEPT_AMD_INSTINCT_SOFTWARE_GPU_GATE")
        self.assertEqual(body["physical_gate"], "ACTION_REQUIRED")

    def test_numeric_failure_rejected_even_if_device_visible(self):
        observation = {"kfd_device": True, "dri_device": True,
                       "amd_smi": {"available": True, "returncode": 0},
                       "rocminfo": {"available": True, "returncode": 0}}
        with patch.object(gate, "gpu_observation", return_value=observation), patch.object(
                gate, "active_matmul", return_value={"numerically_correct": False, "device_name": "MI300X"}):
            self.assertEqual(gate.probe("a"*32)["verdict"], "GPU_NOT_VERIFIED")

    def test_missing_key_produces_unsigned(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(gate.sign_if_configured({"a": 1})["mode"], "UNSIGNED")

    def test_malformed_receipt_rejected(self):
        self.assertFalse(gate.verify_receipt({"body": {}, "signing": {}}, "0"*64, "x"*32))

if __name__ == "__main__":
    unittest.main()
