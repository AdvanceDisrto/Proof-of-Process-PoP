"""Buddy portable runtime: discover, adapt, execute, prove, hand off."""
import time
from copy import deepcopy
from .identity import derive_from_seed, public_hex
from .discovery import probe
from .device_model import build_device_model
from .adapter import plan_for
from .execute import run_task
from .receipt import build as build_receipt, sign_approval
from .jcs import jcs, sha

class Buddy:
    def __init__(self, seed_phrase: str, state: dict | None = None):
        self.priv=derive_from_seed(seed_phrase); self.id="ed25519:"+public_hex(self.priv)
        self.state=state or {"seq":0,"last_receipt":None,"receipts":[],"lessons":[]}
    def arrive(self, device_override: dict | None=None):
        return build_device_model(probe(device_override))
    def execute_on(self, device, task, approver_priv=None):
        plan=plan_for(device, task); approval=None
        if approver_priv is not None and plan.get("feasible"):
            approval=sign_approval(approver_priv, plan["plan_hash"], self.id, self.state["seq"])
        execution=run_task(task, plan)
        knowledge={"lessons":deepcopy(self.state["lessons"]),"prior_receipt_count":len(self.state["receipts"]),
                   "chain_root":sha(jcs([r["receipt_id"] for r in self.state["receipts"]])) if self.state["receipts"] else None}
        receipt=build_receipt(self.priv,device,plan,execution,task,self.state["seq"],self.state["last_receipt"],knowledge,approval)
        self.state["seq"]+=1; self.state["last_receipt"]=receipt["receipt_id"]; self.state["receipts"].append(receipt)
        if plan.get("feasible"):
            self.state["lessons"].append({"device_class":device["class"],"precision":plan["precision"],
                "batch":plan["batch"],"output_hash_prefix":execution["output_hash"][:16] if execution.get("output_hash") else None})
        return receipt
    def handoff(self):
        return {"spec":"buddy-handoff/1.0","buddy_id":self.id,"state":self.state,
                "exported_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    @classmethod
    def from_handoff(cls,handoff,seed_phrase):
        expected="ed25519:"+public_hex(derive_from_seed(seed_phrase))
        if expected != handoff["buddy_id"]: raise ValueError(f"identity mismatch: seed produces {expected}, handoff claims {handoff['buddy_id']}")
        return cls(seed_phrase,state=handoff["state"])
