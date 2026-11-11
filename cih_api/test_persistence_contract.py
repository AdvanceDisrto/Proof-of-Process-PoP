"""Registry persistence and local-only trust management; no remote IdP."""
import base64
import json
import sqlite3

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException
from cih_api.krdid import database, enroll, readiness, store_path, authenticate, signed_bytes


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("CIH_LOCAL_DB_PATH", str(tmp_path / "CIH" / "sovereign.sqlite3"))
    key = Ed25519PrivateKey.generate()
    raw = key.public_key().public_bytes(serialization.Encoding.Raw,
                                         serialization.PublicFormat.Raw)
    return key, base64.b64encode(raw).decode()


def test_new_registry_denies_all_until_trusted_enrollment(isolated):
    key, public = isolated
    assert readiness()["enrolled"] == 0
    with pytest.raises(HTTPException) as exc:
        authenticate(None, None, None, None, {}, "/api/v1/receipts")
    assert exc.value.status_code == 401
    enroll("operator.krdid", public)
    assert readiness() == {"ready": True, "enrolled": 1}


def test_duplicate_enrollment_never_replaces_trusted_key(isolated):
    key, public = isolated
    enroll("operator.krdid", public)
    with pytest.raises(ValueError, match="already enrolled"):
        enroll("operator.krdid", public)
    with sqlite3.connect(store_path()) as db:
        assert db.execute("SELECT COUNT(*) FROM identities").fetchone()[0] == 1


def test_no_untrusted_public_key_can_override_pinned_identity(isolated):
    _, trusted_pub = isolated
    enroll("operator.krdid", trusted_pub)
    attacker = Ed25519PrivateKey.generate()
    data = {"source_id": "operator"}
    import time, uuid
    stamp = int(time.time())
    nonce = uuid.uuid4().hex
    signature = base64.b64encode(attacker.sign(
        signed_bytes("operator.krdid", stamp, nonce, data, "/api/v1/receipts"))).decode()
    with pytest.raises(HTTPException) as exc:
        authenticate("operator.krdid", signature, str(stamp), nonce, data, "/api/v1/receipts")
    assert exc.value.status_code == 403
    assert exc.value.detail == "INVALID_KRDID_SIGNATURE"


def test_registry_survives_reopening_sqlite(isolated):
    key, pub = isolated
    enroll("operator.krdid", pub)
    with sqlite3.connect(store_path()) as db:
        assert db.execute("SELECT pubkey_b64 FROM identities WHERE krdid=?",
                          ("operator.krdid",)).fetchone()[0] == pub
    assert readiness()["enrolled"] == 1


def test_public_key_enrollment_rejects_malformed_key(isolated):
    with pytest.raises(ValueError):
        enroll("bad.krdid", "notbase64")
    with pytest.raises(ValueError):
        enroll("not-an-id", isolated[1])
