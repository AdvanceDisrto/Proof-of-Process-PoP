import asyncio,time,json
from dataclasses import dataclass,asdict
from core.crypto import canonical,sha,new_key,public_hex,sign,verify

@dataclass
class DomainReceipt:
    body:dict
    signature:str
    receipt_id:str

def leaf(r): return bytes.fromhex(r.receipt_id.split(":",1)[1])
def merkle(receipts):
    nodes=[sha(b"i-pop-leaf-v1:"+leaf(r)) for r in sorted(receipts,key=lambda x:x.receipt_id)]
    if not nodes:return None
    raw=[bytes.fromhex(x.split(":",1)[1]) for x in nodes]
    while len(raw)>1:
        if len(raw)%2:raw.append(raw[-1])
        raw=[bytes.fromhex(sha(b"i-pop-node-v1:"+raw[i]+raw[i+1]).split(":",1)[1]) for i in range(0,len(raw),2)]
    return "sha256:"+raw[0].hex()

class Domain:
    def __init__(self,name):self.name=name;self.key=new_key()
    async def execute(self,work):
        started=time.time_ns()
        try:
            payload=await work(); state=payload.pop("state","VERIFIED_PROCESS")
        except Exception as e:
            payload={"error_type":type(e).__name__};state="FAILED"
        body={"spec":"innovulis-parallel-domain/1.0","domain":self.name,"state":state,"payload":payload,"started_utc_ns":started,"completed_utc_ns":time.time_ns(),"signer":"ed25519:"+public_hex(self.key),"proves":["this signer attested to this domain execution result"],"does_not_prove":["picosecond physical timing","hardware independence unless separately attested"],"disclosures":["timestamps are software clock observations"]}
        return DomainReceipt(body,sign(self.key,body),sha(canonical(body)))

def verify_domain(r):
    return r.receipt_id==sha(canonical(r.body)) and verify(r.body["signer"].split(":",1)[1],r.body,r.signature)

def aggregate(receipts):
    key=new_key(); complete=all(verify_domain(r) and r.body["state"] not in ("FAILED","ACTION_REQUIRED") for r in receipts)
    body={"spec":"innovulis-parallel-pop/1.1","state":"VERIFIED_PROCESS" if complete else "INCOMPLETE","domains_count":len(receipts),"merkle_root":merkle(receipts),"domain_receipts":[asdict(r) for r in sorted(receipts,key=lambda x:x.body["domain"])],"aggregated_utc_ns":time.time_ns(),"signer":"ed25519:"+public_hex(key),"proves":["cryptographic inclusion and integrity of the listed domain receipts"],"does_not_prove":["simultaneity","picosecond physical time","physical separation of signers","truth of unverified payload claims"],"disclosures":["Merkle convergence proves set inclusion, not simultaneous physical existence."]}
    out={"body":body,"signature":sign(key,body)};out["master_receipt_id"]=sha(canonical(body));return out

async def demo():
    async def work(name): await asyncio.sleep(.01); return {"state":"VERIFIED_PROCESS","workload":name}
    rs=await asyncio.gather(*[Domain(x).execute(lambda x=x:work(x)) for x in ("SILICON","AI","ENERGY","NETWORK")])
    out=aggregate(rs);json.dump(out,open("PARALLEL_MASTER_RECEIPT.json","w"),indent=2);return out
if __name__=="__main__": print(json.dumps(asyncio.run(demo()),indent=2))
