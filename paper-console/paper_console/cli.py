"""Operator-first CLI; demo uses explicitly synthetic events. Real printer off by default."""
import argparse
import hashlib
import json
import time
from pathlib import Path
import numpy as np
from .codec import Event, canonical
from .store import EventStore
from .math_receipt import compute_covariance_svd
from .atlas import ingest_atlas, atlas_event, cable_transit_observation
from .popc import GateInputs, popc_admission


def run_demo(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    store=EventStore(out/"paper_console.sqlite3")
    now=int(time.time())
    try:
        # Real math on a non-diagnostic deterministic synthetic array.
        image=np.random.default_rng(20261108).normal(size=(16,16))
        math=compute_covariance_svd(image,patch=4)
        (out/"covariance_svd.json").write_text(json.dumps(math,indent=2,sort_keys=True)+"\n")
        store.append(Event(event_id="math-"+math["covariance_f64le_sha256"][:32],occurred_at=now,
            track="covariance",subject="synthetic:matrix-16x16",claim_verdict="UNRESOLVED",
            verification="NOT_CHECKED",source_tier="MATH_COMPUTED",details=math))
        # Do not fabricate public data from screenshots not attached in this session.
        atlas=ingest_atlas(Path(__file__).resolve().parents[1]/"data/atlas_example.json")
        (out/"atlas_import.json").write_text(json.dumps(atlas,indent=2,sort_keys=True)+"\n")
        for row in atlas["entities"]:store.append(atlas_event(row,atlas["source_sha256"],now))
        route=cable_transit_observation(origin="New York",destination="London",declared_route="MAREA")
        store.append(Event(event_id="transit-"+hashlib.sha256(canonical(route)).hexdigest()[:32],
            occurred_at=now,track="subsea",subject="operator-demo:NYC-to-London",
            claim_verdict="UNRESOLVED",verification="NOT_CHECKED",
            source_tier="DEMO",details=route))
        gate=popc_admission(GateInputs(False,False,False,False,True,False,True,False),"a"*64)
        store.append(Event(event_id="popc-"+gate["gate_input_commitment_sha256"][:32],
            occurred_at=now,track="popc",subject="demo:host-supplied-physics-flags",
            claim_verdict="UNRESOLVED",verification="NOT_CHECKED",source_tier="DEMO",details=gate))
        result={"scope":"SYNTHETIC_INPUTS_PLUS_REAL_NUMPY_MATH", "receipt_verification":"NOT_PERFORMED",
                "hardware_energy":"NOT_CONNECTED", "printer":"DISABLED", "count":store.stats()["total_events"],
                "stats":store.stats(),"integrity":store.integrity()}
        (out/"demo_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        return result
    finally:store.close()


def main(argv=None):
    p=argparse.ArgumentParser(prog="innovulis-paper-console")
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("demo",help="Run synthetic local inputs, real NumPy math, no printer")
    a.add_argument("--out",default="evidence/demo")
    a=sub.add_parser("atlas",help="Hash and validate an operator-supplied offline geography JSON")
    a.add_argument("--input",required=True)
    a=sub.add_parser("verify",help="OFFLINE ipQR v1 verification and append to console DB; no hardware output")
    for flag in ("input", "trust", "anchor-pin", "revocations", "issuance-log", "subject", "evidence-dir", "db"):
        a.add_argument("--"+flag,required=True)
    a.add_argument("--preview-escpos",help="write untrusted ESC/POS bytes to local file, never hardware")
    a=sub.add_parser("serve",help="localhost-only dashboard; simulated events OFF")
    a.add_argument("--db",default="paper_console.sqlite3")
    a.add_argument("--port",type=int,default=8780)
    args=p.parse_args(argv)
    if args.command=="demo":output=run_demo(args.out)
    elif args.command=="atlas":output=ingest_atlas(args.input)
    elif args.command=="verify":
        from .verification import IndependentReceiptGate
        from .escpos import render_receipt,PrintPolicy,DryRunPrinter
        from innovulis_receipt.codec import encode_qr_text
        read=lambda p:json.loads(Path(p).read_text())
        packet=read(args.input)
        gate=IndependentReceiptGate(trust=read(args.trust),revocations=read(args.revocations),
            issuance_log=read(args.issuance_log),independently_pinned_anchor_sha256=args.anchor_pin,
            expected_subject=args.subject,evidence_dir=args.evidence_dir)
        event,decision=gate.check(packet,carrier=encode_qr_text(packet))
        store=EventStore(args.db)
        try:append=store.append(event)
        finally:store.close()
        output={"decision":decision["code"],"verification_success":bool(decision["verified"]),
                "claim_verdict":event.claim_verdict,"event_id":event.event_id,
                "audit_event_hash":append["event_hash"],"physical_printer":"NOT_CONNECTED"}
        if args.preview_escpos:
            if not decision["verified"]:
                output["escpos_preview"]="BLOCKED_NO_VERIFIED_RECEIPT"
            else:
                data,meta=render_receipt(event,policy=PrintPolicy())
                DryRunPrinter(args.preview_escpos).write(data)
                output["escpos_preview"]=str(args.preview_escpos)
        if not decision["verified"]:
            print(json.dumps(output,indent=2,sort_keys=True))
            raise SystemExit(2)
    else:
        import uvicorn
        from .service import create_app
        app=create_app(db_path=args.db)
        print("Operator ingestion token (do not log/share):",app.state.operator_token,flush=True)
        uvicorn.run(app,host="127.0.0.1",port=args.port,log_level="warning",access_log=False)
        return
    print(json.dumps(output,sort_keys=True,indent=2))

if __name__=="__main__":main()
