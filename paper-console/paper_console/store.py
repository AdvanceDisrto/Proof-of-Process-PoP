"""Append-only-in-ordinary-operation SQLite ledger, durable print outbox and rate budgets.

A DB administrator can rewrite local files. A hash chain makes tampering detectable
against an independently pinned checkpoint, not impossible.
"""
from __future__ import annotations
from contextlib import contextmanager
import json
import sqlite3
import time
from .codec import Event, canonical, sha256, InvalidEvent


class EventStore:
    def __init__(self, db_path="paper_console.sqlite3"):
        self.db=sqlite3.connect(str(db_path), isolation_level=None, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL,
            json TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT UNIQUE NOT NULL,
            inserted_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS outbox (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
            state TEXT NOT NULL CHECK(state IN ('PENDING','CLAIMED','DONE','HOLD')),
            attempts INTEGER NOT NULL DEFAULT 0, error TEXT,
            created_at INTEGER NOT NULL, FOREIGN KEY(event_id) REFERENCES events(event_id));
        CREATE TABLE IF NOT EXISTS print_history (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL,
            printed_at INTEGER NOT NULL, body_sha256 TEXT NOT NULL);
        """)

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def append(self, event: Event) -> dict:
        raw=canonical(event.as_dict()).decode()
        with self.transaction():
            dup=self.db.execute("SELECT seq,event_hash,json FROM events WHERE event_id=?",(event.event_id,)).fetchone()
            if dup:
                if dup[2] != raw:
                    raise InvalidEvent("event_id reused with different bytes")
                return {"seq":dup[0], "event_hash":dup[1], "duplicate":True}
            head=self.db.execute("SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            previous=head[0] if head else "0"*64
            entry_hash=sha256({"prev":previous,"event":event.as_dict()})
            cur=self.db.execute("INSERT INTO events(event_id,json,previous_hash,event_hash,inserted_at) VALUES (?,?,?,?,?)",
                                (event.event_id,raw,previous,entry_hash,int(time.time())))
            return {"seq":cur.lastrowid,"event_hash":entry_hash,"duplicate":False}

    def integrity(self) -> dict:
        previous="0"*64;total=0
        for seq,raw,prev,h in self.db.execute("SELECT seq,json,previous_hash,event_hash FROM events ORDER BY seq"):
            e=json.loads(raw)
            if prev != previous or sha256({"prev":prev,"event":e}) != h:
                return {"chain_ok":False,"at_seq":seq,"checked":total,"head":previous}
            previous=h;total+=1
        return {"chain_ok":True,"checked":total,"head":previous,
                "warning":"DB hash chain alone is mutable; compare with separately pinned checkpoint"}

    def get_event(self,event_id):
        row=self.db.execute("SELECT json FROM events WHERE event_id=?",(event_id,)).fetchone()
        return Event(**json.loads(row[0])) if row else None

    def latest(self,limit=100) -> list[dict]:
        limit=max(1,min(500,int(limit)))
        return [{"seq":seq,"event_hash":h,**json.loads(s)}
                for seq,h,s in self.db.execute("SELECT seq,event_hash,json FROM events ORDER BY seq DESC LIMIT ?",(limit,))]

    def stats(self) -> dict:
        # Exact counters use SQL; never estimate total traffic from a last-page sample.
        total=self.db.execute("SELECT count(*) FROM events").fetchone()[0]
        verified=self.db.execute("SELECT count(*) FROM events WHERE json_extract(json,'$.verification')='VERIFIED_DIGITAL_RECEIPT'").fetchone()[0]
        refuted=self.db.execute("SELECT count(*) FROM events WHERE json_extract(json,'$.claim_verdict')='REFUTED_FALSE'").fetchone()[0]
        raw=self.db.execute("SELECT json_extract(json,'$.observed_joules'), json_extract(json,'$.source_tier') FROM events WHERE json_extract(json,'$.observed_joules') IS NOT NULL").fetchall()
        measured=sum(float(v) for v,t in raw if t=="INA226_CALIBRATED_UNATTESTED")
        claimed=sum(float(v) for v,t in raw if t!="INA226_CALIBRATED_UNATTESTED")
        return {"total_events":total,"verified_digital_receipts":verified,"refuted_claims":refuted,
                "joules_meter_derived_unattested":round(measured,9),
                "joules_other_reported_unverified":round(claimed,9),
                "incomplete_track_counts":False,"all_energy_totals_are_source_labeled":True,
                "queued_prints":self.db.execute("SELECT count(*) FROM outbox WHERE state='PENDING'").fetchone()[0]}

    def queue(self,event_id: str):
        with self.transaction():
            if self.db.execute("SELECT 1 FROM events WHERE event_id=?",(event_id,)).fetchone() is None:
                raise KeyError("event not present")
            self.db.execute("INSERT OR IGNORE INTO outbox(event_id,state,created_at) VALUES (?,'PENDING',?)",
                            (event_id,int(time.time())))

    def next_print(self):
        with self.transaction():
            row=self.db.execute("SELECT seq,event_id FROM outbox WHERE state='PENDING' ORDER BY seq LIMIT 1").fetchone()
            if row is None: return None
            self.db.execute("UPDATE outbox SET state='CLAIMED',attempts=attempts+1 WHERE seq=?",(row[0],))
            ev=self.db.execute("SELECT json FROM events WHERE event_id=?",(row[1],)).fetchone()[0]
            return row[1],Event(**json.loads(ev))

    def finish_print(self,event_id,body_sha256,now):
        with self.transaction():
            self.db.execute("UPDATE outbox SET state='DONE' WHERE event_id=? AND state='CLAIMED'",(event_id,))
            self.db.execute("INSERT INTO print_history(event_id,printed_at,body_sha256) VALUES (?,?,?)",
                            (event_id,int(now),body_sha256))

    def hold_print(self,event_id,error):
        with self.transaction():
            self.db.execute("UPDATE outbox SET state='HOLD',error=? WHERE event_id=?",(str(error)[:150],event_id))

    def last_print_time(self):
        row=self.db.execute("SELECT MAX(printed_at) FROM print_history").fetchone()
        return row[0]

    def prints_since(self,now,seconds):
        return self.db.execute("SELECT count(*) FROM print_history WHERE printed_at>=?",(int(now-seconds),)).fetchone()[0]

    def recover_claimed_as_hold(self):
        self.db.execute("UPDATE outbox SET state='HOLD',error='RESTART_UNCERTAIN_MAY_HAVE_PRINTED' WHERE state='CLAIMED'")

    def close(self):
        self.db.close()
