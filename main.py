from __future__ import annotations

import os
import time
from pathlib import Path

import orjson
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

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
    allow_methods=["GET"],
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
