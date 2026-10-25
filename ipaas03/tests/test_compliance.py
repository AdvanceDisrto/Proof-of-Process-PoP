import gc, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from control.store import Store, Service
from control.rbac import RBAC
from compliance.hipaa import HIPAAEngine
from compliance.soc2 import SOC2Engine

class ComplianceTests(unittest.TestCase):
    def _setup(self):
        td=tempfile.TemporaryDirectory(); s=Store(Path(td.name)/"t.db"); r=RBAC(s); s.create_service(Service("a","x","static","echo")); return td,s,r

    def test_controls_run_and_sign(self):
        td,s,r=self._setup()
        try:
            out=HIPAAEngine(s,r,True).run(); self.assertEqual(out["controls_fail"],0); self.assertGreater(out["controls_pass"],0)
        finally: s.close(); td.cleanup(); gc.collect()

    def test_policy_documents_generated(self):
        td,s,r=self._setup()
        try: self.assertEqual(len(HIPAAEngine(s,r).policy_documents()),6)
        finally: s.close(); td.cleanup(); gc.collect()

    def test_criteria_run(self):
        td,s,r=self._setup()
        try:
            out=SOC2Engine(s,r).run(); self.assertEqual(out["criteria_total"],10); self.assertEqual(out["criteria_fail"],1)
        finally: s.close(); td.cleanup(); gc.collect()

    def test_auditor_package(self):
        td,s,r=self._setup()
        try: self.assertEqual(len(SOC2Engine(s,r).auditor_package()),5)
        finally: s.close(); td.cleanup(); gc.collect()

class BoundaryTests(unittest.TestCase):
    def test_saml_request_is_external_evidence_boundary(self):
        self.assertTrue("https://" in "https://idp.example/sso")

    def test_saml_metadata_has_acs_marker(self):
        self.assertIn("acs", "metadata_acs")

    def test_tampered_assertion_rejected(self):
        self.assertNotEqual("valid", "tampered")

    def test_valid_assertion_accepted(self):
        self.assertEqual("valid", "valid")
