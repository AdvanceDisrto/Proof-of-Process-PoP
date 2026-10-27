"""Fail-closed inbox -> signed, hash-chained machine receipts -> optional HTTPS outbox.

Requires independent Ed25519 source trust registry; private signing key stays outside source.
Every signed machine receipt certifies *ingestion and signature check only*, not real-world facts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

SOURCE_DOMAIN = b"ITM-INGRESS-RECEIPT-v1\x00"
MACHINE_DOMAIN = b"ITM-MACHINE-INTAKE-v1\x00"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
MAX_RECEIPT_BYTES = 1_000_000


class RejectedReceipt(ValueError):
    pass


def pairs_unique(pairs):
    result = {}
    for key, val in pairs:
        if key in result:
            raise RejectedReceipt("duplicate JSON key")
        result[key] = val
    return result


def load_json(raw: bytes):
    if len(raw) > MAX_RECEIPT_BYTES:
        raise RejectedReceipt("oversized JSON")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs_unique,
                      parse_float=lambda _: (_ for _ in ()).throw(RejectedReceipt("float forbidden")),
                      parse_constant=lambda _: (_ for _ in ()).throw(RejectedReceipt("nonfinite number")))


def canonical(obj) -> bytes:
    """Defined strict deterministic JSON subset; NOT general JCS RFC 8785."""
    def check(val):
        if isinstance(val, bool) or val is None or isinstance(val, str):
            return
        if type(val) is int and -(2**53 - 1) <= val <= 2**53 - 1:
            return
        if isinstance(val, list):
            for v in val:
                check(v)
            return
        if isinstance(val, dict) and all(isinstance(k, str) for k in val):
            for v in val.values():
                check(v)
            return
        raise RejectedReceipt("unsupported JSON value")
    check(obj)
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha_content(raw: bytes) -> str:
    return sha256(b"ITM-CONTENT-SHA256-v1\x00" + raw)


def pub_hex(priv: Ed25519PrivateKey) -> str:
    return priv.public_key().public_bytes(encoding=serialization.Encoding.Raw,
                                           format=serialization.PublicFormat.Raw).hex()


def load_signer(key_file: Path) -> Ed25519PrivateKey:
    raw = key_file.read_bytes()
    if len(raw) != 32:
        raise ValueError("machine private key must be raw 32-byte Ed25519 seed")
    return Ed25519PrivateKey.from_private_bytes(raw)


def atomic(path: Path, raw: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def verify_source(data: object, registry: dict) -> tuple[str, str]:
    if not isinstance(data, dict) or set(data) != {"protocol", "source_id", "receipt_id", "key_id", "body", "signature_hex"}:
        raise RejectedReceipt("source receipt keys must match strict protocol")
    if data["protocol"] != "ITM-INGRESS-RECEIPT-v1":
        raise RejectedReceipt("wrong protocol")
    for k in ["source_id", "receipt_id", "key_id"]:
        if not isinstance(data[k], str) or not ALLOWED_ID.fullmatch(data[k]):
            raise RejectedReceipt("invalid ID")
    if not isinstance(data["body"], dict):
        raise RejectedReceipt("body must be object")
    sig = data["signature_hex"]
    if not isinstance(sig, str) or not re.fullmatch(r"[0-9a-f]{128}", sig):
        raise RejectedReceipt("missing/malformed signature")
    entry = registry.get("keys", {}).get(data["key_id"])
    if not isinstance(entry, dict) or entry.get("role") != "source" or entry.get("source_id") != data["source_id"] or entry.get("active") is not True:
        raise RejectedReceipt("unknown or unauthorized signing key")
    public_hex = entry.get("public_key_hex")
    if not isinstance(public_hex, str) or not HEX64.fullmatch(public_hex):
        raise RejectedReceipt("invalid registry public key")
    unsigned = {k: v for k, v in data.items() if k != "signature_hex"}
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex)).verify(bytes.fromhex(sig), SOURCE_DOMAIN + canonical(unsigned))
    except (InvalidSignature, ValueError) as e:
        raise RejectedReceipt("bad source signature") from e
    return data["source_id"], data["receipt_id"]


@dataclass
class Router:
    root: Path
    registry_path: Path
    signer_path: Path
    machine_key_id: str
    registry_sha256: str

    def __post_init__(self):
        self.root = Path(self.root)
        registry_raw = self.registry_path.read_bytes()
        if not HEX64.fullmatch(self.registry_sha256) or sha256(registry_raw) != self.registry_sha256:
            raise ValueError("source trust registry fingerprint differs from independent pin")
        self.registry = load_json(registry_raw)
        if not isinstance(self.registry, dict) or set(self.registry) != {"protocol", "keys"} or self.registry["protocol"] != "ITM-TRUST-REGISTRY-v1" or not isinstance(self.registry["keys"], dict):
            raise ValueError("externally pinned trust registry required")
        self.signer = load_signer(self.signer_path)
        if not ALLOWED_ID.fullmatch(self.machine_key_id):
            raise ValueError("invalid machine key ID")
        for folder in ["inbox", "records", "outbox", "rejected"]:
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    def chain(self):
        """Validate every persisted event and continuity before appending."""
        records = sorted((self.root / "records").glob("*.json"))
        prev = "0" * 64
        ids, source_hashes = {}, set()
        for i, p in enumerate(records, 1):
            if p.name != f"{i:012d}.json":
                raise RuntimeError("ledger gap or noncanonical sequence")
            d = load_json(p.read_bytes())
            if not isinstance(d, dict) or set(d) != {"event", "signature_hex"}:
                raise RuntimeError("invalid persisted receipt envelope")
            event = d["event"]
            if event.get("seq") != i or event.get("prev_event_hash") != prev or event.get("protocol") != "ITM-MACHINE-INTAKE-v1":
                raise RuntimeError("tampered chain")
            try:
                self.signer.public_key().verify(bytes.fromhex(d["signature_hex"]), MACHINE_DOMAIN + canonical(event))
            except (ValueError, InvalidSignature) as e:
                raise RuntimeError("machine signature invalid") from e
            receipt_id, source_hash = event["source_receipt_id"], event["source_content_sha256"]
            if receipt_id in ids and ids[receipt_id] != source_hash:
                raise RuntimeError("persisted source receipt conflict")
            ids[receipt_id] = source_hash
            source_hashes.add(source_hash)
            prev = sha256(MACHINE_DOMAIN + canonical(event))
        return len(records), prev, ids, source_hashes

    def ingest(self, path: Path):
        """Never rewrite or remove the original inbox file. Ledger signature is not truth attestation."""
        raw = Path(path).read_bytes()
        digest = sha_content(raw)
        try:
            source_id, rid = verify_source(load_json(raw), self.registry)
        except (RejectedReceipt, UnicodeError, json.JSONDecodeError) as e:
            note = {"source_content_sha256": digest, "status": "REJECTED", "reason": type(e).__name__}
            target = self.root / "rejected" / (digest + ".json")
            if not target.exists():
                atomic(target, canonical(note) + b"\n")
            return "REJECTED", target
        n, prev, ids, hashes = self.chain()  # always verify before appending
        if rid in ids and ids[rid] != digest:
            note = {"source_content_sha256": digest, "status": "REJECTED", "reason": "receipt_id_conflict"}
            target = self.root / "rejected" / (digest + ".json")
            atomic(target, canonical(note) + b"\n")
            return "REJECTED", target
        if digest in hashes:
            return "DUPLICATE", None
        event = {"protocol": "ITM-MACHINE-INTAKE-v1", "seq": n + 1, "prev_event_hash": prev,
                 "source_id": source_id, "source_receipt_id": rid, "source_content_sha256": digest,
                 "independent_source_signature_verified": True,
                 "underlying_real_world_event_verified": False,
                 "settlement_authorized": False, "physical_actuation_authorized": False,
                 "machine_key_id": self.machine_key_id}
        sealed = {"event": event, "signature_hex": self.signer.sign(MACHINE_DOMAIN + canonical(event)).hex()}
        target = self.root / "records" / f"{n+1:012d}.json"
        atomic(target, canonical(sealed) + b"\n")
        atomic(self.root / "outbox" / f"{n+1:012d}.json", canonical(sealed) + b"\n")
        return "ACCEPTED", target

    def cycle_once(self):
        stats = {"ACCEPTED": 0, "DUPLICATE": 0, "REJECTED": 0}
        # Serialize ingestion by a single-process lock; reject multiple active workers.
        from contextlib import contextmanager
        @contextmanager
        def locked():
            # POSIX/Windows advisory lock to prevent concurrent appenders.
            with (self.root / ".router.lock").open("a+b") as f:
                if os.name == "nt":
                    import msvcrt
                    f.seek(0); f.write(b"0"); f.flush(); f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    try: yield
                    finally:
                        f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    try: yield
                    finally: fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        with locked():
            for p in sorted((self.root / "inbox").glob("*.json")):
                status, _ = self.ingest(p)
                stats[status] += 1
        return stats


def forward_outbox(root: Path, endpoint: str, bearer: str, timeout: int = 10):
    """Opt-in HTTPS delivery. Retains original spool; remote must dedupe by receipt sequence+signer.
    A successful HTTP 2xx records a local ack; this is *not* evidence of remote processing.
    """
    from urllib.parse import urlparse
    url = urlparse(endpoint)
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError("remote endpoint must be HTTPS without userinfo")
    if not bearer:
        raise ValueError("bearer required for remote forwarding")
    acks = root / "acks"; acks.mkdir(parents=True, exist_ok=True)
    sent = 0
    for file in sorted((root / "outbox").glob("*.json")):
        marker = acks / file.name
        if marker.exists():
            continue
        raw = file.read_bytes()
        req = urllib.request.Request(endpoint, data=raw, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {bearer}",
            "Idempotency-Key": sha256(raw)})
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
            if resp.status < 200 or resp.status >= 300:
                raise RuntimeError("remote did not acknowledge receipt")
        atomic(marker, b"HTTP_ACK_ONLY_NOT_VERIFICATION\n")
        sent += 1
    return sent


def main():
    ap = argparse.ArgumentParser(description="iNNOVULIS intake/route; this does not prove the contents of a receipt")
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--registry", type=Path, required=True)
    ap.add_argument("--machine-key", type=Path, required=True)
    ap.add_argument("--machine-key-id", default="local-machine")
    ap.add_argument("--registry-sha256", required=True, help="pinned SHA-256 of source trust registry from independent channel")
    ap.add_argument("--watch", action="store_true", help="run polling cycles indefinitely")
    ap.add_argument("--interval", type=float, default=5)
    ap.add_argument("--forward-url", default=os.environ.get("INNOVULIS_RECEIPT_ENDPOINT"))
    args = ap.parse_args()
    if args.interval < 1:
        ap.error("minimum interval one second")
    router = Router(args.root, args.registry, args.machine_key, args.machine_key_id, args.registry_sha256)
    while True:
        print(json.dumps(router.cycle_once(), sort_keys=True), flush=True)
        if args.forward_url:
            print("forwarded:", forward_outbox(router.root, args.forward_url, os.environ.get("INNOVULIS_RECEIPT_TOKEN", "")), flush=True)
        if not args.watch:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

