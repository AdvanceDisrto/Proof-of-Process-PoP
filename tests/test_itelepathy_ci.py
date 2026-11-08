import asyncio, copy, hashlib, tempfile, unittest
from pathlib import Path
from itelepathy import Identity, Sender, Receiver, Rejected, Policy, verify_ack
from itelepathy.core import canonical
from itelepathy.loopback import start_receiver,send_local

class TrustIntent(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.a,self.b,self.bad=Identity("alice"),Identity("buddy"),Identity("untrusted")
        self.policy=Policy()
        self.sender=Sender(self.a,self.policy,consent=True,clock=lambda:1_800_000_000)
        self.receiver=Receiver(self.b,{"alice":self.a.public()},Path(self.tmp.name)/"received.db",
                               self.policy,consent=True,clock=lambda:1_800_000_000)
    def tearDown(self):
        self.receiver.close();self.tmp.cleanup()
    def packet(self):
        return self.sender.seal(self.b.public(),action="SEND_MESSAGE",value=500,message="private")
    def test_real_z3_bound(self):
        self.assertTrue(self.policy.allowed(1000,1000))
        self.assertFalse(self.policy.allowed(1001,1000))
    def test_negative_and_boolean_denied(self):
        self.assertFalse(self.policy.allowed(-1,1000))
        self.assertFalse(self.policy.allowed(True,1000))
    def test_roundtrip_and_offline_ack(self):
        p=self.packet();ack=self.receiver.receive(p)
        self.assertTrue(verify_ack(ack,self.b.public(),p))
        self.assertEqual(ack["body"]["status"],"ACKNOWLEDGED_NO_EXTERNAL_ACTION")
        self.assertNotIn(b"private",canonical(ack))
    def test_confidential_wire(self):
        self.assertNotIn(b"private",canonical(self.packet()))
    def test_replay_denied(self):
        p=self.packet();self.receiver.receive(p)
        with self.assertRaises(Rejected):self.receiver.receive(p)
    def test_stale_order_denied(self):
        p1=self.packet();p2=self.packet();self.receiver.receive(p2)
        with self.assertRaises(Rejected):self.receiver.receive(p1)
    def test_persistent_replay_after_restart(self):
        p=self.packet();self.receiver.receive(p);self.receiver.close()
        self.receiver=Receiver(self.b,{"alice":self.a.public()},Path(self.tmp.name)/"received.db",
                               self.policy,consent=True,clock=lambda:1_800_000_000)
        with self.assertRaises(Rejected):self.receiver.receive(p)
    def test_signature_tamper_denied(self):
        p=self.packet();p["signature_hex"]="00"*64
        with self.assertRaises(Rejected):self.receiver.receive(p)
    def test_ciphertext_tamper_denied(self):
        p=self.packet();p["envelope"]["ciphertext_hex"]="00"+p["envelope"]["ciphertext_hex"][2:]
        with self.assertRaises(Rejected):self.receiver.receive(p)
    def test_ack_tamper_denied(self):
        p=self.packet();ack=self.receiver.receive(p)
        ack["body"]["sequence"]+=1
        self.assertFalse(verify_ack(ack,self.b.public(),p))
    def test_wrong_receiver_denied(self):
        p=self.sender.seal(self.bad.public(),action="PING",value=0)
        with self.assertRaises(Rejected):self.receiver.receive(p)
    def test_untrusted_identity_denied(self):
        p=Sender(self.bad,self.policy,consent=True,clock=lambda:1_800_000_000).seal(
             self.b.public(),action="PING",value=0)
        with self.assertRaises(Rejected):self.receiver.receive(p)
    def test_receiver_consent_required(self):
        p=self.packet();self.receiver.consent=False
        with self.assertRaises(Rejected):self.receiver.receive(p)
    def test_sender_consent_required(self):
        s=Sender(self.a,self.policy,consent=False)
        with self.assertRaises(Rejected):s.seal(self.b.public(),action="PING",value=0)
    def test_expired_packet_denied(self):
        p=self.packet();self.receiver.clock=lambda:1_800_000_100
        with self.assertRaises(Rejected):self.receiver.receive(p)
    def test_receiver_limit_pinned(self):
        p=self.sender.seal(self.b.public(),action="PING",value=500,limit=2000)
        with self.assertRaises(Rejected):self.receiver.receive(p)
    def test_disallowed_financial_door_weapon_commands(self):
        for act in ("TRANSFER_FUNDS","UNLOCK_DOOR","FIRE_WEAPON","EXECUTE_SCRIPT"):
            with self.assertRaises(Rejected):self.sender.seal(self.b.public(),action=act,value=100)
    def test_out_of_range_rejected_before_signing(self):
        before=self.sender.sequence
        with self.assertRaises(Rejected):self.sender.seal(self.b.public(),action="PING",value=100000)
        self.assertEqual(before,self.sender.sequence)
    def test_no_raw_message_persisted(self):
        self.receiver.receive(self.packet())
        self.assertNotIn(b"private",Path(self.tmp.name,"received.db").read_bytes())
    def test_ack_key_pin(self):
        p=self.packet();ack=self.receiver.receive(p)
        self.assertFalse(verify_ack(ack,self.bad.public(),p))

class NetworkIntent(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.a=Identity("alice");self.b=Identity("buddy")
        p=Policy();self.s=Sender(self.a,p,consent=True)
        self.r=Receiver(self.b,{"alice":self.a.public()},Path(self.tmp.name)/"recv.db",p,consent=True)
        self.srv=await start_receiver(self.r)
    async def asyncTearDown(self):
        self.srv.close();await self.srv.wait_closed();self.r.close();self.tmp.cleanup()
    async def test_real_tcp_loopback(self):
        packet=self.s.seal(self.b.public(),action="PING",value=10)
        result=await send_local(self.srv.sockets[0].getsockname()[1],packet)
        self.assertTrue(result["ok"])
        self.assertTrue(verify_ack(result["ack"],self.b.public(),packet))
    async def test_tcp_replay_fails(self):
        packet=self.s.seal(self.b.public(),action="PING",value=10)
        port=self.srv.sockets[0].getsockname()[1]
        self.assertTrue((await send_local(port,packet))["ok"])
        self.assertFalse((await send_local(port,packet))["ok"])
    async def test_tcp_bad_signature_fails(self):
        packet=self.s.seal(self.b.public(),action="PING",value=10)
        packet["signature_hex"]="00"*64
        self.assertEqual((await send_local(self.srv.sockets[0].getsockname()[1],packet))["status"],"REJECTED")

if __name__=="__main__":unittest.main()
