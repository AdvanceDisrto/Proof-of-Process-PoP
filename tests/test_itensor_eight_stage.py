import copy,unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from integrations.eil_production_trust import canonical,digest
from integrations.itensor_eight_stage import EightStagePipeline,PipelineBlocked,signed_record,byte_width_adapter,validate_record

def pub(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
class EightStageTests(unittest.TestCase):
    def setUp(self):
        self.operator=Ed25519PrivateKey.generate()
        self.receipt_key=Ed25519PrivateKey.generate()
        self.calls=[]
        def adapter(arguments):
            self.calls.append(arguments)
            return byte_width_adapter(arguments)
        self.pipe=EightStagePipeline({"enabled":True,"allow_operations":["byte_width"]},
            pub(self.operator),pub(self.receipt_key),self.receipt_key.sign,{"byte_width":adapter})
        self.command={"operation":"byte_width","arguments":{"unit":"byte"},"request_id":"req-001"}
        self.auth_body={"schema":"ipqr/operator-authorization/v1","operation":"byte_width",
            "request_id":"req-001","arguments_hash":digest(canonical(self.command["arguments"])),"parent":None}
        self.auth=signed_record(self.auth_body,self.operator.sign,pub(self.operator))
    def test_valid_local_flow(self):
        result=self.pipe.run(self.auth,self.command)
        self.assertEqual(result["status"],"LOCAL_INTEGRITY_VERIFIED")
        self.assertEqual(result["receipt"]["body"]["result"]["bits"],8)
        self.assertTrue(validate_record(result["receipt"],pub(self.receipt_key)))
        self.assertIsNone(result["external_anchor"])
        self.assertEqual(len(self.calls),1)
    def test_tampered_auth_prevents_execution(self):
        forged=copy.deepcopy(self.auth);forged["body"]["operation"]="other"
        with self.assertRaises(PipelineBlocked):self.pipe.run(forged,self.command)
        self.assertEqual(self.calls,[])
    def test_wrong_operator_key_blocks(self):
        self.pipe.operator_pubkey=pub(Ed25519PrivateKey.generate())
        with self.assertRaises(PipelineBlocked):self.pipe.run(self.auth,self.command)
        self.assertEqual(self.calls,[])
    def test_arguments_change_blocked(self):
        self.command["arguments"]={"unit":"kilobyte"}
        with self.assertRaises(PipelineBlocked):self.pipe.run(self.auth,self.command)
        self.assertEqual(self.calls,[])
    def test_request_id_change_blocked(self):
        self.command["request_id"]="req-other"
        with self.assertRaises(PipelineBlocked):self.pipe.run(self.auth,self.command)
        self.assertEqual(self.calls,[])
    def test_scope_change_blocked(self):
        with self.assertRaises(PipelineBlocked):self.pipe.run(self.auth,self.command,expected_parent="sha256:"+"1"*64)
        self.assertEqual(self.calls,[])
    def test_policy_disabled(self):
        self.pipe.policy["enabled"]=False
        with self.assertRaises(PipelineBlocked):self.pipe.run(self.auth,self.command)
        self.assertEqual(self.calls,[])
    def test_missing_adapter(self):
        self.pipe.adapters.clear()
        with self.assertRaises(PipelineBlocked):self.pipe.run(self.auth,self.command)
        self.assertEqual(self.calls,[])
    def test_no_unapproved_extra_fields(self):
        self.command["shell"]="rm -rf /"
        with self.assertRaises(PipelineBlocked):self.pipe.run(self.auth,self.command)
        self.assertEqual(self.calls,[])
    def test_wrong_receipt_key_rejected(self):
        self.pipe.receipt_pubkey=pub(Ed25519PrivateKey.generate())
        with self.assertRaises(PipelineBlocked):self.pipe.run(self.auth,self.command)
    def test_invalid_result_fails(self):
        self.pipe.adapters["byte_width"]=lambda _:5
        with self.assertRaises(PipelineBlocked):self.pipe.run(self.auth,self.command)
    def test_signed_receipt_tampering_rejected(self):
        receipt=self.pipe.run(self.auth,self.command)["receipt"]
        receipt["body"]["result"]["bits"]=9
        self.assertFalse(validate_record(receipt,pub(self.receipt_key)))
if __name__=="__main__":unittest.main()
