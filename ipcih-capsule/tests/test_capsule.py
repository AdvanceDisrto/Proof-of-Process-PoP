import io, json, tempfile, unittest, copy, zlib
from pathlib import Path
from PIL import Image
from cryptography.hazmat.primitives.asymmetric import ed25519
from ipcih import Issuer,CapsuleRejected,verify,encode_wire,decode_wire,render_dual,decode_exact_color,first_stage_bootstrap,make_qr
from ipcih.core import b64e,b64d,make_app,sha,canonical,MAX_WIRE
from ipcih.auditor import audit_assertion

class CapsuleTest(unittest.TestCase):
    def setUp(self):
        self.key=ed25519.Ed25519PrivateKey.generate()
        self.issuer=Issuer(self.key)
        self.packet=self.issuer.issue('Buddy™ Capsule',now=1800000000)
        self.pub=self.issuer.public_raw()
    def test_proof_scoped(self):
        got=verify(self.packet,self.pub,now=1800000001)
        self.assertEqual(got['claim_truth'],'NOT_EVALUATED')
    def test_no_hardware_claim(self):
        self.assertEqual(self.packet['body']['evidence_tier'],'SYNTHETIC_SOFTWARE')
        self.assertIn('measured joules',self.packet['body']['does_not_prove'])
    def test_tampered_claim(self):
        p=copy.deepcopy(self.packet);p['body']['claim']='Malicious'
        with self.assertRaises(CapsuleRejected):verify(p,self.pub,now=1800000001)
    def test_tampered_code(self):
        p=copy.deepcopy(self.packet);p['body']['app_b64']=b64e(b'<script>alert(1)</script>')
        with self.assertRaises(CapsuleRejected):verify(p,self.pub,now=1800000001)
    def test_tampered_hash(self):
        p=copy.deepcopy(self.packet);p['body']['app_sha256']='0'*64
        with self.assertRaises(CapsuleRejected):verify(p,self.pub,now=1800000001)
    def test_unpinned_key(self):
        with self.assertRaises(CapsuleRejected):verify(self.packet,b'\x01'*32,now=1800000001)
    def test_key_missing(self):
        with self.assertRaises(CapsuleRejected):verify(self.packet,None,now=1800000001)
    def test_expired(self):
        with self.assertRaises(CapsuleRejected):verify(self.packet,self.pub,now=1800001000)
    def test_not_yet_issued(self):
        with self.assertRaises(CapsuleRejected):verify(self.packet,self.pub,now=1799999000)
    def test_invalid_lifetime(self):
        with self.assertRaises(CapsuleRejected):self.issuer.issue('x',now=100,lifetime=0)
        with self.assertRaises(CapsuleRejected):self.issuer.issue('x',now=100,lifetime=4000)
    def test_malformed_schema(self):
        p=copy.deepcopy(self.packet);p['body']['new']='unknown'
        with self.assertRaises(CapsuleRejected):verify(p,self.pub,now=1800000001)
    def test_template_no_xss(self):
        app=make_app('</script><script>alert(1)</script>')
        self.assertNotIn(b'</script><script>alert(1)</script>',app)
    def test_control_character(self):
        with self.assertRaises(CapsuleRejected):make_app('x\ny')
    def test_large_label(self):
        with self.assertRaises(CapsuleRejected):self.issuer.issue('x'*71,now=1800000000)
    def test_carrier_roundtrip(self):
        wire=encode_wire(self.packet)
        self.assertEqual(decode_wire(wire),self.packet)
    def test_wrong_prefix(self):
        with self.assertRaises(CapsuleRejected):decode_wire('qr1:'+encode_wire(self.packet))
    def test_truncated_compressed_data(self):
        wire=encode_wire(self.packet)
        with self.assertRaises(CapsuleRejected):decode_wire(wire[:-12])
    def test_bomb_rejected(self):
        from ipcih.core import b64e
        wire='ipcih1z:'+b64e(zlib.compress(b'A'*(MAX_WIRE+10000)))
        with self.assertRaises(CapsuleRejected):decode_wire(wire)
    def test_padded_base64_rejected(self):
        with self.assertRaises(CapsuleRejected):b64d('a===')
    def test_deterministic_template(self):
        self.assertEqual(make_app('x'),make_app('x'))
    def test_dual_carrier_pixel_exact(self):
        wire=encode_wire(self.packet)
        image=render_dual(wire)
        self.assertEqual(decode_exact_color(image),wire)
    def test_color_pixel_tamper(self):
        image=render_dual(encode_wire(self.packet));image.putpixel((2,2),(200,5,8))
        with self.assertRaises(CapsuleRejected):decode_exact_color(image)
    def test_color_unsupported_distortion(self):
        image=render_dual(encode_wire(self.packet));image=image.resize((250,250))
        with self.assertRaises(CapsuleRejected):decode_exact_color(image)
    def test_color_capacity(self):
        with self.assertRaises(CapsuleRejected):render_dual('ipcih1z:'+'a'*5000,width=20)
    def test_real_qr_bootstrap_decode(self):
        from pyzbar.pyzbar import decode
        wire=encode_wire(self.packet)
        bootstrap=first_stage_bootstrap(wire,issuer_fingerprint=self.issuer.public_fingerprint())
        image=make_qr(bootstrap)
        self.assertEqual(decode(image)[0].data.decode(),bootstrap)
    def test_real_full_qr_decode(self):
        from pyzbar.pyzbar import decode
        wire=encode_wire(self.packet)
        image=make_qr(wire,ecc='L')
        self.assertEqual(decode(image)[0].data.decode(),wire)
    def test_bootstrap_does_not_contain_app(self):
        bootstrap=first_stage_bootstrap(encode_wire(self.packet),issuer_fingerprint=self.issuer.public_fingerprint())
        self.assertNotIn('app_b64',bootstrap)
        self.assertLess(len(bootstrap),150)
    def test_wrong_issuer_origin(self):
        p=Issuer(ed25519.Ed25519PrivateKey.generate()).issue('x',now=1800000000)
        with self.assertRaises(CapsuleRejected):verify(p,self.pub,now=1800000001)
    def test_declared_arithmetic_true(self):
        a=audit_assertion({'kind':'declared_integer_relation','lhs':2,'op':'==','rhs':2})
        self.assertEqual(a.status,'DECLARED_ARITHMETIC_TRUE')
    def test_declared_arithmetic_false(self):
        a=audit_assertion({'kind':'declared_integer_relation','lhs':2,'op':'<','rhs':1})
        self.assertEqual(a.status,'DECLARED_ARITHMETIC_FALSE')
    def test_natural_language_unresolved(self):
        a=audit_assertion({'claim':'This patient has no cancer'})
        self.assertEqual(a.status,'UNRESOLVED')
    def test_booleans_do_not_count_ints(self):
        a=audit_assertion({'kind':'declared_integer_relation','lhs':True,'op':'==','rhs':1})
        self.assertEqual(a.status,'UNRESOLVED')
    def test_bad_op_unresolved(self):
        a=audit_assertion({'kind':'declared_integer_relation','lhs':1,'op':'eval','rhs':1})
        self.assertEqual(a.status,'UNRESOLVED')

if __name__=='__main__':unittest.main()
