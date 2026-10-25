"""Verify receipts and their complete provenance chain."""
from cryptography.hazmat.primitives.asymmetric import ed25519
from .jcs import jcs, sha

def verify_receipt(rec: dict) -> dict:
    errors = []
    body_no_sig = {k:v for k,v in rec.items() if k != "signature"}
    expected_id = sha(jcs({k:v for k,v in body_no_sig.items() if k != "receipt_id"}))
    if rec.get("receipt_id") != expected_id: errors.append("receipt_id mismatch")
    try:
        pub = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(rec["buddy_id"].split(":")[-1]))
        pub.verify(bytes.fromhex(rec["signature"]), jcs(body_no_sig))
    except Exception as e: errors.append(f"buddy signature: {e}")
    if rec.get("approval"):
        try:
            appr=rec["approval"]; pub=ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(appr["approver_id"].split(":")[-1]))
            pub.verify(bytes.fromhex(appr["signature"]), jcs(appr["signed_body"]))
            if appr["signed_body"]["plan_hash"] != rec["plan"].get("plan_hash"): errors.append("approval plan mismatch")
            if appr["signed_body"]["buddy_id"] != rec["buddy_id"]: errors.append("approval buddy mismatch")
        except Exception as e: errors.append(f"approval signature: {e}")
    for name in ("proves","does_not_prove","disclosures"):
        if not rec.get(name): errors.append(f"{name} empty")
    return {"ok": not errors, "errors": errors}

def verify_chain(receipts: list[dict]) -> dict:
    errors=[]; prev=None; seq=0; buddy_id=None
    for i,rec in enumerate(receipts):
        v=verify_receipt(rec)
        if not v["ok"]: errors.extend([f"receipt[{i}]: {e}" for e in v["errors"]])
        if buddy_id is None: buddy_id=rec["buddy_id"]
        elif rec["buddy_id"] != buddy_id: errors.append(f"receipt[{i}]: buddy_id changed")
        if rec["seq"] != seq: errors.append(f"receipt[{i}]: seq {rec['seq']} != {seq}")
        if rec["prev_receipt"] != prev: errors.append(f"receipt[{i}]: prev_receipt mismatch")
        prev, seq = rec["receipt_id"], seq+1
    return {"ok": not errors, "errors": errors}
