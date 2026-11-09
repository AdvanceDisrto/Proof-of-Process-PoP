"""Local-only evidence hash inventory + SQLite hash-linked journal.

This journal detects accidental/partial changes but does NOT prevent a person
with database write access from rewriting the entire history. External anchors
are required for strong append-only guarantees.
"""
from __future__ import annotations
import hashlib, json, sqlite3, time
from pathlib import Path
from .rules import GATES, GATE_STATUSES, evaluate

GENESIS = "0" * 64


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def case_id_ok(value: str) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 64 and all(c.isalnum() or c in "-_" for c in value)


class CaseBook:
    def __init__(self, db: str | Path):
        self.path = Path(db)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), timeout=8)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=8000")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS cases(case_id TEXT PRIMARY KEY, created_ns INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS evidence(
            case_id TEXT NOT NULL, sha256 TEXT NOT NULL, label TEXT NOT NULL,
            size_bytes INTEGER NOT NULL, PRIMARY KEY(case_id,sha256),
            FOREIGN KEY(case_id) REFERENCES cases(case_id));
        CREATE TABLE IF NOT EXISTS gate_states(
            case_id TEXT NOT NULL, gate INTEGER NOT NULL CHECK(gate BETWEEN 1 AND 18),
            status TEXT NOT NULL, evidence_hash TEXT,
            PRIMARY KEY(case_id,gate), FOREIGN KEY(case_id) REFERENCES cases(case_id));
        CREATE TABLE IF NOT EXISTS audit(
            seq INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL,
            event_json TEXT NOT NULL, prev_hash TEXT NOT NULL,
            event_hash TEXT NOT NULL, FOREIGN KEY(case_id) REFERENCES cases(case_id));
        ''')
        self.db.commit()

    def close(self):
        self.db.close()

    def _ensure(self, case_id):
        if not case_id_ok(case_id): raise ValueError("invalid case reference")
        if not self.db.execute("SELECT 1 FROM cases WHERE case_id=?", (case_id,)).fetchone():
            raise ValueError("case does not exist")

    def _append(self, case_id, action, data):
        row = self.db.execute("SELECT event_hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        previous = row[0] if row else GENESIS
        event = {"case_id":case_id,"action":action,"data":data,"timestamp_ns":time.time_ns()}
        serialized = canonical(event)
        checksum = digest(bytes.fromhex(previous) + serialized)
        self.db.execute("INSERT INTO audit(case_id,event_json,prev_hash,event_hash) VALUES(?,?,?,?)",
                        (case_id,serialized.decode("ascii"),previous,checksum))
        return checksum

    def create(self, case_id: str):
        if not case_id_ok(case_id): raise ValueError("invalid case reference")
        with self.db:
            self.db.execute("INSERT INTO cases VALUES(?,?)", (case_id, time.time_ns()))
            self.db.executemany("INSERT INTO gate_states VALUES(?,?,?,NULL)",
                                [(case_id,g["gate"],"NOT_REVIEWED") for g in GATES])
            self._append(case_id,"CASE_OPENED",{"schema":"twinions-legal-intake/0.1",
                                                 "raw_case_files_stored":False})

    def add_evidence(self, case_id: str, filepath: str | Path, label: str):
        self._ensure(case_id)
        if not isinstance(label,str) or not 1 <= len(label) <= 100 or any(ord(c)<32 for c in label):
            raise ValueError("invalid evidence label")
        p=Path(filepath)
        if p.is_symlink() or not p.is_file():raise ValueError("regular local file required; symlinks blocked")
        if p.stat().st_size > 25*1024*1024:raise ValueError("evidence exceeds 25 MiB local hashing limit")
        h=hashlib.sha256(); n=0
        with p.open("rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""):
                n+=len(chunk)
                if n>25*1024*1024:raise ValueError("evidence limit exceeded")
                h.update(chunk)
        sha=h.hexdigest()
        with self.db:
            self.db.execute("INSERT INTO evidence VALUES(?,?,?,?)",(case_id,sha,label,n))
            self._append(case_id,"EVIDENCE_HASHED",{"sha256":sha,"label":label,"size_bytes":n})
        return sha

    def set_gate(self, case_id: str, gate: int, status: str, evidence_hash: str | None = None):
        self._ensure(case_id)
        if type(gate) is not int or not 1<=gate<=18 or status not in GATE_STATUSES:
            raise ValueError("invalid gate/status")
        if status in ("EVIDENCE_ATTACHED","CONTESTED"):
            if not evidence_hash or not self.db.execute(
                "SELECT 1 FROM evidence WHERE case_id=? AND sha256=?",(case_id,evidence_hash)).fetchone():
                raise ValueError("actual locally hashed evidence is required")
        elif evidence_hash:
            raise ValueError("status must attach evidence or clear evidence hash")
        with self.db:
            self.db.execute("UPDATE gate_states SET status=?, evidence_hash=? WHERE case_id=? AND gate=?",
                            (status,evidence_hash,case_id,gate))
            self._append(case_id,"GATE_REVIEWED",{"gate":gate,"status":status,"evidence_hash":evidence_hash})

    def record(self, case_id: str, kind: str, evidence_hash: str, actor_label: str):
        """Attest that the operator recorded evidence of notice/reply/counsel review.
        DOES NOT attest delivery, bar license, or authenticity of content.
        """
        self._ensure(case_id)
        if kind not in ("NOTICE_EVIDENCE","REPLY_EVIDENCE","COUNSEL_REVIEW_EVIDENCE"):
            raise ValueError("unsupported action")
        if not self.db.execute("SELECT 1 FROM evidence WHERE case_id=? AND sha256=?",
                               (case_id,evidence_hash)).fetchone():
            raise ValueError("provide locally hashed documentary evidence")
        if not actor_label or len(actor_label)>120 or any(ord(c)<32 for c in actor_label):
            raise ValueError("actor label required")
        with self.db:
            self._append(case_id,kind,{"evidence_hash":evidence_hash,"actor_label_unverified":actor_label})

    def status(self, case_id):
        self._ensure(case_id)
        raw=self.db.execute("SELECT gate,status,evidence_hash FROM gate_states WHERE case_id=? ORDER BY gate",(case_id,)).fetchall()
        gates=[{**GATES[r["gate"]-1],"status":r["status"],"evidence_hash":r["evidence_hash"]} for r in raw]
        evs=self.db.execute("SELECT event_json FROM audit WHERE case_id=? ORDER BY seq",(case_id,)).fetchall()
        event_kinds={json.loads(r[0])["action"] for r in evs}
        result=evaluate(gates,"NOTICE_EVIDENCE" in event_kinds,
                        "REPLY_EVIDENCE" in event_kinds,"COUNSEL_REVIEW_EVIDENCE" in event_kinds)
        result["case_id"]=case_id
        result["gate_states"]=gates
        result["evidence_hash_count"]=self.db.execute("SELECT COUNT(*) FROM evidence WHERE case_id=?",(case_id,)).fetchone()[0]
        result["journal_tip_sha256"]=self.tip()
        return result

    def tip(self):
        r=self.db.execute("SELECT event_hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        return r[0] if r else GENESIS

    def verify_log(self):
        last=GENESIS
        count=0
        for row in self.db.execute("SELECT seq,case_id,event_json,prev_hash,event_hash FROM audit ORDER BY seq"):
            try:
                value=json.loads(row["event_json"])
                good=(row["prev_hash"]==last and
                      row["case_id"]==value["case_id"] and
                      canonical(value).decode("ascii")==row["event_json"] and
                      row["event_hash"]==digest(bytes.fromhex(last)+canonical(value)))
            except (ValueError,TypeError,KeyError):good=False
            if not good:return {"valid":False,"first_failed_sequence":row["seq"],"does_not_prove":"append-only storage or external timestamp"}
            last=row["event_hash"]; count+=1
        return {"valid":True,"events":count,"tip_sha256":last,
                "does_not_prove":"external integrity: privileged actors can rewrite the local SQLite database"}

    def audit_events(self, case_id):
        self._ensure(case_id)
        return [json.loads(x[0]) for x in self.db.execute("SELECT event_json FROM audit WHERE case_id=? ORDER BY seq",(case_id,))]
