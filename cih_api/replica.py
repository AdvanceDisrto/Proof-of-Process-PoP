"""Optional, fail-open-to-local-only CIH signed receipt replication to Supabase.

The sole authority for a request is an enrolled local .krdid Ed25519 identity.
Supabase is only a *secondary replica*, never the signer or authentication
service. Local SQLite persists first and enqueues every receipt for later retry.

New sb_secret_ API keys are sent in the apikey header only; legacy service_role
JWTs are supported temporarily for backwards compatibility. No client key can
write to the protected remote table. No secrets are logged.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from cih_api.krdid import database

PROJECT_HOST = "tkrxmdonmxpeockpbazl.supabase.co"
TABLE_PATH = "/rest/v1/cih_receipts"
REMOTE_ACKNOWLEDGED = "REPLICA_ACKNOWLEDGED"
NOT_CONFIGURED = "NOT_CONFIGURED"
PENDING_RETRY = "PENDING_RETRY"
CONFIGURATION_INVALID = "CONFIGURATION_INVALID"


def replica_config() -> tuple[str, str] | None:
    """No network calls. Accept only the pinned BUDDY project URL."""
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SECRET_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != PROJECT_HOST or parsed.port is not None or parsed.path or parsed.query or parsed.fragment or parsed.username:
        return None
    if key.startswith("sb_secret_") and len(key) > 20:
        return url, key
    # Legacy JWT key (not a publishable or anon key).
    if key.count(".") == 2 and len(key) > 80:
        return url, key
    return None


def replica_readiness() -> dict:
    key = os.getenv("SUPABASE_SECRET_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    url = os.getenv("SUPABASE_URL", "")
    config = replica_config()
    try:
        with database() as db:
            pending = db.execute("SELECT COUNT(*) FROM mirror_queue WHERE state != 'ACKNOWLEDGED'").fetchone()[0]
            acknowledged = db.execute("SELECT COUNT(*) FROM mirror_queue WHERE state = 'ACKNOWLEDGED'").fetchone()[0]
    except Exception:
        pending, acknowledged = -1, -1
    return {
        "configured": config is not None,
        "configuration_invalid": bool(url and key) and config is None,
        "pending_count": pending,
        "acknowledged_count": acknowledged,
        "provider": "SUPABASE_POSTGRES_OPTIONAL",
    }


def _headers(key: str) -> dict[str, str]:
    result = {
        "apikey": key,
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
        "User-Agent": "iNNOVULIS-CIH-Replica/0.2",
    }
    if not key.startswith("sb_secret_"):
        result["Authorization"] = "Bearer " + key
    return result


def _acknowledge(receipt_hash: str) -> None:
    with database() as db:
        db.execute(
            "UPDATE mirror_queue SET state='ACKNOWLEDGED', attempts=attempts+1, last_error=NULL,"
            " last_attempt=strftime('%s','now'), replicated_at=strftime('%s','now') WHERE receipt_sha256=?",
            (receipt_hash,),
        )
        db.commit()


def _pending(receipt_hash: str, reason: str) -> None:
    with database() as db:
        db.execute(
            "UPDATE mirror_queue SET state='PENDING', attempts=attempts+1, last_error=?,"
            " last_attempt=strftime('%s','now') WHERE receipt_sha256=?",
            (reason[:80], receipt_hash),
        )
        db.commit()


def mirror_receipt(receipt_hash: str) -> str:
    """Attempt one mirror write. Failures preserve the committed local receipt."""
    key_config = replica_config()
    if key_config is None:
        key = os.getenv("SUPABASE_SECRET_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        url = os.getenv("SUPABASE_URL", "")
        return CONFIGURATION_INVALID if key and url else NOT_CONFIGURED
    with database() as db:
        local = db.execute(
            "SELECT r.receipt_json, q.state FROM receipts r JOIN mirror_queue q"
            " ON r.receipt_sha256=q.receipt_sha256 WHERE r.receipt_sha256=?",
            (receipt_hash,),
        ).fetchone()
    if local is None:
        return PENDING_RETRY
    if local[1] == "ACKNOWLEDGED":
        return REMOTE_ACKNOWLEDGED

    stored = json.loads(local[0])
    body = stored["body"]
    # Match Supabase's signed receipt constraint; do not send any private keys.
    data = {
        "receipt_hash": receipt_hash,
        "requester_subject": body["requester_subject"],
        "receipt_body": body,
        "signature_b64": stored["signature_b64"],
        "key_id": stored["key_id"],
    }
    url, key = key_config
    request = Request(
        url + TABLE_PATH,
        data=json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers=_headers(key),
    )
    try:
        with urlopen(request, timeout=4) as response:
            if response.status not in (200, 201, 204):
                _pending(receipt_hash, "UNEXPECTED_RESPONSE")
                return PENDING_RETRY
    except HTTPError as exc:
        if exc.code == 409:
            # A duplicate is only acknowledged when remote content matches
            # the exact local hash, requester and signature.
            probe = Request(
                url + TABLE_PATH + "?receipt_hash=eq." + receipt_hash +
                "&select=receipt_hash,requester_subject,signature_b64,key_id",
                headers=_headers(key),
                method="GET",
            )
            try:
                with urlopen(probe, timeout=4) as response:
                    rows = json.load(response)
                if len(rows) == 1 and all(rows[0].get(k) == data[k] for k in
                                           ("receipt_hash", "requester_subject", "signature_b64", "key_id")):
                    _acknowledge(receipt_hash)
                    return REMOTE_ACKNOWLEDGED
            except (HTTPError, URLError, ValueError, OSError, TypeError):
                pass
            _pending(receipt_hash, "REMOTE_HASH_CONFLICT")
            return PENDING_RETRY
        _pending(receipt_hash, "HTTP_" + str(exc.code))
        return PENDING_RETRY
    except (URLError, OSError, TimeoutError, ValueError):
        _pending(receipt_hash, "NETWORK_OR_RESPONSE_ERROR")
        return PENDING_RETRY

    _acknowledge(receipt_hash)
    return REMOTE_ACKNOWLEDGED


def sync_pending(limit: int = 100) -> dict:
    """Manual retry queue; no background promises, no remote dependency."""
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    with database() as db:
        hashes = [
            row[0] for row in db.execute(
                "SELECT receipt_sha256 FROM mirror_queue WHERE state!='ACKNOWLEDGED'"
                " ORDER BY last_attempt ASC, receipt_sha256 ASC LIMIT ?",
                (limit,),
            ).fetchall()
        ]
    results = [mirror_receipt(h) for h in hashes]
    state = replica_readiness()
    return {
        "checked": len(results),
        "acknowledged": results.count(REMOTE_ACKNOWLEDGED),
        "not_configured": results.count(NOT_CONFIGURED),
        "pending": results.count(PENDING_RETRY) + results.count(CONFIGURATION_INVALID),
        "remaining_pending": state["pending_count"],
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Optional Supabase replica for locally signed receipts")
    parser.add_argument("action", choices=["status", "sync"])
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if args.action == "status":
        print(json.dumps(replica_readiness(), indent=2))
    else:
        print(json.dumps(sync_pending(args.limit), indent=2))


if __name__ == "__main__":
    main()
