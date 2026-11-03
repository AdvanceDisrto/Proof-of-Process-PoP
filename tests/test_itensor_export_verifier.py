import copy,unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from integrations.eil_production_trust import digest,canonical
from integrations.itensor_eight_stage import EightStagePipeline,signed_record,byte_width_adapter
from integrations.itensor_export_verifier import verify_export

def public(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()

class IndependentExportVerifierTests(unittest.TestCase):
    def setUp(self):
        self.op=Ed25519PrivateKey.generate(); self.signer=Ed25519PrivateKey.generate()
        self.a={"schema":"ipqr/operator-authorization/v1","operation":"byte_width",
                "request_id":"r-1","arguments_hash":digest(canonical({"unit":"byte"})),"parent":None}
        auth=signed_record(self.a,self.op.sign,public(self.op))
        pipe=EightStagePipeline({"enabled":True,"allow_operations":["byte_width"]},
            public(self.op),public(self.signer),self.signer.sign,{"byte_width":byte_width_adapter})
        self.bundle=pipe.run(auth,{"operation":"byte_width","arguments":{"unit":"byte"},"request_id":"r-1"})
    def check(self,bundle=None,operator=None,receipt=None,ops=None,**kwargs):
        return verify_export(bundle if bundle is not None else self.bundle,
            operator if operator is not None else public(self.op),
            receipt if receipt is not None else public(self.signer),
            ops if ops is not None else {"byte_width"},**kwargs)["verdict"]
    def test_valid_local(self):self.assertEqual(self.check(),"ACCEPT_LOCAL_INTEGRITY")
    def test_fake_production_trust(self):
        d=copy.deepcopy(self.bundle);d["production_trust"]="ESTABLISHED"
        self.assertEqual(self.check(d),"REJECT")
    def test_fake_anchor(self):
        d=copy.deepcopy(self.bundle);d["external_anchor"]={"verified":True}
        self.assertEqual(self.check(d),"REJECT")
    def test_tamper_result(self):
        d=copy.deepcopy(self.bundle);d["receipt"]["body"]["result"]["bits"]=9
        self.assertEqual(self.check(d),"REJECT")
    def test_wrong_operator(self):self.assertEqual(self.check(operator=public(Ed25519PrivateKey.generate())),"REJECT")
    def test_wrong_signer(self):self.assertEqual(self.check(receipt=public(Ed25519PrivateKey.generate())),"REJECT")
    def test_operation_policy(self):self.assertEqual(self.check(ops={"inference"}),"REJECT")
    def test_missing_policy(self):self.assertEqual(self.check(ops=set()),"REJECT")
    def test_parent_mismatch(self):self.assertEqual(self.check(expected_parent="sha256:"+"0"*64),"REJECT")
    def test_request_replay(self):self.assertEqual(self.check(seen_requests={"r-1"}),"REJECT")
    def test_modified_auth(self):
        d=copy.deepcopy(self.bundle);d["authorization"]["body"]["operation"]="fake"
        self.assertEqual(self.check(d),"REJECT")
    def test_distinct_roles(self):self.assertEqual(self.check(receipt=public(self.op)),"REJECT")
    def test_add_unknown_field(self):
        d=copy.deepcopy(self.bundle);d["production_verified"]=True
        self.assertEqual(self.check(d),"REJECT")
    def test_bad_output_binding_with_valid_receipt_signer(self):
        d=copy.deepcopy(self.bundle)
        d["receipt"]["body"]["result_hash"]="sha256:"+"f"*64
        d["receipt"]["hash"]=digest(canonical(d["receipt"]["body"]))
        d["receipt"]["signature_hex"]=self.signer.sign(canonical(d["receipt"]["body"])).hex()
        self.assertEqual(self.check(d),"REJECT")
if __name__=="__main__":unittest.main()
