import json
from dataclasses import dataclass
from tools.mmr import MMR,jcs,sha
@dataclass
class Node:
    node_id:str
    parent_id:str|None
    kind:str
    payload:dict
class CognitiveGraph:
    def __init__(self,root_hash): self.root_hash=root_hash; self.nodes=[]
    def add_raw_node(self,node_id,parent_id,kind,payload): self.nodes.append(Node(node_id,parent_id,kind,payload))
    def _validate(self,n):
        e=[]
        if n.parent_id and not any(x.node_id==n.parent_id for x in self.nodes): e.append("missing_parent")
        if isinstance(n.payload,dict) and n.payload.get("physical_gate")=="MEASURED_PASS": e.append("unverified_measured_pass")
        return e
    def to_receipt(self):
        m=MMR();out=[]
        for n in self.nodes:
            e=self._validate(n);st="VERIFIED_PROCESS" if not e else "REFUTED"
            out.append({"node_id":n.node_id,"parent_id":n.parent_id,"kind":n.kind,"status":st,"physical_gate":"ACTION_REQUIRED","payload_sha256":sha(jcs(n.payload)),"errors":e})
            m.append(jcs({"node_id":n.node_id,"parent_id":n.parent_id,"kind":n.kind,"payload":n.payload,"status":st,"errors":e}))
        return {"spec":"innovulis-pop-graph/1.0","root_hash":self.root_hash,"node_count":len(out),"verified_count":sum(x["status"]=="VERIFIED_PROCESS" for x in out),"pruned_count":sum(bool(x["errors"]) for x in out),"nodes":out,"registry_root":m.root(),"physical_gate":"ACTION_REQUIRED"}
