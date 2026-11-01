import copy,unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from integrations.minimal_warrant import mint,verify_t1,pub,sha,sign_evidence,verify_warrant
class MinimalWarrantTests(unittest.TestCase):
    def setUp(self):
        self.k=Ed25519PrivateKey.generate();self.s=Ed25519PrivateKey.generate();self.e=b"CI job 1 passed"
        self.ev=sign_evidence(self.e,"github_ci","B",self.s)
        self.r=mint({"result":"passed","evidence_hash":sha(self.e)},self.k)
        self.policy={"trusted_claimants":[pub(self.k)],"trusted_source_pubkeys":[pub(self.s)],
            "min_grade_by_claim_type":{"ci":"B"},"max_grade_by_source_pubkey":{pub(self.s):"B"}}
    def outcome(self,r=None,e=None,ev=None,p=None):
        return verify_warrant(r if r is not None else self.r,"ci",
            e if e is not None else self.e,ev if ev is not None else self.ev,
            p if p is not None else self.policy)["tier"]
    def test_t1(self):self.assertTrue(verify_t1(self.r,{pub(self.k)}))
    def test_bad_claimant(self):self.assertFalse(verify_t1(self.r,{pub(Ed25519PrivateKey.generate())}))
    def test_tamper(self):
        x=copy.deepcopy(self.r);x["body"]["claim"]["result"]="failed"
        self.assertFalse(verify_t1(x,{pub(self.k)}))
    def test_t2(self):self.assertEqual(self.outcome(),"T2_WARRANT")
    def test_wrong_evidence(self):self.assertEqual(self.outcome(e=b"changed"),"REJECTED")
    def test_bad_source(self):
        x=copy.deepcopy(self.ev);x["signature"]="00"*64
        self.assertEqual(self.outcome(ev=x),"REJECTED")
    def test_untrusted_source(self):
        p=copy.deepcopy(self.policy);p["trusted_source_pubkeys"]=[]
        self.assertEqual(self.outcome(p=p),"REJECTED")
    def test_grade_ceiling(self):
        x=sign_evidence(self.e,"github_ci","A",self.s)
        self.assertEqual(self.outcome(ev=x),"REJECTED")
    def test_missing_evidence_link(self):
        r=mint({"result":"passed"},self.k)
        self.assertEqual(self.outcome(r=r),"REJECTED")
    def test_untrusted_claimant(self):
        p=copy.deepcopy(self.policy);p["trusted_claimants"]=[]
        self.assertEqual(self.outcome(p=p),"REJECTED")
if __name__=="__main__":unittest.main()
