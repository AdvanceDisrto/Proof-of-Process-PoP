#!/usr/bin/env python3
import hashlib, json, secrets, time
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def jcs(o): return json.dumps(o,sort_keys=True,separators=(",",":")).encode()
def sha(b): return "sha256:"+hashlib.sha256(b).hexdigest()

class SovereignMeshNode:
    def __init__(self,node_id):
        self.node_id=node_id
        self.priv=ed25519.Ed25519PrivateKey.generate()
        self.pub=self.priv.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
    def transmit(self,payload,transport):
        intent={"node_id":self.node_id,"transport":transport,"payload_hash":sha(payload),
                "timestamp_ns":time.time_ns(),"nonce":secrets.token_hex(16)}
        return {"spec":"innovulis-mesh-receipt/1.0","intent":intent,
                "signature":self.priv.sign(jcs(intent)).hex(),"signer_pub":self.pub,
                "state":"VERIFIED_PROCESS"}

class PeerWitness:
    def __init__(self,peer_id):
        self.peer_id=peer_id
        self.priv=ed25519.Ed25519PrivateKey.generate()
        self.pub=self.priv.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
    def witness(self,receipt):
        stmt={"peer_id":self.peer_id,"observed_receipt_id":sha(jcs(receipt)),"timestamp_utc":time.time()}
        return {"witness_statement":stmt,"peer_signature":self.priv.sign(jcs(stmt)).hex(),"peer_pub":self.pub}

def merkle_root(receipts):
    layer=[sha(jcs(r)).encode() for r in receipts]
    if not layer: raise ValueError("no receipts")
    while len(layer)>1:
        nxt=[]
        for i in range(0,len(layer),2):
            left=layer[i]; right=layer[i+1] if i+1<len(layer) else left
            nxt.append(("sha256:"+hashlib.sha256(left+right).hexdigest()).encode())
        layer=nxt
    return layer[0].decode()

if __name__=="__main__":
    node=SovereignMeshNode("did:iska:node:alpha-01")
    r=node.transmit(b"iNetty packet","LoRa_868MHz")
    w1=PeerWitness("did:iska:node:peer-bravo").witness(r)
    w2=PeerWitness("did:iska:node:peer-charlie").witness(r)
    final={**r,"witnesses":[w1,w2],"state":"VERIFIED_PROCESS","physical_gate":"ACTION_REQUIRED"}
    artifact={"spec":"innovulis-sovereign-iaas/1.0","mesh_receipt":final,
              "aggregation":{"type":"Merkle demo","root":merkle_root([final])},
              "physical_gate":"ACTION_REQUIRED",
              "the_central_rule":"The receipt can record reality; it cannot manufacture reality."}
    Path("evidence").mkdir(exist_ok=True)
    Path("evidence/sovereign_mesh_receipt.json").write_text(json.dumps(artifact,indent=2))
    print(json.dumps(artifact,indent=2))
