"""Optional dumb-carrier receipt and explicit TCP output. Default: PREVIEW ONLY.

A successful socket write confirms neither paper feed nor trusted evidence.
A network printer can copy or substitute any previously signed payload.
"""
from __future__ import annotations
import ipaddress
import io
import json
import socket
import zlib
from .crypto import ReceiptError, canonical, b64url, verify_envelope


class PrintBlocked(RuntimeError):
    pass


def carrier_text(envelope:dict) ->str:
    """Distinct rgpu1 transport: NOT equivalent to ipqr1/Open Receipt v1."""
    return "rgpu1z:"+b64url(zlib.compress(canonical(envelope),9))


def raster_and_escpos(envelope:dict, pinned_public_hex:str, *, width_px=576, modules_px=4):
    from PIL import Image
    import qrcode
    from qrcode.exceptions import DataOverflowError
    if width_px not in (384,576) or not 4<=modules_px<=10:
        raise PrintBlocked("unsupported physical printer width or unsafe QR module size")
    try:
        payload=verify_envelope(envelope,pinned_public_hex)
    except ReceiptError as e:
        raise PrintBlocked("cannot print carrier without valid Ed25519 under independent pin") from e
    qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=1,border=4)
    try:qr.add_data(carrier_text(envelope),optimize=0);qr.make(fit=True)
    except (DataOverflowError,ValueError) as e:raise PrintBlocked("complete signed receipt exceeds standard QR capacity") from e
    pixels=qr.get_matrix()
    height=len(pixels)*modules_px
    if len(pixels)*modules_px>width_px or height>2048:
        raise PrintBlocked("full signed payload too dense for optical scanner on this printer")
    image=Image.new('1',(width_px,height),color=1)
    for y,row in enumerate(pixels):
        for x,is_black in enumerate(row):
            if is_black:
                px=(width_px-len(pixels)*modules_px)//2 + x*modules_px
                py=y*modules_px
                for dy in range(modules_px):
                    for dx in range(modules_px):image.putpixel((px+dx,py+dy),0)
    raw=bytearray()
    for y in range(height):
        for bx in range(width_px//8):
            value=0
            for shift in range(8):
                if image.getpixel((bx*8+shift,y))==0:value|=0x80>>shift
            raw.append(value)
    width_bytes=width_px//8
    raster=b'\x1d\x76\x30\x00'+bytes([width_bytes&255,(width_bytes>>8)&255,height&255,(height>>8)&255])+bytes(raw)
    header=("\n i(TM) iNNOVULIS GENESIS RECEIPT\n"
            " UNTRUSTED PAPER / VERIFY BY SCANNING\n"
            f" SEQUENCE {payload['sequence']:06d}\n"
            f" CLAIM {payload['claim']}\n"
            f" SOURCE {payload['source_tier']}\n"
            f" VERDICT {payload['declared_verdict']} (DECLARED)\n"
            f" SHA256 {envelope['payload_sha256'][:32]}...\n"
            " SOFTWARE ED25519 / NOT A PHYSICAL TPM\n"
            " ENERGY: NOT MEASURED BY INA226\n"
            " PRINTER DELIVERY: UNCONFIRMED\n"
            " rgpu1 FORMAT (NOT ipqr1)\n\n").encode('ascii')
    return (b'\x1b\x40'+header+raster+b'\n\nSCAN WITH PINNED OPEN VERIFIER\n\n',image)


class TcpPrinter:
    def __init__(self,host,port=9100,*,explicit_operator_approval=False,emulator_only=False):
        if explicit_operator_approval is not True:raise PrintBlocked("operator approval required")
        try:ip=ipaddress.ip_address(host)
        except ValueError as e:raise PrintBlocked("IP address literal required; no DNS rebound") from e
        if not (1<=port<=65535):raise PrintBlocked("invalid printer port")
        if emulator_only:
            if not ip.is_loopback:raise PrintBlocked("emulator must be loopback")
        elif not ip.is_private or ip.is_loopback or ip.is_link_local:
            raise PrintBlocked("physical printer must be an explicit private-LAN IP")
        self.host=str(ip);self.port=port

    def write(self,payload):
        if not isinstance(payload,bytes) or len(payload)>1_000_000:raise PrintBlocked("invalid ESC/POS write")
        with socket.create_connection((self.host,self.port),timeout=3) as conn:
            conn.settimeout(3)
            conn.sendall(payload)
        return {"status":"SENT_UNCONFIRMED","bytes":len(payload),
                "actual_paper_seen":False,"device_status":"UNKNOWN_NOT_POLLED"}
