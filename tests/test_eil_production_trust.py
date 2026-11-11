import copy, pathlib, tempfile, unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from integrations.eil_production_trust import ProductionGate,canonical,digest,AppendOnlyLedger,verify_sig

def pub(k):return k.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
class TrustGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        d=pathlib.Path(self.temp.name)
        self.keys={role:Ed25519PrivateKey.generate() for role in ("requester","executor","verifier","policy_gate","inference_witness","bitcoin_witness","printer_witness")}
        root={"issuer_pub_hex":pub(self.keys["policy_gate"])}
        self.root=d/"root.json";self.root.write_bytes(canonical(root))
        self.policy={"schema":"ipqr/production-trust-policy/v1","enabled":True,"root_sha256":digest(self.root.read_bytes()),"root_issuer_pub_hex":root["issuer_pub_hex"],"role_pubkeys":{r:pub(k) for r,k in self.keys.items()},"allowed_operations":["byte_width"],"allowed_transition_scopes":["REPORT_ONLY"],"min_bitcoin_confirmations":3}
        self.policy_path=d/"policy.json";self.policy_path.write_bytes(canonical(self.policy))
        self.gate=ProductionGate(self.root,self.policy_path,digest(self.root.read_bytes()),digest(self.policy_path.read_bytes()))
        self.nodes=[];prev=None
        for stage,role,fields in (("INTENT","requester",{"task":"byte_width","authorized_operation":"byte_width"}),("EXECUTION","executor",{"operation":"byte_width","result":"8 bits"}),("VERIFICATION","verifier",{"passed":True}),("TRANSITION","policy_gate",{"decision":"ALLOW","scope":"REPORT_ONLY"})):
            body={"schema":"ipqr/eil-node/v1","stage":stage,"previous":prev,**fields}
            prev=digest(canonical(body))
            self.nodes.append({"payload":body,"hash":prev,"signature":{"role":role,"public_key":pub(self.keys[role]),"hex":self.keys[role].sign(canonical(body)).hex()}})
        self.witnesses={}
        for kind,data in (("inference",{"observed":True,"output_hash":digest(b"8 bits"),"operation":"byte_width"}),("printer",{"observed":True,"printed_graph_tip":prev}),("bitcoin",{"observed":True,"network":"mainnet","txid":"a"*64,"commitment":prev})):
            body={"schema":"ipqr/eil-witness/v1","kind":kind,"graph_tip":prev,**data}
            self.witnesses[kind]={"body":body,"signature_hex":self.keys[kind+"_witness"].sign(canonical(body)).hex()}
        self.fake_lookup=lambda txid:{"network":"mainnet","commitments":[self.nodes[-1]["hash"]],"confirmations":6}
    def test_development_fixture_only(self):
        self.assertEqual(self.gate.assess(self.nodes,self.witnesses,self.fake_lookup)["verdict"],"ACCEPT")
    def test_no_chain_lookup(self):
        self.assertEqual(self.gate.assess(self.nodes,self.witnesses)["verdict"],"BLOCKED")
    def test_tampered_root(self):
        self.root.write_text("{}")
        self.assertEqual(self.gate.assess(self.nodes,self.witnesses,self.fake_lookup)["verdict"],"BLOCKED")
    def test_untrusted_root_pin(self):
        self.gate.root_pin="sha256:"+"0"*64
        self.assertEqual(self.gate.assess(self.nodes,self.witnesses,self.fake_lookup)["verdict"],"BLOCKED")
    def test_wrong_evidence(self):
        graph=copy.deepcopy(self.nodes);graph[1]["payload"]["result"]="9 bits"
        self.assertEqual(self.gate.assess(graph,self.witnesses,self.fake_lookup)["verdict"],"BLOCKED")
    def test_self_reported_success_not_enough(self):
        witnesses=copy.deepcopy(self.witnesses);witnesses["bitcoin"]["body"]["verified"]=True
        self.assertEqual(self.gate.assess(self.nodes,witnesses,self.fake_lookup)["verdict"],"BLOCKED")
    def test_fake_bitcoin_commitment_rejected(self):
        result=self.gate.assess(self.nodes,self.witnesses,lambda _:{"network":"mainnet","commitments":[],"confirmations":6})
        self.assertEqual(result["verdict"],"BLOCKED")
    def test_missing_witness(self):
        witnesses=copy.deepcopy(self.witnesses);del witnesses["printer"]
        self.assertEqual(self.gate.assess(self.nodes,witnesses,self.fake_lookup)["verdict"],"BLOCKED")
    def test_signature_byte_tamper(self):
        self.assertFalse(verify_sig({"t":2},"00"*64,pub(self.keys["requester"])))
    def test_ledger_tamper(self):
        db=AppendOnlyLedger(str(pathlib.Path(self.temp.name)/"ledger.sqlite"))
        db.append({"hello":1});db.append({"hello":2});self.assertTrue(db.verify())
        db.conn.execute("UPDATE receipts SET body=? WHERE seq=1",(b'{"hello":9}',));db.conn.commit()
        self.assertFalse(db.verify())
if __name__=="__main__":unittest.main()
