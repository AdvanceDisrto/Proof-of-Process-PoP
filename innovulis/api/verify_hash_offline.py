#!/usr/bin/env python3
"""Stateless iVerify T1/T2 receipt verifier, offline with independently pinned key.

Usage: python api/verify_hash_offline.py receipt.json --pinned-public-key HEX
Optional: --banner banner.txt compares SHA-256 of exact external banner bytes
against receipt.body.prompt_hash; a mismatch adds external banner content hash mismatch.
"""
import argparse
import json
from pathlib import Path
try:
    from . import hash_receipts
except ImportError:
    import hash_receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('--pinned-public-key', required=True)
    parser.add_argument('--banner', type=Path)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding='utf-8'))
    result = hash_receipts.verify(receipt, args.pinned_public_key)
    if args.banner:
        supplied = hash_receipts.digest(args.banner.read_bytes())
        recorded = receipt.get('body', {}).get('prompt_hash')
        result['banner_hash_ok'] = supplied == recorded
        if not result['banner_hash_ok']:
            result['ok'] = False
            result['errors'].append('external banner content hash mismatch')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ok'] else 2)

if __name__ == '__main__':
    main()
