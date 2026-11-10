import base64
import hashlib
import json
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from cih_api.app import app, canonical, require_auth

client = TestClient(app)


@pytest.fixture(autouse=True)
def secure_config(monkeypatch):
    key = Ed25519PrivateKey.generate()
    raw_private = key.private_bytes(serialization.Encoding.Raw,
                                    serialization.PrivateFormat.Raw,
                                    serialization.NoEncryption())
    raw_public = key.public_key().public_bytes(serialization.Encoding.Raw,
                                              serialization.PublicFormat.Raw)
    monkeypatch.setenv("CIH_ED25519_PRIVATE_KEY_B64", base64.b64encode(raw_private).decode())
    monkeypatch.setenv("CIH_ED25519_PUBLIC_KEY_B64", base64.b64encode(raw_public).decode())
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    app.dependency_overrides[require_auth] = lambda: "auth0|fixture"
    yield
    app.dependency_overrides.clear()


def issue(evidence=None, parents=None):
    evidence = evidence or {"value": 42, "unit": "mock"}
    digest = hashlib.sha256(canonical(evidence)).hexdigest()
    return client.post("/api/v1/receipts", json={
        "claim": "Declared input was hashed",
        "evidence": evidence,
        "expected_evidence_sha256": digest,
        "source_id": "test-node",
        "parent_receipt_hashes": parents or [],
    })


def test_health_does_not_fake_attestation():
    body = client.get("/api/v1/health").json()
    assert body["hardware_attestation"] == "NOT_CONNECTED"
    assert body["independent_truth_engine"] == "NOT_CONNECTED"


def test_signed_receipt_verifies_but_does_not_prove_truth():
    created = issue()
    assert created.status_code == 200, created.text
    receipt = created.json()
    assert receipt["storage_status"] == "NOT_CONFIGURED"
    assert receipt["body"]["assessment"] == "INPUT_DIGEST_MATCHED"
    verify = client.post("/api/v1/verify", json=receipt)
    assert verify.status_code == 200 and verify.json()["integrity_valid"] is True
    assert len(verify.json()["does_not_prove"]) > 0


def test_tampering_rejected():
    receipt = issue().json()
    receipt["body"]["claim"] = "modified claim after signing"
    response = client.post("/api/v1/verify", json=receipt)
    assert response.status_code == 200
    assert response.json()["status"] == "REFUTED_SIGNATURE"


def test_no_signing_key_fails_closed(monkeypatch):
    monkeypatch.delenv("CIH_ED25519_PRIVATE_KEY_B64")
    response = issue()
    assert response.status_code == 503
    assert response.json()["detail"] == "SIGNING_KEY_UNAVAILABLE"


def test_wrong_evidence_digest_rejected():
    response = client.post("/api/v1/receipts", json={
        "claim": "Wrong digest supplied", "evidence": {"value": 1},
        "expected_evidence_sha256": "0" * 64, "source_id": "fixture",
    })
    assert response.status_code == 422
    assert response.json()["detail"] == "EVIDENCE_DIGEST_MISMATCH"


def test_fragment_requires_topological_parents():
    parent = issue().json()
    child = issue({"value": 43}, [parent["body_sha256"]]).json()
    accepted = client.post("/api/v1/reconcile", json={"receipts": [parent, child]})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "FRAGMENT_INTEGRITY_ACCEPTED"
    rejected = client.post("/api/v1/reconcile", json={"receipts": [child]})
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["status"] == "REJECTED_MISSING_PARENT"


def test_malformed_parent_rejected():
    response = issue(parents=["invalid"])
    assert response.status_code == 422


def test_missing_auth_config_fails_closed(monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.delenv("AUTH0_ISSUER", raising=False)
    monkeypatch.delenv("AUTH0_AUDIENCE", raising=False)
    response = issue()
    assert response.status_code == 503
    assert response.json()["detail"] == "AUTH_PROVIDER_UNCONFIGURED"
