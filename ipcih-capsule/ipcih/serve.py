"""Loopback only static open verifier; does not issue credentials or expose a model API."""
from __future__ import annotations
import argparse
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from functools import partial

ROOT=Path(__file__).resolve().parent/'web'
class Headers(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()')
        self.send_header('Cross-Origin-Resource-Policy','same-origin')
        super().end_headers()
    def log_message(self,*args):pass

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8768)
    a=parser.parse_args()
    if not 1<=a.port<=65535:parser.error('invalid port')
    server=ThreadingHTTPServer(('127.0.0.1',a.port),partial(Headers,directory=str(ROOT)))
    print(f'iP.CiH OPEN VERIFIER: http://127.0.0.1:{server.server_port} (loopback only)',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
