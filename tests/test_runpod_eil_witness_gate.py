import copy
import json
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from integrations.eil_production_trust import canonical,digest
from integrations.runpod_eil_gpu import SCHEMA, COUNT, expected_vector, sha, encoded
from integrations.runpod_eil_witness_gate import assess, WITNESS_SCHEMA, ROLE

def public(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()

class RunpodWitnessGateTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        directory=Path(t.name)
        self.keys={role:Ed25519PrivateKey.generate() for role in
            ("requester","executor","verifier","policy_gate","inference_witness",
             "printer_witness","bitcoin_witness")}
        self.root=directory/"itensor-root.json"
        self.root.write_bytes(canonical({"issuer_pub_hex":public(self.keys["policy_gate"])}))
        self.root_pin=digest(self.root.read_bytes())
        self.policy=directory/"policy.json"
        self.policy_data={
            "schema":"ipqr/production-trust-policy/v1",
            "enabled":True,
            "root_sha256":self.root_pin,
            "root_issuer_pub_hex":public(self.keys["policy_gate"]),
            "role_pubkeys":{role:public(key) for role,key in self.keys.items()},
            "min_bitcoin_confirmations":3,
            "allow_gpu_development_observation":True
        }
        self.policy.write_bytes(canonical(self.policy_data))
        self.policy_pin=digest(self.policy.read_bytes())
        self.nonce="a"*64
        output_hash=sha(encoded(expected_vector(self.nonce)))
        self.observation={
            "schema":SCHEMA,"verdict":"CUDA_RUNTIME_OBSERVATION","nonce":self.nonce,
            "provider_reported":"RUNPOD","pod_id_reported":"SYNTHETIC_TEST_POD",
            "hardware_reported":"SIMULATED_GPU_FIXTURE","cuda_runtime_reported":"fixture",
            "operation":"int64_challenged_vector_v1","count":COUNT,
            "output_sha256":output_hash,"expected_sha256":output_hash,
            "production_trust":"UNVERIFIED","hardware_attestation":None,
            "external_anchor":None,"independent_witness":None
        }
        self.witness_body={
            "schema":WITNESS_SCHEMA,"role":ROLE,"nonce":self.nonce,
            "observation_hash":digest(canonical(self.observation)),
            "observed_output_hash":output_hash,
            "claim_scope":"INDEPENDENT_REVIEW_OF_UNATTESTED_CUDA_REPORT",
            "authority_root_sha256":self.root_pin
        }
        self.witness=self.sign_witness(self.witness_body)
    def sign_witness(self,body):
        return {"body":body,
                "public_key_hex":public(self.keys["inference_witness"]),
                "signature_hex":self.keys["inference_witness"].sign(canonical(body)).hex()}
    def check(self,observation=None,witness=None,nonce=None,seen=None,root_pin=None,policy_pin=None):
        return assess(self.observation if observation is None else observation,
             self.witness if witness is None else witness,
             root_path=self.root,policy_path=self.policy,
             root_pin=self.root_pin if root_pin is None else root_pin,
             policy_pin=self.policy_pin if policy_pin is None else policy_pin,
             expected_nonce=self.nonce if nonce is None else nonce,
             seen_challenges=set() if seen is None else seen)
    def test_valid_signed_fixture_only(self):
        result=self.check()
        self.assertEqual(result["verdict"],"SIGNED_DEVELOPMENT_WITNESS_VALID")
        self.assertFalse(result["gpu_hardware_attested"])
        self.assertEqual(result["production_trust"],"UNVERIFIED")
    def test_missing_replay_registry_blocks(self):
        result=assess(self.observation,self.witness,root_path=self.root,
          policy_path=self.policy,root_pin=self.root_pin,policy_pin=self.policy_pin,
          expected_nonce=self.nonce)
        self.assertEqual(result["verdict"],"BLOCKED")
    def test_reused_challenge_blocks(self):
        self.assertEqual(self.check(seen={self.nonce})["verdict"],"BLOCKED")
    def test_invalid_nonce_blocks(self):
        self.assertEqual(self.check(nonce="b"*64)["verdict"],"BLOCKED")
    def test_observation_tamper_blocks(self):
        record=copy.deepcopy(self.observation);record["output_sha256"]="sha256:"+"0"*64
        self.assertEqual(self.check(observation=record)["verdict"],"BLOCKED")
    def test_witness_signature_tamper_blocks(self):
        record=copy.deepcopy(self.witness);record["signature_hex"]="00"*64
        self.assertEqual(self.check(witness=record)["verdict"],"BLOCKED")
    def test_witness_key_spoof_blocks(self):
        record=copy.deepcopy(self.witness);record["public_key_hex"]="11"*32
        self.assertEqual(self.check(witness=record)["verdict"],"BLOCKED")
    def test_wrong_root_pin_blocks(self):
        self.assertEqual(self.check(root_pin="sha256:"+"1"*64)["verdict"],"BLOCKED")
    def test_wrong_policy_pin_blocks(self):
        self.assertEqual(self.check(policy_pin="sha256:"+"1"*64)["verdict"],"BLOCKED")
    def test_unapproved_policy_blocks(self):
        self.policy_data["allow_gpu_development_observation"]=False
        self.policy.write_bytes(canonical(self.policy_data))
        self.policy_pin=digest(self.policy.read_bytes())
        self.assertEqual(self.check()["verdict"],"BLOCKED")
    def test_witness_incorrect_output_binding_blocks(self):
        body=copy.deepcopy(self.witness_body);body["observed_output_hash"]="sha256:"+"0"*64
        self.assertEqual(self.check(witness=self.sign_witness(body))["verdict"],"BLOCKED")
    def test_witness_claim_promotion_blocks(self):
        body=copy.deepcopy(self.witness_body);body["claim_scope"]="PRODUCTION_GPU_ATTESTED"
        self.assertEqual(self.check(witness=self.sign_witness(body))["verdict"],"BLOCKED")
    def test_root_issuer_change_blocks(self):
        self.root.write_bytes(canonical({"issuer_pub_hex":"0"*64}))
        self.assertEqual(self.check()["verdict"],"BLOCKED")
    def test_missing_policy_blocks(self):
        self.policy.unlink()
        self.assertEqual(self.check()["verdict"],"BLOCKED")
if __name__=="__main__":unittest.main()
