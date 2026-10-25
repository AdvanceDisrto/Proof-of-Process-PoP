"""Signed receipt binding identity, device, plan, execution, and provenance."""
import time
from .identity import public_hex
from .jcs import jcs, sha

def build(buddy_priv, device, plan, execution, task, seq, prev_receipt, knowledge, approval=None):
    body = {
        "spec": "buddy-receipt/1.0", "buddy_id": "ed25519:" + public_hex(buddy_priv),
        "seq": seq, "prev_receipt": prev_receipt,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "device": device, "plan": plan, "task": task, "execution": execution,
        "approval": approval, "knowledge": knowledge,
        "proves": [
            "this receipt was signed by the same buddy_id as its predecessors",
            "the device model was built from local probes or explicitly disclosed simulation",
            "the plan was derived deterministically from the device model",
            "execution.output_hash matches the recomputed output",
            "plan.plan_hash recomputes from the plan fields",
        ],
        "does_not_prove": [
            "that device discovery is exhaustive",
            "that the plan is optimal",
            "that the output is intelligent — it is a deterministic dot product",
            "that the same plan would be chosen on a different equivalent device",
            "that knowledge accumulates semantically",
            "physical execution beyond software evidence without hardware attestation",
        ],
        "disclosures": [
            "device probes are best-effort and may be incomplete",
            "if device.runtime.simulated is true, the demo overrode the probe",
            "the seed phrase controls the buddy; anyone with the seed controls it",
        ],
    }
    if approval is None:
        body["disclosures"].append("no human approval was attached — this execution was unapproved")
    body["receipt_id"] = sha(jcs(body))
    body["signature"] = buddy_priv.sign(jcs(body)).hex()
    return body

def sign_approval(approver_priv, plan_hash: str, buddy_id: str, seq: int) -> dict:
    body = {"plan_hash": plan_hash, "buddy_id": buddy_id, "seq": seq}
    return {"approver_id": "ed25519:" + public_hex(approver_priv),
            "signed_body": body, "signature": approver_priv.sign(jcs(body)).hex()}
