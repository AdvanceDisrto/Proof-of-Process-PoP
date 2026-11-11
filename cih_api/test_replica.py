"""Optional Supabase replica tests: no remote identity and no fake storage acknowledgement."""
from __future__ import annotations

import base64
import io
import json
import sqlite3
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import pytest

from cih_api.krdid import database, store_path
from cih_api.replica import (
    CONFIGURATION_INVALID, NOT_CONFIGURED, PENDING_RETRY, REMOTE_ACKNOWLEDGED,
    mirror_receipt, replica_readiness, sync_pending, PROJECT_HOST,
)

HASH = "a" * 64
SUBJECT = "local-test-node.krdid"


@pytest.fixture
def local_receipt(monkeypatch, tmp_path):
    monkeypatch.setenv("CIH_LOCAL_DB_PATH", str(tmp_path / "cih.sqlite3"))
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("CIH_REPLICA_TRANSPORT", raising=False)
    body = {
        "schema": "innovulis.cih.receipt.v0.1",
        "requester_subject": SUBJECT,
        "claim": "Test-only input hash matched",
        "operation": "evidence_digest_validation",
    }
    receipt = {
        "body": body,
        "body_sha256": HASH,
        "signature_b64": base64.b64encode(b"s" * 64).decode("ascii"),
        "key_id": "ed25519-sha256:" + "b" * 24,
        "storage_status": "LOCAL_SQLITE_COMMITTED",
    }
    with database() as db:
        db.execute(
            "INSERT INTO receipts(receipt_sha256,krdid,receipt_json,created_at)"
            " VALUES (?,?,?,123)",
            (HASH, SUBJECT, json.dumps(receipt)),
        )
        db.execute("INSERT INTO mirror_queue(receipt_sha256) VALUES (?)", (HASH,))
        db.commit()
    return receipt


def configure_server(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://" + PROJECT_HOST)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_" + "A" * 50)


class Response:
    def __init__(self, status=201, value=None):
        self.status = status
        self.value = value
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, *args):
        return json.dumps(self.value or []).encode("utf-8")


def test_offline_receipt_remains_valid_without_supabase(local_receipt):
    assert mirror_receipt(HASH) == NOT_CONFIGURED
    assert replica_readiness()["pending_count"] == 1
    with sqlite3.connect(store_path()) as db:
        assert db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 1


def test_public_key_never_gains_server_write_authority(local_receipt, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://" + PROJECT_HOST)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_publishable_dont_use_for_evidence_table")
    with patch("cih_api.replica.urlopen") as upstream:
        assert mirror_receipt(HASH) == CONFIGURATION_INVALID
        upstream.assert_not_called()


def test_reject_unpinned_remote_target(local_receipt, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://attacker.example/evil")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_" + "A" * 50)
    with patch("cih_api.replica.urlopen") as upstream:
        assert mirror_receipt(HASH) == CONFIGURATION_INVALID
        upstream.assert_not_called()


def test_successful_server_only_replication_acknowledged(local_receipt, monkeypatch):
    configure_server(monkeypatch)
    with patch("cih_api.replica.urlopen", return_value=Response(201)) as upstream:
        assert mirror_receipt(HASH) == REMOTE_ACKNOWLEDGED
        request = upstream.call_args.args[0]
        assert request.get_method() == "POST"
        assert request.full_url == "https://" + PROJECT_HOST + "/rest/v1/cih_receipts"
        assert "Authorization" not in request.headers  # sb_secret_ is NOT a JWT
        assert request.headers["Apikey"].startswith("sb_secret_")
        written = json.loads(request.data)
        assert written["requester_subject"] == SUBJECT
        assert written["receipt_body"] == local_receipt["body"]
        assert written["receipt_hash"] == HASH
        assert "private_b64" not in request.data.decode()
        assert "supabase_key" not in request.data.decode()
    assert replica_readiness()["pending_count"] == 0
    with sqlite3.connect(store_path()) as db:
        assert db.execute("SELECT state FROM mirror_queue").fetchone()[0] == "ACKNOWLEDGED"


def test_remote_outage_does_not_invalidate_locally_committed_receipt(local_receipt, monkeypatch):
    configure_server(monkeypatch)
    with patch("cih_api.replica.urlopen", side_effect=URLError("offline")):
        assert mirror_receipt(HASH) == PENDING_RETRY
    state = replica_readiness()
    assert state["pending_count"] == 1
    with sqlite3.connect(store_path()) as db:
        assert db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 1
        assert db.execute("SELECT attempts FROM mirror_queue").fetchone()[0] == 1


def test_pending_queue_retries_after_network_recovery(local_receipt, monkeypatch):
    configure_server(monkeypatch)
    with patch("cih_api.replica.urlopen", side_effect=URLError("offline")):
        assert mirror_receipt(HASH) == PENDING_RETRY
    with patch("cih_api.replica.urlopen", return_value=Response(201)):
        r = sync_pending()
    assert r["checked"] == 1
    assert r["acknowledged"] == 1
    assert r["remaining_pending"] == 0
    with patch("cih_api.replica.urlopen") as upstream:
        assert mirror_receipt(HASH) == REMOTE_ACKNOWLEDGED
        upstream.assert_not_called()


def test_duplicate_receipt_only_acks_when_remote_content_matches(local_receipt, monkeypatch):
    configure_server(monkeypatch)
    mismatch = {
        "receipt_hash": HASH,
        "requester_subject": "attacker.krdid",
        "signature_b64": "FAKE",
        "key_id": local_receipt["key_id"],
    }
    duplicate = HTTPError(
        "https://" + PROJECT_HOST + "/rest/v1/cih_receipts",
        409, "Conflict", hdrs={}, fp=None,
    )
    with patch("cih_api.replica.urlopen", side_effect=[duplicate, Response(200, [mismatch])]):
        assert mirror_receipt(HASH) == PENDING_RETRY
    assert replica_readiness()["pending_count"] == 1
    same = dict(mismatch, requester_subject=SUBJECT,
                signature_b64=local_receipt["signature_b64"])
    with patch("cih_api.replica.urlopen", side_effect=[duplicate, Response(200, [same])]):
        assert mirror_receipt(HASH) == REMOTE_ACKNOWLEDGED
    assert replica_readiness()["pending_count"] == 0


def test_new_secret_key_not_sent_as_authorization_bearer(local_receipt, monkeypatch):
    configure_server(monkeypatch)
    with patch("cih_api.replica.urlopen", return_value=Response(204)) as request:
        assert mirror_receipt(HASH) == REMOTE_ACKNOWLEDGED
        headers = request.call_args.args[0].headers
        assert "Authorization" not in headers
        assert headers["Apikey"].startswith("sb_secret_")


def test_legacy_server_role_key_still_supported_for_migration(local_receipt, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://" + PROJECT_HOST)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "a" * 30 + "." + "b" * 30 + "." + "c" * 30)
    with patch("cih_api.replica.urlopen", return_value=Response(201)) as request:
        assert mirror_receipt(HASH) == REMOTE_ACKNOWLEDGED
        assert request.call_args.args[0].headers["Authorization"].startswith("Bearer ")


def test_edge_transport_needs_no_supabase_secret_on_local_node(local_receipt, monkeypatch):
    monkeypatch.setenv("CIH_REPLICA_TRANSPORT", "edge")
    assert replica_readiness()["configured"] is True
    assert replica_readiness()["transport"] == "SIGNED_CIH_EDGE_NO_LOCAL_SECRET"
    expected = {"status": "REPLICA_ACKNOWLEDGED", "receipt_hash": HASH}
    with patch("cih_api.replica.urlopen", return_value=Response(200, expected)) as mocked:
        assert mirror_receipt(HASH) == REMOTE_ACKNOWLEDGED
        req = mocked.call_args.args[0]
        assert req.get_method() == "POST"
        assert req.full_url == "https://" + PROJECT_HOST + "/functions/v1/strmkrd-signing/cih-mirror"
        assert "Apikey" not in req.headers
        assert "Authorization" not in req.headers
        sent = json.loads(req.data)
        assert sent["signature_b64"] == local_receipt["signature_b64"]
        assert sent["body_sha256"] == HASH
    assert replica_readiness()["pending_count"] == 0


def test_edge_unenrolled_node_is_pending_not_acknowledged(local_receipt, monkeypatch):
    monkeypatch.setenv("CIH_REPLICA_TRANSPORT", "edge")
    denial = HTTPError("https://"+PROJECT_HOST+"/functions/v1/strmkrd-signing/cih-mirror",
                       403, "Node not enrolled", hdrs={}, fp=None)
    with patch("cih_api.replica.urlopen", side_effect=denial):
        assert mirror_receipt(HASH) == PENDING_RETRY
    with sqlite3.connect(store_path()) as db:
        assert db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 1
        assert db.execute("SELECT last_error FROM mirror_queue").fetchone()[0] == "EDGE_HTTP_403"


def test_edge_forged_ack_cannot_mark_local_queue_committed(local_receipt, monkeypatch):
    monkeypatch.setenv("CIH_REPLICA_TRANSPORT", "edge")
    wrong = {"status": "REPLICA_ACKNOWLEDGED", "receipt_hash": "b" * 64}
    with patch("cih_api.replica.urlopen", return_value=Response(200, wrong)):
        assert mirror_receipt(HASH) == PENDING_RETRY
    assert replica_readiness()["pending_count"] == 1


def test_edge_outage_does_not_block_signed_local_receipt(local_receipt, monkeypatch):
    monkeypatch.setenv("CIH_REPLICA_TRANSPORT", "edge")
    with patch("cih_api.replica.urlopen", side_effect=URLError("offline")):
        assert mirror_receipt(HASH) == PENDING_RETRY
    with sqlite3.connect(store_path()) as db:
        assert db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM mirror_queue WHERE state='PENDING'").fetchone()[0] == 1
