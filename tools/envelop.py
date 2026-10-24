"""Signed, manifest-bound Innovulis Envelop with receiver-side gate derivation."""
import hashlib, json, time
from dataclasses import dataclass
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from tools.mmr_pipeline import MerkleMountainRange
from tools.gate import physical_gate

def jcs(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()

def sha(b):
    return "sha256:" + hashlib.sha256(b).hexdigest()

@dataclass
class Content:
    path: str
    kind: str
    data: bytes

def _leaf(e):
    return jcs({"path": e["path"], "kind": e["kind"], "sha256": e["sha256"], "size": e["size"]})

class Envelop:
    def __init__(self, priv):
        self._priv = priv
        self.pub = priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex()

    @staticmethod
    def keypair():
        return ed25519.Ed25519PrivateKey.generate()

    def seal(self, contents, *, purpose, to_label=None, tee_quote=None, energy=None):
        entries, mmr = [], MerkleMountainRange()
        for c in contents:
            e = {"path": c.path, "kind": c.kind, "sha256": sha(c.data), "size": len(c.data)}
            entries.append(e)
            mmr.append(_leaf(e))
        gate = physical_gate(tee_quote, energy)
        body = {
            "spec": "innovulis-envelop/1.0",
            "created_utc": time.time(),
            "from": self.pub,
            "to": to_label,
            "purpose": purpose,
            "contents": entries,
            "manifest_mmr_root": mmr.root(),
            "attestations": {"tee_quote": tee_quote, "energy": energy},
            "physical_gate": gate,
            "issuer_pubkey": self.pub,
        }
        signature = self._priv.sign(jcs(body)).hex()
        return {**body, "signature": signature, "envelop_sha256": sha(jcs(body))}

def verify(env, blobs_by_path):
    errors = []
    expected_paths = {e["path"] for e in env.get("contents", [])}
    supplied_paths = set(blobs_by_path)
    if supplied_paths - expected_paths:
        errors.extend(f"unexpected:{p}" for p in sorted(supplied_paths - expected_paths))
    recomputed = []
    for e in env.get("contents", []):
        data = blobs_by_path.get(e["path"])
        if data is None:
            errors.append(f"missing:{e['path']}")
            continue
        h = sha(data)
        if h != e["sha256"]:
            errors.append(f"content_hash_mismatch:{e['path']}")
        if len(data) != e["size"]:
            errors.append(f"content_size_mismatch:{e['path']}")
        recomputed.append({"path": e["path"], "kind": e["kind"], "sha256": h, "size": len(data)})
    mmr = MerkleMountainRange()
    for e in recomputed:
        mmr.append(_leaf(e))
    manifest = mmr.root()
    if manifest != env.get("manifest_mmr_root"):
        errors.append("manifest_mmr_root_mismatch")
    body = {k: v for k, v in env.items() if k not in ("signature", "envelop_sha256")}
    try:
        pub = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(env["issuer_pubkey"]))
        pub.verify(bytes.fromhex(env["signature"]), jcs(body))
    except Exception as ex:
        errors.append(f"signature_invalid:{type(ex).__name__}")
    if sha(jcs(body)) != env.get("envelop_sha256"):
        errors.append("envelop_sha256_mismatch")
    attest = env.get("attestations", {})
    derived = physical_gate(attest.get("tee_quote"), attest.get("energy"))
    if derived != env.get("physical_gate"):
        errors.append(f"gate_mismatch:stored={env.get('physical_gate')}:derived={derived}")
    return {"ok": not errors, "errors": errors, "physical_gate": derived, "manifest_mmr_root": manifest}
