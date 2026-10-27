"""Make non-production disposable source and machine Ed25519 keys in a local directory.

Never use these keys or intentionally manufactured claims in real environments.
"""
import argparse
import json
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from .router import canonical, SOURCE_DOMAIN, pub_hex, sha256


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path('runtime'))
    a = p.parse_args()
    a.root.mkdir(parents=True, exist_ok=True)
    if (a.root / 'machine.key').exists():
        p.error('refusing to overwrite existing keys')
    key = Ed25519PrivateKey.generate()
    source = Ed25519PrivateKey.generate()
    for name, signer in [('machine', key), ('source', source)]:
        target = a.root / (name + '.key')
        target.write_bytes(signer.private_bytes(serialization.Encoding.Raw,
                          serialization.PrivateFormat.Raw, serialization.NoEncryption()))
        target.chmod(0o600)
    registry = {'protocol':'ITM-TRUST-REGISTRY-v1','keys':{'source-dev':{
      'role':'source', 'source_id':'demo-device', 'active':True,
      'public_key_hex':pub_hex(source)}}}
    (a.root / 'registry.json').write_bytes(canonical(registry))
    print('out_of_band_demo_registry_sha256:',sha256((a.root / 'registry.json').read_bytes()))
    data = {'protocol':'ITM-INGRESS-RECEIPT-v1','source_id':'demo-device',
            'receipt_id':'DEMONSTRATION-ONLY-0001','key_id':'source-dev',
            'body':{'claim':'EXAMPLE_ONLY_NOT_INDEPENDENTLY_CORROBORATED'}}
    data['signature_hex'] = source.sign(SOURCE_DOMAIN + canonical(data)).hex()
    inbox = a.root / 'inbox'; inbox.mkdir(exist_ok=True)
    (inbox / 'demo.json').write_bytes(canonical(data))
    print('DEMO KEYS GENERATED; NOT FOR REAL RECEIPT ATTESTATION')
    print('local_machine_pubkey_ed25519:', pub_hex(key))

if __name__ == '__main__':main()

