"""Buddy™ v2 signed BrainGate receipt envelope.

V1 remains unchanged and hash-verifiable with its original algorithm. V2 is a
NEW schema, using a strict no-numbers RFC 8785 profile so Python and JS agree.

Only local software / DEMO signing is exercised here; not your CIH node key.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from brain_registry import GENESIS, BrainDispatcher, build_dispatcher

SCHEMA = 'bitwitness/brain/receipt/v2'
HASH_RE = re.compile(r'^sha256:[a-f0-9]{64}$')
TS_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')
KIND = {'deterministic', 'head', 'router', 'oracle', 'external_llm', 'refusal'}
VERDICT = {'ACCEPT', 'ACCEPT-REFUSAL', 'REJECT'}
BODY_FIELDS = (
    'schema','brain','kind','role','has_checkpoint','connection_status',
    'external_provider','external_model_version','request_hash','output_hash',
    'claims','refusals','disclosure','gate_verdict','gate_checks','gate_reason',
    'prev_hash','genesis','ts','legacy_receipt_hash',
)
ALL_FIELDS = BODY_FIELDS + ('receipt_hash', 'signer_pubkey', 'signature')


def utc_ms() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def _validate_unicode(text: str) -> None:
    # JCS/I-JSON forbids unpaired UTF-16 surrogates. Python can hold them.
    try:
        text.encode('utf-8', 'strict')
    except UnicodeEncodeError as exc:
        raise ValueError('INVALID_UNICODE_SURROGATE') from exc


def canon(value: Any) -> bytes:
    """RFC 8785 canonicalization for THIS schema's number-free I-JSON profile.

    Do not use this helper for arbitrary floating-point JSON: it refuses all
    numeric values, so no Python-versus-ECMAScript number drift is possible.
    """
    def serialize(obj: Any) -> str:
        if obj is None:
            return 'null'
        if obj is True:
            return 'true'
        if obj is False:
            return 'false'
        if isinstance(obj, str):
            _validate_unicode(obj)
            return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
        if isinstance(obj, (int, float)):
            raise ValueError('V2_CANONICAL_PROFILE_PROHIBITS_NUMBERS')
        if isinstance(obj, list):
            return '[' + ','.join(serialize(item) for item in obj) + ']'
        if isinstance(obj, dict):
            if not all(isinstance(key, str) for key in obj):
                raise ValueError('JSON_KEYS_MUST_BE_STRINGS')
            # RFC8785 UTF-16 code-unit order, not Python Unicode scalar order.
            keys = sorted(obj, key=lambda x: x.encode('utf-16-be', 'surrogatepass'))
            return '{' + ','.join(serialize(key) + ':' + serialize(obj[key]) for key in keys) + '}'
        raise ValueError('UNSUPPORTED_CANONICAL_TYPE')
    return serialize(value).encode('utf-8', 'strict')


def sha(data: bytes) -> str:
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def pubkey_bytes(private: Ed25519PrivateKey) -> bytes:
    return private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


def validate_receipt(record: Any) -> dict:
    if not isinstance(record, dict) or set(record) != set(ALL_FIELDS):
        raise ValueError('V2_SCHEMA_FIELDS_MISMATCH')
    if record['schema'] != SCHEMA:
        raise ValueError('UNSUPPORTED_RECEIPT_VERSION')
    if record['kind'] not in KIND or record['gate_verdict'] not in VERDICT:
        raise ValueError('UNSUPPORTED_BRAIN_KIND_OR_VERDICT')
    for field in ('brain','kind','role','connection_status','external_provider',
                  'external_model_version','disclosure','gate_verdict','gate_reason','ts'):
        if not isinstance(record[field],str):
            raise ValueError('V2_BAD_STRING_' + field)
    if record['connection_status'] not in ('', 'n/a', 'ready', 'not_connected', 'unreachable'):
        raise ValueError('INVALID_CONNECTION_STATUS')
    if not record['brain'] or not record['disclosure']:
        raise ValueError('V2_REQUIRED_TEXT_EMPTY')
    if type(record['has_checkpoint']) is not bool or type(record['genesis']) is not bool:
        raise ValueError('V2_BOOLEAN_INVALID')
    if not TS_RE.fullmatch(record['ts']):
        raise ValueError('V2_TIMESTAMP_MUST_BE_UTC_RFC3339_MS')
    try:
        datetime.fromisoformat(record['ts'].replace('Z','+00:00'))
    except ValueError as exc:
        raise ValueError('V2_TIMESTAMP_INVALID') from exc
    for field in ('claims','refusals','gate_checks'):
        if not isinstance(record[field],list) or not all(isinstance(s,str) for s in record[field]):
            raise ValueError('V2_ARRAY_INVALID_'+field)
    for field in ('request_hash','prev_hash','legacy_receipt_hash','receipt_hash'):
        if not isinstance(record[field],str) or not HASH_RE.fullmatch(record[field]):
            raise ValueError('V2_HASH_INVALID_'+field)
    if record['output_hash'] and (not isinstance(record['output_hash'],str)
                                  or not HASH_RE.fullmatch(record['output_hash'])):
        raise ValueError('V2_OUTPUT_HASH_INVALID')
    if not isinstance(record['signer_pubkey'],str) or not isinstance(record['signature'],str):
        raise ValueError('V2_SIGNATURE_FIELDS_INVALID')
    try:
        pk = base64.b64decode(record['signer_pubkey'],validate=True)
        sig = base64.b64decode(record['signature'],validate=True)
    except (ValueError,base64.binascii.Error) as exc:
        raise ValueError('V2_BAD_BASE64') from exc
    if len(pk) != 32 or len(sig) != 64:
        raise ValueError('V2_WRONG_KEY_OR_SIGNATURE_LENGTH')
    if record['genesis'] and record['prev_hash'] != GENESIS:
        raise ValueError('GENESIS_MUST_HAVE_ZERO_PREV')
    # Schema + no-numeric canonical restriction, recursively validates bytes.
    canon(record)
    return record


def check_receipt(record: dict, independently_trusted_pubkey: bytes) -> bool:
    """Signature + integrity AND external trust key: never trust scanned pubkey alone."""
    try:
        validate_receipt(record)
        if len(independently_trusted_pubkey) != 32:
            return False
        decoded = base64.b64decode(record['signer_pubkey'],validate=True)
        if decoded != independently_trusted_pubkey:
            return False
        body = {field:record[field] for field in BODY_FIELDS}
        if sha(canon(body)) != record['receipt_hash']:
            return False
        signed = {**body,'receipt_hash':record['receipt_hash']}
        Ed25519PublicKey.from_public_bytes(independently_trusted_pubkey).verify(
            base64.b64decode(record['signature'],validate=True), canon(signed))
        return True
    except (ValueError, TypeError, InvalidSignature):
        return False


class SignedBrainDispatcher:
    """Add a NEW signed v2 chain without changing historical BrainReceipt v1 hashes."""
    def __init__(self, signer: Ed25519PrivateKey, legacy: BrainDispatcher | None = None):
        if not isinstance(signer, Ed25519PrivateKey):
            raise TypeError('REAL_ED25519_PRIVATE_KEY_REQUIRED')
        self.signer = signer
        self.legacy = legacy if legacy is not None else build_dispatcher()
        self.chain: list[dict] = []
        self._sealed_tip = GENESIS
        self.public_key = pubkey_bytes(signer)

    def dispatch(self, text: str, forced: str | None = None) -> dict:
        # Deterministic BrainGate executes before receipt signing.
        legacy = self.legacy.dispatch(text, forced=forced)
        original = asdict(legacy)
        # Explicit v2 projection: deliberately OMIT legacy float confidence;
        # retain legacy_receipt_hash to reference original v1 evidence.
        body = {
            'schema': SCHEMA,
            'brain': original['brain'], 'kind':original['kind'], 'role': original['role'],
            'has_checkpoint':original['has_checkpoint'],
            'connection_status':original['connection_status'],
            'external_provider':original['external_provider'],
            'external_model_version':original['external_model_version'],
            'request_hash':original['request_hash'], 'output_hash':original['output_hash'],
            'claims':original['claims'], 'refusals':original['refusals'],
            'disclosure':original['disclosure'],
            'gate_verdict':original['gate_verdict'], 'gate_checks':original['gate_checks'],
            'gate_reason':original['gate_reason'],
            'prev_hash':self._sealed_tip, 'genesis':not bool(self.chain),
            'ts':utc_ms(), 'legacy_receipt_hash':original['receipt_hash'],
        }
        if self.chain:
            # Fail before sealing if either past signed receipt or current tip was modified.
            if not self.verify_chain()['ok'] or self._sealed_tip != self.chain[-1]['receipt_hash']:
                raise RuntimeError('CHAIN_FORK_OR_TAMPER_BEFORE_SEAL')
            if body['prev_hash'] != self.chain[-1]['receipt_hash'] or body['genesis']:
                raise RuntimeError('INVALID_SIGNING_PARENT')
        elif body['prev_hash'] != GENESIS or not body['genesis']:
            raise RuntimeError('INVALID_SIGNING_GENESIS')
        root = sha(canon(body))
        signed = {**body, 'receipt_hash':root}
        signature = self.signer.sign(canon(signed))
        receipt = {**signed,
                   'signer_pubkey':base64.b64encode(self.public_key).decode('ascii'),
                   'signature':base64.b64encode(signature).decode('ascii')}
        validate_receipt(receipt)
        self.chain.append(receipt)
        self._sealed_tip = root
        return receipt

    def verify_chain(self) -> dict:
        prev=GENESIS
        for i, receipt in enumerate(self.chain):
            if receipt.get('prev_hash') != prev or receipt.get('genesis') is not (i == 0):
                return {'ok':False,'index':i,'reason':'CHAIN_LINK_MISMATCH'}
            if not check_receipt(receipt,self.public_key):
                return {'ok':False,'index':i,'reason':'SIGNATURE_OR_HASH_MISMATCH'}
            prev=receipt['receipt_hash']
        return {'ok':True,'count':len(self.chain),'tip':prev,
                'external_genesis_pinned':False}


def make_demo() -> tuple[dict, bytes, dict]:
    signer=Ed25519PrivateKey.generate()  # explicitly ephemeral, never saved
    d=SignedBrainDispatcher(signer)
    receipts=[d.dispatch('add 40 and 2'),
              d.dispatch('What disease does this patient have?',forced='OracleHumanReview'),
              d.dispatch('Write a poem about sovereignty.',forced='Claude')]
    assert d.verify_chain()['ok']
    anchor={'scope':'TEST_EPHEMERAL_SIGNER_ONLY','schema':SCHEMA,
            'public_key_b64':base64.b64encode(d.public_key).decode('ascii'),
            'public_key_sha256':hashlib.sha256(d.public_key).hexdigest(),
            'note':'Demo key supplied with independently reviewed verifier; not production CIH trust.'}
    return {'receipts':receipts,'verification':d.verify_chain(),
            'does_not_prove':['real CIH node signer','physical truth','live external LLM',
                              'externally anchored ledger','hardware-backed signer']},d.public_key,anchor
