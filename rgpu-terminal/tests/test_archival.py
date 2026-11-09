import io, socket, threading, tempfile, unittest
from pathlib import Path
from rgpu_terminal.journal import ReceiptJournal
from rgpu_terminal.archival import (carrier_text,raster_and_escpos,TcpPrinter,PrintBlocked)
from rgpu_terminal.crypto import unb64url

class Archival(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.j=ReceiptJournal(self.tmp.name)
        self.e=self.j.ensure_genesis()
    def tearDown(self):self.j.close();self.tmp.cleanup()
    def test_complete_carrier_roundtrip(self):
        import json
        c=carrier_text(self.e)
        self.assertTrue(c.startswith('rgpu1z:'))
        import zlib
        self.assertEqual(json.loads(zlib.decompress(unb64url(c.split(':',1)[1]))),self.e)
    def test_80mm_escpos_is_full_signed_data(self):
        b,img=raster_and_escpos(self.e,self.j.public_key,width_px=576)
        self.assertTrue(b.startswith(b'\x1b\x40'))
        self.assertIn(b'NOT A PHYSICAL TPM',b)
        self.assertEqual(img.width,576)
        self.assertTrue(b.find(b'\x1d\x76\x30\x00')>0)
    def test_wrong_pin_refuses_print(self):
        with self.assertRaises(PrintBlocked):raster_and_escpos(self.e,'11'*32)
    def test_unsupported_width(self):
        with self.assertRaises(PrintBlocked):raster_and_escpos(self.e,self.j.public_key,width_px=500)
    def test_printer_disabled_by_default(self):
        with self.assertRaises(PrintBlocked):TcpPrinter('127.0.0.1',9100)
    def test_no_external_emulator_rebind(self):
        with self.assertRaises(PrintBlocked):TcpPrinter('192.168.1.1',9100,explicit_operator_approval=True,emulator_only=True)
    def test_physical_printer_not_loopback(self):
        with self.assertRaises(PrintBlocked):TcpPrinter('127.0.0.1',9100,explicit_operator_approval=True)
    def test_tcp_escpos_loopback_emulator_real_bytes(self):
        b,img=raster_and_escpos(self.e,self.j.public_key)
        received=[];s=socket.socket();s.bind(('127.0.0.1',0));s.listen(1)
        port=s.getsockname()[1]
        def read():
            conn,_=s.accept()
            with conn:
                data=bytearray()
                while True:
                    chunk=conn.recv(65536)
                    if not chunk:break
                    data.extend(chunk)
                received.append(bytes(data))
            s.close()
        t=threading.Thread(target=read,daemon=True);t.start()
        output=TcpPrinter('127.0.0.1',port,explicit_operator_approval=True,emulator_only=True).write(b)
        t.join(timeout=5)
        self.assertEqual(received[0],b)
        self.assertEqual(output['status'],'SENT_UNCONFIRMED')
        self.assertFalse(output['actual_paper_seen'])
