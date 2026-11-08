"""Fail-closed, append-only-by-policy SQLite receipt journal.

SQLite is durable locally, but cannot provide an externally immutable ledger.
"""
from __future__ import annotations
from pathlib import Path
import json
import sqlite3
import time
import threading
import hashlib
import secrets
from .crypto import (SCHEMA, ZERO_HASH, ReceiptError, canonical, make_envelope,
                     verify_envelope, load_or_create_identity, public_hex,
                     public_fingerprint)


class ReceiptJournal:
    def __init__(self, data_dir):
        root=Path(data_dir)
        root.mkdir(parents=True, exist_ok=True,mode=0o700)
        self.identity=load_or_create_identity(root/"terminal_identity.pem")
        self.public_key=public_hex(self.identity)
        self.fingerprint=public_fingerprint(self.public_key)
        self.db=sqlite3.connect(str(root/"receipts.sqlite3"), isolation_level=None,
                                timeout=5, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("CREATE TABLE IF NOT EXISTS metadata (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS receipts (sequence INTEGER PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE, envelope_json TEXT NOT NULL, timestamp_ns INTEGER NOT NULL)")
        self._lock=threading.Lock()
        saved=self.db.execute("SELECT value FROM metadata WHERE name='issuer_fingerprint'").fetchone()
        if saved and saved[0]!=self.fingerprint:
            raise ReceiptError("persisted journal signer differs from identity; refuse issuance")
        self.db.execute("INSERT OR IGNORE INTO metadata (name,value) VALUES ('issuer_fingerprint',?)",(self.fingerprint,))
        self.verify_all()

    def close(self): self.db.close()

    def verify_all(self):
        """Refuse to continue on missing, corrupt, forged or chained-out-of-order records."""
        previous=ZERO_HASH
        expected=1
        for seq,sha,envelope_json,_ in self.db.execute("SELECT sequence,sha256,envelope_json,timestamp_ns FROM receipts ORDER BY sequence"):
            try:
                envelope=json.loads(envelope_json)
                payload=verify_envelope(envelope,self.public_key,previous=previous,expected_sequence=expected)
                if sha!=envelope["payload_sha256"] or seq!=expected:
                    raise ReceiptError("stored record does not match signed payload")
                if canonical(envelope).decode()!=envelope_json:
                    raise ReceiptError("noncanonical stored envelope")
            except (ValueError,TypeError) as e:
                raise ReceiptError(f"journal integrity failed at sequence {expected}") from e
            previous=sha
            expected+=1
        return {"entries":expected-1,"last_hash":previous,"verified":True}

    def last(self):
        row=self.db.execute("SELECT sequence,sha256 FROM receipts ORDER BY sequence DESC LIMIT 1").fetchone()
        return (int(row[0]),row[1]) if row else (0,ZERO_HASH)

    def append(self, *, claim, telemetry, source_tier, verdict, operator_attestation="NOT_ATTESTED"):
        if claim not in ("HUB_INITIALIZED", "SYNTHETIC_TELEMETRY"):
            raise ReceiptError("unapproved claim kind")
        if claim=="SYNTHETIC_TELEMETRY" and source_tier!="SYNTHETIC_DEMO":
            raise ReceiptError("simulated measurements cannot masquerade as hardware")
        if claim=="HUB_INITIALIZED" and source_tier!="LOCAL_SOFTWARE_ONLY":
            raise ReceiptError("startup is only a local software event")
        if verdict not in ("PROCESS_OBSERVED", "PROVEN_TRUE", "REFUTED_FALSE", "UNRESOLVED"):
            raise ReceiptError("invalid scoped verdict")
        if type(telemetry) is not dict or len(canonical(telemetry))>4096:
            raise ReceiptError("telemetry payload invalid or too large")
        with self._lock:
            # No retry of externally unknown writes: a failed transaction does not publish.
            self.db.execute("BEGIN IMMEDIATE")
            try:
                seq,prev=self.last()
                payload={
                    "schema":SCHEMA,"sequence":seq+1,"previous_sha256":prev,
                    "timestamp_ns":time.time_ns(),"event_nonce":secrets.token_hex(16),
                    "claim":claim,"declared_verdict":verdict,"source_tier":source_tier,
                    "operator_attestation":operator_attestation,
                    "telemetry":telemetry,"device_crypto":"SOFTWARE_ED25519_0600_KEY",
                    "does_not_prove":["TPM or PUF signing","physical joules","clinical correctness", "actual GPU execution"],
                }
                envelope=make_envelope(payload,self.identity)
                self.db.execute("INSERT INTO receipts (sequence,sha256,envelope_json,timestamp_ns) VALUES (?,?,?,?)",
                                (seq+1,envelope["payload_sha256"],canonical(envelope).decode(),payload["timestamp_ns"]))
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
        return envelope

    def get_after(self,seq=0,limit=100):
        if type(seq) is not int or seq<0 or seq>1_000_000_000 or type(limit) is not int or not 1<=limit<=100:
            raise ReceiptError("invalid pagination")
        rows=self.db.execute("SELECT envelope_json FROM receipts WHERE sequence>? ORDER BY sequence LIMIT ?",(seq,limit)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def get(self, seq):
        if type(seq) is not int or seq<1:raise ReceiptError("invalid record index")
        row=self.db.execute("SELECT envelope_json FROM receipts WHERE sequence=?",(seq,)).fetchone()
        return json.loads(row[0]) if row else None

    def ensure_genesis(self):
        if self.last()[0]!=0:return None
        return self.append(claim="HUB_INITIALIZED", source_tier="LOCAL_SOFTWARE_ONLY",
                           verdict="PROCESS_OBSERVED",operator_attestation="NOT_ATTESTED",
                           telemetry={"machine_process":"API_STARTED_LOCAL", "physical_joules":None,
                           "INA226":"NOT_CONNECTED","TPM":"NOT_CONNECTED",
                           "ATECC608C":"NOT_CONNECTED","PRINTER":"NOT_CONNECTED",
                           "FPGA":"NOT_EXECUTED","clinical_scope":"NO_PATIENT_DATA"})
