"""CIH production-integration contract tests; no live secrets or provider writes."""
import base64
import json
from unittest.mock import patch
from urllib.error import HTTPError

import pytest
from fastapi import HTTPException

from cih_api.app import SignedReceipt, append_to_supabase, canonical


@pytest.fixture
def example_receipt():
    return SignedReceipt(
        body={
            "schema": "innovulis.cih.receipt.v0.1",
            "operation": "evidence_digest_validation",
            "requester_subject": "auth0|test-local",
        },
        body_sha256="a" * 64,
        signature_b64=base64.b64encode(b"x" * 64).decode("ascii"),
        key_id="ed25519-sha256:" + "b" * 24,
    )


def test_no_database_configuration_does_not_claim_write(example_receipt, monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    assert append_to_supabase(example_receipt, "auth0|test-local") == "NOT_CONFIGURED"


def test_database_request_uses_subject_and_server_side_credential(example_receipt, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-only-not-a-real-key")

    class FakeResponse:
        status = 201
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    with patch("urllib.request.urlopen", return_value=FakeResponse()) as upstream:
        assert append_to_supabase(example_receipt, "auth0|test-local") == "DATABASE_ACKNOWLEDGED"

    request = upstream.call_args.args[0]
    assert request.full_url == "https://example.supabase.co/rest/v1/cih_receipts"
    assert request.get_method() == "POST"
    body = json.loads(request.data)
    assert body["auth0_subject"] == "auth0|test-local"
    assert body["receipt_hash"] == "a" * 64
    assert body["receipt_body"]["requester_subject"] == body["auth0_subject"]
    assert body["signature_b64"] == example_receipt.signature_b64
    assert request.headers["Apikey"] == "test-only-not-a-real-key"
    assert request.headers["Authorization"] == "Bearer test-only-not-a-real-key"
    assert "test-only-not-a-real-key" not in str(body)


def test_database_write_error_fails_closed(example_receipt, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-only-not-a-real-key")
    error = HTTPError("https://example.supabase.co", 403, "Forbidden", hdrs={}, fp=None)
    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(HTTPException) as exc:
            append_to_supabase(example_receipt, "auth0|test-local")
    assert exc.value.status_code == 503
    assert exc.value.detail == "PERSISTENCE_FAILED"
