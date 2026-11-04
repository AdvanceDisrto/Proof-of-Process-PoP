"""iNNOVULIS iVerify: signed *observations*, not evidence of factual truth."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
try:
    from . import hash_receipts
except ImportError:
    import hash_receipts

try:
    from . import smoke
except ImportError:
    import smoke

VERSION = "0.3.0"
DB_PATH = os.environ.get("INNOVULIS_DB", "/tmp/innovulis-receipts.db")
API_KEYS = [k.strip() for k in os.environ.get("INNOVULIS_API_KEYS", "").split(",") if k.strip()]
SEED_HEX = os.environ.get("INNOVULIS_SIGNING_SEED", "")
if len(SEED_HEX) != 64 or not re.fullmatch(r"[0-9a-fA-F]{64}", SEED_HEX):
    raise RuntimeError("INNOVULIS_SIGNING_SEED must be an explicitly configured 32-byte hex seed")
if not API_KEYS:
    raise RuntimeError("INNOVULIS_API_KEYS must be explicitly configured")
private_key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(SEED_HEX))
public_key = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
KEY_ID = "sha256:" + hashlib.sha256(bytes.fromhex(public_key)).hexdigest()[:16]


def canonical(obj: Any) -> bytes:
    """Deterministic Python JSON encoding, NOT an RFC-8785/JCS claim."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_key(x_api_key: str | None) -> None:
    if not x_api_key or not any(hmac.compare_digest(x_api_key, k) for k in API_KEYS):
        raise HTTPException(status_code=401, detail="invalid API key")


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, receipt_json TEXT NOT NULL, created_at TEXT NOT NULL)")


init_db()
app = FastAPI(title="iNNOVULIS iVerify API", version=VERSION, description="Signed observation receipts; simulation does not certify physical hardware")


class MintRequest(BaseModel):
    claim: str = Field(min_length=1, max_length=10000)
    evidence: str | None = Field(default=None, max_length=100000)
    model: str | None = Field(default=None, max_length=200)
    provider: str | None = Field(default=None, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerifyRequest(BaseModel):
    receipt: dict[str, Any]
    pinned_pubkey_hex: str | None = None


def sign_and_store(payload: dict) -> dict:
    data = canonical(payload)
    receipt = {"receipt_id": str(uuid.uuid4()), "payload": payload,
               "payload_hash": sha256(data),
               "signature": {"algorithm": "Ed25519", "value": private_key.sign(data).hex(),
                             "public_key_hex": public_key, "key_id": KEY_ID}}
    with connect() as db:
        db.execute("INSERT INTO receipts(id, receipt_json, created_at) VALUES (?, ?, ?)",
                   (receipt["receipt_id"], json.dumps(receipt, allow_nan=False), now()))
    return receipt


def verify_offline(receipt: dict, pinned_pubkey_hex: str) -> tuple[bool, str]:
    """Validate signature against an externally pinned trust anchor; no trust in embedded key."""
    try:
        if not isinstance(receipt, dict) or not isinstance(receipt.get("payload"), dict):
            return False, "malformed receipt"
        payload = receipt["payload"]
        if not isinstance(payload.get("schema"), str) or not payload["schema"].startswith("ipqr/"):
            return False, "unexpected schema"
        sig = receipt["signature"]
        if sig.get("algorithm") != "Ed25519":
            return False, "unexpected signature algorithm"
        declared = sig["public_key_hex"]
        if not hmac.compare_digest(declared, pinned_pubkey_hex):
            return False, "untrusted signer: public key differs from trusted pin"
        if not hmac.compare_digest(sig.get("key_id", ""), "sha256:"+hashlib.sha256(bytes.fromhex(declared)).hexdigest()[:16]):
            return False, "key id mismatch"
        data = canonical(payload)
        if not hmac.compare_digest(sha256(data), receipt.get("payload_hash", "")):
            return False, "payload hash mismatch"
        ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(pinned_pubkey_hex)).verify(bytes.fromhex(sig["value"]), data)
        return True, "ACCEPT_SIGNED_PAYLOAD_INTEGRITY_ONLY"
    except Exception:
        return False, "invalid receipt signature or encoding"


@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION, "service": "iNNOVULIS iVerify"}


@app.get("/v1/keys")
def keys():
    return {"algorithm": "Ed25519", "public_key_hex": public_key, "key_id": KEY_ID,
            "trust_note": "Pin this key using an independently authenticated enrollment channel."}


@app.post("/v1/mint")
def mint(req: MintRequest, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    if req.evidence and req.evidence.startswith("sha256:"):
        if not re.fullmatch(r"sha256:[a-fA-F0-9]{64}", req.evidence):
            raise HTTPException(status_code=422, detail="invalid evidence digest")
        evidence_hash = req.evidence.lower()
    else:
        evidence_hash = sha256(req.evidence.encode()) if req.evidence is not None else None
    payload = {"schema": "ipqr/claim-observation/v1", "issuer": "iNNOVULIS",
               "claim": req.claim, "evidence_hash": evidence_hash, "model": req.model,
               "provider": req.provider, "metadata": req.metadata, "timestamp_utc": now(),
               "evidence_level": "EVIDENCE_DIGEST_RECORDED" if evidence_hash else "CLAIM_RECORDED",
               "does_not_prove": "Evidence or claim is true"}
    return sign_and_store(payload)


@app.post("/v1/verify")
def verify(req: VerifyRequest):
    # Default is explicitly pinned to this server's configured key; clients
    # should independently know and pin a key for verifiability off-server.
    pin = req.pinned_pubkey_hex or public_key
    valid, reason = verify_offline(req.receipt, pin)
    return {"valid": valid, "verdict": reason,
            "trust_basis": "external_pin" if req.pinned_pubkey_hex else "this_server_configured_key",
            "note": "Signature validates payload integrity and trusted issuer, not factual truth"}


@app.get("/v1/receipt/{receipt_id}")
def receipt(receipt_id: str, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    with connect() as db:
        row = db.execute("SELECT receipt_json FROM receipts WHERE id=?", (receipt_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="receipt not found")
    return json.loads(row[0])


@app.post("/v1/spu/smoke")
def run_smoke(x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    result = smoke.run_cwa_smoke()
    return sign_and_store({"schema": "ipqr/spu-cwa-smoke/v1", "issuer": "iNNOVULIS", "timestamp_utc": now(),
                           "execution_tier": "CPU_SIMULATION", "result": result,
                           "verdict": "PASS_SOFTWARE_MODEL" if result["verdict"] == "PASS" else "FAIL_SOFTWARE_MODEL",
                           "physical_gate": "ACTION_REQUIRED"})


@app.post("/v1/spu/empirical")
def run_empirical(x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    result = smoke.run_spu_empirical()
    return sign_and_store({"schema": "ipqr/spu-model-sweep/v1", "issuer": "iNNOVULIS", "timestamp_utc": now(),
                           "execution_tier": "CPU_PARAMETER_MODEL", "result": result,
                           "verdict": "MODEL_COMPUTED_NOT_MEASURED", "physical_gate": "ACTION_REQUIRED"})


@app.get("/v1/icore/status")
def icore_status():
    # Static historical declared milestone. We do not query GitHub live here.
    return {"version": "0.3", "status_source": "declared_milestone_not_live_ci",
            "architecture": {"type": "digital_systolic", "stationarity": "output_stationary", "array_dims": [2, 2]},
            "software_gate": {"reported": "PASSED_IN_PRIOR_GITHUB_CI", "vectors": 1568},
            "physical_gate": {"fpga_bitstream": "NOT_VERIFIED", "physical_execution": "NOT_VERIFIED",
                              "verdict": "ACTION_REQUIRED"}}


@app.get("/", response_class=HTMLResponse)
def landing():
    return (Path(__file__).parent / "index.html").read_text(encoding="utf-8")


# Portable, four-hash-style observation receipt endpoints (separate from /v1/mint).
# Never imply that a signature alone verifies a computation or source evidence.
from fastapi import Request
from fastapi.responses import JSONResponse

@app.post("/receipt")
@app.post("/receipt/warrant")
async def mint_hash_receipt(request: Request, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, "application/json required")
    if request.headers.get("content-length") and int(request.headers["content-length"]) > 65536:
        raise HTTPException(413, "body exceeds 64KiB")
    data = await request.body()
    if len(data) > 65536:
        raise HTTPException(413, "body exceeds 64KiB")
    try:
        body = json.loads(data)
        tier = "T2" if request.url.path.endswith("/warrant") else "T1"
        response = hash_receipts.mint(body, tier, private_key, public_key)
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e)) from e
    return response

@app.post("/verify")
async def verify_hash_receipt(request: Request):
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, "application/json required")
    if request.headers.get("content-length") and int(request.headers["content-length"]) > 65536:
        raise HTTPException(413, "body exceeds 64KiB")
    data = await request.body()
    if len(data) > 65536:
        raise HTTPException(413, "body exceeds 64KiB")
    try:
        obj = json.loads(data)
    except (ValueError, TypeError) as e:
        raise HTTPException(400, "invalid JSON") from e
    if not isinstance(obj, dict) or not isinstance(obj.get("receipt"), dict):
        raise HTTPException(400, "expected receipt object")
    pin = obj.get("pinned_pubkey_hex")
    if pin is None:
        raise HTTPException(400, "independently pinned public key required")
    if not isinstance(pin, str):
        raise HTTPException(400, "invalid pinned key")
    return hash_receipts.verify(obj["receipt"], pin)

@app.get("/pubkey")
def hash_receipt_pubkey():
    return {"public_key_hex": public_key, "trust_note": "Obtain the pin independently"}
