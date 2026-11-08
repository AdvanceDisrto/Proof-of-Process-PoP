import tempfile, unittest
from rgpu_terminal.journal import ReceiptJournal
from rgpu_terminal.archival import raster_and_escpos,carrier_text
from rgpu_terminal.crypto import verify_envelope,ZERO_HASH
from pyzbar.pyzbar import decode

class Optical(unittest.TestCase):
    def test_real_optical_scan_and_signature(self):
        with tempfile.TemporaryDirectory() as td:
            journal=ReceiptJournal(td);envelope=journal.ensure_genesis()
            raster,img=raster_and_escpos(envelope,journal.public_key,width_px=576,modules_px=4)
            optical=decode(img)
            self.assertEqual(len(optical),1)
            recovered=optical[0].data.decode('ascii')
            self.assertEqual(recovered,carrier_text(envelope))
            import json,zlib
            from rgpu_terminal.crypto import unb64url
            binary=zlib.decompress(unb64url(recovered.split(':',1)[1]))
            decoded=json.loads(binary)
            signed=verify_envelope(decoded,journal.public_key,previous=ZERO_HASH,expected_sequence=1)
            self.assertEqual(signed['claim'],'HUB_INITIALIZED')
            journal.close()
