"""Local-only synthetic Human Hub. No patient data accepted."""
from __future__ import annotations
from contextlib import asynccontextmanager
import hmac
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from .core import HumanHub, HubRejected, SCOPE

class DemoRequest(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    explicit_demo_consent: bool
    observed: int=Field(default=45000,ge=-1000000,le=1000000)
    limit: int=Field(default=50000,ge=-1000000,le=1000000)

class ReviewRequest(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    confirm_scope: bool

def create_app(*, database=":memory:",operator_token: str) -> FastAPI:
    if not isinstance(operator_token,str) or len(operator_token)<24:
        raise ValueError("provide a strong operator token outside source control")
    hub=HumanHub(database)
    @asynccontextmanager
    async def lifespan(app):
        yield
        hub.close()
    app=FastAPI(title="iNNOVULIS Human-Centric Hub",lifespan=lifespan,
                docs_url=None,redoc_url=None,openapi_url=None)
    app.state.hub=hub

    def require(value):
        if not value or not hmac.compare_digest(value,operator_token):
            raise HTTPException(403,"local operator authorization required")

    def fail_closed(exc):
        raise HTTPException(422,str(exc)) from exc

    @app.get("/health")
    def health():
        return {"status":"ONLINE_LOCAL_DEMO","clinical_ready":False,
                "physical_acceptance":False,"source":SCOPE.tier}

    @app.get("/api/feeds")
    def feeds(x_i_hub_token: str | None=Header(default=None)):
        require(x_i_hub_token)
        return hub.read_feed()

    @app.post("/api/demo")
    def demo(payload:DemoRequest,x_i_hub_token: str | None=Header(default=None)):
        require(x_i_hub_token)
        try:
            return hub.create_synthetic_receipt(
                observed=payload.observed,limit=payload.limit,
                explicit_demo_consent=payload.explicit_demo_consent)
        except HubRejected as exc:fail_closed(exc)

    @app.get("/api/qr/{event_id}")
    def qr(event_id:str,x_i_hub_token: str | None=Header(default=None)):
        require(x_i_hub_token)
        try:data=hub.render_qr_png(event_id)
        except HubRejected as exc:fail_closed(exc)
        return Response(content=data,media_type="image/png",headers={
            "Cache-Control":"no-store","X-Receipt-Demo-Only":"true"})

    @app.get("/api/print-preview/{event_id}")
    def preview(event_id:str,x_i_hub_token: str | None=Header(default=None)):
        require(x_i_hub_token)
        try:data=hub.print_preview_bytes(event_id)
        except (HubRejected,ValueError) as exc:fail_closed(exc)
        return Response(content=data,media_type="application/octet-stream",headers={
            "Cache-Control":"no-store","X-Actual-Printer-Used":"false",
            "Content-Disposition":"attachment; filename=demo-only-ipqr.escpos"})

    @app.post("/api/review/{event_id}")
    def review(event_id:str,payload:ReviewRequest,x_i_hub_token: str | None=Header(default=None)):
        require(x_i_hub_token)
        try:return hub.acknowledge_review(event_id,confirm_scope=payload.confirm_scope)
        except HubRejected as exc:fail_closed(exc)

    @app.get("/",response_class=HTMLResponse)
    def index():
        page=(Path(__file__).parent/"index.html").read_text(encoding="utf-8")
        return HTMLResponse(page,headers={
            "Cache-Control":"no-store","Referrer-Policy":"no-referrer",
            "Content-Security-Policy":"default-src 'none'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"})
    return app
