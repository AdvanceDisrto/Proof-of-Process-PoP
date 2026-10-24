from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from pathlib import Path

import orjson
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from iska_authority import verify_receipt
from ledger_persistence import commit_verified_receipt, validate_ledger_record

BASE_DIR = Path(__file__).resolve().parent
UI_PATH = BASE_DIR / "index.html"


class OrjsonResponse(Response):
    media_type = "application/json"

    def render(self, content: object) -> bytes:
        return orjson.dumps(content, option=orjson.OPT_NON_STR_KEYS)


app = FastAPI(
    title="i™ Proof of Process (PoP) API",
    version="1.1",
    default_response_class=OrjsonResponse,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://proofofprocess.online",
        "https://www.proofofprocess.online",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{time.perf_counter() - started:.6f}"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "microphone=(), camera=(), geolocation=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


CHALLENGE_TTL_SECONDS = 300
ACTIVE_CHALLENGES: dict[str, dict[str, object]] = {}


class ChallengeRequest(BaseModel):
    provider_name: str
    instance_id: str
    hardware_type: str


class AttestationSubmission(BaseModel):
    instance_id: str
    nonce: str
    attestation_token_b64: str
    workload_hash: str


class LedgerCommitRequest(BaseModel):
    signed_receipt: dict[str, object]
    receipt_id: str
    instance_id: str
    provider_name: str | None = None
    hardware_type: str
    workload_hash: str
    evidence_sha256: str
    attestation_verification: str
    physical_gate: str
    evidence_origin: str
    verifier_receipt_id: str
    identity_root_id: str | None = None
    identity_epoch: str | None = None
    receipt_signature: str | None = None
    delegation_certificate: dict[str, object] | None = None
    metadata: dict[str, object] = {}


@app.post("/api/lifecycle/challenge")
def issue_attestation_challenge(request: ChallengeRequest):
    nonce = secrets.token_hex(32)
    ACTIVE_CHALLENGES[request.instance_id] = {
        "nonce": nonce,
        "expires": time.time() + CHALLENGE_TTL_SECONDS,
        "provider_name": request.provider_name,
        "hardware_type": request.hardware_type,
    }
    return {
        "status": "ELIGIBLE_FOR_ATTESTATION",
        "physical_gate": "ACTION_REQUIRED",
        "instance_id": request.instance_id,
        "challenge_nonce": nonce,
        "expires_in_seconds": CHALLENGE_TTL_SECONDS,
    }


@app.post("/api/lifecycle/verify")
def verify_attestation_submission(submission: AttestationSubmission):
    session = ACTIVE_CHALLENGES.pop(submission.instance_id, None)
    if session is None:
        raise HTTPException(status_code=403, detail="No active challenge or challenge already consumed.")
    if time.time() > float(session["expires"]):
        raise HTTPException(status_code=408, detail="Challenge expired.")
    if not secrets.compare_digest(submission.nonce, str(session["nonce"])):
        raise HTTPException(status_code=401, detail="Nonce mismatch; evidence rejected.")

    try:
        evidence = base64.b64decode(submission.attestation_token_b64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Malformed base64 attestation evidence.") from exc
    if len(evidence) < 64:
        raise HTTPException(status_code=422, detail="Attestation evidence is structurally insufficient.")
    if len(submission.workload_hash) != 64:
        raise HTTPException(status_code=422, detail="workload_hash must be a SHA-256 hex digest.")
    try:
        bytes.fromhex(submission.workload_hash)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="workload_hash is not hexadecimal.") from exc

    # Structural ingestion is intentionally not hardware verification. Promotion
    # requires a provider/vendor verifier that validates the signed quote,
    # certificate chain, nonce binding, device measurement and workload binding.
    return {
        "status": "EVIDENCE_RECEIVED_UNVERIFIED",
        "physical_gate": "ACTION_REQUIRED",
        "materialization": "BLOCKED",
        "evidence_sha256": hashlib.sha256(evidence).hexdigest(),
        "workload_hash": submission.workload_hash,
        "provider_name": session["provider_name"],
        "hardware_type": session["hardware_type"],
        "action_required": "Verify vendor hardware quote and certificate chain before promotion.",
    }



@app.get("/api/identity/manifest")
def identity_manifest():
    root_id = os.getenv("ISKA_ROOT_ID")
    root_public_key = os.getenv("ISKA_ROOT_PUBLIC_KEY")
    if not root_id or not root_public_key:
        return {
            "status": "ACTION_REQUIRED",
            "identity_state": "UNCONFIGURED",
            "root_private_key": "NOT_PRESENT_IN_BACKEND",
            "reason": "Configure the public iSKA identity only; never place the root private key on the provider backend.",
        }
    return {
        "status": "VERIFIED_PROCESS",
        "identity_state": "ROOT_PUBLIC_IDENTITY_CONFIGURED",
        "root_id": root_id,
        "root_public_key": root_public_key,
        "root_private_key": "NOT_PRESENT_IN_BACKEND",
        "provider_key": "DELEGATED_ONLY",
    }


@app.post("/api/ledger/commit")
def commit_ledger_record(request: LedgerCommitRequest):
    if not verify_receipt(request.signed_receipt):
        raise HTTPException(status_code=422, detail="iSKA receipt signature/delegation verification failed.")
    signed_payload = request.signed_receipt.get("receipt", {})
    if not isinstance(signed_payload, dict):
        raise HTTPException(status_code=422, detail="Signed receipt payload is malformed.")
    if signed_payload.get("physical_gate") != "MEASURED_PASS":
        raise HTTPException(status_code=422, detail="Signed receipt is not a verified physical receipt.")
    if signed_payload.get("attestation_verification") != "VERIFIED":
        raise HTTPException(status_code=422, detail="Signed receipt lacks independent attestation verification.")
    if signed_payload.get("evidence_origin") in {"SIMULATED", "MOCK", "SYNTHETIC"}:
        raise HTTPException(status_code=422, detail="Synthetic evidence cannot enter the physical ledger.")
    if signed_payload.get("workload_hash") != request.workload_hash:
        raise HTTPException(status_code=422, detail="Signed receipt workload hash does not match ledger record.")
    record = request.model_dump(exclude={"signed_receipt"})
    try:
        validate_ledger_record(record)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        row = commit_verified_receipt(record)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "COMMITTED_VERIFIED_RECEIPT", "ledger_record": row}

@app.get("/")
def serve_ui():
    if not UI_PATH.is_file():
        raise RuntimeError("index.html is missing; refusing to serve a partial deployment.")
    return FileResponse(UI_PATH)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "i-pop-core",
        "transport": "fastapi+uvicorn",
        "json": "orjson",
    }


@app.get("/reality/manifest")
def reality_manifest():
    # A null manifest hash is intentional: process evidence exists, but no
    # external/founder seal is claimed by this public API.
    return {
        "spec": "innovulis-reality-evidence/1.1",
        "state": "VERIFIED_PROCESS",
        "seal_state": "UNCLAIMED / NOT SEALED",
        "physical_gate": "ACTION_REQUIRED",
        "master_manifest_hash": None,
        "reason": "No external/founder seal is evidenced by this deployment.",
        "does_not_prove": [
            "absolute entirety of existence",
            "experimental proof of represented physics",
            "physical silicon fabrication",
            "foundry acceptance",
            "measured physical energy",
            "hardware root of trust",
            "external blockchain anchoring",
        ],
        "disclosure": "No fabricated manifest hash is returned by this API.",
    }


@app.get("/truth-boundary")
def truth_boundary():
    return {
        "physical_gate": "ACTION_REQUIRED",
        "fabricated_evidence": False,
        "does_not_prove": [
            "experimental proof of quantum physics",
            "physical silicon fabrication",
            "foundry acceptance",
            "measured physical energy",
            "hardware root of trust",
            "external blockchain anchoring",
        ],
        "the_central_rule": "The receipt can record reality; it cannot manufacture reality.",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        loop="uvloop",
        http="httptools",
    )
