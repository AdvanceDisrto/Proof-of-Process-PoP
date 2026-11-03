import copy,sys,unittest
from unittest.mock import patch
from integrations.cuda_observation import (N,SCHEMA,expected_output_bytes,
        verify_cuda_observation,run_cuda)
from integrations.hardware_neutral_receipt import digest

def fixture():
    return {"schema":SCHEMA,"scope":"UNATTESTED_CUDA_RUNTIME_REPORT",
            "cuda_available":True,"device_name_reported":"FIXTURE_ONLY_NOT_REAL_GPU",
            "task":"int64_linear_transform_x3_plus_7",
            "elements":N,"output_hash":digest(expected_output_bytes()),
            "external_anchor":None,"production_trust":"UNVERIFIED",
            "physical_gpu_attestation":None}

class CudaObservationTests(unittest.TestCase):
    def test_cpu_recomputes_fixture_arithmetic_not_gpu_proof(self):
        result=verify_cuda_observation(fixture())
        self.assertEqual(result["verdict"],"ARITHMETIC_RECOMPUTED")
        self.assertIs(result["hardware_proven"],False)
    def test_missing_torch_blocks(self):
        with patch.dict(sys.modules,{"torch":None}):
            self.assertEqual(run_cuda()["verdict"],"BLOCKED")
    def test_changed_output_blocks(self):
        data=fixture();data["output_hash"]="sha256:"+"0"*64
        self.assertEqual(verify_cuda_observation(data)["verdict"],"BLOCKED")
    def test_fake_attestation_blocks(self):
        data=fixture();data["physical_gpu_attestation"]={"claimed":True}
        self.assertEqual(verify_cuda_observation(data)["verdict"],"BLOCKED")
    def test_fake_production_trust_blocks(self):
        data=fixture();data["production_trust"]="VERIFIED"
        self.assertEqual(verify_cuda_observation(data)["verdict"],"BLOCKED")
    def test_external_anchor_injection_blocks(self):
        data=fixture();data["external_anchor"]={"confirmed":True}
        self.assertEqual(verify_cuda_observation(data)["verdict"],"BLOCKED")
    def test_wrong_count_blocks(self):
        data=fixture();data["elements"]=N+1
        self.assertEqual(verify_cuda_observation(data)["verdict"],"BLOCKED")
    def test_missing_device_claim_blocks(self):
        data=fixture();data["device_name_reported"]=""
        self.assertEqual(verify_cuda_observation(data)["verdict"],"BLOCKED")
    def test_missing_field_blocks(self):
        data=fixture();del data["scope"]
        self.assertEqual(verify_cuda_observation(data)["verdict"],"BLOCKED")
    def test_cpu_expected_is_deterministic(self):
        self.assertEqual(expected_output_bytes()[:3],b'[7,')
if __name__=="__main__":unittest.main()
