#!/usr/bin/env python3
# Copyright 2026 AdvanceDisrto · Apache-2.0
"""Buddy signed liveness beacon and witness proof.

T0.5 is loopback/single-host. T1 is a witnessed LAN UDP exchange between
distinct source IPs. The cryptographic receipt is transport-independent.
Physical hardware/TEE truth remains ACTION_REQUIRED.
"""
import argparse, hashlib, json, os, secrets, socket, sys, threading, time
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

BEACON_PORT=9123
ACK_PORT=9124
BUDDY_KEY=Path("evidence/buddy_key.pem")

def jcs(obj): return json.dumps(obj,sort_keys=True,separators=(",",":")).encode()
def sha(b): return "sha256:"+hashlib.sha256(b).hexdigest()

def pubkey_hex(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()

def load_or_create_buddy_key():
    if BUDDY_KEY.exists():
        return ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(BUDDY_KEY.read_text().strip()))
    key=ed25519.Ed25519PrivateKey.generate()
    BUDDY_KEY.parent.mkdir(parents=True,exist_ok=True)
    BUDDY_KEY.write_text(key.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption()).hex())
    try: os.chmod(BUDDY_KEY,0o600)
    except OSError: pass
    return key

def make_beacon(key,response,model):
    body={"spec":"buddy-liveness/1.0","buddy":pubkey_hex(key)[:16],"model":model,
          "resp":sha(response.encode()),"nonce":secrets.token_hex(8),"ts_ps":time.time_ns()*1000}
    return {"body":body,"sig":key.sign(jcs(body)).hex(),"pub_full":pubkey_hex(key)}

def verify_beacon(beacon):
    try:
        pub=ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(beacon["pub_full"]))
        if beacon["body"]["buddy"] != beacon["pub_full"][:16]: return False
        pub.verify(bytes.fromhex(beacon["sig"]),jcs(beacon["body"]))
        return True
    except Exception: return False

def make_ack(key,beacon):
    body={"spec":"buddy-witness/1.0","witness":pubkey_hex(key)[:16],
          "observed":sha(jcs(beacon)),"ts_utc":time.time()}
    return {"body":body,"sig":key.sign(jcs(body)).hex(),"pub_full":pubkey_hex(key)}

def verify_ack(ack):
    try:
        pub=ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(ack["pub_full"]))
        if ack["body"]["witness"] != ack["pub_full"][:16]: return False
        pub.verify(bytes.fromhex(ack["sig"]),jcs(ack["body"]))
        return True
    except Exception: return False

def merkle_root(items):
    if not items: return "sha256:"+"0"*64
    hashes=[hashlib.sha256(jcs(x)).hexdigest() for x in items]
    while len(hashes)>1:
        if len(hashes)%2: hashes.append(hashes[-1])
        hashes=[hashlib.sha256((hashes[i]+hashes[i+1]).encode()).hexdigest() for i in range(0,len(hashes),2)]
    return "sha256:"+hashes[0]

def my_ips():
    ips={"127.0.0.1"}
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(("8.8.8.8",80))
        ips.add(s.getsockname()[0]); s.close()
    except OSError: pass
    return ips

def classify_tier(beacon_src_ip,ack_src_ip,self_ips):
    if beacon_src_ip in self_ips and ack_src_ip in self_ips: return "T0.5"
    if beacon_src_ip != ack_src_ip: return "T1"
    return "T0.5"

def verify_receipt(receipt):
    errors=[]
    try:
        if not verify_beacon(receipt["beacon"]): errors.append("beacon_signature_invalid")
        if not verify_ack(receipt["witness_ack"]): errors.append("witness_signature_invalid")
        if receipt["witness_ack"]["body"]["observed"] != sha(jcs(receipt["beacon"])): errors.append("observed_hash_mismatch")
        if merkle_root([receipt["beacon"],receipt["witness_ack"]]) != receipt["merkle_root"]: errors.append("merkle_root_mismatch")
    except (KeyError,TypeError,ValueError): errors.append("receipt_structure_invalid")
    return {"ok":not errors,"errors":errors}

def run_self_test(out_path="evidence/buddy_self_test.json"):
    bk,wk=ed25519.Ed25519PrivateKey.generate(),ed25519.Ed25519PrivateKey.generate()
    b=make_beacon(bk,"hello from the self-test","self-test-model"); a=make_ack(wk,b)
    r={"spec":"buddy-liveness-receipt/1.0","signal_tier":"T0.5","signal_transport":"loopback UDP (self-test; no physical radio)",
       "beacon":b,"witness_ack":a,"merkle_root":merkle_root([b,a]),"access_tier":"FREE_PUBLIC_BOOTSTRAP",
       "physical_gate":"ACTION_REQUIRED"}
    v=verify_receipt(r); r["verification"]=v; r["state"]="VERIFIED_PROCESS" if v["ok"] else "FAIL"
    tampered=json.loads(json.dumps(r)); tampered["beacon"]["body"]["resp"]=sha(b"different")
    tamper_ok=not verify_receipt(tampered)["ok"]
    Path(out_path).parent.mkdir(parents=True,exist_ok=True); Path(out_path).write_text(json.dumps(r,indent=2)+"\n")
    print(f"[Buddy self-test] state={r['state']} tamper_detected={tamper_ok} physical_gate=ACTION_REQUIRED")
    return 0 if v["ok"] and tamper_ok else 1

def run_buddy(response,model,timeout,out_path):
    key=load_or_create_buddy_key(); beacon=make_beacon(key,response,model)
    holder={}
    def listen():
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        s.bind(("",ACK_PORT)); s.settimeout(timeout)
        try:
            data,addr=s.recvfrom(65536); holder["ack"]=json.loads(data); holder["ack_from"]=addr[0]
        except socket.timeout: pass
        finally: s.close()
    t=threading.Thread(target=listen,daemon=True); t.start(); time.sleep(0.1)
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP); s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
    for target in ("255.255.255.255","127.0.0.1"):
        try: s.sendto(jcs(beacon),(target,BEACON_PORT))
        except OSError: pass
    s.close(); t.join(timeout+0.5)
    if "ack" not in holder: print("[Buddy] no witness reply"); return 1
    ack=holder["ack"]
    if not verify_ack(ack) or ack["body"]["observed"] != sha(jcs(beacon)): print("[Buddy] invalid witness"); return 1
    tier="T1" if holder["ack_from"] not in my_ips() else "T0.5"
    receipt={"spec":"buddy-liveness-receipt/1.0","mark":"iNetty™️🧾 · Buddy","created_utc":time.time(),
      "signal_tier":tier,"signal_transport":"UDP broadcast over LAN Wi-Fi" if tier=="T1" else "loopback UDP",
      "beacon":beacon,"witness_ack":ack,"merkle_root":merkle_root([beacon,ack]),
      "access_tier":"FREE_PUBLIC_BOOTSTRAP",
      "proves":["Buddy signed a response commitment.","A witness signed the beacon hash.","Both statements bind to one Merkle root."],
      "does_not_prove":["AI truthfulness.","Untampered radio hardware.","TEE-backed physical identity.","Any cellular or LoRa transport."],
      "physical_gate":"ACTION_REQUIRED","the_central_rule":"The receipt can record reality; it cannot manufacture reality."}
    v=verify_receipt(receipt); receipt["verification"]=v; receipt["state"]="VERIFIED_PROCESS" if v["ok"] else "FAIL"
    Path(out_path).parent.mkdir(parents=True,exist_ok=True); Path(out_path).write_text(json.dumps(receipt,indent=2)+"\n")
    print(f"[Buddy] witness={holder['ack_from']} tier={tier} root={receipt['merkle_root']} state={receipt['state']}")
    return 0 if v["ok"] else 1

def run_witness(timeout):
    key=ed25519.Ed25519PrivateKey.generate(); s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(("",BEACON_PORT)); s.settimeout(timeout)
    try: data,addr=s.recvfrom(65536)
    except socket.timeout: print("[Witness] timeout"); return 1
    finally: s.close()
    beacon=json.loads(data)
    if not verify_beacon(beacon): print("[Witness] invalid beacon"); return 1
    out=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); out.sendto(jcs(make_ack(key,beacon)),(addr[0],ACK_PORT)); out.close()
    print(f"[Witness] verified beacon from {addr[0]} and sent signed ack"); return 0

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="mode",required=True)
    b=sub.add_parser("buddy"); b.add_argument("--text",required=True); b.add_argument("--model",default="unnamed-model"); b.add_argument("--timeout",type=float,default=15); b.add_argument("--out",default="evidence/buddy_live.json")
    w=sub.add_parser("witness"); w.add_argument("--timeout",type=float,default=30)
    v=sub.add_parser("verify"); v.add_argument("file"); sub.add_parser("self-test")
    a=p.parse_args()
    if a.mode=="buddy": return run_buddy(a.text,a.model,a.timeout,a.out)
    if a.mode=="witness": return run_witness(a.timeout)
    if a.mode=="verify":
        r=verify_receipt(json.loads(Path(a.file).read_text())); print(json.dumps(r,indent=2)); return 0 if r["ok"] else 1
    return run_self_test()
if __name__=="__main__": sys.exit(main())
