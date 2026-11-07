"""Read-only factory P-256 cryptographic test vectors; NO chip provisioning."""
import copy
import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"hardware/strmkrd-node/factory_provisioning_gate.py"
spec=importlib.util.spec_from_file_location("strmkrd_p256_provisioning",path)
sys.modules[spec.name]=gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

def mint_test_record():
    private=ec.generate_private_key(ec.SECP256R1())  # EPHEMERAL SOFTWARE KEY, not hardware
    message=gate.payload("0123456789abcdef01","b1"*32,"STRMKRD-REV0-JIG-001",0)
    digest=hashlib.sha256(gate.canonical(message)).digest()
    signature=private.sign(digest,ec.ECDSA(utils.Prehashed(hashes.SHA256())))
    pub=private.public_key().public_bytes(
        serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return {"spec":"strmkrd/rev0/p256-proof-of-possession/v1",
            "source_tier":"SYNTHETIC_SOFTWARE_KEY","signature_algorithm":"ECDSA-P256-SHA256",
            "payload":message,"public_key_pem":pub,"signature_der_hex":signature.hex()}

class TestP256ReadOnlyProtocol(unittest.TestCase):
    def setUp(self):
        self.good=mint_test_record()
    def test_valid_cryptographic_signature_no_hardware_promotion(self):
        v=gate.verify(self.good)
        self.assertEqual(v["status"],"ECDSA_P256_PROOF_OF_KEY_POSSESSION_VALID")
        self.assertEqual(v["hardware_origin"],"NOT_VERIFIED")
    def test_changed_nonce_rejected(self):
        r=copy.deepcopy(self.good);r["payload"]["challenge_hex"]="a1"*32
        with self.assertRaises(ValueError):gate.verify(r)
    def test_changed_board_identity_rejected(self):
        r=copy.deepcopy(self.good);r["payload"]["board_id"]="OTHERS"
        with self.assertRaises(ValueError):gate.verify(r)
    def test_changed_serial_rejected(self):
        r=copy.deepcopy(self.good);r["payload"]["device_serial_hex"]="aa"*9
        with self.assertRaises(ValueError):gate.verify(r)
    def test_invalid_signature_rejected(self):
        r=copy.deepcopy(self.good);r["signature_der_hex"]="30"
        with self.assertRaises(ValueError):gate.verify(r)
    def test_ed25519_algorithm_spoof_rejected(self):
        r=copy.deepcopy(self.good);r["signature_algorithm"]="Ed25519"
        with self.assertRaises(ValueError):gate.verify(r)
    def test_attested_source_spoof_rejected(self):
        r=copy.deepcopy(self.good);r["source_tier"]="PHYSICAL_ATTESTED"
        with self.assertRaises(ValueError):gate.verify(r)
    def test_p256_curve_required(self):
        r=copy.deepcopy(self.good)
        wrong=ec.generate_private_key(ec.SECP384R1())
        r["public_key_pem"]=wrong.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        with self.assertRaises(ValueError):gate.verify(r)
    def test_wrong_key_rejected(self):
        r=copy.deepcopy(self.good)
        wrong=ec.generate_private_key(ec.SECP256R1())
        r["public_key_pem"]=wrong.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        with self.assertRaises(ValueError):gate.verify(r)
    def test_reject_noncanonical_uppercase_hex(self):
        r=copy.deepcopy(self.good);r["payload"]["challenge_hex"]="B1"*32
        with self.assertRaises(ValueError):gate.verify(r)
    def test_no_programming_commands_in_verifier(self):
        text=path.read_text()
        self.assertNotIn("ioctl(",text)
        self.assertNotIn("Lock(",text)
        self.assertNotIn("GenKey(",text)
        self.assertIn("NOT_VERIFIED",text)

if __name__=="__main__":unittest.main()
