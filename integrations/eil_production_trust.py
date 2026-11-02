"""Fail-closed iRECEIPT EiL production trust verifier.
External pins only: no genesis/key generation or network mutation. Not RFC8785 JCS.
"""
from __future__ import annotations
import hashlib,json,pathlib,re,subprocess,sqlite3
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

def canonical(x):return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def digest(x):return "sha256:"+hashlib.sha256(x).hexdigest()
def is_hash(x):return isinstance(x,str) and bool(re.fullmatch(r"sha256:[0-9a-f]{64}",x))
def verify_sig(body,signature,pubkey):
    try:
        if not re.fullmatch(r"[0-9a-f]{128}",signature) or not re.fullmatch(r"[0-9a-f]{64}",pubkey):return False
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pubkey)).verify(bytes.fromhex(signature),canonical(body))
        return True
    except (ValueError,TypeError,InvalidSignature):return False

class ProductionGate:
    def __init__(self,root_file,policy_file,root_pin,policy_pin):
        self.root_file=root_file;self.policy_file=policy_file;self.root_pin=root_pin;self.policy_pin=policy_pin
    def authority(self):
        for name,path,pin in (("ROOT",self.root_file,self.root_pin),("POLICY",self.policy_file,self.policy_pin)):
            if not is_hash(pin):raise ValueError(name+"_PIN_MISSING")
            if digest(pathlib.Path(path).read_bytes())!=pin:raise ValueError(name+"_PIN_MISMATCH")
        root=json.loads(pathlib.Path(self.root_file).read_bytes())
        policy=json.loads(pathlib.Path(self.policy_file).read_bytes())
        if policy.get("schema")!="ipqr/production-trust-policy/v1" or policy.get("enabled") is not True:raise ValueError("POLICY_DISABLED")
        if policy.get("root_sha256")!=self.root_pin or policy.get("root_issuer_pub_hex")!=root.get("issuer_pub_hex"):raise ValueError("AUTHORITY_MISMATCH")
        roles=("requester","executor","verifier","policy_gate","inference_witness","printer_witness","bitcoin_witness")
        keys=policy.get("role_pubkeys")
        if not isinstance(keys,dict) or any(not isinstance(keys.get(r),str) or not re.fullmatch("[0-9a-f]{64}",keys[r]) for r in roles):raise ValueError("INVALID_ROLE_KEYS")
        if len(set(keys[r] for r in roles))!=len(roles):raise ValueError("NONINDEPENDENT_KEYS")
        if not isinstance(policy.get("min_bitcoin_confirmations"),int) or policy["min_bitcoin_confirmations"]<1:raise ValueError("BTC_POLICY_INVALID")
        return policy
    def assess(self,graph,witnesses,bitcoin_lookup=None):
        try:
            policy=self.authority()
            if not isinstance(graph,list) or len(graph)!=4:raise ValueError("GRAPH_LENGTH")
            prev=None
            for i,(stage,role) in enumerate(zip(("INTENT","EXECUTION","VERIFICATION","TRANSITION"),("requester","executor","verifier","policy_gate"))):
                node=graph[i];body=node["payload"];sig=node["signature"];key=policy["role_pubkeys"][role]
                if body.get("schema")!="ipqr/eil-node/v1" or body.get("stage")!=stage or body.get("previous")!=prev:raise ValueError("CHAIN_STAGE_LINK")
                prev=digest(canonical(body))
                if node.get("hash")!=prev or sig.get("role")!=role or sig.get("public_key")!=key or not verify_sig(body,sig["hex"],key):raise ValueError("SIGNATURE_OR_HASH")
            intent,execution,verification,transition=(n["payload"] for n in graph)
            if intent.get("authorized_operation") not in policy.get("allowed_operations",[]):raise ValueError("OPERATION_NOT_ALLOWED")
            if execution.get("operation")!=intent.get("task") or execution.get("operation")!=intent.get("authorized_operation"):raise ValueError("EXECUTION_NOT_AUTHORIZED")
            if verification.get("passed") is not True or transition.get("decision")!="ALLOW":raise ValueError("VERIFICATION_DENIED")
            if transition.get("scope") not in policy.get("allowed_transition_scopes",[]):raise ValueError("TRANSITION_SCOPE")
            if not isinstance(witnesses,dict):raise ValueError("WITNESSES_MISSING")
            tip=graph[-1]["hash"]
            for kind in ("inference","printer","bitcoin"):
                w=witnesses[kind];body=w["body"]
                if body.get("schema")!="ipqr/eil-witness/v1" or body.get("kind")!=kind or body.get("graph_tip")!=tip:raise ValueError("WITNESS_BINDING")
                if not verify_sig(body,w["signature_hex"],policy["role_pubkeys"][kind+"_witness"]):raise ValueError("WITNESS_SIGNATURE")
            infer=witnesses["inference"]["body"]
            if infer.get("observed") is not True or not is_hash(infer.get("output_hash")) or infer.get("operation")!=execution["operation"]:raise ValueError("INFERENCE_WITNESS")
            printer=witnesses["printer"]["body"]
            if printer.get("observed") is not True or printer.get("printed_graph_tip")!=tip:raise ValueError("PRINTER_WITNESS")
            btc=witnesses["bitcoin"]["body"]
            if btc.get("observed") is not True or btc.get("network")!="mainnet" or btc.get("commitment")!=tip or not re.fullmatch("[0-9a-f]{64}",str(btc.get("txid"))):raise ValueError("BTC_WITNESS")
            if bitcoin_lookup is None:raise ValueError("BTC_INDEPENDENT_NODE_REQUIRED")
            result=bitcoin_lookup(btc["txid"])
            if result.get("network")!="mainnet" or tip not in result.get("commitments",[]) or result.get("confirmations",0)<policy["min_bitcoin_confirmations"]:raise ValueError("BTC_NOT_CONFIRMED")
            return {"verdict":"ACCEPT","scope":"POLICY_AND_WITNESS_SIGNATURES_ONLY","root_pin":self.root_pin,"graph_tip":tip}
        except (OSError,ValueError,TypeError,KeyError,IndexError,InvalidSignature) as e:
            return {"verdict":"BLOCKED","reason":str(e) or type(e).__name__,"production_trust":"UNVERIFIED"}

def bitcoin_core_readonly_lookup(txid,bitcoin_cli="bitcoin-cli"):
    """Read-only MAINNET Bitcoin Core RPC. Never sign or broadcast."""
    if not isinstance(txid,str) or not re.fullmatch("[0-9a-f]{64}",txid):raise ValueError("BAD_TXID")
    def rpc(*args):return json.loads(subprocess.run([bitcoin_cli,*args],capture_output=True,text=True,check=True,timeout=15).stdout)
    if rpc("getblockchaininfo").get("chain")!="main":raise ValueError("NOT_MAINNET")
    tx=rpc("getrawtransaction",txid,"true")
    if tx.get("txid")!=txid or not tx.get("blockhash"):raise ValueError("TX_NOT_CONFIRMED")
    conf=rpc("getblockheader",tx["blockhash"],"true").get("confirmations",0)
    if not isinstance(conf,int) or conf<1:raise ValueError("BLOCK_NOT_ACTIVE")
    commitments=[]
    for v in tx.get("vout",[]):
        s=v.get("scriptPubKey",{}).get("hex","").lower()
        if re.fullmatch("6a20[0-9a-f]{64}",s):commitments.append("sha256:"+s[4:])
        if re.fullmatch("6a4c20[0-9a-f]{64}",s):commitments.append("sha256:"+s[6:])
    return {"network":"mainnet","confirmations":conf,"commitments":commitments}

class AppendOnlyLedger:
    """Application-level append-only API. SQLite files are not immutable or independently anchored."""
    def __init__(self,path):
        self.conn=sqlite3.connect(path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS receipts(seq INTEGER PRIMARY KEY,prev TEXT,body BLOB NOT NULL,entry_hash TEXT UNIQUE NOT NULL)")
    def append(self,record):
        raw=canonical(record)
        with self.conn:
            row=self.conn.execute("SELECT entry_hash FROM receipts ORDER BY seq DESC LIMIT 1").fetchone()
            prev=row[0] if row else None
            h=digest(canonical({"prev":prev,"record_hash":digest(raw)}))
            self.conn.execute("INSERT INTO receipts(prev,body,entry_hash) VALUES(?,?,?)",(prev,raw,h))
        return h
    def verify(self):
        prev=None
        for previous,raw,h in self.conn.execute("SELECT prev,body,entry_hash FROM receipts ORDER BY seq"):
            if previous!=prev or digest(canonical({"prev":prev,"record_hash":digest(raw)}))!=h:return False
            prev=h
        return True
