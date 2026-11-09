"""Run a real software-only signed optical capsule smoke and capture evidence."""
import json,time,argparse
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from . import Issuer,verify,encode_wire,decode_wire,render_dual,decode_exact_color,make_qr,first_stage_bootstrap
from .auditor import audit_assertion

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='evidence/demo');a=ap.parse_args()
    root=Path(a.output);root.mkdir(parents=True,exist_ok=True)
    issuer=Issuer(ed25519.Ed25519PrivateKey.generate(),issuer_id='DEMO_EPHEMERAL')
    now=int(time.time())
    packet=issuer.issue('Buddy™ · Sovereign Capsule',now=now)
    wire=encode_wire(packet)
    verified=verify(decode_wire(wire),issuer.public_raw(),now=now+1)
    fullqr=None
    try:
        img=make_qr(wire,ecc='L');fullqr=root/'signed_capsule_qr.png';img.save(fullqr)
    except Exception:pass
    bootstrap=first_stage_bootstrap(wire,issuer_fingerprint=issuer.public_fingerprint())
    make_qr(bootstrap).save(root/'standard_bootstrap_qr.png')
    im=render_dual(wire);im.save(root/'experimental_imorphus_color.png')
    assert decode_exact_color(im)==wire
    (root/'signed_capsule.txt').write_text(wire)
    (root/'pinned_pubkey_hex.txt').write_text(issuer.public_raw().hex())
    result={'status':verified['status'],'claim_truth':'NOT_EVALUATED','signed_app_sha256':verified['app_sha256'],
            'issuer_fingerprint':verified['fingerprint'],'full_qr_created':fullqr is not None,'wire_bytes':len(wire),
            'imorphus':'EXACT_PIXEL_ROUNDTRIP_ONLY','webrtc':'NOT_ESTABLISHED',
            'tpm_atecc':'NOT_CONNECTED','physical_energy':'NOT_MEASURED',
            'auditor':audit_assertion({'kind':'declared_integer_relation','lhs':2,'op':'==','rhs':2}).status}
    (root/'acceptance.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
