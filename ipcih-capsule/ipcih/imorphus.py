"""Experimental iMorphus dual carrier. First stage is REAL standards QR.

Second stage uses a 4-color *pixel-exact* grid with independent SHA-256 and CRC,
NOT a JAB code or camera-robust 6MB optical codec. Finder-art is never claimed QR.
"""
from __future__ import annotations
import hashlib,io,struct,zlib
from PIL import Image
from .core import CapsuleRejected,encode_wire
COLORS=[(12,26,31),(20,209,165),(222,245,240),(113,76,217)]
MAGIC=b'IMORPHUSv1\0'

def render_dual(wire, *, width=100, pixels_per_cell=5):
    if not wire.startswith('ipcih1z:'):raise CapsuleRejected('bad capsule')
    if len(wire.encode())>8192:raise CapsuleRejected('color carrier size cap 8192')
    data=wire.encode('ascii')
    header=MAGIC+struct.pack('>I',len(data))+hashlib.sha256(data).digest()+struct.pack('>I',zlib.crc32(data))
    buf=header+data
    bits=len(buf)*4
    if bits>width*width:raise CapsuleRejected('not enough color cells')
    im=Image.new('RGB',(width*pixels_per_cell,width*pixels_per_cell),COLORS[0]);px=im.load()
    for n in range(width*width):
        code=((buf[n//4]>>(6-2*(n%4)))&3) if n<bits else 0
        col=COLORS[code];row=n//width;column=n%width
        for yy in range(row*pixels_per_cell,(row+1)*pixels_per_cell):
            for xx in range(column*pixels_per_cell,(column+1)*pixels_per_cell):px[xx,yy]=col
    return im

def decode_exact_color(im,*,width=100,pixels_per_cell=5):
    # Pixel-exact bench only; camera resampling, gamma, blur, print are unsupported.
    if im.size!=(width*pixels_per_cell,width*pixels_per_cell) or im.mode!='RGB':raise CapsuleRejected('wrong experimental carrier shape')
    symbols=[]
    for n in range(width*width):
        x=(n%width)*pixels_per_cell+pixels_per_cell//2
        y=(n//width)*pixels_per_cell+pixels_per_cell//2
        c=im.getpixel((x,y))
        if c not in COLORS:raise CapsuleRejected('unrecognized color; no image tolerance certified')
        symbols.append(COLORS.index(c))
    buf=bytearray()
    for i in range(0,len(symbols)-3,4):buf.append((symbols[i]<<6)|(symbols[i+1]<<4)|(symbols[i+2]<<2)|symbols[i+3])
    if not bytes(buf).startswith(MAGIC):raise CapsuleRejected('bad color header')
    size=struct.unpack('>I',buf[len(MAGIC):len(MAGIC)+4])[0]
    if size>8192:raise CapsuleRejected('oversized color data')
    offset=len(MAGIC)+4+32+4
    data=bytes(buf[offset:offset+size])
    if len(data)!=size or hashlib.sha256(data).digest()!=bytes(buf[len(MAGIC)+4:len(MAGIC)+36]) or zlib.crc32(data)!=struct.unpack('>I',buf[len(MAGIC)+36:offset])[0]:raise CapsuleRejected('color checksum/hash failure')
    try:return data.decode('ascii')
    except UnicodeError as exc:raise CapsuleRejected('invalid color text') from exc

def first_stage_bootstrap(wire, *, issuer_fingerprint):
    # True standard QR encodes a bounded bootstrap and requires the experimental
    # color payload or another source to recover entire signed capsule.
    if not wire.startswith('ipcih1z:') or not isinstance(issuer_fingerprint,str) or len(issuer_fingerprint)!=64:raise CapsuleRejected('bad bootstrap')
    return 'ipcih-boot1:'+hashlib.sha256(wire.encode()).hexdigest()+':'+issuer_fingerprint

def make_qr(text,*,ecc='M'):
    import qrcode
    levels={'L':qrcode.constants.ERROR_CORRECT_L,'M':qrcode.constants.ERROR_CORRECT_M,'Q':qrcode.constants.ERROR_CORRECT_Q}
    qr=qrcode.QRCode(error_correction=levels[ecc],box_size=8,border=4)
    try:qr.add_data(text,optimize=0);qr.make(fit=True)
    except Exception as exc:raise CapsuleRejected('QR capacity exceeded') from exc
    return qr.make_image(fill_color='black',back_color='white').convert('RGB')
