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
            body = {"verdict": "GPU_NOT_VERIFIED"}
            signing = gate.sign_if_configured(body)
        receipt = {"body": body, "signing": signing, "body_sha256": hashlib.sha256(gate.canonical(body)).hexdigest()}
        self.assertTrue(gate.verify_receipt(receipt, signing["public_key"]))
        self.assertFalse(gate.verify_receipt(receipt, "0"*64))
        receipt["body"]["verdict"] = "ACCEPT_AMD_INSTINCT_SOFTWARE_GPU_GATE"
        self.assertFalse(gate.verify_receipt(receipt, signing["public_key"]))

if __name__ == "__main__":
    unittest.main()
