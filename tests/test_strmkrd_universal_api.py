"""Real FastAPI TestClient + P256 verifier + fail-closed local hardware interface."""
import importlib.util
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"hardware/strmkrd-node/universal_api.py"
spec=importlib.util.spec_from_file_location("strmkrd_universal_api_v0",SOURCE)
sys.modules[spec.name]=api=importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
TOKEN="real-local-transport-token-value-for-unit-test"
KEY=ec.generate_private_key(ec.SECP256R1())
PIN=KEY.public_key().public_bytes(serialization.Encoding.PEM,
          serialization.PublicFormat.SubjectPublicKeyInfo).decode("ascii")

def demo():
    return {"spec":api.SCHEMA,"source_tier":"SYNTHETIC_SIMULATOR",
            "measurement_sixteenths_c":392, "policy":"demo_only",
            "does_not_prove":["hardware signer","sensor reality"]}

def i2c():
    return {"source_tier":"UNAUTHENTICATED_I2C_OBSERVATION",
            "silicon_signature":"NOT_PRESENT","physical_device_authentication":"NOT_VERIFIED",
            "temperature":{"temperature_sixteenths_c":392,
                           "source_tier":"UNAUTHENTICATED_I2C_OBSERVATION"},
            "power_meter":{"bus_v":"5.0000","power_w":"5",
                           "source_tier":"UNAUTHENTICATED_I2C_OBSERVATION"}}

class TestStrmkrdUniversalAPI(unittest.TestCase):
    def client(self, probe=None):
        return TestClient(api.create_app(token=TOKEN,probe=probe))

    def test_api_token_required(self):
        self.assertEqual(self.client(probe=i2c).get("/api/v1/observation").status_code,401)
    def test_bad_token(self):
        self.assertEqual(self.client(probe=i2c).get("/api/v1/observation",headers={"x-api-key":"wrong"}).status_code,401)
    def test_no_short_secret(self):
        with self.assertRaises(ValueError):api.create_app(token="test")
    def test_health_does_not_promote_physical(self):
        r=self.client().get("/api/v1/status")
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()["hardware_device"],"NOT_VERIFIED")
        self.assertEqual(r.json()["qow_minting"],"NOT_ENABLED")
    def test_observation_policy_real_z3(self):
        r=self.client(probe=i2c).get("/api/v1/observation",headers={"x-api-key":TOKEN})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()["formal_policy"]["verdict"],"PROVEN_TRUE")
        self.assertEqual(r.json()["receipt"],"NOT_MINTED")
    def test_out_of_range_declines(self):
        def wrong():
            x=i2c();x["temperature"]["temperature_sixteenths_c"]=-900
            return x
        r=self.client(probe=wrong).get("/api/v1/observation",headers={"x-api-key":TOKEN})
        self.assertEqual(r.json()["formal_policy"]["verdict"],"REFUTED_FALSE")
        self.assertEqual(r.json()["receipt"],"NOT_MINTED")
    def test_unauthenticated_source_cannot_be_promoted(self):
        def spoof():
            x=i2c();x["physical_device_authentication"]="VERIFIED"
            return x
        self.assertEqual(self.client(probe=spoof).get("/api/v1/observation",headers={"x-api-key":TOKEN}).status_code,503)
    def test_io_failure_fail_closed(self):
        def missing():raise OSError("No actual sensor")
        r=self.client(probe=missing).get("/api/v1/observation",headers={"x-api-key":TOKEN})
        self.assertEqual(r.status_code,503)
        self.assertNotIn("No actual sensor",r.text)
    def test_unprovisioned_receipt_fails(self):
        r=self.client(probe=i2c).get("/api/v1/receipt",headers={"x-api-key":TOKEN})
        self.assertEqual(r.status_code,503)
    def test_sign_and_verify_demo_p256(self):
        signed=api.sign_test_only_p256(demo(),KEY)
        r=self.client().post("/api/v1/verify",json={"receipt":signed,"pinned_public_key_pem":PIN})
        self.assertTrue(r.json()["valid"],r.text)
        self.assertEqual(r.json()["verdict"],"SIGNED_PAYLOAD_INTEGRITY_ONLY")
    def test_tamper_rejected(self):
        signed=api.sign_test_only_p256(demo(),KEY)
        signed["body"]["measurement_sixteenths_c"]=480
        self.assertFalse(api.verify_p256(signed,PIN)["valid"])
    def test_wrong_trust_anchor(self):
        signed=api.sign_test_only_p256(demo(),KEY)
        different=ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        self.assertFalse(api.verify_p256(signed,different)["valid"])
    def test_algorithm_swap_rejected(self):
        signed=api.sign_test_only_p256(demo(),KEY)
        signed["signature"]["algorithm"]="Ed25519"
        self.assertFalse(api.verify_p256(signed,PIN)["valid"])
    def test_signature_tamper(self):
        signed=api.sign_test_only_p256(demo(),KEY)
        signed["signature"]["value"]="00"
        self.assertFalse(api.verify_p256(signed,PIN)["valid"])
    def test_test_signer_refuses_real_claim(self):
        body=demo();body["source_tier"]="REAL_HARDWARE"
        with self.assertRaises(ValueError):api.sign_test_only_p256(body,KEY)
    def test_verifier_missing_pin(self):
        r=self.client().post("/api/v1/verify",json={"receipt":api.sign_test_only_p256(demo(),KEY)})
        self.assertEqual(r.status_code,422)

if __name__=="__main__":unittest.main()
