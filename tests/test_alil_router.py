import copy
import json
import os
import subprocess
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from alil.router import (Router, SOURCE_DOMAIN, MACHINE_DOMAIN, canonical, load_json,
                         sha_content, sha256, pub_hex, verify_source, RejectedReceipt, forward_outbox)


@pytest.fixture
def setup(tmp_path):
    src = Ed25519PrivateKey.generate()
    machine = Ed25519PrivateKey.generate()
    machinepath = tmp_path / 'machine-key'
    machinepath.write_bytes(machine.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()))
    registry = {'protocol': 'ITM-TRUST-REGISTRY-v1', 'keys': {'src-01': {
        'role': 'source', 'source_id': 'bank-01', 'active': True,
        'public_key_hex': pub_hex(src)}}}
    regpath = tmp_path / 'registry.json'
    regpath.write_bytes(canonical(registry))
    engine = Router(tmp_path / 'runtime', regpath, machinepath, 'machine-01')
    def make(rid='receipt1', body=None):
        d = {'protocol': 'ITM-INGRESS-RECEIPT-v1', 'source_id': 'bank-01',
             'receipt_id': rid, 'key_id': 'src-01', 'body': body if body is not None else {'amount_minor': 1250}}
        d['signature_hex'] = src.sign(SOURCE_DOMAIN + canonical(d)).hex()
        return d
    def write(d, name='x.json'):
        path = engine.root / 'inbox' / name
        path.write_bytes(canonical(d))
        return path
    return engine, src, machine, make, write


def test_valid_signature_and_hash_chain(setup):
    eng, _, signer, make, write = setup
    write(make(), '01.json')
    write(make('receipt2', {'amount_minor': 999}), '02.json')
    assert eng.cycle_once() == {'ACCEPTED': 2, 'DUPLICATE': 0, 'REJECTED': 0}
    assert eng.chain()[0] == 2
    first = load_json((eng.root / 'records' / '000000000001.json').read_bytes())
    second = load_json((eng.root / 'records' / '000000000002.json').read_bytes())
    assert second['event']['prev_event_hash'] == sha256(MACHINE_DOMAIN + canonical(first['event']))
    signer.public_key().verify(bytes.fromhex(first['signature_hex']), MACHINE_DOMAIN + canonical(first['event']))
    assert first['event']['underlying_real_world_event_verified'] is False
    assert first['event']['settlement_authorized'] is False
    assert list((eng.root / 'outbox').glob('*.json'))


def test_duplicate_not_reissued(setup):
    eng, _, _, make, write = setup
    write(make())
    assert eng.cycle_once()['ACCEPTED'] == 1
    assert eng.cycle_once()['DUPLICATE'] == 1
    assert eng.chain()[0] == 1


def test_modified_payload_rejected(setup):
    eng, _, _, make, write = setup
    d = make()
    d['body']['amount_minor'] = 2222
    write(d)
    assert eng.cycle_once()['REJECTED'] == 1
    assert eng.chain()[0] == 0


def test_unauthorized_source_rejected(setup):
    eng, _, _, make, write = setup
    d = make()
    d['source_id'] = 'other-bank'
    write(d)
    assert eng.cycle_once()['REJECTED'] == 1


def test_conflicting_id_quarantined(setup):
    eng, _, _, make, write = setup
    write(make())
    assert eng.cycle_once()['ACCEPTED'] == 1
    write(make(body={'amount_minor': 999}), 'other.json')
    result = eng.cycle_once()
    assert result['REJECTED'] == 1 and eng.chain()[0] == 1


def test_tamper_halting_append(setup):
    eng, _, _, make, write = setup
    write(make())
    assert eng.cycle_once()['ACCEPTED'] == 1
    p = eng.root / 'records' / '000000000001.json'
    d = load_json(p.read_bytes())
    d['event']['settlement_authorized'] = True
    p.write_bytes(canonical(d))
    write(make('receipt2'), 'second.json')
    with pytest.raises(RuntimeError, match='invalid|tamper'):
        eng.cycle_once()


def test_source_registry_mutation_cannot_self_attest(setup):
    eng, src, _, make, write = setup
    d = make()
    d['key_id'] = 'nonexistent'
    write(d)
    assert eng.cycle_once()['REJECTED'] == 1


def test_duplicate_keys_and_floats_fail_closed(setup):
    eng, _, _, _, _ = setup
    path = eng.root / 'inbox' / 'unsafe.json'
    path.write_bytes(b'{"protocol":"x","protocol":"x"}')
    assert eng.cycle_once()['REJECTED'] == 1
    path.write_bytes(b'{"amount":1.1}')
    assert eng.cycle_once()['REJECTED'] == 1


def test_https_delivery_only(setup):
    eng, _, _, make, write = setup
    write(make()); eng.cycle_once()
    with pytest.raises(ValueError, match='HTTPS'):
        forward_outbox(eng.root, 'http://example.com/ingest', 'token')
    with pytest.raises(ValueError, match='bearer'):
        forward_outbox(eng.root, 'https://example.com/ingest', '')


def test_go_python_cross_language_digest(setup):
    eng, _, _, make, _ = setup
    raw = canonical(make())
    try:
        p = subprocess.run(['go', 'run', 'go/hashproof/main.go'],
                           input=raw, capture_output=True, check=True, timeout=30)
    except FileNotFoundError:
        pytest.skip('Go toolchain not installed')
    assert p.stdout.decode().strip() == sha_content(raw)


def test_rejected_cannot_claim_legal_facts(setup):
    eng, _, _, make, write = setup
    d = make()
    d['body']['pretextualProsecutionScore'] = 9999
    write(d)
    assert eng.cycle_once()['REJECTED'] == 1


def test_independent_machine_signature_verification(setup):
    from alil.verify import verify_chain
    eng, _, signer, make, write = setup
    write(make()); eng.cycle_once()
    result = verify_chain(eng.root / 'records', pub_hex(signer))
    assert result['receipt_count'] == 1
    assert result['underlying_events_verified'] is False
    with pytest.raises(ValueError):
        verify_chain(eng.root / 'records', pub_hex(Ed25519PrivateKey.generate()))

