"""Sovereign CIH end-to-end API contract tests using real Ed25519 signatures."""
import base64
import hashlib
import json
import sqlite3
import time
import uuid

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from cih_api.app import app, canonical
from cih_api.krdid import enroll, signed_bytes, store_path

client = TestClient(app)
IDENTITY = "local-test-node.krdid"


@pytest.fixture(autouse=True)
def secure_config(monkeypatch, tmp_path):
    monkeypatch.setenv("CIH_LOCAL_DB_PATH", str(tmp_path / "sovereign.db"))
    node_key = Ed25519PrivateKey.generate()
    node_private = node_key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                          serialization.NoEncryption())
    node_public = node_key.public_key().public_bytes(serialization.Encoding.Raw,
                                                     serialization.PublicFormat.Raw)
    monkeypatch.setenv("CIH_ED25519_PRIVATE_KEY_B64", base64.b64encode(node_private).decode())
    monkeypatch.setenv("CIH_ED25519_PUBLIC_KEY_B64", base64.b64encode(node_public).decode())
    requester_key = Ed25519PrivateKey.generate()
    requester_pub = requester_key.public_key().public_bytes(serialization.Encoding.Raw,
                                                             serialization.PublicFormat.Raw)
    enroll(IDENTITY, base64.b64encode(requester_pub).decode())
    yield requester_key


def payload(evidence=None, parents=None):
    item = evidence if evidence is not None else {"value": 42, "unit": "mock"}
    return {
        "claim": "Self-declared input digest matches submitted evidence",
        "evidence": item,
        "expected_evidence_sha256": hashlib.sha256(canonical(item)).hexdigest(),
        "source_id": "fixture-node", "parent_receipt_hashes": parents or [],
    }


def authorize(requester, data, path="/api/v1/receipts", krdid=IDENTITY, timestamp=None, nonce=None):
    stamp = int(time.time()) if timestamp is None else timestamp
    number = nonce or uuid.uuid4().hex
    message = signed_bytes(krdid, stamp, number, data, path)
    signature = base64.b64encode(requester.sign(message)).decode()
    return {
        "X-Krdid": krdid,
        "X-Krdid-Signature": signature,
        "X-Krdid-Timestamp": str(stamp),
        "X-Krdid-Nonce": number,
    }


def issue(requester, evidence=None, parents=None, headers=None, body=None):
    item = body if body is not None else payload(evidence, parents)
    return client.post("/api/v1/receipts", json=item,
                       headers=headers if headers is not None else authorize(requester, item))


def reconcile(requester, receipts, nonce=None):
    data = {"receipts": receipts}
    return client.post("/api/v1/reconcile", json=data, headers=authorize(
        requester, data, path="/api/v1/reconcile", nonce=nonce))


def test_health_reports_actual_krdid_and_no_hardware_claim(secure_config):
    h = client.get("/api/v1/health").json()
    assert h["auth_provider"] == "LOCAL_KRDID_ED25519"
    assert h["auth_configured"] is True
    assert h["krdid_enrolled_count"] == 1
    assert h["storage_provider"] == "LOCAL_SQLITE"
    assert h["storage_configured"] is True
    assert h["hardware_backed_identity"] == "NOT_ATTESTED"
    assert h["independent_truth_engine"] == "NOT_CONNECTED"
    assert h["hardware_attestation"] == "NOT_CONNECTED"


def test_signed_receipt_verifies_and_persists_locally(secure_config):
    response = issue(secure_config)
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["storage_status"] == "LOCAL_SQLITE_COMMITTED"
    assert receipt["body"]["requester_subject"] == IDENTITY
    assert receipt["body"]["request_identity"]["method"] == "LOCAL_ENROLLED_KRDID_ED25519"
    verification = client.post("/api/v1/verify", json=receipt)
    assert verification.status_code == 200
    assert verification.json()["status"] == "SIGNATURE_VALID"
    assert len(verification.json()["does_not_prove"]) > 0
    with sqlite3.connect(store_path()) as db:
        assert db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM nonces").fetchone()[0] == 1


def test_receipt_tampering_refuted(secure_config):
    receipt = issue(secure_config).json()
    receipt["body"]["claim"] = "Different claim after signing"
    resp = client.post("/api/v1/verify", json=receipt)
    assert resp.status_code == 200
    assert resp.json()["status"] == "REFUTED_SIGNATURE"


def test_no_signing_key_fails_closed(secure_config, monkeypatch):
    monkeypatch.delenv("CIH_ED25519_PRIVATE_KEY_B64")
    response = issue(secure_config)
    assert response.status_code == 503
    assert response.json()["detail"] == "SIGNING_KEY_UNAVAILABLE"


def test_wrong_evidence_digest_rejected(secure_config):
    item = payload()
    item["expected_evidence_sha256"] = "0" * 64
    response = issue(secure_config, body=item)
    assert response.status_code == 422
    assert response.json()["detail"] == "EVIDENCE_DIGEST_MISMATCH"


def test_fragment_requires_topological_parents(secure_config):
    parent = issue(secure_config).json()
    child = issue(secure_config, evidence={"value": 43},
                  parents=[parent["body_sha256"]]).json()
    accepted = reconcile(secure_config, [parent, child])
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "FRAGMENT_INTEGRITY_ACCEPTED"
    rejected = reconcile(secure_config, [child])
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["status"] == "REJECTED_MISSING_PARENT"


def test_reconcile_replay_rejected(secure_config):
    receipt = issue(secure_config).json()
    data = {"receipts": [receipt]}
    auth = authorize(secure_config, data, path="/api/v1/reconcile")
    assert client.post("/api/v1/reconcile", json=data, headers=auth).status_code == 200
    resp = client.post("/api/v1/reconcile", json=data, headers=auth)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "KRDID_REPLAY_OR_DUPLICATE"


def test_malformed_parent_hash_rejected(secure_config):
    item = payload(parents=["invalid"])
    assert issue(secure_config, body=item).status_code == 422


def test_missing_krdid_auth_fails_closed(secure_config):
    response = client.post("/api/v1/receipts", json=payload())
    assert response.status_code == 401
    assert response.json()["detail"] == "KRDID_SIGNATURE_REQUIRED"


def test_unenrolled_self_signed_identity_is_forbidden(secure_config):
    attacker = Ed25519PrivateKey.generate()
    item = payload()
    headers = authorize(attacker, item, krdid="attacker.krdid")
    response = client.post("/api/v1/receipts", json=item, headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "KRDID_NOT_ENROLLED"


def test_tampered_request_signature_refused(secure_config):
    original = payload()
    auth = authorize(secure_config, original)
    modified = dict(original)
    modified["claim"] = "Changed after signature"
    response = client.post("/api/v1/receipts", json=modified, headers=auth)
    assert response.status_code == 403
    assert response.json()["detail"] == "INVALID_KRDID_SIGNATURE"


def test_signed_request_path_is_bound(secure_config):
    item = payload()
    headers = authorize(secure_config, item, path="/api/v1/reconcile")
    response = client.post("/api/v1/receipts", json=item, headers=headers)
    assert response.status_code == 403


def test_expired_signed_request_blocked(secure_config):
    item = payload()
    headers = authorize(secure_config, item, timestamp=int(time.time()) - 3600)
    response = client.post("/api/v1/receipts", json=item, headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "KRDID_SIGNATURE_EXPIRED"


def test_receipt_replay_rejected_even_after_new_http_client(secure_config):
    item = payload()
    headers = authorize(secure_config, item)
    first = client.post("/api/v1/receipts", json=item, headers=headers)
    assert first.status_code == 200
    second = TestClient(app).post("/api/v1/receipts", json=item, headers=headers)
    assert second.status_code == 409
    assert second.json()["detail"] == "KRDID_REPLAY_OR_DUPLICATE"
    with sqlite3.connect(store_path()) as db:
        assert db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 1


def test_bad_signature_or_fake_public_key_cannot_authorize(secure_config):
    item = payload()
    auth = authorize(secure_config, item)
    auth["X-Krdid-Signature"] = base64.b64encode(b"0" * 64).decode()
    auth["X-Krdid-Pubkey"] = base64.b64encode(b"1" * 32).decode()
    response = client.post("/api/v1/receipts", json=item, headers=auth)
    assert response.status_code == 403


def test_health_does_not_claim_registry_before_enrollment(secure_config, monkeypatch, tmp_path):
    monkeypatch.setenv("CIH_LOCAL_DB_PATH", str(tmp_path / "fresh" / "empty.db"))
    h = client.get("/api/v1/health").json()
    assert h["krdid_enrolled_count"] == 0
    assert h["auth_configured"] is False
