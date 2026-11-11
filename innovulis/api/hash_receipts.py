"""iVerify hash-only claims. Python-canonicalized; not proof of inference.

Canonical encoding: deterministic Python JSON, explicitly NOT RFC 8785 JCS.
Public verification needs an independently trusted Ed25519 key pin.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timezone
from typing import Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

HASH_RE = re.compile(r'^sha256:[0-9a-f]{64}$')
KEY_RE = re.compile(r'^[0-9a-f]{64}$')
GRADES = {'A', 'B', 'C', 'D'}
MAX_EVIDENCE = 32

def canonical(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def digest(data: bytes) -> str:
    return 'sha256:' + hashlib.sha256(data).hexdigest()

def urn_from_hash(value: str) -> str:
    if not isinstance(value, str) or not HASH_RE.fullmatch(value):
        raise ValueError('invalid receipt hash')
    return 'urn:iverify:' + value[7:]

def validate_mint(body: dict, tier: str):
    if not isinstance(body, dict):
        raise ValueError('JSON object required')
    required = ('prompt_hash', 'output_hash', 'model_id', 'model_version')
    for key in required:
        value = body.get(key)
        if not isinstance(value, str) or not value or len(value) > 200:
            raise ValueError('missing or invalid ' + key)
    for key in ('prompt_hash', 'output_hash'):
        if not HASH_RE.fullmatch(body[key]):
            raise ValueError(key + ' must be sha256:<64 lowercase hex>')
    if tier == 'T2':
        evidence = body.get('evidence')
        errors = check_evidence(evidence)
        if errors:
            raise ValueError('; '.join(errors))

def check_evidence(evidence) -> list[str]:
    if not isinstance(evidence, list) or not (1 <= len(evidence) <= MAX_EVIDENCE):
        return ['evidence must contain 1..32 items']
    errors = []
    for n, item in enumerate(evidence):
        if not isinstance(item, dict):
            errors.append(f'evidence[{n}] must be object'); continue
        keys = ('source_id', 'payload_hash', 'source_pubkey_hex', 'grade')
        missing = [key for key in keys if key not in item]
        if missing:
            errors.append(f'evidence[{n}] missing {missing}'); continue
        if not isinstance(item['source_id'], str) or not item['source_id'] or len(item['source_id']) > 200:
            errors.append(f'evidence[{n}] invalid source_id')
        if not isinstance(item['payload_hash'], str) or not HASH_RE.fullmatch(item['payload_hash']):
            errors.append(f'evidence[{n}] invalid payload_hash')
        if not isinstance(item['source_pubkey_hex'], str) or not KEY_RE.fullmatch(item['source_pubkey_hex']):
            errors.append(f'evidence[{n}] invalid source_pubkey_hex')
        if not isinstance(item['grade'], str) or item['grade'] not in GRADES:
            errors.append(f'evidence[{n}] invalid grade')
    return errors

def mint(body: dict, tier: str, key, pubkey_hex: str) -> dict:
    validate_mint(body, tier)
    fields = {k: body[k] for k in ('prompt_hash','output_hash','model_id','model_version')}
    fields['spec'] = 'iverify/receipt/1.0'
    fields['tier'] = tier
    fields['created_at_utc'] = datetime.now(timezone.utc).isoformat()
    fields['nonce'] = secrets.token_hex(16)
    if tier == 'T2':
        fields['evidence'] = body['evidence']
    caveats = [
        'prompt and output hashes came from the computation claimed',
        'model_id identifies the weights that ran',
        'the output is correct or factually true',
        'the server or signer is trusted without an independently pinned key',
    ] + (['evidence content, evidence signatures, and grades are independently verified'] if tier == 'T2' else [])
    fields['does_not_prove'] = caveats
    b = canonical(fields)
    rid = digest(b)
    return {
        'spec': 'iverify/receipt/1.0', 'tier': tier,
        'receipt_id': rid, 'receipt_urn': urn_from_hash(rid),
        'body': fields, 'signature': key.sign(b).hex(), 'public_key_hex': pubkey_hex,
        'does_not_prove': caveats,
    }

def verify(receipt: dict, pinned_public_key: str) -> dict:
    errors = []
    if not isinstance(receipt, dict):
        return {'ok': False, 'errors': ['receipt must be an object'], 'warnings': []}
    for k in ('spec','tier','receipt_id','body','signature','public_key_hex','receipt_urn'):
        if k not in receipt:
            errors.append('missing ' + k)
    if errors:
        return {'ok': False, 'errors': errors, 'warnings': []}
    if receipt['spec'] != 'iverify/receipt/1.0' or receipt['tier'] not in ('T1','T2'):
        errors.append('invalid spec or tier')
    if not isinstance(receipt['body'], dict):
        errors.append('invalid body')
        return {'ok': False, 'errors': errors, 'warnings': []}
    if receipt['body'].get('spec') != receipt['spec'] or receipt['body'].get('tier') != receipt['tier']:
        errors.append('unsigned envelope tier or spec mismatch')
    if receipt['body'].get('does_not_prove') != receipt.get('does_not_prove'):
        errors.append('unsigned caveat mismatch')
    try:
        b = canonical(receipt['body'])
        computed = digest(b)
        if not isinstance(receipt['receipt_id'], str) or receipt['receipt_id'] != computed:
            errors.append('receipt_id mismatch')
        if receipt['receipt_urn'] != urn_from_hash(computed):
            errors.append('receipt_urn does not match body hash')
        if not isinstance(pinned_public_key, str) or not KEY_RE.fullmatch(pinned_public_key):
            errors.append('external trusted key pin required')
        elif not isinstance(receipt['public_key_hex'], str) or not hmac.compare_digest(receipt['public_key_hex'], pinned_public_key):
            errors.append('public_key_hex does not match pinned key')
        else:
            try:
                Ed25519PublicKey.from_public_bytes(bytes.fromhex(pinned_public_key)).verify(bytes.fromhex(receipt['signature']), b)
            except Exception as ex:
                errors.append('signature invalid: ' + type(ex).__name__)
        if receipt['tier'] == 'T2':
            errors += check_evidence(receipt['body'].get('evidence'))
    except (TypeError, ValueError, OverflowError) as ex:
        errors.append('invalid receipt encoding: ' + type(ex).__name__)
    integrity_ok = receipt.get('receipt_id') == digest(b) if 'b' in locals() else False
    signature_ok = not any('signature invalid' in e or 'pinned key' in e or 'key pin' in e or 'public_key_hex' in e for e in errors) and isinstance(pinned_public_key, str) and bool(KEY_RE.fullmatch(pinned_public_key))
    return {'ok': not errors, 'errors': errors, 'warnings': [], 'integrity_ok': integrity_ok, 'signature_ok': signature_ok, 'trust_basis': 'external_pin'}
