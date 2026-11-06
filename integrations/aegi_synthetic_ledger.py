"""AeGi synthetic audit ledger. No HoTT, MMR, thermodynamic or token-settlement claim."""
import hashlib, json
from decimal import Decimal
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from z3 import Int, Solver, Not, unsat, sat

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def h(tag, x):
    return hashlib.sha256(tag.encode()+b"\0"+canonical(x)).hexdigest()

def public(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

def sign(key, body):
    return {"body":body,"public_key":public(key),"signature":key.sign(canonical(body)).hex()}

def verify(envelope, pin):
    try:
        if envelope["public_key"] != pin: return False
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pin)).verify(
            bytes.fromhex(envelope["signature"]), canonical(envelope["body"]))
        return True
    except (KeyError, TypeError, ValueError):
        return False

def merkle(leaves):
    """Domain-separated binary Merkle tree, NOT an MMR."""
    if not leaves: return hashlib.sha256(b"aegi:empty:v1").hexdigest()
    layer=[hashlib.sha256(b"aegi:leaf:v1"+bytes.fromhex(x)).digest() for x in leaves]
    while len(layer)>1:
        if len(layer)%2: layer.append(layer[-1])
        layer=[hashlib.sha256(b"aegi:node:v1"+layer[i]+layer[i+1]).digest()
               for i in range(0,len(layer),2)]
    return layer[0].hex()

def check_frequency(value_millihz):
    if type(value_millihz) is not int: raise ValueError("integer millihertz required")
    x=Int("observed_millihz")
    s=Solver(); s.add(x==value_millihz)
    s.add(Not((x>=59900)&(x<=60100)))
    outcome=s.check()
    return "PROVEN_TRUE" if outcome==unsat else "REFUTED_FALSE" if outcome==sat else "UNKNOWN"

class AeGiSyntheticLedger:
    def __init__(self):
        self.key=Ed25519PrivateKey.generate()
        self.pin=public(self.key)
        self.last_sequence={}
        self.staged=[]
        self.blocks=[]
        self.weights={}
        self.balances={}

    def register(self, name, weight):
        w=Decimal(str(weight))
        if not w.is_finite() or w<=0 or name in self.weights:
            raise ValueError("bad weight or duplicate node")
        self.weights[name]=w; self.balances[name]=Decimal(0)

    def ingest(self, frame, envelope, trusted_device_key):
        if frame.get("source_tier")!="SYNTHETIC_SIMULATOR":
            raise ValueError("real device evidence not supported")
        if not verify(envelope,trusted_device_key) or envelope["body"]!=frame:
            raise ValueError("sensor signature mismatch")
        device=frame["device_id"]; seq=frame["sequence"]
        if type(seq) is not int or seq!=self.last_sequence.get(device,0)+1:
            raise ValueError("replay or sequence gap")
        verdict=check_frequency(frame["frequency_millihz"])
        self.last_sequence[device]=seq
        if verdict!="PROVEN_TRUE":
            return {"accepted":False,"verdict":verdict}
        body={"spec":"aegi/synthetic-verified-node/v1","source_tier":"SYNTHETIC_SIMULATOR",
              "sensor_hash":h("sensor",frame),"sensor_pubkey":trusted_device_key,
              "verdict":verdict,"measured_millihz":frame["frequency_millihz"],
              "policy":"59900 <= observed_millihz <= 60100",
              "does_not_prove":["hardware authenticity","grid safety","HoTT","thermodynamic metering"]}
        receipt=sign(self.key,body);self.staged.append(receipt)
        return {"accepted":True,"verdict":verdict,"receipt":receipt}

    def mint(self,miner):
        if miner not in self.weights or not self.staged:
            raise ValueError("unknown miner or empty pool")
        if not all(verify(x,self.pin) for x in self.staged):
            raise ValueError("invalid staged signature")
        hashes=[h("receipt",x) for x in self.staged]
        body={"spec":"aegi/synthetic-block/v1","index":len(self.blocks)+1,
              "previous_block_hash":self.blocks[-1]["block_hash"] if self.blocks else "0"*64,
              "merkle_root":merkle(hashes),"receipt_hashes":hashes,
              "miner":miner,"count":len(hashes)}
        block=sign(self.key,body)
        block["block_hash"]=h("block",block)
        # Bookkeeping-only demo credits; no real tokens are minted or transferred.
        credit=Decimal("12.50")*len(hashes)*self.weights[miner]/sum(self.weights.values())
        self.balances[miner]+=credit
        block["demo_credit"]=str(credit)
        self.blocks.append(block);self.staged.clear()
        return block

def smoke():
    key=Ed25519PrivateKey.generate()
    engine=AeGiSyntheticLedger()
    engine.register("EAST",3);engine.register("WEST",1)
    good={"device_id":"DEMO-01","sequence":1,"frequency_millihz":60010,
          "source_tier":"SYNTHETIC_SIMULATOR"}
    bad={**good,"sequence":2,"frequency_millihz":54200}
    assert engine.ingest(good,sign(key,good),public(key))["accepted"]
    assert engine.ingest(bad,sign(key,bad),public(key))["verdict"]=="REFUTED_FALSE"
    block=engine.mint("EAST")
    assert verify(block,engine.pin)
    return {"status":"ACCEPT_AEGI_SYNTHETIC_LEDGER_SMOKE",
            "merkle_root":block["body"]["merkle_root"],
            "block_hash":block["block_hash"],
            "demo_credit":block["demo_credit"],
            "does_not_prove":["HoTT formalization","MMR","physics energy bounds",
                              "physical sensor","token settlement","clinical or grid safety"]}

if __name__=="__main__":
    print(json.dumps(smoke(),indent=2))
