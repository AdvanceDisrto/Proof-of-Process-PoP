from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/fab", tags=["fabrication"])

COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class FabPrepareRequest(BaseModel):
    commit: str = Field(min_length=40, max_length=40)
    target: str = Field(min_length=1, max_length=128)
    die_count: int = Field(default=64, ge=1, le=4096)
    priority: Literal["reliability", "cost"] = "reliability"


@router.post("/prepare")
def prepare_wafer_run(request: FabPrepareRequest) -> dict[str, object]:
    if not COMMIT_RE.fullmatch(request.commit):
        return {
            "status": "ACTION_REQUIRED",
            "reason": "commit must be a 40-character Git object ID",
        }

    manifest = {
        "schema": "iTensor-WaferRun/v1",
        "commit": request.commit.lower(),
        "target": request.target,
        "die_count": request.die_count,
        "priority": request.priority,
        "created_at_ms": int(time.time() * 1000),
        "evidence_policy": {
            "simulated_execution": False,
            "mock_receipts": False,
            "promotion_requires_executor": True,
            "promotion_requires_verifier": True,
        },
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    provenance_hash = "sha256:" + hashlib.sha256(canonical).hexdigest()

    return {
        "status": "READY_FOR_EXECUTOR",
        "provenance_hash": provenance_hash,
        "manifest": manifest,
        "next_required_evidence": [
            "configured executor execution receipt",
            "iComp/iTSC compilation evidence",
            "deterministic test evidence",
            "verifier result",
            "physical attestation only where the promotion boundary requires it",
        ],
    }
