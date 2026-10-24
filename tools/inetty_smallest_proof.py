#!/usr/bin/env python3
# Copyright 2026 AdvanceDisrto · Apache-2.0
"""Smallest cryptographic iNetty proof: two identities, witness, Merkle root.

This is an in-process transport proof. It is deliberately NOT a radio/network
measurement. physical_gate remains ACTION_REQUIRED.
"""
import hashlib,json,secrets,sys,time
from dataclasses import dataclass,field
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

def jcs(obj): return json.dumps(obj,sort_keys=True,separators=(",",":")).encode()
def sha(b): return "sha256:"+hashlib.sha256(b).hexdigest()
def derive_sovereign_ipv6(pubkey_hex):
    h=hashlib.sha256(bytes.fromhex(pubkey_hex)).digest()[:8]
    return "200:"+":".join(f"{h[i]:02x}{h[i+1]:02x}" for i in range(0,8,2))+"::1"

@dataclass
class Node:
    name:str
    priv:ed25519.Ed25519PrivateKey=field(default_factory=ed25519.Ed25519PrivateKey.generate)
    @property
    def pubkey_hex(self): return self.priv.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
    @property
    def sovereign_ipv6(self): return derive_sovereign_ipv6(self.pubkey_hex)
    def sign(self,payload): return self.priv.sign(jcs(payload)).hex()
    def identity(self): return {"name":self.name,"pubkey_hex":self.pubkey_hex,"sovereign_ipv6":self.sovereign_ipv6}

def transmit(sender,payload,transport="SIMULATED_LOCAL"):
    body={"sender":sender.identity(),"transport":transport,"payload_hash":sha(payload),"timestamp_ps":time.time_ns()*1000,"nonce":secrets.token_hex(16)}
    return {**body,"signature":sender.sign(body)}

def witness(peer,receipt):
    body={"witness":peer.identity(),"observed_receipt_id":sha(jcs({k:v for k,v in receipt.items() if k!="signature"})),"timestamp_utc":time.time()}
    return {**body,"signature":peer.sign(body)}

def merkle_root(items):
    if not items:return "sha256:"+"0"*64
    hs=[hashlib.sha256(jcs(x)).hexdigest() for x in items]
    while len(hs)>1:
        if len(hs)%2:hs.append(hs[-1])
        hs=[hashlib.sha256((hs[i]+hs[i+1]).encode()).hexdigest() for i in range(0,len(hs),2)]
    return "sha256:"+hs[0]

def verify(receipt):
    errors=[]; tr,ws=receipt["transmit"],receipt["witness"]
    try:
        pub=ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(tr["sender"]["pubkey_hex"]))
        pub.verify(bytes.fromhex(tr["signature"]),jcs({k:v for k,v in tr.items() if k!="signature"}))
    except Exception as e: errors.append(f"sender_signature:{e}")
    try:
        pub=ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(ws["witness"]["pubkey_hex"]))
        pub.verify(bytes.fromhex(ws["signature"]),jcs({k:v for k,v in ws.items() if k!="signature"}))
    except Exception as e: errors.append(f"witness_signature:{e}")
    if sha(jcs({k:v for k,v in tr.items() if k!="signature"}))!=ws["observed_receipt_id"]: errors.append("observed_receipt_id_mismatch")
    if merkle_root([tr,ws])!=receipt["merkle_root"]: errors.append("merkle_root_mismatch")
    return {"ok":not errors,"errors":errors}

def run(out_path="evidence/inetty_smallest_proof.json"):
    alice,bob=Node("alice"),Node("bob"); payload=b"HELLO FROM THE SOVEREIGN MESH"
    tr=transmit(alice,payload); ws=witness(bob,tr); root=merkle_root([tr,ws])
    receipt={"spec":"innovulis-inetty-smallest-proof/1.0","mark":"iNetty™️🧾","created_utc":time.time(),
      "transmit":tr,"witness":ws,"merkle_root":root,"transport_tier":"SIMULATED",
      "proves":["Two independent Ed25519 identities were generated.","The witness statement binds to the signed transmit receipt.","Both statements bind to one Merkle root.","The sovereign IPv6 values are deterministic derivations of public keys."],
      "does_not_prove":["Physical radio transmission.","Yggdrasil or Reticulum routing.","Token issuance or service distribution.","Untampered physical hardware."],
      "physical_gate":"ACTION_REQUIRED","the_central_rule":"The receipt can record reality; it cannot manufacture reality."}
    v=verify(receipt); receipt["verification"]=v; receipt["state"]="VERIFIED_PROCESS" if v["ok"] else "FAIL"
    Path(out_path).parent.mkdir(parents=True,exist_ok=True); Path(out_path).write_text(json.dumps(receipt,indent=2)+"\n")
    return receipt

def run_tamper_check():
    r=run("/tmp/inetty_tamper.json"); r["transmit"]["payload_hash"]=sha(b"HELLO FROM THE SOVEREIGN MESh")
    return not verify(r)["ok"]

if __name__=="__main__":
    r=run(); ok=run_tamper_check(); print(f"state={r['state']} verification={r['verification']} tamper_detected={ok} physical_gate=ACTION_REQUIRED"); sys.exit(0 if r["verification"]["ok"] and ok else 1)
