"""Explicit command line gates. No implicit physical hardware actions."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .physical import record_report,assert_no_upgrade
from .board import audit_file
from .bridge import run_synthetic_closed_loop


def main(argv=None):
    ap=argparse.ArgumentParser(prog="innovulis-unified")
    s=ap.add_subparsers(dest="cmd",required=True)
    demo=s.add_parser("smoke-synthetic",help="Actual signed software receipts/optical/print preview; no hardware")
    demo.add_argument("--out",default="evidence/synthetic-smoke")
    s.add_parser("physical-gates",help="Fail-closed physical status report")
    board=s.add_parser("audit-board",help="Candidate-netlist semantic check, NOT ERC or fabrication approval")
    board.add_argument("path")
    args=ap.parse_args(argv)
    if args.cmd=="smoke-synthetic":
        result=run_synthetic_closed_loop(Path(args.out))
    elif args.cmd=="physical-gates":
        result=record_report();assert_no_upgrade(result)
    else:
        result=audit_file(args.path)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=='__main__':raise SystemExit(main())
