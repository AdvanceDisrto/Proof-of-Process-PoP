#!/usr/bin/env python3
"""Offline verifier. Requires only cryptography + an independently trusted pin.

Does not import the API, access SQLite, fetch keys, or depend on server secrets.
"""
from __future__ import annotations
import argparse
import hashlib
import hmac
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def verify_receipt(receipt: dict, pinned_public_key: str) -> tuple[bool, str]:
    try:
        payload=receipt['payload']
        sig=receipt['signature']
        if not isinstance(payload,dict) or not payload.get('schema','').startswith('ipqr/'):
            return False, 'invalid schema'
        if sig['algorithm']!='Ed25519':
            return False,'invalid algorithm'
        if not hmac.compare_digest(sig['public_key_hex'],pinned_public_key):
            return False,'untrusted signing key'
        body=json.dumps(payload,sort_keys=True,separators=(',', ':'),ensure_ascii=False,allow_nan=False).encode()
        if not hmac.compare_digest('sha256:'+hashlib.sha256(body).hexdigest(),receipt['payload_hash']):
            return False,'tampered payload hash'
        key_id='sha256:'+hashlib.sha256(bytes.fromhex(pinned_public_key)).hexdigest()[:16]
        if sig.get('key_id')!=key_id:
            return False,'key ID mismatch'
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pinned_public_key)).verify(bytes.fromhex(sig['value']),body)
        return True,'ACCEPT_SIGNED_PAYLOAD_INTEGRITY_ONLY'
    except Exception:
        return False,'malformed or invalid signature'


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt')
    parser.add_argument('--pinned-public-key',required=True)
    args=parser.parse_args()
    with open(args.receipt,encoding='utf-8') as f:
        r=json.load(f)
    ok, verdict=verify_receipt(r,args.pinned_public_key)
    print(json.dumps({'valid':ok,'verdict':verdict}))
    raise SystemExit(0 if ok else 2)
