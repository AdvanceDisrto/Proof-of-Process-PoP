import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from integrations.aegi_synthetic_ledger import (
    AeGiSyntheticLedger,check_frequency,sign,public,verify,merkle,smoke)

class TestAeGiSyntheticLedger(unittest.TestCase):
    def setUp(self):
        self.key=Ed25519PrivateKey.generate()
        self.engine=AeGiSyntheticLedger()
        self.engine.register("east",3);self.engine.register("west",1)
    def send(self,seq,value):
        f={"device_id":"demo","sequence":seq,"frequency_millihz":value,
           "source_tier":"SYNTHETIC_SIMULATOR"}
        return self.engine.ingest(f,sign(self.key,f),public(self.key))
    def test_valid(self):self.assertEqual(check_frequency(60000),"PROVEN_TRUE")
    def test_invalid(self):self.assertEqual(check_frequency(54200),"REFUTED_FALSE")
    def test_bounds(self):
        self.assertEqual(check_frequency(59900),"PROVEN_TRUE")
        self.assertEqual(check_frequency(60101),"REFUTED_FALSE")
    def test_noninteger(self):
        with self.assertRaises(ValueError):check_frequency(60000.0)
    def test_signature_tamper(self):
        f={"device_id":"demo","sequence":1,"frequency_millihz":60000,
           "source_tier":"SYNTHETIC_SIMULATOR"}
        env=sign(self.key,f);env["body"]["frequency_millihz"]=54000
        with self.assertRaises(ValueError):self.engine.ingest(f,env,public(self.key))
    def test_wrong_pin(self):
        f={"device_id":"demo","sequence":1,"frequency_millihz":60000,
           "source_tier":"SYNTHETIC_SIMULATOR"}
        with self.assertRaises(ValueError):
            self.engine.ingest(f,sign(self.key,f),public(Ed25519PrivateKey.generate()))
    def test_replay(self):
        self.send(1,60000)
        with self.assertRaises(ValueError):self.send(1,60000)
    def test_gap(self):
        with self.assertRaises(ValueError):self.send(3,60000)
    def test_reject_outside(self):
        self.assertFalse(self.send(1,54200)["accepted"])
    def test_signed_block(self):
        self.send(1,60000);b=self.engine.mint("east")
        self.assertTrue(verify(b,self.engine.pin))
        self.assertEqual(b["demo_credit"],"9.3750")
    def test_empty_pool(self):
        with self.assertRaises(ValueError):self.engine.mint("east")
    def test_chain(self):
        self.send(1,60000);a=self.engine.mint("east")
        self.send(2,60000);b=self.engine.mint("east")
        self.assertEqual(b["body"]["previous_block_hash"],a["block_hash"])
    def test_merkle_order(self):
        self.assertNotEqual(merkle(["a"*64,"b"*64]),merkle(["b"*64,"a"*64]))
    def test_negative_weight(self):
        with self.assertRaises(ValueError):self.engine.register("invalid",-1)
    def test_no_fake_hardware(self):
        f={"device_id":"demo","sequence":1,"frequency_millihz":60000,
           "source_tier":"REAL_HARDWARE"}
        with self.assertRaises(ValueError):self.engine.ingest(f,sign(self.key,f),public(self.key))
    def test_smoke(self):
        self.assertEqual(smoke()["status"],"ACCEPT_AEGI_SYNTHETIC_LEDGER_SMOKE")

if __name__=="__main__":unittest.main()
