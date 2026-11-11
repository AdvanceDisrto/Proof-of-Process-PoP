import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from integrations.runpod_eil_gpu import (
    COUNT, SCHEMA, expected_vector, encoded, sha, observe, verify, main
)

NONCE="a"*64

def fixture():
    h=sha(encoded(expected_vector(NONCE)))
    return {"schema":SCHEMA,"verdict":"CUDA_RUNTIME_OBSERVATION",
            "nonce":NONCE,"provider_reported":"RUNPOD","pod_id_reported":"DEVELOPMENT_FIXTURE",
            "hardware_reported":"FIXTURE_NOT_A_REAL_GPU","cuda_runtime_reported":"mock",
            "operation":"int64_challenged_vector_v1","count":COUNT,
            "output_sha256":h,"expected_sha256":h,"production_trust":"UNVERIFIED",
            "hardware_attestation":None,"external_anchor":None,
            "independent_witness":None}

class RunpodGPUFailClosedTests(unittest.TestCase):
    def test_fixture_arithmetic_not_gpu_proof(self):
        result=verify(fixture(),NONCE)
        self.assertEqual(result["verdict"],"CHALLENGED_ARITHMETIC_MATCH")
        self.assertFalse(result["gpu_hardware_attested"])
        self.assertFalse(result["provider_authenticated"])
    def test_missing_pod_fails(self):
        with patch.dict("os.environ",{},clear=True):
            self.assertEqual(observe(NONCE)["verdict"],"BLOCKED")
    def test_missing_torch_fails(self):
        with patch.dict("os.environ",{"RUNPOD_POD_ID":"fixture"},clear=True):
            with patch.dict("sys.modules",{"torch":None}):
                self.assertEqual(observe(NONCE)["verdict"],"BLOCKED")
    def test_short_nonce_fails(self):
        self.assertEqual(observe("short")["verdict"],"BLOCKED")
    def test_tamper_result_fails(self):
        record=fixture();record["output_sha256"]="sha256:"+"0"*64
        self.assertEqual(verify(record,NONCE)["verdict"],"BLOCKED")
    def test_tamper_challenge_fails(self):
        self.assertEqual(verify(fixture(),"b"*64)["verdict"],"BLOCKED")
    def test_fake_attestation_fails(self):
        record=fixture();record["hardware_attestation"]={"trusted":True}
        self.assertEqual(verify(record,NONCE)["verdict"],"BLOCKED")
    def test_fake_external_anchor_fails(self):
        record=fixture();record["external_anchor"]={"confirmed":True}
        self.assertEqual(verify(record,NONCE)["verdict"],"BLOCKED")
    def test_fake_witness_fails(self):
        record=fixture();record["independent_witness"]={"verified":True}
        self.assertEqual(verify(record,NONCE)["verdict"],"BLOCKED")
    def test_fake_production_trust_fails(self):
        record=fixture();record["production_trust"]="VERIFIED"
        self.assertEqual(verify(record,NONCE)["verdict"],"BLOCKED")
    def test_fake_provider_fails(self):
        record=fixture();record["provider_reported"]="OTHER"
        self.assertEqual(verify(record,NONCE)["verdict"],"BLOCKED")
    def test_unknown_extra_field_fails(self):
        record=fixture();record["gpu_proven"]=True
        self.assertEqual(verify(record,NONCE)["verdict"],"BLOCKED")
    def test_bad_count_fails(self):
        record=fixture();record["count"]=False
        self.assertEqual(verify(record,NONCE)["verdict"],"BLOCKED")
    def test_wrong_hardware_claim_fails(self):
        record=fixture();record["hardware_reported"]=""
        self.assertEqual(verify(record,NONCE)["verdict"],"BLOCKED")
    def test_cli_fixture_readable_only_as_development_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"observation.json"
            path.write_bytes(encoded(fixture()))
            self.assertEqual(main(["verify","--nonce",NONCE,"--input",str(path)]),0)
    def test_cli_missing_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main(["verify","--nonce",NONCE,
                                   "--input",str(Path(tmp)/"missing.json")]),2)
if __name__=="__main__":unittest.main()
