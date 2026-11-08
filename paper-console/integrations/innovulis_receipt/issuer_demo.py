"""Generate synthetic, clearly DEMO-only acceptance fixtures.

No signing private keys are ever written into the output bundle. This module
is not a production issuer and does not import production credentials.
"""
from __future__ import annotations
from pathlib import Path
import json
import secrets
import time
from cryptography.hazmat.primitives.asymmetric import ed25519
from .codec import canonical, sha256
from .crypto import (public_hex, sign, merkle_root, witness_commitment,
                     ISSUER_DOMAIN, ENGINEER_DOMAIN, WITNESS_DOMAIN, REVOCATION_DOMAIN, ISSUANCE_LOG_DOMAIN)


def create_demo(at_time=None, *, verdict="PROVEN_TRUE", observed=45000, limit=50000,
                subject="sensor:demo-unit-314", claim_context="SYNTHETIC_CALIBRATION_NOT_REAL"):
    """Create a fresh mock publisher/engineer and five distinct signing keys.

    A real deployment MUST provision trusted keys and engineer identity out of
    band. DEMO keys are ephemeral, only public keys and signatures are emitted.
    """
    now = int(time.time()) if at_time is None else at_time
    issuer=ed25519.Ed25519PrivateKey.generate()
    engineer=ed25519.Ed25519PrivateKey.generate()
    authority=ed25519.Ed25519PrivateKey.generate()
    log_authority=ed25519.Ed25519PrivateKey.generate()
    witnesses=[ed25519.Ed25519PrivateKey.generate() for _ in range(5)]
    def key_entry(name,key):
        return {"id":name, "public_key":public_hex(key),
                "valid_from": now-10000, "valid_until":now+86400}
    trust={"schema":"ipqr-anchor/v1", "anchor_id":"DEMO_ONLY_NOT_TRUSTED_IN_PRODUCTION",
           "issuer_keys":[key_entry("issuer-demo-001",issuer)],
           "witnesses":[key_entry(f"witness-demo-{i+1:02d}",key) for i,key in enumerate(witnesses)],
           "engineers":[{**key_entry("engineer-demo-001",engineer),
                         "name":"Synthetic Test Engineer", "organization":"DEMO ONLY",
                         "role":"Demo signatory; no real-world professional credentials"}],
           "revocation_authority":{"id":"revocation-demo-001","public_key":public_hex(authority)},
           "issuance_log_authority":{"id":"log-demo-001","public_key":public_hex(log_authority)},
           "policy":{"witness_threshold":3,"max_receipt_age_seconds":3600,
                     "max_clock_skew_seconds":60,"max_observation_lag_seconds":300,
                     "max_revocation_age_seconds":1800,"minimum_revocation_serial":1,
                     "max_evidence_file_bytes":1048576,
                     "minimum_log_serial":1,"max_log_age_seconds":3600}}
    evidence=b"SYNTHETIC SENSOR TRACE; NOT PHYSICAL EVIDENCE\nobserved=45000\nlimit=50000\n"
    manifest=[{"name":"sensor_demo_trace.txt","sha256":sha256(evidence)}]
    claim={"kind":"integer_lte","observed":observed,"limit":limit,"unit":"micro_celsius_demo"}
    receipt={"schema":"ipqr-receipt/v1","issuer_id":"issuer-demo-001","issuer_key_id":"issuer-demo-001",
             "subject":subject,"claim":claim,"claim_sha256":sha256(canonical(claim)),"verdict":verdict,
             "issued_at":now-10,"observed_at":now-15,"expires_at":now+1800,
             "nonce_hex":secrets.token_hex(16),"evidence_manifest":manifest,
             "evidence_root":merkle_root(manifest),"witness_set_root":witness_commitment(trust),
             "responsible_id":"engineer-demo-001","energy_microjoules":None,
             "time_basis":"ISSUER_CLOCK_UNTRUSTED"}
    packet={"schema":"ipqr-packet/v1","receipt":receipt,
            "issuer_signature":sign(issuer,ISSUER_DOMAIN,receipt),
            "engineer_signature":sign(engineer,ENGINEER_DOMAIN,receipt),
            "witness_signatures":[{"id":f"witness-demo-{i+1:02d}",
                                   "signature":sign(key,WITNESS_DOMAIN,receipt)}
                                  for i,key in enumerate(witnesses[:3])]}
    snapshot={"schema":"ipqr-revocations/v1","authority_id":"revocation-demo-001",
              "serial":1,"issued_at":now-100,"next_update":now+1800,"revoked_keys":[]}
    revocations={"snapshot":snapshot,"signature":sign(authority,REVOCATION_DOMAIN,snapshot)}
    receipt_hash=sha256(canonical(receipt))
    entries=[receipt_hash]
    checkpoint={"schema":"ipqr-issuance/v1","authority_id":"log-demo-001",
                "serial":1,"issued_at":now-5,"entries":entries,
                "merkle_root":merkle_root([{"receipt_sha256":digest} for digest in entries])}
    issuance_log={"checkpoint":checkpoint,
                  "signature":sign(log_authority,ISSUANCE_LOG_DOMAIN,checkpoint)}
    return {"packet":packet,"trust":trust,"revocations":revocations,"issuance_log":issuance_log,"evidence":evidence,
            "trust_sha256":sha256(canonical(trust)), "demo_time":now,
            "_private_for_tests":{"issuer":issuer,"engineer":engineer,"authority":authority,"log_authority":log_authority,"witnesses":witnesses}}


def write_demo(out_dir):
    from .carrier import make_svg, make_png
    out=Path(out_dir)
    out.mkdir(parents=True,exist_ok=True)
    data=create_demo()
    for name,content in (("receipt.json",data["packet"]),("trust_anchor.json",data["trust"]),
                         ("signed_revocations.json",data["revocations"]),
                         ("signed_issuance_log.json",data["issuance_log"])):
        (out/name).write_bytes(json.dumps(content,indent=2,sort_keys=True).encode()+b"\n")
    (out/"sensor_demo_trace.txt").write_bytes(data["evidence"])
    (out/"DEMO_ANCHOR_SHA256_NOT_TRUSTED.txt").write_text(data["trust_sha256"]+"\n",encoding="ascii")
    (out/"ipqr_carrier.txt").write_text(__import__("innovulis_receipt.codec",fromlist=["encode_qr_text"]).encode_qr_text(data["packet"])+"\n")
    try:
        make_svg(data["packet"],out/"receipt_carrier.svg")
        make_png(data["packet"],out/"receipt_carrier.png")
    except (ImportError,ValueError) as exc:
        (out/"QR_NOT_AVAILABLE.txt").write_text(str(exc)+"\n")
    (out/"DISCLAIMER.txt").write_text("\n".join([
        "DEMO ONLY. NOT A TRUST ANCHOR FOR PRODUCTION.",
        "No real sensors, independent witnesses, human certification, or trusted timestamps.",
        "The SHA-256 in DEMO_ANCHOR_SHA256_NOT_TRUSTED.txt is synthetic and NOT independently trusted.",
        "For production, acquire and pin anchor fingerprint independently of the scanned QR.",
        "The 3 witness keys and issuance log authority were generated in one demo process.",
        "The signed issuance-log checkpoint is not a globally transparent append-only log.",
        "Private signing keys are NOT exported in any demo output.",
    ])+"\n")
    return data
