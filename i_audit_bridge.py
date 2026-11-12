"""i™ ΔiΔ exact-span audit -> existing CIH authenticated receipt request.

Conservative deterministic text matcher; NOT a semantic entailment engine, model
certifier, ISO certificate, Z3 proof, permanent ledger, or validation of source truth.
The existing CIH /api/v1/receipts owns authentication, signing and persistence.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime
from typing import Any

AUDIT_SCHEMA = "innovulis.i.audit.exact_span.v1"
POLICY_VERSION = "i-audit-exact-span-2026-11"
MAX_DOCUMENT_BYTES = 262_144
MAX_CLAIMS = 64
MAX_SOURCES = 32
HASH_RE = re.compile(r"[a-f0-9]{64}\Z")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalized(value: str) -> str:
    return " ".join(value.split())


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and HASH_RE.fullmatch(value) is not None


def audit_exact_spans(sources: list[dict], claims: list[dict]) -> dict:
    """Verify exact source spans, not truth or entailment; refuse uncertain claims.

    Source: {source_id, version, text, expected_sha256, retrieved_at_utc}
    Claim: {claim, source_id, source_version, quote, start, end}
    Offsets are Python Unicode code-point indices [start, end) in source text.
    """
    if not isinstance(sources, list) or not isinstance(claims, list):
        raise ValueError("AUDIT_INPUT_NOT_LIST")
    if len(sources) > MAX_SOURCES or not 1 <= len(claims) <= MAX_CLAIMS:
        raise ValueError("AUDIT_SIZE_LIMIT")
    known: dict[str, dict] = {}
    invalid: set[str] = set()
    source_metadata = []
    for src in sources:
        if not isinstance(src, dict):
            raise ValueError("SOURCE_NOT_OBJECT")
        key, version, raw = src.get("source_id"), src.get("version"), src.get("text")
        expected, retrieved = src.get("expected_sha256"), src.get("retrieved_at_utc")
        if not (isinstance(key, str) and 1 <= len(key) <= 160
                and isinstance(version, str) and bool(version)
                and isinstance(raw, str) and len(raw.encode("utf-8")) <= MAX_DOCUMENT_BYTES
                and _valid_hash(expected) and isinstance(retrieved, str) and retrieved):
            raise ValueError("INVALID_SOURCE_METADATA")
        try:
            parsed = datetime.fromisoformat(retrieved.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError()
        except ValueError as exc:
            raise ValueError("SOURCE_TIMESTAMP_NOT_UTC_AWARE") from exc
        if key in known or key in invalid:
            raise ValueError("DUPLICATE_SOURCE_ID")
        content_hash = text_hash(raw)
        if content_hash == expected:
            known[key] = src
        else:
            invalid.add(key)
        source_metadata.append({"source_id": key, "version": version,
                                "expected_sha256": expected,
                                "digest_matches": content_hash == expected,
                                "retrieved_at_utc": retrieved,
                                "source_recoverability": "REQUIRES_ORIGINAL_DOCUMENT"})

    decisions: list[dict] = []
    for idx, item in enumerate(claims):
        if not isinstance(item, dict):
            raise ValueError("CLAIM_NOT_OBJECT")
        claim = item.get("claim")
        ref = item.get("source_id")
        quote = item.get("quote")
        start, end = item.get("start"), item.get("end")
        version = item.get("source_version")
        reason = "SUPPORTED_EXACT_SPAN"
        if not isinstance(claim, str) or not claim.strip():
            reason = "EMPTY_CLAIM"
        elif ref in invalid:
            reason = "SOURCE_DIGEST_MISMATCH"
        elif ref not in known:
            reason = "SOURCE_NOT_AVAILABLE"
        elif known[ref]["version"] != version:
            reason = "SOURCE_VERSION_MISMATCH"
        elif type(start) is not int or type(end) is not int or start < 0 or end <= start or end > len(known[ref]["text"]):
            reason = "INVALID_SPAN"
        elif not isinstance(quote, str) or known[ref]["text"][start:end] != quote:
            reason = "SPAN_TEXT_MISMATCH"
        elif _normalized(claim) != _normalized(quote):
            reason = "ENTAILMENT_UNVERIFIED"
        decisions.append({"index": idx, "source_id": ref,
                          "status": "SUPPORTED_EXACT_SPAN" if reason == "SUPPORTED_EXACT_SPAN" else "REFUSED",
                          "reason": reason,
                          "claim_sha256": text_hash(claim) if isinstance(claim, str) else None,
                          "quote_sha256": text_hash(quote) if isinstance(quote, str) else None,
                          "start": start if type(start) is int else None,
                          "end": end if type(end) is int else None})

    supported = sum(d["status"] == "SUPPORTED_EXACT_SPAN" for d in decisions)
    policy = {"schema": AUDIT_SCHEMA, "policy_version": POLICY_VERSION,
              "decision_rule": "claim must equal exact cited span after whitespace normalization",
              "evaluation": "deterministic_document_text_only"}
    body = {"schema": AUDIT_SCHEMA, "policy_version": POLICY_VERSION,
            "policy_sha256": digest(policy), "sources": source_metadata,
            "decisions": decisions, "supported": supported, "requested": len(decisions),
            "coverage_ratio": supported / len(decisions),
            "verdict": "PASS_EXACT_SPAN_CHECK" if supported == len(decisions) else "REFUSED_UNSUPPORTED_CLAIMS",
            "human_review": "REQUIRED_FOR_FACTUAL_TRUTH_AND_COMPLIANCE",
            "evidence_tier": "EXACT_TEXT_MATCH_ONLY",
            "does_not_prove": ["that the source is factual or trustworthy",
                               "that a paraphrase is logically supported",
                               "that any legal compliance or certification has been achieved",
                               "that source artifacts remain recoverable without external storage",
                               "that an LLM executed, a physical process occurred, or OTS anchored"]}
    return {**body, "report_sha256": digest(body)}


def to_cih_receipt_request(report: dict, *, source_id: str = "i-audit-bridge",
                           parents: list[str] | None = None) -> dict:
    """Build payload for existing KRDID-gated POST /api/v1/receipts.

    Does NOT mint/sign a receipt. Existing CIH authenticates caller, checks
    evidence digest, signs and durably records it.
    """
    if not isinstance(report, dict) or report.get("schema") != AUDIT_SCHEMA:
        raise ValueError("UNSUPPORTED_AUDIT_SCHEMA")
    body = {k: v for k, v in report.items() if k != "report_sha256"}
    if digest(body) != report.get("report_sha256"):
        raise ValueError("AUDIT_REPORT_TAMPERED")
    parent_hashes = [] if parents is None else parents
    if len(parent_hashes) > 32 or len(set(parent_hashes)) != len(parent_hashes) or any(not _valid_hash(h) for h in parent_hashes):
        raise ValueError("INVALID_PARENT_HASHES")
    evidence = {"audit_report": report, "bridge": "AUDITOR_TEXT_CHECK_NOT_CIH_SIGNATURE"}
    return {"claim": "Deterministic exact-span audit event (not independent source truth)",
            "evidence": evidence, "expected_evidence_sha256": digest(evidence),
            "source_id": source_id, "parent_receipt_hashes": parent_hashes}
