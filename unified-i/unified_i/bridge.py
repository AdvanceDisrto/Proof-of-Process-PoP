"""Real cross-module smoke: Human Hub -> open verifier -> SQLite -> QR -> print
preview -> Twinions -> bounded sovereign acceptance.

This is fully synthetic and NEVER sends a job to physical equipment.
"""
from __future__ import annotations
import json
import time
import secrets
from pathlib import Path
from PIL import Image
from cryptography.hazmat.primitives.asymmetric import ed25519
from .codec import ClaimRecord, sha256, canonical
from .signing import sign,verify,public_hex
from .physical import record_report,assert_no_upgrade
from .arbiter import twinions_compare,bounded_integer_verdict,audit_free_text


def run_synthetic_closed_loop(out_dir:str|Path,*,now:int|None=None)->dict:
    from human_hub.core import HumanHub
    from innovulis_receipt.codec import decode_qr_text
    from pyzbar.pyzbar import decode
    from ipcih import Issuer,verify as verify_capsule,encode_wire,decode_wire,render_dual,decode_exact_color

    now=int(time.time()) if now is None else now
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    hub=HumanHub(out/("demo_event_journal_"+secrets.token_hex(6)+".sqlite3"))
    try:
        good=hub.create_synthetic_receipt(observed=25000,limit=40000,explicit_demo_consent=True,now=now)
        bad=hub.create_synthetic_receipt(observed=45000,limit=40000,explicit_demo_consent=True,now=now)
        assert good["issuer_claim"]=="PROVEN_TRUE"
        assert bad["issuer_claim"]=="REFUTED_FALSE"
        good_event=hub.get_event(good["event_id"])
        png=hub.render_qr_png(good["event_id"])
        (out/"signed_ipqr_synthetic.png").write_bytes(png)
        codes=decode(Image.open(out/"signed_ipqr_synthetic.png"))
        if len(codes)!=1 or codes[0].data.decode()!=good_event.carrier:
            raise RuntimeError("actual QR pixels did not decode the exact signed carrier")
        if decode_qr_text(good_event.carrier)["receipt"]["subject"]!="demo:equipment-bench-001":
            raise RuntimeError("receipt subject binding broken")
        escrow=hub.print_preview_bytes(good["event_id"])
        if not escrow.startswith(b"\x1b@") or len(escrow)<1000:
            raise RuntimeError("ESC/POS preview missing")
        (out/"synthetic_unprinted.escpos").write_bytes(escrow)
        ack=hub.acknowledge_review(good["event_id"],confirm_scope=True)
        if ack["is_professional_medical_approval"]:raise RuntimeError("improper medical approval")
        journal=hub.store.integrity()
        if not journal["chain_ok"] or journal["checked"]!=3:
            raise RuntimeError("journal tampering or untracked event")
    finally:
        hub.close()

    signer=ed25519.Ed25519PrivateKey.generate()
    claim=ClaimRecord(event_id="synthetic:unified-001",subject="demo:equipment-bench-001",
        assertion_kind="INTEGER_LTE",verdict="PASS_BOUNDED_CLAIM",source_tier="SYNTHETIC",
        evidence_sha256=sha256(b"SYNTHETIC ONLY"),issuer_key_id="synthetic-demo-key",
        sequence=1,issued_at=now,expires_at=now+120,
        limitations=("synthetic data", "software key", "no authenticated physical measurement"),
        observed_micro_units=25000,maximum_micro_units=40000)
    unified=sign(claim,signer)
    anchor=public_hex(signer)  # demo self-pin, MUST be an independent trust distribution in production
    verified=verify(unified,pinned_public_key_hex=anchor,pinned_key_id="synthetic-demo-key",
                    now=now,expected_subject="demo:equipment-bench-001")
    if verified.verdict!="PASS_BOUNDED_CLAIM":raise RuntimeError("unified receipt mismatch")

    issuer=Issuer(ed25519.Ed25519PrivateKey.generate())
    capsule=issuer.issue("Synthetic i™ Hub",now=now)
    cap_verified=verify_capsule(decode_wire(encode_wire(capsule)),issuer.public_raw(),now=now+1)
    color=render_dual(encode_wire(capsule));color.save(out/"imorphus_exact_pixels.png")
    if decode_exact_color(color)!=encode_wire(capsule):
        raise RuntimeError("exact pixel color decode mismatch")
    conflict=twinions_compare([
        {"source":"Model A synthetic","question_id":"diagnosis","answer":"benign"},
        {"source":"Model B synthetic","question_id":"diagnosis","answer":"malignant"}])
    if conflict["factual_verdict"]!="UNDETERMINED":raise RuntimeError("spurious clinical certainty")
    gate=record_report();assert_no_upgrade(gate)
    result={
        "schema":"i-unified-software-acceptance/v1",
        "synthetic_signed_ipqr":"PIXEL_DECODE_AND_LOCAL_DEMO_ANCHOR_VERIFIED",
        "signed_ipqr_sha256":good["receipt_sha256"],
        "false_claim_receipt":"AUTHENTIC_REFUTED_BOUNDED_DEMO",
        "escpos":"BYTES_RENDERED_NOT_PHYSICALLY_PRINTED",
        "bytes_written_to_preview":len(escrow),
        "human":"READ_ACKNOWLEDGED_NOT_CERTIFIED",
        "sqlite_journal":journal,
        "independent_unified_signature":"VERIFIED_WITH_EXPLICIT_SYNTHETIC_PIN",
        "ipcih_app":"SIGNED_TEMPLATE_VERIFIED_NOT_IN_BROWSER",
        "imorphus":"EXACT_PIXEL_ONLY_NOT_CAMERA_RESILIENT",
        "twinions":conflict["status"],"twinions_factual_truth":"UNDETERMINED",
        "physically_measured_joules":None,
        "root_of_trust":"EPHEMERAL_SOFTWARE_NOT_HARDWARE",
        "independent_witnesses":False,
        "hardware_gates":gate,
        "does_not_prove":["real hardware", "clinical correctness", "legal claims", "physical printing", "manufacturability", "independent witnesses"]}
    (out/"acceptance.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    (out/"unified_signed_claim.json").write_text(json.dumps(unified,indent=2,sort_keys=True)+"\n")
    (out/"DEMO_PUBLIC_PIN_NOT_EXTERNAL.txt").write_text(anchor+"\n")
    return result
