import json,os
from core.crypto import canonical,sha
class ContinuousLedger:
    def __init__(self,path="CONTINUOUS_LEDGER.jsonl"): self.path=path
    def append(self,body):
        prev=None
        if os.path.exists(self.path):
            lines=open(self.path,encoding="utf-8").read().splitlines()
            if lines: prev=json.loads(lines[-1])["node_id"]
        node={"prev":prev,"body":body}; node["node_id"]=sha(canonical(node))
        with open(self.path,"a",encoding="utf-8") as f:f.write(json.dumps(node,separators=(",",":"))+"\n")
        return node
