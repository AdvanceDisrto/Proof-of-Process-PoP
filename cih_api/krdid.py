"""Local .krdid identity authority: pinned Ed25519 keys, replay protection, and durable receipts.

This is software-key proof, NOT hardware-backed attestation. Operators enroll
trusted public keys out of band using a local CLI; caller-supplied keys are never
accepted as authority. SQLite is local persistent state, not replicated consensus.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from fastapi import HTTPException

PREFIX = b"iNNOVULIS-KRDID-ED25519-REQUEST-V1\x00"
KRID = re.compile(r"^[a-z][a-z0-9_-]{2,62}\.krdid$")
NONCE = re.compile(r"^[0-9a-f]{32}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
MAX_CLOCK_SKEW_SECONDS = 300


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def store_path() -> Path:
    custom = os.getenv("CIH_LOCAL_DB_PATH")
    if custom:
        return Path(custom).expanduser()
    root = os.getenv("LOCALAPPDATA") or os.getenv("XDG_DATA_HOME")
    if not root:
        root = str(Path.home() / ".local" / "share")
    return Path(root) / "iNNOVULIS" / "CIH" / "sovereign.sqlite3"


def identity_key_path() -> Path:
    root = os.getenv("LOCALAPPDATA") or os.getenv("XDG_DATA_HOME")
    if not root:
        root = str(Path.home() / ".local" / "share")
    return Path(root) / "iNNOVULIS" / "CIH" / "local-krdid-identity.json"


def database():
    path = store_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        db = sqlite3.connect(str(path), timeout=8.0)
        db.execute("PRAGMA busy_timeout=8000")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("""CREATE TABLE IF NOT EXISTS identities (
            krdid TEXT PRIMARY KEY, pubkey_b64 TEXT NOT NULL,
            enrolled_at INTEGER NOT NULL, disabled INTEGER NOT NULL DEFAULT 0
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS nonces (
            krdid TEXT NOT NULL, nonce TEXT NOT NULL, receipt_sha256 TEXT NOT NULL,
            used_at INTEGER NOT NULL, PRIMARY KEY (krdid, nonce)
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS receipts (
            receipt_sha256 TEXT PRIMARY KEY, krdid TEXT NOT NULL,
            receipt_json TEXT NOT NULL, created_at INTEGER NOT NULL
        )""")
        db.commit()
        if os.name != "nt":
            os.chmod(path, 0o600)
        return db
    except (OSError, sqlite3.Error) as exc:
        raise HTTPException(status_code=503, detail="LOCAL_STORE_UNAVAILABLE") from exc


def readiness() -> dict:
    try:
        with database() as db:
            enrolled = db.execute("SELECT COUNT(*) FROM identities WHERE disabled=0").fetchone()[0]
        return {"ready": True, "enrolled": enrolled}
    except HTTPException:
        return {"ready": False, "enrolled": 0}


def enroll(krdid: str, pubkey_b64: str):
    if not KRID.fullmatch(krdid):
        raise ValueError("Invalid .krdid identifier")
    try:
        decoded = base64.b64decode(pubkey_b64, validate=True)
        if len(decoded) != 32:
            raise ValueError("Expected raw 32-byte Ed25519 public key")
        Ed25519PublicKey.from_public_bytes(decoded)
    except (ValueError, TypeError) as exc:
        raise ValueError("Malformed Ed25519 public key") from exc
    with database() as db:
        try:
            db.execute("INSERT INTO identities (krdid,pubkey_b64,enrolled_at) VALUES (?,?,?)",
                       (krdid, pubkey_b64, int(time.time())))
            db.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("Identity already enrolled; no silent overwrite") from exc


def signed_bytes(krdid: str, timestamp: int, nonce: str, request_payload: dict,
                 path: str) -> bytes:
    envelope = {
        "domain": "innovulis.krdid.request.v1",
        "method": "POST",
        "path": path,
        "krdid": krdid,
        "timestamp": timestamp,
        "nonce": nonce,
        "payload": request_payload,
    }
    return PREFIX + canonical(envelope)


def authenticate(krdid: str | None, signature_b64: str | None, timestamp: str | None,
                 nonce: str | None, request_payload: dict, path: str) -> dict:
    if not all((krdid, signature_b64, timestamp, nonce)):
        raise HTTPException(status_code=401, detail="KRDID_SIGNATURE_REQUIRED")
    if not KRID.fullmatch(krdid) or not NONCE.fullmatch(nonce) or not timestamp.isdecimal():
        raise HTTPException(status_code=400, detail="INVALID_KRDID_AUTH_HEADERS")
    stamp = int(timestamp)
    if abs(int(time.time()) - stamp) > MAX_CLOCK_SKEW_SECONDS:
        raise HTTPException(status_code=401, detail="KRDID_SIGNATURE_EXPIRED")
    try:
        with database() as db:
            row = db.execute("SELECT pubkey_b64 FROM identities WHERE krdid=? AND disabled=0", (krdid,)).fetchone()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="LOCAL_STORE_UNAVAILABLE") from exc
    if not row:
        raise HTTPException(status_code=403, detail="KRDID_NOT_ENROLLED")
    try:
        pub = base64.b64decode(row[0], validate=True)
        signature = base64.b64decode(signature_b64, validate=True)
        if len(signature) != 64:
            raise ValueError("Bad Ed25519 signature length")
        Ed25519PublicKey.from_public_bytes(pub).verify(
            signature, signed_bytes(krdid, stamp, nonce, request_payload, path))
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise HTTPException(status_code=403, detail="INVALID_KRDID_SIGNATURE") from exc
    return {
        "krdid": krdid,
        "nonce": nonce,
        "timestamp": stamp,
        "request_sha256": hashlib.sha256(signed_bytes(krdid, stamp, nonce, request_payload, path)).hexdigest(),
        "public_key_sha256": hashlib.sha256(pub).hexdigest(),
    }


def commit_receipt(authorization: dict, receipt: dict) -> str:
    krdid = authorization["krdid"]
    nonce = authorization["nonce"]
    receipt_hash = receipt["body_sha256"]
    try:
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            # Recheck membership inside commit transaction (prevents mid-flight revocation).
            row = db.execute("SELECT disabled FROM identities WHERE krdid=?", (krdid,)).fetchone()
            if not row or row[0]:
                raise HTTPException(status_code=403, detail="KRDID_NOT_ENROLLED")
            db.execute("INSERT INTO nonces(krdid,nonce,receipt_sha256,used_at) VALUES (?,?,?,?)",
                       (krdid, nonce, receipt_hash, int(time.time())))
            db.execute("INSERT INTO receipts(receipt_sha256,krdid,receipt_json,created_at) VALUES (?,?,?,?)",
                       (receipt_hash, krdid, json.dumps(receipt, ensure_ascii=False, sort_keys=True), int(time.time())))
            db.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="KRDID_REPLAY_OR_DUPLICATE") from exc
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="LOCAL_PERSISTENCE_FAILED") from exc
    return "LOCAL_SQLITE_COMMITTED"


def consume_nonce(authorization: dict, operation_hash: str):
    """Persist one-time authorization for non-issuing operations."""
    try:
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT disabled FROM identities WHERE krdid=?",
                             (authorization["krdid"],)).fetchone()
            if not row or row[0]:
                raise HTTPException(status_code=403, detail="KRDID_NOT_ENROLLED")
            db.execute("INSERT INTO nonces(krdid,nonce,receipt_sha256,used_at) VALUES(?,?,?,?)",
                       (authorization["krdid"], authorization["nonce"],
                        operation_hash, int(time.time())))
            db.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="KRDID_REPLAY_OR_DUPLICATE") from exc
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="LOCAL_PERSISTENCE_FAILED") from exc


def _protect_file(path: Path):
    if os.name == "nt":
        import subprocess
        owner = subprocess.check_output(["whoami"], text=True).strip()
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", owner + ":(F)"],
                       check=True, capture_output=True, text=True)
    else:
        path.chmod(0o600)


def initialize_local_identity(krdid="local-test-node.krdid"):
    """Operator-only local CLI bootstrap; never callable through API."""
    path = identity_key_path()
    if path.exists():
        raise ValueError("Private identity file exists; refusing to replace or auto-enroll again")
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                serialization.NoEncryption())
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    record = {"krdid": krdid, "private_b64": base64.b64encode(private).decode(),
              "public_b64": base64.b64encode(pub).decode()}
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
        _protect_file(path)
        enroll(krdid, record["public_b64"])
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return record["krdid"], hashlib.sha256(pub).hexdigest()


def smoke(url: str):
    """Actual HTTP flow using the locally enrolled software key (not a hardware claim)."""
    import urllib.request
    record = json.loads(identity_key_path().read_text(encoding="utf-8"))
    key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(record["private_b64"], validate=True))
    evidence = {"temperature": 36.5, "unit": "C"}
    payload = {
        "claim": "Self-declared sample temperature of 36.5 C",
        "evidence": evidence, "expected_evidence_sha256": hashlib.sha256(canonical(evidence)).hexdigest(),
        "source_id": "local-test-node", "parent_receipt_hashes": [],
    }
    stamp = int(time.time())
    nonce = uuid.uuid4().hex
    signature = base64.b64encode(key.sign(signed_bytes(record["krdid"], stamp, nonce,
                                                        payload, "/api/v1/receipts"))).decode()
    req = urllib.request.Request(url.rstrip("/") + "/api/v1/receipts",
        data=canonical(payload), method="POST",
        headers={"Content-Type": "application/json", "X-Krdid": record["krdid"],
                 "X-Krdid-Signature": signature, "X-Krdid-Timestamp": str(stamp),
                 "X-Krdid-Nonce": nonce})
    with urllib.request.urlopen(req, timeout=10) as resp:
        receipt = json.load(resp)
    with urllib.request.urlopen(urllib.request.Request(url.rstrip("/") + "/api/v1/verify",
           data=canonical(receipt), method="POST", headers={"Content-Type": "application/json"}), timeout=10) as resp:
        verified = json.load(resp)
    if not verified.get("integrity_valid") or receipt.get("storage_status") != "LOCAL_SQLITE_COMMITTED":
        raise RuntimeError("Signed receipt or local persistence not verified")
    print(json.dumps({"status": "VERIFIED_PROCESS_LOCAL",
        "receipt_sha256": receipt["body_sha256"], "signature_verification": verified["status"],
        "storage": receipt["storage_status"], "krdid": record["krdid"],
        "does_not_prove": "factual truth, hardware-backed identity, global replication or consensus"}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Local sovereign .krdid identity utility; no cloud required")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init-local")
    init.add_argument("--id", default="local-test-node.krdid")
    reg = commands.add_parser("enroll")
    reg.add_argument("--id", required=True)
    reg.add_argument("--public-key-b64", required=True)
    revoke = commands.add_parser("revoke")
    revoke.add_argument("--id", required=True)
    commands.add_parser("list")
    test = commands.add_parser("smoke")
    test.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    if args.command == "init-local":
        krdid, pub_digest = initialize_local_identity(args.id)
        print("Enrolled local software identity:", krdid)
        print("Public key SHA-256:", pub_digest)
        print("Secret stored under LOCALAPPDATA; never paste or commit the file.")
    elif args.command == "enroll":
        enroll(args.id, args.public_key_b64)
        print("Operator-enrolled public key:", args.id)
    elif args.command == "revoke":
        with database() as db:
            updated = db.execute("UPDATE identities SET disabled=1 WHERE krdid=?", (args.id,)).rowcount
            db.commit()
        if not updated:
            raise SystemExit("No such identity")
        print("Identity disabled:", args.id)
    elif args.command == "list":
        with database() as db:
            for krdid, disabled in db.execute("SELECT krdid, disabled FROM identities ORDER BY krdid"):
                print(krdid, "DISABLED" if disabled else "ENROLLED")
    elif args.command == "smoke":
        smoke(args.url)


if __name__ == "__main__":
    main()
