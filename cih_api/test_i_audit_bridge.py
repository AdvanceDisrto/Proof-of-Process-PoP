"""End-to-end audit bridge against the EXISTING authenticated CIH receipt endpoint."""
import hashlib
import pytest
from cih_api.test_app import client, secure_config, authorize
from i_audit_bridge import audit_exact_spans, to_cih_receipt_request


def fixture_pair():
    text = "The system has a declared 15 kW allocation limit."
    source = {"source_id": "fixture://energy-policy", "version": "2026.11",
              "text": text, "expected_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
              "retrieved_at_utc": "2026-11-11T19:00:00Z"}
    claim = {"source_id": source["source_id"], "source_version": "2026.11",
             "claim": text, "quote": text, "start": 0, "end": len(text)}
    return source, claim


def test_audited_span_is_signed_by_existing_cih(secure_config):
    source, claim = fixture_pair()
    report = audit_exact_spans([source], [claim])
    assert report["verdict"] == "PASS_EXACT_SPAN_CHECK"
    request = to_cih_receipt_request(report)
    response = client.post("/api/v1/receipts", json=request,
                           headers=authorize(secure_config, request))
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["storage_status"] == "LOCAL_SQLITE_COMMITTED"
    assert receipt["body"]["assessment"] == "INPUT_DIGEST_MATCHED"
    verification = client.post("/api/v1/verify", json=receipt)
    assert verification.status_code == 200
    assert verification.json()["integrity_valid"] is True
    assert "source data" in " ".join(receipt["body"]["does_not_prove"])


def test_unsupported_claim_is_still_documented_not_passed(secure_config):
    source, claim = fixture_pair()
    claim["claim"] = "The system can consume exactly 15 kW"
    report = audit_exact_spans([source], [claim])
    assert report["verdict"] == "REFUSED_UNSUPPORTED_CLAIMS"
    payload = to_cih_receipt_request(report)
    result = client.post("/api/v1/receipts", json=payload,
                         headers=authorize(secure_config, payload))
    assert result.status_code == 200
    assert payload["evidence"]["audit_report"]["decisions"][0]["status"] == "REFUSED"


def test_unenrolled_or_missing_identity_cannot_mint(secure_config):
    source, claim = fixture_pair()
    request = to_cih_receipt_request(audit_exact_spans([source], [claim]))
    assert client.post("/api/v1/receipts", json=request).status_code == 401


def test_replay_of_audit_receipt_request_blocked(secure_config):
    source, claim = fixture_pair()
    request = to_cih_receipt_request(audit_exact_spans([source], [claim]))
    headers = authorize(secure_config, request)
    assert client.post("/api/v1/receipts", json=request, headers=headers).status_code == 200
    retry = client.post("/api/v1/receipts", json=request, headers=headers)
    assert retry.status_code == 409
    assert retry.json()["detail"] == "KRDID_REPLAY_OR_DUPLICATE"


def test_modified_evidence_after_authorization_rejected(secure_config):
    source, claim = fixture_pair()
    request = to_cih_receipt_request(audit_exact_spans([source], [claim]))
    headers = authorize(secure_config, request)
    request["evidence"]["audit_report"]["coverage_ratio"] = 0.25
    response = client.post("/api/v1/receipts", json=request, headers=headers)
    assert response.status_code in (403, 422)


def test_citation_digest_mismatch_fails_closed(secure_config):
    source, claim = fixture_pair()
    source["expected_sha256"] = "0" * 64
    report = audit_exact_spans([source], [claim])
    assert report["decisions"][0]["reason"] == "SOURCE_DIGEST_MISMATCH"
    assert report["coverage_ratio"] == 0.0
