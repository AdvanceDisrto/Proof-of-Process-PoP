import gc, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from control.store import Store, Service
from control.rbac import RBAC
from control.previews import PreviewManager
from autoscale.manager import Autoscaler, ScalePolicy
from router.caddy_gen import render_caddyfile

class EnterpriseTests(unittest.TestCase):
    def _store(self):
        td=tempfile.TemporaryDirectory(); return td, Store(Path(td.name)/"t.db")

    def test_roles_and_permissions(self):
        td,s=self._store()
        try:
            r=RBAC(s); r.add_user("a","admin"); r.add_user("d","deployer"); r.add_user("v","viewer")
            self.assertTrue(r.has_permission("a","anything:any")); self.assertTrue(r.has_permission("d","deploy:create"))
            self.assertFalse(r.has_permission("d","user:create")); self.assertTrue(r.has_permission("v","service:read")); self.assertFalse(r.has_permission("v","deploy:create"))
        finally: s.close(); td.cleanup(); gc.collect()

    def test_revoke(self):
        td,s=self._store()
        try:
            r=RBAC(s); r.add_user("a","admin"); r.remove_user("a"); self.assertFalse(r.has_permission("a","anything"))
        finally: s.close(); td.cleanup(); gc.collect()

    def test_main_branch_rejected(self):
        td,s=self._store()
        try:
            s.create_service(Service("a","x","static","echo")); self.assertFalse(PreviewManager(s).create("a","main")["ok"])
        finally: s.close(); td.cleanup(); gc.collect()

    def test_branch_creates_preview(self):
        td,s=self._store()
        try:
            s.create_service(Service("a","x","static","echo")); r=PreviewManager(s).create("a","feature/login")
            self.assertTrue(r["ok"]); self.assertIn("feature-login",r["hostname"])
        finally: s.close(); td.cleanup(); gc.collect()

    def test_policy_set_and_get(self):
        td,s=self._store()
        try:
            a=Autoscaler(s); a.set_policy(ScalePolicy("svc",1,4)); self.assertEqual(a.get_policy("svc"),{"min_replicas":1,"max_replicas":4})
        finally: s.close(); td.cleanup(); gc.collect()

    def test_static_renders_with_cache(self):
        out=render_caddyfile([{"name":"site","runtime":"static","hostname":"site.example.com"}],3600)
        self.assertIn("site.example.com",out); self.assertIn("file_server",out); self.assertIn("max-age=3600",out)

    def test_web_renders_upstreams(self):
        out=render_caddyfile([{"name":"api","runtime":"python","hostname":"api.example.com"}],upstreams={"api":[("127.0.0.1",8000),("127.0.0.1",8001)]})
        self.assertIn("reverse_proxy",out); self.assertIn("127.0.0.1:8000",out); self.assertIn("Upgrade",out)
