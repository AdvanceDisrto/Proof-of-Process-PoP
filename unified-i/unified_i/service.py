"""Local-only human-owned acceptance UI/API. This is a DEMO with no PHI."""
from __future__ import annotations
import hmac
import os
import tempfile
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from .physical import record_report
from .arbiter import bounded_integer_verdict, audit_free_text
from .bridge import run_synthetic_closed_loop

class DemoRequest(BaseModel):
    observed: int=Field(default=25000,ge=-1000000,le=1000000)
    limit: int=Field(default=40000,ge=-1000000,le=1000000)
    explicit_demo_ack: bool=False


def create_app(*, operator_token: str)->FastAPI:
    if type(operator_token) is not str or len(operator_token)<32:
        raise ValueError("operator token at least 32 characters, separately supplied")
    app=FastAPI(title="i™ integrated software acceptance",docs_url=None,redoc_url=None,openapi_url=None)

    @app.get("/",response_class=HTMLResponse)
    def index():
        return (Path(__file__).parent/"dashboard.html").read_text(encoding="utf8")

    @app.get("/health")
    def health():
        return {"status":"RUNNING_SOFTWARE_ONLY","physical":"PENDING","production":False}

    @app.get("/v1/gates")
    def gates(x_operator_token:str|None=Header(None)):
        if x_operator_token is None or not hmac.compare_digest(x_operator_token,operator_token):
            raise HTTPException(status_code=401,detail="operator authentication required")
        return record_report()

    @app.post("/v1/demo/claim")
    def demo_claim(query:DemoRequest,x_operator_token:str|None=Header(None)):
        if x_operator_token is None or not hmac.compare_digest(x_operator_token,operator_token):
            raise HTTPException(status_code=401,detail="operator authentication required")
        if query.explicit_demo_ack is not True:
            raise HTTPException(status_code=403,detail="explicit synthetic-only acknowledgement required")
        result=bounded_integer_verdict(query.observed,query.limit)
        # Does not issue a legal/medical/physical receipt or authenticate values.
        return {**result,"source":"OPERATOR_SUPPLIED_UNTRUSTED","is_clinical_decision":False}

    @app.post("/v1/audit/free-text")
    def free_text(claim:dict,x_operator_token:str|None=Header(None)):
        if x_operator_token is None or not hmac.compare_digest(x_operator_token,operator_token):
            raise HTTPException(status_code=401,detail="operator authentication required")
        if set(claim)!={"text"} or type(claim["text"]) is not str:
            raise HTTPException(status_code=422,detail="free text only")
        if len(claim["text"])>4000:
            raise HTTPException(status_code=422,detail="bounded text only")
        return audit_free_text(claim["text"])
    return app
