"""iNNOVULIS Human-Centric Hub v0.1: synthetic-only, no clinical decisions."""
from __future__ import annotations
import secrets, time
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import dataclass, replace

from paper_console.codec import Event
from paper_console.store import EventStore
from paper_console.escpos import PrintPolicy, render_receipt
from paper_console.verification import IndependentReceiptGate
from innovulis_receipt.codec import canonical, encode_qr_text, decode_qr_text, sha256
from innovulis_receipt.issuer_demo import create_demo
from innovulis_receipt.crypto import merkle_root, sign, ISSUER_DOMAIN, ENGINEER_DOMAIN, WITNESS_DOMAIN, ISSUANCE_LOG_DOMAIN

class HubRejected(ValueError):
    pass

@dataclass(frozen=True)
class HubScope:
    tier: str = "SYNTHETIC_DEMO_NO_PHI"
    patient_data: str = "NOT_ACCEPTED"
    clinical_decision: str = "NOT_IMPLEMENTED"
    medical_device_certification: str = "NOT_ESTABLISHED"
    hipaa_gdpr_compliance: str = "NOT_ASSESSED"
    trust_anchor: str = "EPHEMERAL_DEMO_ANCHOR_NOT_INDEPENDENT"
    sensor: str = "SYNTHETIC_NOT_CALIBRATED"
    hardware_signer: str = "NOT_CONNECTED"
    human_licensure: str = "NOT_VERIFIED"
    physical_printer: str = "NOT_CONNECTED"
    zero_knowledge: str = "NOT_PERFORMED"

SCOPE = HubScope()

class HumanHub:
    """Local synthetic demo. The issuer, witnesses and engineer are NOT independent."""
    def __init__(self, database=":memory:"):
        self.store=EventStore(database)
    def close(self):
        self.store.close()

    @staticmethod
    def _int(value,label):
        if type(value) is not int or not -1000000 <= value <= 1000000:
            raise HubRejected(f"{label} must be a bounded demo integer")
        return value

    @staticmethod
    def _fixture(observed,limit,now):
        demo=create_demo(at_time=now,subject="demo:equipment-bench-001")
        keys=demo["_private_for_tests"]; packet=demo["packet"]; receipt=packet["receipt"]
        evidence=("SYNTHETIC BENCH TRACE - NO DEVICE ATTACHED\n"
                  f"observed={observed}\nlimit={limit}\nunit=micro_celsius_demo\n"
                  "No patient, clinician, real equipment, or physical measurement.\n").encode()
        demo["evidence"]=evidence
        manifest=[{"name":"synthetic_bench_trace.txt","sha256":sha256(evidence)}]
        receipt["evidence_manifest"]=manifest;receipt["evidence_root"]=merkle_root(manifest)
        receipt["claim"]={"kind":"integer_lte","observed":observed,"limit":limit,"unit":"micro_celsius_demo"}
        receipt["claim_sha256"]=sha256(canonical(receipt["claim"]))
        receipt["verdict"]="PROVEN_TRUE" if observed<=limit else "REFUTED_FALSE"
        receipt["nonce_hex"]=secrets.token_hex(16)
        packet["issuer_signature"]=sign(keys["issuer"],ISSUER_DOMAIN,receipt)
        packet["engineer_signature"]=sign(keys["engineer"],ENGINEER_DOMAIN,receipt)
        packet["witness_signatures"]=[
            {"id":f"witness-demo-{i+1:02d}","signature":sign(keys["witnesses"][i],WITNESS_DOMAIN,receipt)}
            for i in range(3)]
        rec_hash=sha256(canonical(receipt))
        checkpoint=demo["issuance_log"]["checkpoint"]
        checkpoint["entries"]=[rec_hash]
        checkpoint["merkle_root"]=merkle_root([{"receipt_sha256":rec_hash}])
        demo["issuance_log"]["signature"]=sign(keys["log_authority"],ISSUANCE_LOG_DOMAIN,checkpoint)
        return demo

    def create_synthetic_receipt(self,*,observed=45000,limit=50000,explicit_demo_consent=False,now=None):
        if explicit_demo_consent is not True:raise HubRejected("explicit demonstration acknowledgment required")
        observed=self._int(observed,"observed");limit=self._int(limit,"limit")
        now=int(time.time()) if now is None else now
        if type(now) is not int or now<1700000000 or now>4100000000:
            raise HubRejected("invalid fixture timestamp")
        demo=self._fixture(observed,limit,now)
        packet=demo["packet"];carrier=encode_qr_text(packet)
        with TemporaryDirectory(prefix="innovulis-hub-demo-") as td:
            Path(td,"synthetic_bench_trace.txt").write_bytes(demo["evidence"])
            gate=IndependentReceiptGate(
                trust=demo["trust"],revocations=demo["revocations"],
                issuance_log=demo["issuance_log"],independently_pinned_anchor_sha256=demo["trust_sha256"],
                expected_subject=packet["receipt"]["subject"],evidence_dir=td)
            event,decision=gate.check(packet,now=now,carrier=carrier)
        if not decision["verified"] or decision["code"]!="VERIFIED_DIGITAL_RECEIPT":
            raise HubRejected("synthetic evidence/signature verification failed")
        expected="PROVEN_TRUE" if observed<=limit else "REFUTED_FALSE"
        if event.claim_verdict!=expected:raise HubRejected("verdict mismatch")
        event=replace(event,details={**event.details,
            "demonstration":True,"clinical_use":"PROHIBITED",
            "trust_provisioning":"EPHEMERAL_SELF_PINNED_WITHIN_DEMO",
            "sensor_source":"SYNTHETIC","has_real_witness_operators":False})
        saved=self.store.append(event)
        return {"event_id":event.event_id,"journal_event_hash":saved["event_hash"],
                "issuer_claim":event.claim_verdict,
                "digital_receipt_authentic_under_synthetic_anchor":True,
                "independent_real_world_verification":False,
                "scope":SCOPE.__dict__,"receipt_sha256":event.receipt_sha256,
                "qr_bytes":len(carrier.encode("ascii"))}

    def get_event(self,event_id):
        event=self.store.get_event(event_id)
        if event is None:raise HubRejected("unknown event")
        return event

    def read_feed(self):
        rows=self.store.latest(100);safe=[]
        for row in rows:
            row.pop("carrier",None)
            if row.get("details",{}).get("demonstration") is True:safe.append(row)
        return {"scope":SCOPE.__dict__,"events":safe,"journal":self.store.integrity()}

    def render_qr_png(self,event_id):
        event=self.get_event(event_id)
        if event.details.get("demonstration") is not True or not event.carrier:
            raise HubRejected("no signed demo carrier")
        from innovulis_receipt.carrier import make_png
        with TemporaryDirectory(prefix="hub-qr-") as d:
            path=Path(d,"receipt.png")
            make_png(decode_qr_text(event.carrier),path,box_size=6)
            return path.read_bytes()

    def print_preview_bytes(self,event_id):
        event=self.get_event(event_id)
        if event.details.get("demonstration") is not True:
            raise HubRejected("not a demo event")
        data,meta=render_receipt(event,policy=PrintPolicy(),include_qr=True)
        assert meta["is_real_printer"] is False
        banner=(b"\n*** SYNTHETIC DEMO ONLY ***\n"
                b"NO PATIENT DATA / NO CLINICAL PROOF\n"
                b"NO REAL DEVICE OR TRUSTED WITNESS\n\n")
        return data[:2]+banner+data[2:]

    def acknowledge_review(self,event_id,*,confirm_scope=False):
        if confirm_scope is not True:raise HubRejected("explicit demo acknowledgment required")
        event=self.get_event(event_id)
        if event.details.get("demonstration") is not True or event.verification!="VERIFIED_DIGITAL_RECEIPT":
            raise HubRejected("valid synthetic demo receipt required")
        review=Event(event_id="demo-human-review:"+secrets.token_hex(12),
            occurred_at=int(time.time()),track="claim",subject="demo:human-review",
            claim_verdict="NOT_APPLICABLE",verification="NOT_CHECKED",
            details={"demonstration":True,"review_of":event_id,
                     "result":"HUMAN_ACKNOWLEDGED_READING_ONLY",
                     "medical_decision":"NOT_PERFORMED","professional_credentials":"NOT_VERIFIED"},
            source_tier="DEMO")
        saved=self.store.append(review)
        return {"review_event_hash":saved["event_hash"],
                "scope":"HUMAN_ACKNOWLEDGED_READING_ONLY",
                "is_professional_medical_approval":False,
                "human_identity_independently_verified":False}
