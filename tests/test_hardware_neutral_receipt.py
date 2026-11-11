import copy,unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from integrations.hardware_neutral_receipt import observation,sign,verify,export_for_edge,hardware_capability_matrix,canonical,digest,DOMAIN
def pub(k):
    return k.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()

class PortableReceiptTests(unittest.TestCase):
    def setUp(self):
        self.k=Ed25519PrivateKey.generate();self.key=pub(self.k);self.e=b'voltage=123.45 (synthetic)'
        self.body=observation(device_class="CPU",operation="sensor_observation",
                              evidence_bytes=self.e,request_id="req-1")
        self.r=sign(self.body,self.k.sign,self.key)
    def test_all_declared_device_classes(self):
        for device in ("CPU","GPU","NPU","MCU","MICROPROCESSOR"):
            with self.subTest(device=device):
                b=observation(device_class=device,operation="compute_observation",
                              evidence_bytes=self.e,request_id="req-1")
                r=sign(b,self.k.sign,self.key)
                self.assertTrue(verify(r,{self.key},self.e))
    def test_pinned_identity(self):
        self.assertFalse(verify(self.r,{pub(Ed25519PrivateKey.generate())},self.e))
    def test_tampered_observation(self):
        r=copy.deepcopy(self.r);r["body"]["device_class_reported"]="GPU"
        self.assertFalse(verify(r,{self.key},self.e))
    def test_tampered_evidence(self):
        self.assertFalse(verify(self.r,{self.key},b'voltage=999.99 (synthetic)'))
    def test_no_external_anchor_promotions(self):
        r=copy.deepcopy(self.r);r["external_anchor"]={"verified":True}
        self.assertFalse(verify(r,{self.key},self.e))
    def test_reject_fake_signature(self):
        r=copy.deepcopy(self.r);r["signature"]["signature_hex"]="00"*64
        self.assertFalse(verify(r,{self.key},self.e))
    def test_refuse_wrong_signing_key(self):
        with self.assertRaises(ValueError):
            sign(self.body,Ed25519PrivateKey.generate().sign,self.key)
    def test_unknown_device(self):
        with self.assertRaises(ValueError):
            observation(device_class="H100",operation="sensor_observation",
                        evidence_bytes=self.e,request_id="req-1")
    def test_edge_wire_round_trip(self):
        import json
        decoded=json.loads(export_for_edge(self.r))
        self.assertTrue(verify(decoded,{self.key},self.e))
    def test_external_parent_integrity(self):
        parent=digest(b'previous receipt')
        body=observation(device_class="MCU",operation="sensor_observation",
                         evidence_bytes=self.e,request_id="r-2",parent=parent)
        receipt=sign(body,self.k.sign,self.key)
        self.assertEqual(receipt["body"]["parent"],parent)
        self.assertTrue(verify(receipt,{self.key},self.e))
    def test_domain_separation(self):
        self.assertNotEqual(digest(canonical(self.body)),self.r["receipt_id"])
        self.assertEqual(digest(DOMAIN+canonical(self.body)),self.r["receipt_id"])
    def test_no_real_gpu_claims(self):
        self.assertEqual(hardware_capability_matrix()["GPU"]["benchmark"],"NOT_MEASURED")
    def test_nonjson_nan_rejected(self):
        with self.assertRaises(ValueError):canonical({"x":float("nan")})
    def test_missing_metadata_rejected(self):
        r=copy.deepcopy(self.r);r["body"].pop("request_id")
        self.assertFalse(verify(r,{self.key}))
    def test_test_vector_reproducible_bytes(self):
        self.assertEqual(canonical({"z":1,"a":2}),b'{"a":2,"z":1}')
if __name__=="__main__":unittest.main()
