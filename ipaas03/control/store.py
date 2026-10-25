from __future__ import annotations
import hashlib, json, sqlite3, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class Service:
    name: str
    git_url: str
    runtime: str
    build_cmd: str
    output_dir: str = "."
    hostname: str = ""

class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS services(
          name TEXT PRIMARY KEY, git_url TEXT, runtime TEXT,
          build_cmd TEXT, output_dir TEXT, hostname TEXT
        );
        CREATE TABLE IF NOT EXISTS deploys(
          deploy_id INTEGER PRIMARY KEY AUTOINCREMENT, service TEXT,
          commit_sha TEXT, status TEXT, log_path TEXT, artifact_path TEXT, ts REAL
        );
        CREATE TABLE IF NOT EXISTS audit(
          id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, payload TEXT,
          prev_hash TEXT, hash TEXT, ts REAL
        );
        """)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def _audit(self, action: str, payload: dict[str, Any]) -> None:
        prev = self.conn.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
        prev_hash = str(prev["hash"]) if prev else ""
        ts = time.time()
        body = json.dumps({"action": action, "payload": payload, "ts": ts}, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256((prev_hash + body).encode()).hexdigest()
        self.conn.execute(
            "INSERT INTO audit(action,payload,prev_hash,hash,ts) VALUES(?,?,?,?,?)",
            (action, body, prev_hash, digest, ts),
        )
        self.conn.commit()

    def create_service(self, service: Service) -> dict[str, object]:
        try:
            self.conn.execute(
                "INSERT INTO services VALUES(?,?,?,?,?,?)",
                (service.name, service.git_url, service.runtime, service.build_cmd, service.output_dir, service.hostname),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            return {"ok": False}
        self._audit("service.create", service.__dict__)
        return {"ok": True}

    def get_service(self, name: str) -> dict[str, object] | None:
        row = self.conn.execute("SELECT * FROM services WHERE name=?", (name,)).fetchone()
        return dict(row) if row else None

    def list_services(self) -> list[dict[str, object]]:
        return [dict(row) for row in self.conn.execute("SELECT * FROM services ORDER BY name")]

    def create_deploy(self, service: str, commit_sha: str = "") -> dict[str, object]:
        cur = self.conn.execute(
            "INSERT INTO deploys(service,commit_sha,status,ts) VALUES(?,?,?,?)",
            (service, commit_sha, "queued", time.time()),
        )
        self.conn.commit()
        self._audit("deploy.create", {"service": service, "commit_sha": commit_sha})
        return {"ok": True, "deploy_id": cur.lastrowid}

    def claim_next_deploy(self) -> dict[str, object] | None:
        row = self.conn.execute(
            "SELECT * FROM deploys WHERE status='queued' ORDER BY deploy_id LIMIT 1"
        ).fetchone()
        if not row:
            return None
        self.conn.execute("UPDATE deploys SET status='building' WHERE deploy_id=?", (row["deploy_id"],))
        self.conn.commit()
        self._audit("deploy.claim", {"deploy_id": row["deploy_id"]})
        return dict(self.conn.execute("SELECT * FROM deploys WHERE deploy_id=?", (row["deploy_id"],)).fetchone())

    def finish_deploy(self, deploy_id: int, ok: bool, log_path: str | None = None, artifact_path: str | None = None) -> None:
        status = "live" if ok else "failed"
        self.conn.execute(
            "UPDATE deploys SET status=?,log_path=?,artifact_path=? WHERE deploy_id=?",
            (status, log_path, artifact_path, deploy_id),
        )
        self.conn.commit()
        self._audit("deploy.finish", {"deploy_id": deploy_id, "status": status})

    def list_deploys(self, service: str) -> list[dict[str, object]]:
        return [dict(row) for row in self.conn.execute("SELECT * FROM deploys WHERE service=? ORDER BY deploy_id DESC", (service,))]

    def audit_log(self) -> list[dict[str, object]]:
        return [dict(row) for row in self.conn.execute("SELECT * FROM audit ORDER BY id")]

    def receipts(self) -> list[dict[str, object]]:
        return self.audit_log()

    def verify_chain(self) -> dict[str, object]:
        previous = ""
        rows = self.audit_log()
        for row in rows:
            if row["prev_hash"] != previous:
                return {"ok": False, "length": len(rows), "head": row["hash"]}
            expected = hashlib.sha256((previous + str(row["payload"])).encode()).hexdigest()
            if expected != row["hash"]:
                return {"ok": False, "length": len(rows), "head": row["hash"]}
            previous = str(row["hash"])
        return {"ok": True, "length": len(rows), "head": previous or hashlib.sha256(b"").hexdigest()}
