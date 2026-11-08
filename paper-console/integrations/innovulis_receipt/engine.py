"""Fully offline, independent open receipt verifier. No issuer network calls.

A VERIFIED_DIGITAL_RECEIPT means cryptographic authenticity, declared
integer relation, and local evidence-file hashes check out under an
*operator-pinned* trust anchor and fresh-enough signed revocation snapshot.
It is NOT proof the original sensor measured the physical truth.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import hashlib
import hmac
import time
from .codec import canonical, sha256, FormatError
from .crypto import (merkle_root, witness_commitment, ISSUER_DOMAIN, ENGINEER_DOMAIN,
                     WITNESS_DOMAIN, REVOCATION_DOMAIN, ISSUANCE_LOG_DOMAIN, verify_signature, check_hex)
from .schema import validate_packet, validate_trust, validate_revocations, validate_issuance_log


@dataclass
class Verdict:
    code: str = "REJECTED"
    verified: bool = False
    checks: dict = field(default_factory=dict)
    failures: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    receipt_sha256: str | None = None
    trust_anchor_sha256: str | None = None
    subject: str | None = None
    claim_verdict: str | None = None
    accountable_human: dict | None = None
    evidence_file_count_verified: int = 0
    witness_signature_count_verified: int = 0
    proof_scope: str = "Signed digital declaration under an integer comparison; not physical-truth proof"

    def to_dict(self):
        return asdict(self)


def _record(v: Verdict, name: str, ok: bool, reason: str) -> None:
    v.checks[name] = bool(ok)
    if not ok:
        v.failures.append(reason)


def _find(items: list[dict], key: str):
    return next((x for x in items if x["id"] == key), None)


def _key_valid(key, issued):
    return key is not None and key["valid_from"] <= issued <= key["valid_until"]


def _hash_evidence(evidence_dir: str | Path, manifest: list, max_bytes: int) -> tuple[bool, int]:
    base = Path(evidence_dir).resolve(strict=True)
    count = 0
    for item in manifest:
        path = base / item["name"]
        # Only simple basenames are allowed by the strict schema, also reject symlinks.
        if path.is_symlink() or not path.is_file() or path.parent.resolve(strict=True) != base:
            return False, count
        if path.stat().st_size > max_bytes:
            return False, count
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as f:
            for buf in iter(lambda: f.read(65536), b""):
                size += len(buf)
                if size > max_bytes:
                    return False, count
                digest.update(buf)
        if not hmac.compare_digest(digest.hexdigest(), item["sha256"]):
            return False, count
        count += 1
    return True, count


def verify(packet: dict, trust: dict, revocations: dict, issuance_log: dict | None = None, *,
           expected_anchor_sha256: str, expected_subject: str,
           evidence_dir: str | Path | None = None,
           current_time: int | None = None, expected_nonce_hex: str | None = None) -> Verdict:
    """Always requires trust fingerprint and subject supplied *outside* QR input.

    A signed revocation snapshot is checked offline. Offline verification
    cannot detect a newer, unknown revocation or prove issuer clock accuracy.
    The optional fresh nonce independently binds a challenge, if available.
    """
    result = Verdict()
    try:
        validate_packet(packet)
        validate_trust(trust)
        validate_revocations(revocations)
        validate_issuance_log(issuance_log)
        result.checks["strict_schema"] = True
        anchor_hash = sha256(canonical(trust))
        result.trust_anchor_sha256 = anchor_hash
        check_hex(expected_anchor_sha256)
        anchor_ok = hmac.compare_digest(anchor_hash, expected_anchor_sha256)
        _record(result, "independently_pinned_trust_anchor", anchor_ok,
                "trust anchor does not match independently supplied SHA-256 pin")
        if not anchor_ok:
            return result
        r = packet["receipt"]
        result.receipt_sha256 = sha256(canonical(r))
        result.subject = r["subject"]
        result.claim_verdict = r["verdict"]
        _record(result, "independent_subject_match", type(expected_subject) is str and
                hmac.compare_digest(r["subject"], expected_subject),
                "receipt subject differs from the separately identified object")
        if expected_nonce_hex is None:
            result.warnings.append("NO_FRESH_CHALLENGE: signed receipt may be copied/replayed for same subject")
        else:
            check_hex(expected_nonce_hex, 32)
            _record(result, "independent_challenge_nonce", hmac.compare_digest(r["nonce_hex"], expected_nonce_hex),
                    "independently required challenge nonce differs")
        _record(result, "claim_hash", sha256(canonical(r["claim"])) == r["claim_sha256"],
                "claim hash mismatch")
        predicate = (r["claim"]["observed"] <= r["claim"]["limit"])
        _record(result, "independent_integer_predicate",
                (r["verdict"] == "PROVEN_TRUE") == predicate,
                "declared verdict inconsistent with independently calculated integer relation")
        _record(result, "evidence_merkle_root",
                hmac.compare_digest(merkle_root(r["evidence_manifest"]), r["evidence_root"]),
                "evidence manifest does not commit to the declared Merkle root")
        _record(result, "witness_set_merkle_root",
                hmac.compare_digest(witness_commitment(trust), r["witness_set_root"]),
                "witness set does not match the independently pinned trust anchor")
        # A distinct public log authority signs a checkpoint containing the
        # exact receipt digest. This is inclusion in ONE signed small snapshot,
        # not proof of append-only transparency across multiple checkpoints.
        checkpoint = issuance_log["checkpoint"]
        log_authority = trust["issuance_log_authority"]
        log_digests = checkpoint["entries"]
        _record(result, "issuance_log_authority_pin",
                checkpoint["authority_id"] == log_authority["id"],
                "receipt issuance checkpoint authority not trusted")
        _record(result, "issuance_log_signature",
                verify_signature(log_authority["public_key"], ISSUANCE_LOG_DOMAIN,
                                 checkpoint, issuance_log["signature"]),
                "independent issuance checkpoint signature invalid")
        _record(result, "issuance_log_merkle_root",
                hmac.compare_digest(merkle_root([{"receipt_sha256":digest}
                                                  for digest in log_digests]),
                                     checkpoint["merkle_root"]),
                "issuance checkpoint Merkle root invalid")
        _record(result, "issuance_log_receipt_inclusion",
                result.receipt_sha256 in log_digests,
                "exact signed receipt SHA-256 absent from issuance snapshot")

        p = trust["policy"]
        if current_time is None:
            now = int(time.time())
        else:
            if type(current_time) is not int or current_time < 0:
                raise FormatError("invalid verifier clock")
            now = current_time
        _record(result, "issuance_log_freshness",
                checkpoint["serial"] >= p["minimum_log_serial"] and
                checkpoint["issued_at"] >= r["issued_at"] and
                checkpoint["issued_at"] <= now + p["max_clock_skew_seconds"] and
                now - checkpoint["issued_at"] <= p["max_log_age_seconds"],
                "issuance checkpoint stale, prematurely dated, or below independently pinned serial floor")
        result.warnings.append("LOG_TRANSPARENCY_LIMIT: one signed checkpoint does not prove append-only consistency or exclude omitted receipts")
        _record(result, "receipt_freshness",
                r["issued_at"] <= now + p["max_clock_skew_seconds"] and
                now <= r["expires_at"] and
                now - r["issued_at"] <= p["max_receipt_age_seconds"] and
                r["issued_at"] - r["observed_at"] <= p["max_observation_lag_seconds"],
                "receipt stale, not yet issued, or observation outside allowed time window")
        result.warnings.append("ISSUER_TIME_UNTRUSTED: receipt timestamps are signed claims, not independent TSA evidence")
        result.warnings.append("VERIFIER_CLOCK: freshness relies on local OS clock; independent time not established")
        if r["energy_microjoules"] is not None:
            result.warnings.append("ENERGY_READING_UNVERIFIED: signer-attested number; meter calibration and hardware unavailable")

        issuer_key = _find(trust["issuer_keys"], r["issuer_key_id"])
        _record(result, "issuer_identity",
                issuer_key is not None and r["issuer_id"] == r["issuer_key_id"] and
                _key_valid(issuer_key, r["issued_at"]),
                "issuer key not pinned or outside declared key-validity window")
        _record(result, "issuer_signature", issuer_key is not None and
                verify_signature(issuer_key["public_key"], ISSUER_DOMAIN, r, packet["issuer_signature"]),
                "issuer signature invalid")

        engineer_key = _find(trust["engineers"], r["responsible_id"])
        _record(result, "accountable_engineer_key", _key_valid(engineer_key, r["issued_at"]),
                "accountable person not identified by pinned engineer key")
        if engineer_key is not None:
            result.accountable_human = {k: engineer_key[k] for k in ("id", "name", "organization", "role")}
        _record(result, "engineer_countersignature", engineer_key is not None and
                verify_signature(engineer_key["public_key"], ENGINEER_DOMAIN, r, packet["engineer_signature"]),
                "accountability countersignature invalid")
        result.warnings.append("ENGINEER_IDENTITY: trust anchor administrator must verify person and professional credentials")

        snap = revocations["snapshot"]
        auth = trust["revocation_authority"]
        _record(result, "revocation_authority_pin", snap["authority_id"] == auth["id"],
                "revocation signer not pinned")
        _record(result, "revocation_signature", verify_signature(auth["public_key"],
                REVOCATION_DOMAIN, snap, revocations["signature"]),
                "signed revocation snapshot invalid")
        _record(result, "revocation_snapshot_freshness",
                snap["serial"] >= p["minimum_revocation_serial"] and
                snap["issued_at"] <= now + p["max_clock_skew_seconds"] and
                now <= snap["next_update"] and
                now - snap["issued_at"] <= p["max_revocation_age_seconds"],
                "revocation snapshot is stale, expired or below pinned minimum serial")
        result.warnings.append("OFFLINE_REVOCATION_LIMIT: new revocations after the installed signed snapshot cannot be detected")
        revoked = {entry["id"] for entry in snap["revoked_keys"]}
        protected_keys = {r["issuer_key_id"], r["responsible_id"], log_authority["id"]}
        verified_witness_ids = []
        for item in packet["witness_signatures"]:
            witness_key = _find(trust["witnesses"], item["id"])
            if (_key_valid(witness_key, r["issued_at"]) and item["id"] not in revoked and
                verify_signature(witness_key["public_key"], WITNESS_DOMAIN, r, item["signature"])):
                verified_witness_ids.append(item["id"])
            else:
                _record(result, "witness_" + item["id"], False,
                        "invalid, revoked or untrusted witness: " + item["id"])
        result.witness_signature_count_verified = len(verified_witness_ids)
        _record(result, "witness_quorum", len(verified_witness_ids) >= p["witness_threshold"],
                "insufficient independent pinned-key witness signatures")
        _record(result, "signing_key_revocations", not bool((protected_keys | set(verified_witness_ids)) & revoked),
                "issuer, engineer or accepted witness key revoked")
        result.warnings.append("WITNESS_INDEPENDENCE: distinct signed keys do not prove distinct external operators")

        if evidence_dir is None:
            result.checks["evidence_file_bytes"] = None
            result.warnings.append("EVIDENCE_BYTES_UNAVAILABLE: manifest hashes verified but underlying artifacts not inspected")
        else:
            try:
                matched, count = _hash_evidence(evidence_dir, r["evidence_manifest"],
                                                p["max_evidence_file_bytes"])
            except (OSError, RuntimeError):
                matched, count = False, 0
            result.evidence_file_count_verified = count
            _record(result, "evidence_file_bytes", matched,
                    "missing, unsafe or modified original evidence file")

        if result.failures:
            result.code = "REJECTED"
        elif evidence_dir is None:
            result.code = "CRYPTOGRAPHIC_ATTESTATION_ONLY"
        else:
            result.code = "VERIFIED_DIGITAL_RECEIPT"
            result.verified = True
        return result
    except (FormatError, TypeError, ValueError, KeyError, OverflowError, UnicodeError) as err:
        result.failures.append("invalid strict receipt profile: " + str(err)[:200])
        result.checks["strict_schema"] = False
        return result
