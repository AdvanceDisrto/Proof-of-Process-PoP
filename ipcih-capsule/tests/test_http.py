import threading,unittest,urllib.request
from functools import partial
from http.server import ThreadingHTTPServer
from ipcih.serve import Headers,ROOT

class LocalHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),partial(Headers,directory=str(ROOT)))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=3)
    def open(self,path):return urllib.request.urlopen('http://127.0.0.1:'+str(self.server.server_port)+path,timeout=2)
    def test_index_served(self):
        with self.open('/index.html') as r:
            self.assertIn(b'INDEPENDENT TRUST',r.read());self.assertEqual(r.headers['Cache-Control'],'no-store')
    def test_verifier_js_served(self):
        with self.open('/verifier.mjs') as r:self.assertIn(b'crypto.subtle.verify',r.read())
    def test_ui_requires_user_boot(self):
        with self.open('/ui.mjs') as r:
            s=r.read();self.assertIn(b"get('boot').addEventListener('click'",s)
            self.assertNotIn(b'getUserMedia',s)
    def test_no_cdn_dependence(self):
        with self.open('/index.html') as r:
            s=r.read();self.assertNotIn(b'cdn.jsdelivr',s);self.assertNotIn(b'allow-same-origin',s)
    def test_camera_disabled(self):
        with self.open('/index.html') as r:self.assertEqual(r.headers['Permissions-Policy'],'camera=(), microphone=(), geolocation=()')
