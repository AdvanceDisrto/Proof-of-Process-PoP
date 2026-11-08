"""REAL crypto+offline-verifier -> ESC/POS raster -> optical QR read-back.

Only synthetic identities, mock evidence and UNTRUSTED paper. No physical printer.
"""
import json
import hashlib
from pathlib import Path
import tempfile
import numpy as np
from innovulis_receipt.issuer_demo import create_demo
from innovulis_receipt.codec import encode_qr_text, decode_qr_text
from paper_console.verification import IndependentReceiptGate
from paper_console.escpos import render_receipt, PrintPolicy
from paper_console.store import EventStore


def run(out_dir):
    import cv2
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    demo=create_demo(verdict='REFUTED_FALSE', observed=90000, limit=50000)
    with tempfile.TemporaryDirectory() as evidence:
        Path(evidence,'sensor_demo_trace.txt').write_bytes(demo['evidence'])
        gate=IndependentReceiptGate(
            trust=demo['trust'], revocations=demo['revocations'],issuance_log=demo['issuance_log'],
            independently_pinned_anchor_sha256=demo['trust_sha256'],expected_subject='sensor:demo-unit-314',
            evidence_dir=evidence)
        carrier=encode_qr_text(demo['packet'])
        event,decision=gate.check(demo['packet'],now=demo['demo_time'],carrier=carrier)
        assert decision['code']=='VERIFIED_DIGITAL_RECEIPT'
        assert event.claim_verdict=='REFUTED_FALSE'
        data,meta=render_receipt(event,policy=PrintPolicy())
        (out/'synthetic_signed.escpos').write_bytes(data)
        # Reconstruct pixels from actual ESC/POS GS v 0 raster bytes.
        p=data.index(b'\x1dv0\x00')+4
        wb=data[p]|data[p+1]<<8
        h=data[p+2]|data[p+3]<<8
        raw=data[p+4:p+4+wb*h]
        assert len(raw)==wb*h
        gray=255-np.unpackbits(np.frombuffer(raw,dtype=np.uint8).reshape(h,wb),axis=1)*255
        cv2.imwrite(str(out/'synthetic_printed_qr.png'),gray)
        # Independent open-source ZBar optical decoder is more robust for dense
        # signed QR than OpenCV's detector on some random-signature patterns.
        # This decodes rendered pixels, NOT the original carrier string.
        try:
            from pyzbar.pyzbar import decode as zbar_decode
            from PIL import Image
            optical=zbar_decode(Image.fromarray(gray))
            text=optical[0].data.decode("ascii") if optical else ""
            scanner="ZBAR_PIXEL_DECODE"
        except ImportError:
            text,_,_=cv2.QRCodeDetector().detectAndDecode(gray)
            scanner="OPENCV_PIXEL_DECODE"
        assert text==carrier, 'ESC/POS QR failed independent optical pixel decode'
        packet=decode_qr_text(text)
        event_again,second=gate.check(packet,now=demo['demo_time'])
        assert second['code']=='VERIFIED_DIGITAL_RECEIPT'
        assert event_again.claim_verdict=='REFUTED_FALSE'
        store=EventStore(out/'demo_console.sqlite3')
        try:
            result=store.append(event)
            assert store.integrity()['chain_ok']
        finally:store.close()
    result={"synthetic_source_only":True,"real_ed25519":True,"optical_qr_scanned":True,
        "escpos_raster_sha256":hashlib.sha256(data).hexdigest(),
        "signed_carrier_sha256":hashlib.sha256(carrier.encode()).hexdigest(),
        "optical_decoder":scanner,
        "claim_verdict":"REFUTED_FALSE","digital_verification":"VERIFIED_DIGITAL_RECEIPT",
        "ledger_event_hash":result['event_hash'],"printer_hardware":"NOT_CONNECTED",
        "atecc608_hardware":"NOT_CONNECTED","ina226_hardware":"NOT_CONNECTED",
        "runpod_compute":"NOT_EXECUTED","fpga_bitstream":"NOT_BUILT",
        "witness_operators":"SYNTHETIC_KEYS_SAME_PROCESS",
        "verified_scope":"DIGITAL DEMO ONLY; no physical or real-world truth"}
    (out/'synthetic_crypto_print_smoke.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print('SYNTHETIC_SIGNED_QR_OPTICAL=PASS proof_verdict=REFUTED_FALSE sign_integrity=PASS physical=NOT_CONNECTED')
    return result

if __name__=='__main__':
    import sys
    run(sys.argv[1] if len(sys.argv)>1 else 'evidence/signed-optical')
