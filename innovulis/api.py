"""iNNOVULIS Alpha-1 public REST contract and opt-in local-only reference implementation.

Issuer-signature and processing signature are not proof that underlying world events occurred.
No money, hardware, government, or legal decisions are ever authorized by this API.
"""
from __future__ import annotations

import hmac
import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from alil.router import MAX_RECEIPT_BYTES, canonical, load_json, sha256, RejectedReceipt
from alil.verify import verify_chain
from .causal import classify


@dataclass(frozen=True)
class Settings:
    root: Path
    machine_public_key_hex: str
    api_token: str
    intake_enabled: bool = False

    def __post_init__(self):
        if not re.fullmatch(r"[0-9a-f]{64}", self.machine_public_key_hex):
            raise ValueError("Externally pinned Ed25519 machine public key required")
        if len(self.api_token) < 24:
            raise ValueError("Token must have at least 24 characters (use a generated random secret)")
        if self.root.is_symlink():
            raise ValueError("Runtime root cannot be a symlink")

    @classmethod
    def from_env(cls):
        return cls(root=Path(os.environ["INNOVULIS_RUNTIME_ROOT"]),
                   machine_public_key_hex=os.environ["INNOVULIS_MACHINE_PUBLIC_KEY_HEX"],
                   api_token=os.environ["INNOVULIS_API_TOKEN"],
                   intake_enabled=os.environ.get("INNOVULIS_ENABLE_HTTP_INTAKE", "false").lower() == "true")


class CausalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    edges: list[tuple[str, str]] = Field(max_length=1024)
    x: str
    y: str
    z: str


class VerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Strict envelope shape is additionally enforced via ALIL canonical verifier
    receipt: dict = Field(description="Full signed machine receipt envelope")


def make_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="iNNOVULIS Receipt Verification API", version="0.1.0",
                  description="Verifies machine receipt provenance, not underlying physical or legal truth.",
                  docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def no_cache(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    def authorize(value: str | None):
        if not value or not value.startswith("Bearer ") or not hmac.compare_digest(value[7:], settings.api_token):
            raise HTTPException(status_code=401, detail="Bearer token required", headers={"WWW-Authenticate": "Bearer"})

    def verify_records():
        try:
            return verify_chain(settings.root / "records", settings.machine_public_key_hex)
        except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
            raise HTTPException(status_code=409, detail="CHAIN_NOT_VERIFIED") from error

    @app.get("/v1/health", tags=["status"])
    def health():
        return {"service": "iNNOVULIS", "status": "API_PROCESS_RUNNING",
                "receipts_verified": False, "hardware_attested": False,
                "external_anchor_verified": False, "settlement_enabled": False}

    @app.get("/v1/chain/status", tags=["receipts"])
    def status(authorization: str | None = Header(default=None)):
        authorize(authorization)
        return verify_records()

    @app.get("/v1/receipts/{sequence}", tags=["receipts"])
    def get_receipt(sequence: int, authorization: str | None = Header(default=None)):
        authorize(authorization)
        if sequence < 1 or sequence > 999999999999:
            raise HTTPException(422, "Invalid sequence")
        snapshot = verify_records()  # verify entire chain first; don't issue claims from broken chain
        if sequence > snapshot["receipt_count"]:
            raise HTTPException(404, "Receipt not found")
        name = f"{sequence:012d}.json"
        return JSONResponse(content=load_json((settings.root / "records" / name).read_bytes()),
                            headers={"X-Verified-Local-Root": snapshot["last_local_root"]})

    @app.post("/v1/receipts/verify", tags=["receipts"])
    def verify_receipt(data: VerificationRequest, authorization: str | None = Header(default=None)):
        authorize(authorization)
        snapshot = verify_records()
        envelope = data.receipt
        try:
            seq = envelope["event"]["seq"]
            if type(seq) is not int or seq < 1 or seq > snapshot["receipt_count"]:
                raise ValueError("invalid sequence")
            canonical(envelope)
            archived = load_json((settings.root / "records" / f"{seq:012d}.json").read_bytes())
        except (KeyError, TypeError, ValueError, OSError, RejectedReceipt):
            raise HTTPException(422, "Invalid receipt")
        if not hmac.compare_digest(canonical(envelope), canonical(archived)):
            raise HTTPException(409, "RECEIPT_NOT_IN_VERIFIED_CHAIN")
        return {"result": "LOCAL_MACHINE_RECEIPT_VERIFIED", "seq": seq,
                "receipt_hash": sha256(canonical(envelope)),
                "local_root": snapshot["last_local_root"],
                "underlying_event_verified": False,
                "hardware_attested": False,
                "external_anchor_verified": False,
                "financial_or_physical_actions_authorized": False}

    @app.post("/v1/causal/inspect", tags=["causal"])
    def inspect_causal_structure(data: CausalRequest, authorization: str | None = Header(default=None)):
        authorize(authorization)
        try:
            return classify(data.edges, data.x, data.y, data.z)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @app.post("/v1/intake", tags=["ingress"], status_code=202)
    async def enqueue_intake(request: Request, authorization: str | None = Header(default=None)):
        authorize(authorization)
        if not settings.intake_enabled:
            raise HTTPException(403, "INTAKE_DISABLED_BY_POLICY")
        if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
            raise HTTPException(415, "JSON required")
        if request.headers.get("content-length"):
            try:
                if int(request.headers["content-length"]) > MAX_RECEIPT_BYTES:
                    raise HTTPException(413, "Receipt too large")
            except ValueError:
                raise HTTPException(400, "Invalid content length")
        # Enforce limit even for chunked requests, without unbounded buffering.
        chunks = bytearray()
        async for part in request.stream():
            chunks.extend(part)
            if len(chunks) > MAX_RECEIPT_BYTES:
                raise HTTPException(413, "Receipt too large")
        try:
            obj = load_json(bytes(chunks))
            if not isinstance(obj, dict):
                raise RejectedReceipt("JSON object required")
            canonical(obj)
        except (ValueError, UnicodeError, TypeError, json.JSONDecodeError):
            raise HTTPException(422, "Invalid JSON receipt")
        spool = settings.root / "inbox"
        spool.mkdir(parents=True, exist_ok=True)
        if spool.is_symlink():
            raise HTTPException(409, "Unsafe spool")
        payload = canonical(obj) + b"\n"
        name = "api-" + uuid.uuid4().hex + ".json"
        # Exclusive creation prevents overwriting a prior original. Restrictive permissions.
        fd = os.open(spool / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        return {"status": "QUEUED_UNVERIFIED", "queue_id": name.removesuffix(".json"),
                "sha256_canonical": sha256(payload), "machine_signed": False,
                "note": "Independent ALIL watcher must verify and sign before a record exists"}

    return app


# Fail closed when deployed without an externally pinned key and secret.
# Local development can explicitly import make_app(test_settings) without requiring env credentials.
if os.environ.get("INNOVULIS_RUNTIME_ROOT"):
    app = make_app(Settings.from_env())
else:
    app = FastAPI(title="iNNOVULIS configuration required", docs_url=None, redoc_url=None)
    @app.get("/v1/health")
    def missing_config():
        return JSONResponse(status_code=503, content={"status": "ACTION_REQUIRED", "configured": False})
