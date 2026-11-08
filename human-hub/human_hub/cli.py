"""Operator-only synthetic receipt smoke and localhost web UI."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from .core import HumanHub

def main(argv=None):
    p=argparse.ArgumentParser(prog="innovulis-human-hub")
    sub=p.add_subparsers(dest="command",required=True)
    d=sub.add_parser("demo",help="Generate SYNTHETIC signed receipt")
    d.add_argument("--out",default="human-hub-demo")
    d.add_argument("--observed",type=int,default=45000)
    d.add_argument("--limit",type=int,default=50000)
    d.add_argument("--ack-synthetic",action="store_true",required=True)
    s=sub.add_parser("serve",help="localhost-only operator-controlled demo")
    s.add_argument("--db",default="human-hub-demo.sqlite3")
    s.add_argument("--port",type=int,default=8781)
    args=p.parse_args(argv)
    if args.command=="demo":
        out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
        hub=HumanHub(out/"demo.sqlite3")
        try:
            result=hub.create_synthetic_receipt(observed=args.observed,
                limit=args.limit,explicit_demo_consent=True)
            (out/"ipqr_demo.png").write_bytes(hub.render_qr_png(result["event_id"]))
            (out/"ipqr_demo.escpos").write_bytes(hub.print_preview_bytes(result["event_id"]))
            result["journal_integrity"]=hub.store.integrity()
            (out/"run_receipt.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
            print(json.dumps(result,indent=2,sort_keys=True))
        finally:hub.close()
        return 0
    token=os.environ.get("HUB_OPERATOR_TOKEN")
    if not token or len(token)<24:
        raise SystemExit("Set strong HUB_OPERATOR_TOKEN privately, not in source control")
    from .web import create_app
    import uvicorn
    uvicorn.run(create_app(database=args.db,operator_token=token),
                host="127.0.0.1",port=args.port,log_level="warning",access_log=False)
    return 0
