import argparse
import os
import sys
import secrets
from .journal import ReceiptJournal
from .server import create_app


def main():
    p=argparse.ArgumentParser(description="iNNOVULIS rGPU terminal: signed local software telemetry (NO hardware guarantees)")
    p.add_argument("command",choices=["serve","identity","inspect","genesis","monitor"])
    p.add_argument("--data-dir",default=os.environ.get("INNOVULIS_DATA_DIR","./private-terminal-data"))
    p.add_argument("--port",type=int,default=8768)
    p.add_argument("--pin-pub",default="",help="32-byte public key from independent source, 64 lowercase hex")
    args=p.parse_args()
    if args.command=="serve":
        token=os.environ.get("INNOVULIS_OPERATOR_TOKEN","")
        if len(token)<32:
            print("Set INNOVULIS_OPERATOR_TOKEN to >=32 secret characters (not in source)",file=sys.stderr)
            return 2
        app=create_app(data_dir=args.data_dir,operator_token=token,
                       demo_enabled=os.environ.get("INNOVULIS_SYNTHETIC_DEMO")=="1")
        import uvicorn
        uvicorn.run(app,host="127.0.0.1",port=args.port,log_level="warning")
        return 0
    if args.command=="monitor":
        if len(args.pin_pub)!=64:
            print("--pin-pub from independent source required for Rich CLI verifier",file=sys.stderr);return 2
        from .monitor import monitor
        import asyncio
        try:asyncio.run(monitor(f"http://127.0.0.1:{args.port}",args.pin_pub))
        except KeyboardInterrupt:pass
        return 0
    j=ReceiptJournal(args.data_dir)
    try:
        if args.command=="genesis":j.ensure_genesis()
        if args.command=="inspect":print(j.verify_all())
        else:
            print("ED25519_PUBLIC_KEY_HEX="+j.public_key)
            print("ED25519_SHA256_FINGERPRINT="+j.fingerprint)
            print("PRIVATE_KEY=SOFTWARE_ONLY_NEVER_SHARE_OR_UPLOAD")
    finally:j.close()
    return 0

if __name__=="__main__":raise SystemExit(main())
