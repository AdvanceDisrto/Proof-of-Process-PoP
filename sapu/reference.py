import hashlib,json,time
from dataclasses import dataclass
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
_FIXED_PROFILES={
"scaffold/1":{("ESTABLISHED","ATTESTED"):"MEASURED_PASS",("ESTABLISHED","UNATTESTED"):"VERIFIED_PROCESS",("OPEN","ATTESTED"):"ACTION_REQUIRED",("OPEN","UNATTESTED"):"ACTION_REQUIRED",("REFUTED","ATTESTED"):"REFUTED",("REFUTED","UNATTESTED"):"REFUTED",("CONTRADICTORY","ATTESTED"):"CONTRADICTION",("CONTRADICTORY","UNATTESTED"):"CONTRADICTION"},
"scaffold/1-strict":{("ESTABLISHED","ATTESTED"):"MEASURED_PASS",("ESTABLISHED","UNATTESTED"):"VERIFIED_PROCESS",("OPEN","ATTESTED"):"ACTION_REQUIRED",("OPEN","UNATTESTED"):"ACTION_REQUIRED",("REFUTED","ATTESTED"):"REFUTED",("REFUTED","UNATTESTED"):"REFUTED",("CONTRADICTORY","ATTESTED"):"CONTRADICTION",("CONTRADICTORY","UNATTESTED"):"CONTRADICTION"}}
_ISA_VERSION="sapu/1.0"
def _jcs(o):return json.dumps(o,sort_keys=True,separators=(",",":")).encode()
def _sha(b):return "sha256:"+hashlib.sha256(b).hexdigest()
def measurement(profile_id):
    table={f"{a}|{b}":v for (a,b),v in _FIXED_PROFILES[profile_id].items()}
    return _sha(_jcs({"isa":_ISA_VERSION,"profile":profile_id,"table":table}))
class SAPUError(Exception):pass
class SAPU:
    def __init__(self,key_path,profile_id="scaffold/1"):
        if profile_id not in _FIXED_PROFILES:raise SAPUError(f"unknown profile {profile_id}")
        self.profile_id=profile_id;self.measurement=measurement(profile_id);self._slots={"request":None,"response":None,"attestation":None};self._locked=False;self._derived=None;self._receipt_mmr=[];self._epoch_root=_sha(b"")
        p=Path(key_path)
        if p.exists():self._priv=ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(p.read_text().strip()))
        else:
            self._priv=ed25519.Ed25519PrivateKey.generate();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(self._priv.private_bytes(encoding=serialization.Encoding.Raw,format=serialization.PrivateFormat.Raw,encryption_algorithm=serialization.NoEncryption()).hex())
        self.pub=self._priv.public_key().public_bytes(encoding=serialization.Encoding.Raw,format=serialization.PublicFormat.Raw).hex()
    def admit(self,slot,blob):
        if self._locked:raise SAPUError("LOCKED — no further ADMIT")
        if slot not in self._slots:raise SAPUError(f"unknown slot {slot}")
        self._slots[slot]=blob
    def lock(self):self._locked=True
    def derive(self):
        if not self._locked:raise SAPUError("LOCK required before DERIVE")
        truth=self._truth_axis();axis=self._attestation_axis();tier=_FIXED_PROFILES[self.profile_id].get((truth,axis))
        if tier is None:raise SAPUError(f"no table row for ({truth},{axis})")
        self._derived={"truth_axis":truth,"attestation_axis":axis,"tier":tier};return self._derived
    def sign(self):
        if self._derived is None:raise SAPUError("DERIVE required before SIGN")
        body={"spec":"innovulis-sapu-receipt/1.0","issued_utc":time.time(),"sapu":{"measurement":self.measurement,"profile":self.profile_id,"isa":_ISA_VERSION},"inputs":self._canonical_inputs(),"derived":self._derived,"epoch_root_in":self._epoch_root,"issuer_pubkey":self.pub}
        return {**body,"signature":self._priv.sign(_jcs(body)).hex(),"receipt_sha256":_sha(_jcs(body))}
    def accumulate(self,receipt):
        from .mmr import MMR
        h=_sha(_jcs({k:v for k,v in receipt.items() if k!="response_text"}));self._receipt_mmr.append(h);m=MMR()
        for x in self._receipt_mmr:m.append(x.encode())
        self._epoch_root=m.root();return self._epoch_root
    def emit(self,receipt):
        self._slots={"request":None,"response":None,"attestation":None};self._locked=False;self._derived=None;return receipt
    def epoch_root(self):return self._epoch_root
    def _canonical_inputs(self):
        return {k+"_hash":(_sha(_jcs(self._slots[k])) if self._slots[k] else None) for k in ("request","response","attestation")}
    def _truth_axis(self):
        rs=self._slots["response"] or {};det=rs.get("determinism",{})
        if det.get("attempted") and det.get("matched"):return "ESTABLISHED"
        if det.get("attempted") and not det.get("matched"):return "OPEN"
        if self.profile_id.endswith("-strict"):return "OPEN"
        return "ESTABLISHED"
    def _attestation_axis(self):
        from tools.gate import physical_gate
        at=self._slots["attestation"] or {}
        return "ATTESTED" if physical_gate(at.get("tee_quote"),at.get("energy"))=="MEASURED_PASS" else "UNATTESTED"
