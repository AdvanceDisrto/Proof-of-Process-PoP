"""ESC/POS raster QR formatter and fail-closed operator-selected printer sinks.

Never put an unsigned claim on paper labeled VERIFIED. Printer is an untrusted carrier.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import time
from .codec import Event


class PrintBlocked(RuntimeError): pass


@dataclass(frozen=True)
class PrintPolicy:
    minimum_interval_seconds: int = 5
    maximum_per_hour: int = 30
    paper_width_pixels: int = 576
    module_min_px: int = 4

    def __post_init__(self):
        if not 5 <= self.minimum_interval_seconds <= 3600:
            raise ValueError("print interval cannot be under 5 seconds")
        if not 1 <= self.maximum_per_hour <= 120:
            raise ValueError("unsafe print budget")
        if self.paper_width_pixels not in (384,576):
            raise ValueError("only configured 58mm/80mm printer widths")
        if not 3 <= self.module_min_px <= 8:
            raise ValueError("QR modules too small")


def _raster_qr(text:str,policy:PrintPolicy):
    if not text.startswith("ipqr1:"):
        raise PrintBlocked("cannot print an unsigned/non-ipQR payload as a signed carrier")
    try:
        import qrcode
        from qrcode.exceptions import DataOverflowError
    except ImportError as exc:
        raise PrintBlocked("qrcode library required for real QR carrier") from exc
    qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=1, border=8)
    try: qr.add_data(text, optimize=0);qr.make(fit=True)
    except (DataOverflowError, ValueError) as exc:raise PrintBlocked("signed receipt exceeds standard QR capacity") from exc
    modules=qr.get_matrix()
    dot=policy.module_min_px
    if len(modules)*dot > policy.paper_width_pixels:
        raise PrintBlocked("full signed receipt QR too dense for thermal paper at safe resolution")
    offset=(policy.paper_width_pixels-len(modules)*dot)//2
    width_bytes=policy.paper_width_pixels//8
    height=len(modules)*dot
    if height>=65536: raise PrintBlocked("receipt raster height too tall")
    scanlines=bytearray(width_bytes*height)
    for y,row in enumerate(modules):
        for x,ink in enumerate(row):
            if ink:
                for iy in range(dot):
                    py=y*dot+iy
                    for ix in range(dot):
                        px=offset+x*dot+ix
                        scanlines[py*width_bytes+px//8] |= (0x80>>(px%8))
    header=b"\x1d\x76\x30\x00"+bytes([width_bytes&0xff,(width_bytes>>8)&0xff,height&0xff,(height>>8)&0xff])
    return header+bytes(scanlines),{"qr_modules":len(modules),"width_px":policy.paper_width_pixels,"height_px":height}


def render_receipt(event:Event, *, policy:PrintPolicy, include_qr:bool=True) -> tuple[bytes,dict]:
    # Transform user text to printable ASCII rather than silently output device control bytes.
    subject=event.subject.encode("ascii",errors="replace").decode("ascii")[:60]
    claims={"PROVEN_TRUE":"DECLARED_TRUE", "REFUTED_FALSE":"DECLARED_FALSE",
            "UNRESOLVED":"UNRESOLVED", "NOT_APPLICABLE":"NOT_APPLICABLE"}
    head=("\n iNNOVULIS  i(TM)  PAPER CONSOLE\n"
          " UNTRUSTED PAPER / SCAN TO VERIFY\n"
          "--------------------------------\n"
          f"EVENT {event.event_id[:48]}\n"
          f"SUBJECT {subject}\n"
          f"CLAIM {claims[event.claim_verdict]}\n"
          f"DIGITAL {event.verification}\n"
          f"SOURCE {event.source_tier}\n"
          f"UTC {time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(event.occurred_at))}\n"
          f"HASH {event.receipt_sha256 or 'NO_VERIFIED_RECEIPT'}\n"
          "--------------------------------\n").encode("ascii")
    data=b"\x1b@"+head
    meta={"is_real_printer":False,"is_signed_payload_carried":False,
          "warning":"The image/ink is not an authenticated display. Use open verifier with independent anchor."}
    if include_qr:
        if event.carrier is None or event.verification!="VERIFIED_DIGITAL_RECEIPT":
            raise PrintBlocked("full independently verified signed carrier required for printable ipQR")
        raster,rinfo=_raster_qr(event.carrier,policy)
        data+=raster+b"\nVERIFY IN OPEN APP. PAPER CANNOT PROVE.\n"
        meta.update(rinfo,is_signed_payload_carried=True)
    else:
        data+=b"\nNO SIGNED CARRIER: DISPLAY ONLY.\n"
    return data+b"\n\n\n",meta


class DryRunPrinter:
    """Write ESC/POS bytes to a local file; does not touch physical devices."""
    def __init__(self,path): self.path=Path(path)
    def write(self,payload:bytes):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.path.write_bytes(payload)
        return len(payload)


class ApprovedTcpPrinter:
    """Restricted direct TCP ESC/POS sink. Caller must explicitly supply host+approval.

    Does not guarantee delivery; never enabled in the web service by default.
    """
    def __init__(self,host:str,*,port=9100,operator_approved=False):
        import ipaddress
        if not operator_approved: raise PrintBlocked("physical printer write requires operator approval")
        addr=ipaddress.ip_address(host)
        if not addr.is_private or addr.is_loopback or addr.is_link_local:
            raise PrintBlocked("printer must be a configured private-network IP")
        if not 1<=port<=65535:raise PrintBlocked("invalid printer port")
        self.host=host;self.port=port
    def write(self,payload:bytes):
        import socket
        with socket.create_connection((self.host,self.port),timeout=3) as sock:
            sock.settimeout(3);sock.sendall(payload)
        return len(payload)


class PrintScheduler:
    def __init__(self,store,printer,policy=None,*,mode="manual"):
        if mode not in ("manual","exception","continuous","off"):
            raise ValueError("unsupported printer mode")
        self.store=store;self.printer=printer;self.policy=policy or PrintPolicy();self.mode=mode
        self.store.recover_claimed_as_hold()

    def consider(self,event:Event):
        if self.mode=="off":return False
        if self.mode=="manual":return False
        # Must have a verified digital receipt. A rejected receipt is NOT automatically trusted.
        if event.verification!="VERIFIED_DIGITAL_RECEIPT":return False
        if self.mode=="exception" and event.claim_verdict!="REFUTED_FALSE":return False
        self.store.queue(event.event_id)
        return True

    def process_once(self,*,now=None):
        if self.mode=="off":return {"status":"DISABLED"}
        now=int(time.time()) if now is None else int(now)
        last=self.store.last_print_time()
        if last is not None and (now<last or now-last<self.policy.minimum_interval_seconds):
            return {"status":"RATE_LIMITED"}
        if self.store.prints_since(now,3600)>=self.policy.maximum_per_hour:
            return {"status":"HOURLY_BUDGET_EXCEEDED"}
        task=self.store.next_print()
        if task is None:return {"status":"EMPTY"}
        event_id,event=task
        try:
            data,meta=render_receipt(event,policy=self.policy)
            n=self.printer.write(data)
            # Write success does not prove paper physically emerged, or that the receipt was read.
            self.store.finish_print(event_id,hashlib.sha256(data).hexdigest(),now)
            return {"status":"SENT_UNCONFIRMED", "event_id":event_id,"bytes":n,**meta}
        except Exception as exc:
            self.store.hold_print(event_id,exc)
            return {"status":"HOLD", "event_id":event_id,"reason":str(exc)[:180]}


class ApprovedPythonEscposPrinter:
    """Optional python-escpos USB/serial wrapper; no device without explicit approval.

    Device object may be a reviewed printer opened by the operator, or an
    explicit USB/serial config. The printer is a dumb untrusted output device.
    """
    def __init__(self, *, operator_approved=False, printer=None, usb_ids=None, serial_dev=None):
        if not operator_approved:
            raise PrintBlocked("python-escpos requires explicit physical printer approval")
        if printer is None:
            try:
                from escpos.printer import Usb, Serial
            except ImportError as exc:
                raise PrintBlocked("install python-escpos for physical USB/serial devices") from exc
            if usb_ids and serial_dev:
                raise PrintBlocked("choose exactly one physical printer")
            if usb_ids:
                if not (type(usb_ids) is tuple and len(usb_ids)==2 and
                        all(type(v) is int and 0 < v <= 0xffff for v in usb_ids)):
                    raise PrintBlocked("invalid USB VID/PID")
                printer=Usb(*usb_ids)
            elif serial_dev:
                if type(serial_dev) is not str or not serial_dev.startswith("/dev/serial/by-id/"):
                    raise PrintBlocked("use stable /dev/serial/by-id/ path for physical printer")
                printer=Serial(devfile=serial_dev)
            else:
                raise PrintBlocked("physical printer identifiers must be supplied")
        self.printer=printer

    def write(self,payload:bytes):
        # python-escpos exposes _raw for raw ESC/POS commands, subject to profile.
        if type(payload) is not bytes or len(payload)>1024*1024:
            raise PrintBlocked("invalid printer command length")
        raw=getattr(self.printer,"_raw",None)
        if raw is None or not callable(raw):raise PrintBlocked("unsupported printer API")
        raw(payload)
        return len(payload)
