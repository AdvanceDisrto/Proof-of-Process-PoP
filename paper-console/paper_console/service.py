"""Localhost FastAPI + WebSocket ticker; no automatic demo generator in production.

Every inbound event is explicitly UNVERIFIED (the operator cannot submit an arbitrary
verified decision via this endpoint). Real verified receipts must pass the local
IndependentReceiptGate first, outside this public-facing ingest handler.
"""
from __future__ import annotations
import asyncio
import hmac
import json
import secrets
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from .codec import Event, InvalidEvent
from .store import EventStore
from .escpos import render_receipt,PrintPolicy,PrintBlocked


def create_app(*, db_path=":memory:", operator_token: str | None = None):
    store=EventStore(db_path)
    subscribers=set()
    token=operator_token if operator_token is not None else secrets.token_urlsafe(32)
    if not token or len(token)<24:
        raise ValueError("strong operator token required")

    @asynccontextmanager
    async def lifespan(app):
        yield
        store.close()

    app=FastAPI(title="iNNOVULIS Paper Console", lifespan=lifespan, docs_url=None,redoc_url=None,
                openapi_url=None)
    app.state.store=store
    app.state.operator_token=token

    @app.get("/health")
    async def health():return {"alive":True,"scope":"local_console","printer":"DISABLED_UNLESS_CONFIGURED"}

    @app.get("/api/stats")
    async def stats():return store.stats()

    @app.get("/api/timeline")
    async def timeline(limit:int=30):
        # Signed ipQR carrier may contain sensitive information and is never returned
        # from public read-only endpoints. Operator-authenticated printing is separate.
        rows=store.latest(limit)
        for row in rows:row.pop("carrier",None)
        return {"events":rows}

    @app.get("/api/integrity")
    async def integrity():return store.integrity()

    @app.post("/api/ingest")
    async def ingest(payload:dict, x_i_operator_token: str | None = Header(None)):
        if x_i_operator_token is None or not hmac.compare_digest(x_i_operator_token,token):
            raise HTTPException(403,"operator credential required")
        # The API never trusts the claimed verdict as a verified receipt.
        if payload.get("verification") == "VERIFIED_DIGITAL_RECEIPT" or payload.get("source_tier")=="SIGNED_DIGITAL":
            raise HTTPException(422,"signed/verified claims require independent verifier interface")
        if payload.get("carrier"):
            raise HTTPException(422,"raw ipQR must be independently verified before ingestion")
        try:
            event=Event(**payload)
            if abs(int(time.time())-event.occurred_at)>86400:
                raise InvalidEvent("local inbound event outside one-day freshness window")
        except (InvalidEvent,TypeError,ValueError) as exc:
            raise HTTPException(422,str(exc)) from exc
        output=store.append(event)
        if not output["duplicate"]:
            for q in tuple(subscribers):
                try:q.put_nowait({"seq":output["seq"],**event.as_dict()})
                except asyncio.QueueFull:
                    subscribers.discard(q)
        return output

    @app.get("/api/print-preview/{event_id}")
    async def print_preview(event_id:str,x_i_operator_token: str | None = Header(None)):
        if x_i_operator_token is None or not hmac.compare_digest(x_i_operator_token,token):
            raise HTTPException(403,"operator credential required")
        if not 5<=len(event_id)<=100 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-:" for c in event_id):
            raise HTTPException(400,"invalid event ID")
        event=store.get_event(event_id)
        if not event:raise HTTPException(404,"no such event")
        try:
            data,_=render_receipt(event,policy=PrintPolicy(),include_qr=True)
        except PrintBlocked as exc:
            raise HTTPException(409,str(exc)) from exc
        return Response(content=data,media_type="application/octet-stream",
            headers={"Cache-Control":"no-store","Content-Disposition":"attachment; filename=ipqr-print.escpos",
                     "X-Print-Is-Physical":"false"})

    @app.websocket("/ws/timeline")
    async def ws(websocket:WebSocket):
        # This read-only endpoint is local-only by deployment policy.
        await websocket.accept()
        q=asyncio.Queue(maxsize=100)
        subscribers.add(q)
        try:
            await websocket.send_json({"type":"READY","scope":"untrusted telemetry unless verified separately"})
            while True:
                item=await q.get()
                item=dict(item);item.pop("carrier",None)
                await websocket.send_json({"type":"EVENT", "event":item})
        except (WebSocketDisconnect,RuntimeError):pass
        finally:subscribers.discard(q)

    @app.get("/",response_class=HTMLResponse)
    async def home():
        from pathlib import Path
        return (Path(__file__).parent/"dashboard.html").read_text(encoding="utf-8")
    return app
