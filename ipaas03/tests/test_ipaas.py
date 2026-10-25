import gc, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from control.store import Store, Service

class StoreTests(unittest.TestCase):
    def _run(self, fn):
        with tempfile.TemporaryDirectory() as td:
            store = Store(Path(td) / "t.db")
            try: fn(store)
            finally: store.close(); del store; gc.collect()

    def test_create_and_get(self):
        self._run(lambda s: (self.assertTrue(s.create_service(Service("site","x","static","echo"))["ok"]), self.assertEqual(s.get_service("site")["runtime"], "static")))

    def test_duplicate_service_rejected(self):
        def body(s):
            s.create_service(Service("a","x","static","echo"))
            self.assertFalse(s.create_service(Service("a","x","static","echo"))["ok"])
        self._run(body)

    def test_deploy_lifecycle(self):
        def body(s):
            s.create_service(Service("a","x","static","echo"))
            r=s.create_deploy("a","abc123"); d=s.claim_next_deploy()
            self.assertEqual(d["status"],"building")
            s.finish_deploy(d["deploy_id"],True,"/tmp/l")
            self.assertEqual(s.list_deploys("a")[0]["status"],"live")
        self._run(body)

    def test_receipt_chain_verifies(self):
        def body(s):
            s.create_service(Service("a","x","static","echo")); s.create_deploy("a")
            d=s.claim_next_deploy(); s.finish_deploy(d["deploy_id"],True)
            v=s.verify_chain(); self.assertTrue(v["ok"]); self.assertGreaterEqual(v["length"],2)
        self._run(body)

    def test_audit_written_on_every_mutation(self):
        self._run(lambda s: (s.create_service(Service("a","x","static","echo")), self.assertGreaterEqual(len(s.audit_log()),1)))
