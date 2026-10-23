from __future__ import annotations
import hashlib,json,os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(b): return hashlib.sha256(b).digest()

class ProcessBoundData:
    def __init__(self): self.process_chain=[]
    def register_process(self,intent,actor,timestamp_ns):
        parent=self.process_chain[-1]["hash"] if self.process_chain else "GENESIS"
        link={"intent":intent,"actor":actor,"timestamp_ns":timestamp_ns,"parent_hash":parent}
        link["hash"]="sha256:"+sha(canonical(link)).hex(); self.process_chain.append(link)
    def _key(self,root_secret):
        if len(root_secret)!=32: raise ValueError("root_secret must be 32 bytes")
        info=b"innovulis-process-bound-data/v1:"+sha(canonical(self.process_chain))
        return HKDF(algorithm=hashes.SHA256(),length=32,salt=None,info=info).derive(root_secret)
    def seal_data(self,plaintext,root_secret):
        key=self._key(root_secret); nonce=os.urandom(12)
        chain=json.loads(json.dumps(self.process_chain))
        aad=canonical({"spec":"innovulis-process-bound-data/1.1","process_chain":chain})
        ct=AESGCM(key).encrypt(nonce,plaintext,aad)
        return {"spec":"innovulis-process-bound-data/1.1","ciphertext_hex":ct.hex(),"nonce_hex":nonce.hex(),"process_chain":chain}
    def unseal_data(self,sealed,root_secret):
        chain=sealed.get("process_chain")
        if not isinstance(chain,list) or not chain: raise ValueError("DEATH: missing process chain")
        parent="GENESIS"
        for link in chain:
            if link.get("parent_hash")!=parent: raise ValueError("DEATH: broken process chain")
            unsigned={k:v for k,v in link.items() if k!="hash"}
            if "hash" not in link or "sha256:"+sha(canonical(unsigned)).hex()!=link["hash"]: raise ValueError("DEATH: tampered process chain")
            parent=link["hash"]
        self.process_chain=json.loads(json.dumps(chain))
        aad=canonical({"spec":"innovulis-process-bound-data/1.1","process_chain":chain})
        try: return AESGCM(self._key(root_secret)).decrypt(bytes.fromhex(sealed["nonce_hex"]),bytes.fromhex(sealed["ciphertext_hex"]),aad)
        except Exception as exc: raise ValueError("DEATH: authenticated decryption failed") from exc
