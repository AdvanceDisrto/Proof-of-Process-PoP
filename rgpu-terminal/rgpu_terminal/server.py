"""Loopback-only multi-client signed telemetry terminal (not a public service).

The server transports evidence; it does not confer trust. Independent browser
verification requires an out-of-band pinned Ed25519 public key.
"""
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
import hmac
import ipaddress
import json
import math
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit
from dataclasses import dataclass

from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict
from starlette.websockets import WebSocketState

from .crypto import ReceiptError
from .archival import carrier_text
from .journal import ReceiptJournal

STATIC = Path(__file__).parent / "static"


@dataclass(eq=False)
class Subscriber:
    queue: asyncio.Queue
    overrun: bool = False


class TerminalService:
    def __init__(self, journal: ReceiptJournal, *, max_clients=32, queue_size=32, heartbeat_seconds=10.0):
        self.journal=journal
        self.max_clients=max_clients
        self.queue_size=queue_size
        self.clients: set[Subscriber]=set()
        self.lock=asyncio.Lock()

    async def issue(self, **kwargs):
        async with self.lock:
            env=self.journal.append(**kwargs)
            for sub in tuple(self.clients):
                if sub.queue.full():
                    sub.overrun=True
                else:
                    sub.queue.put_nowait(env)
            return env

    async def join(self, after):
        async with self.lock:
            if len(self.clients) >= self.max_clients:
                raise ReceiptError("client limit reached")
            sub=Subscriber(asyncio.Queue(maxsize=self.queue_size))
            self.clients.add(sub)
            # Snapshot retrieval and registration are serialized with issue().
            # 100 max per page: client paginates /api/history from genesis.
            last_seq=self.journal.last()[0]
            return sub,last_seq

    async def leave(self,sub):
        async with self.lock:
            self.clients.discard(sub)


class DemoRequest(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    outcome: str = "PASS"  # Only synthetic demo. No external sensors accepted.


def create_app(*, data_dir: str | Path, operator_token: str, demo_enabled=False,
               max_clients=32, queue_size=32, heartbeat_seconds=10.0):
    if not isinstance(operator_token,str) or len(operator_token)<32:
        raise ValueError("strong local operator token (>=32 chars) required")
    journal=ReceiptJournal(data_dir)
    service=TerminalService(journal,max_clients=max_clients,queue_size=queue_size)

    @asynccontextmanager
    async def lifespan(app):
        journal.ensure_genesis()
        try:yield
        finally:journal.close()

    app=FastAPI(title="iNNOVULIS™ rGPU Evidence Terminal",docs_url=None,redoc_url=None,
                openapi_url=None,lifespan=lifespan)
    app.state.service=service

    def local_host(host):
        if not isinstance(host,str):return False
        bare=host.split(":")[0].lower()
        return bare in ("localhost","127.0.0.1")

    def require_operator(token):
        if not token or not hmac.compare_digest(token,operator_token):
            raise HTTPException(status_code=403,detail="explicit operator token required")

    def response_for(path, media):
        return FileResponse(STATIC/path,media_type=media,headers={
            "Cache-Control":"no-store", "X-Content-Type-Options":"nosniff",
            "Referrer-Policy":"no-referrer", "X-Frame-Options":"DENY"})

    @app.get("/")
    async def index():
        result=response_for("index.html","text/html; charset=utf-8")
        result.headers["Content-Security-Policy"]=(
            "default-src 'none'; script-src 'self'; style-src 'self'; "
            "connect-src 'self' ws://localhost:* ws://127.0.0.1:*; "
            "img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        return result

    @app.get("/static/{asset}")
    async def assets(asset: str):
        mapping={"verify.mjs":"text/javascript; charset=utf-8",
                 "app.mjs":"text/javascript; charset=utf-8",
                 "style.css":"text/css; charset=utf-8"}
        if asset not in mapping:raise HTTPException(status_code=404)
        return response_for(asset,mapping[asset])

    @app.get("/api/health")
    async def health():
        return {"status":"ONLINE_LOCAL_SOFTWARE", "source_tier":"SOFTWARE_ONLY",
                "physical_joules_verified":False,"hardware_signer":False,
                "physical_printer":False,"medical_or_legal_truth":False,
                "clients":len(service.clients)}

    @app.get("/api/identity")
    async def identity():
        return {"ed25519_public_key_hex":journal.public_key,
                "key_fingerprint_sha256":journal.fingerprint,
                "trust":"UNTRUSTED_KEY_DISCOVERY_ONLY_VERIFY_FINGERPRINT_OUT_OF_BAND",
                "hardware_key":False}

    @app.get("/api/history")
    async def history(after: int=Query(default=0,ge=0),limit: int=Query(default=100,ge=1,le=100)):
        return {"envelopes":journal.get_after(after,limit),"next_after":journal.last()[0],
                "source":"LOCAL_SOFTWARE_EVENT_STREAM_NOT_PHYSICAL_PROOF"}

    @app.get("/api/receipt/{sequence}")
    async def receipt(sequence:int):
        try: env=journal.get(sequence)
        except ReceiptError:raise HTTPException(status_code=404)
        if env is None:raise HTTPException(status_code=404)
        return env

    @app.get("/api/receipt/{sequence}/qr.svg")
    async def qr(sequence:int):
        import qrcode
        import qrcode.image.svg
        env=journal.get(sequence)
        if env is None:raise HTTPException(status_code=404)
        # rgpu1 is a *distinct format*, not the Open Receipt v1.0 ipqr1 schema.
        # An offline client must decode and verify this complete signed envelope.
        from .crypto import b64url,canonical
        text=carrier_text(env)
        qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=6,border=4,
                        image_factory=qrcode.image.svg.SvgPathImage)
        try:qr.add_data(text,optimize=0);qr.make(fit=True)
        except Exception as e:raise HTTPException(status_code=422,detail="receipt exceeds safe optical capacity") from e
        data=qr.make_image().to_string()
        return Response(data,media_type="image/svg+xml",headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"})

    @app.post("/api/demo/tick")
    async def synthetic_tick(body: DemoRequest,x_innovulis_operator_token: str|None=Header(default=None)):
        require_operator(x_innovulis_operator_token)
        if not demo_enabled:raise HTTPException(status_code=403,detail="synthetic demo disabled")
        if body.outcome not in ("PASS","REFUTED"):
            raise HTTPException(status_code=422,detail="synthetic outcome must be PASS or REFUTED")
        # No random physical numbers disguised as sensor readings.
        sample={"simulated_tflops":2450.0,"simulated_core_temperature_c":72.0,
                "simulated_joules":4.2,"physical_joules":None,
                "energy_provenance":"SYNTHETIC_NOT_FROM_INA226", "gpu":"NOT_EXECUTED",
                "note":"Synthetic render/alert test. This is not a measurement."}
        return await service.issue(claim="SYNTHETIC_TELEMETRY",source_tier="SYNTHETIC_DEMO",
                                   verdict="REFUTED_FALSE" if body.outcome=="REFUTED" else "PROVEN_TRUE",
                                   telemetry=sample,operator_attestation="NOT_ATTESTED")

    @app.websocket("/ws")
    async def ws(websocket: WebSocket,after:int=0):
        host=websocket.headers.get("host","")
        origin=websocket.headers.get("origin","")
        valid_origins={"http://"+host, "http://localhost", "http://127.0.0.1"}
        # No browser from another website can open the local stream.
        if not local_host(host) or origin not in valid_origins or after<0:
            await websocket.close(code=1008)
            return
        try:sub,last_seq=await service.join(after)
        except ReceiptError:
            await websocket.close(code=1013);return
        await websocket.accept()
        try:
            await websocket.send_json({"type":"hello","last_sequence":last_seq,
                                       "trust":"UNTRUSTED_TRANSPORT_INDEPENDENT_CRYPTO_REQUIRED"})
            while True:
                if sub.overrun:
                    await websocket.send_json({"type":"resync_required","reason":"slow_client_backpressure"})
                    await websocket.close(code=1013)
                    return
                incoming=asyncio.create_task(websocket.receive_text())
                next_record=asyncio.create_task(sub.queue.get())
                done,pending=await asyncio.wait((incoming,next_record),timeout=heartbeat_seconds,
                                                return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    task.cancel()
                    try:await task
                    except asyncio.CancelledError:pass
                if not done:
                    await websocket.send_json({"type":"heartbeat"})
                    continue
                if incoming in done:
                    # Only server-to-client receipt transport is allowed.
                    # A client disconnect is observed promptly, not 10 s later.
                    try:incoming.result()
                    except WebSocketDisconnect:return
                    await websocket.close(code=1008)
                    return
                data=next_record.result()
                await websocket.send_json({"type":"receipt","envelope":data})
        except (WebSocketDisconnect,RuntimeError,OSError):
            pass
        finally:
            await service.leave(sub)

    return app
