"""Create digital GENESIS receipt and optional ESC/POS preview, never print real paper."""
from __future__ import annotations
import json,sys,hashlib,tempfile
from pathlib import Path
from rgpu_terminal.journal import ReceiptJournal
from rgpu_terminal.crypto import verify_envelope,ZERO_HASH
from rgpu_terminal.archival import raster_and_escpos,carrier_text

out=Path(sys.argv[1] if len(sys.argv)>1 else 'evidence/genesis')
out.mkdir(parents=True,exist_ok=True)
# One dedicated throwaway software-demo identity. DO NOT package its secret key.
with tempfile.TemporaryDirectory(prefix='innovulis-genesis-key-') as td:
    journal=ReceiptJournal(td)
    envelope=journal.ensure_genesis()
    pub=journal.public_key
    payload=verify_envelope(envelope,pub,previous=ZERO_HASH,expected_sequence=1)
    (out/'genesis_signed_envelope.json').write_text(json.dumps(envelope,indent=2,sort_keys=True)+'\n')
    (out/'genesis_scoped_claim.json').write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    (out/'demo_public_trust_anchor.json').write_text(json.dumps({
      'public_key_hex':pub,'sha256_fingerprint':journal.fingerprint,
      'tier':'EPHEMERAL_SOFTWARE_KEY_SYNTHETIC_NO_INDEPENDENT_ANCHOR',
      'does_not_prove':['human presence','TPM-PUF','physical joules','printer feed']},indent=2,sort_keys=True)+'\n')
    carrier=carrier_text(envelope)
    (out/'genesis_full_signed_rgpu1z.txt').write_text(carrier+'\n')
    escpos,image=raster_and_escpos(envelope,pub,width_px=576,modules_px=4)
    (out/'genesis_80mm_preview.escpos').write_bytes(escpos)
    image.save(out/'genesis_80mm_qr.png')
    import qrcode
    qrcode.make(carrier,error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=6,border=4).save(out/'genesis_screen_qr.png')
    journal.close()
print(json.dumps({'GENESIS_SOFTWARE_RECEIPT':'SIGNED_AND_REVERIFIED',
 'REAL_JOULES':'NOT_MEASURED','TPM':'NOT_CONNECTED','PRINTER':'NO_PAPER_PRINTED',
 'QR':'FULL_SIGNED_RGPU1Z_ENVELOPE','test_key':'EPHEMERAL_SOFTWARE'},sort_keys=True))
