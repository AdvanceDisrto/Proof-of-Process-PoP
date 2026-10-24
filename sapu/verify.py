from cryptography.hazmat.primitives.asymmetric import ed25519
from .reference import _FIXED_PROFILES,measurement,_jcs,_sha
from tools.gate import physical_gate
def verify_sapu_receipt(r):
    e=[];body={k:v for k,v in r.items() if k not in ("signature","receipt_sha256")}
    try:
        pub=ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(r["issuer_pubkey"]));pub.verify(bytes.fromhex(r["signature"]),_jcs(body))
    except Exception as ex:e.append(f"signature_invalid:{type(ex).__name__}")
    if _sha(_jcs(body))!=r.get("receipt_sha256"):e.append("receipt_sha256_mismatch")
    pid=r.get("sapu",{}).get("profile")
    if pid not in _FIXED_PROFILES:e.append(f"unknown_profile:{pid}")
    else:
        if r.get("sapu",{}).get("measurement")!=measurement(pid):e.append("measurement_mismatch")
        truth=r.get("derived",{}).get("truth_axis");axis=r.get("derived",{}).get("attestation_axis");tier=_FIXED_PROFILES[pid].get((truth,axis))
        if tier!=r.get("derived",{}).get("tier"):e.append(f"tier_mismatch:stored={r.get('derived',{}).get('tier')}:derived={tier}")
    inp=r.get("inputs",{})
    at=r.get("attestation") or {}
    derived_axis="ATTESTED" if physical_gate(at.get("tee_quote"),at.get("energy"))=="MEASURED_PASS" else "UNATTESTED"
    if r.get("derived",{}).get("attestation_axis")!=derived_axis:e.append("attestation_axis_mismatch")
    if r.get("derived",{}).get("tier")=="MEASURED_PASS" and inp.get("attestation_hash") is None:e.append("attestation_implies_tier:MEASURED_PASS_without_attestation_blob")
    return {"ok":not e,"errors":e}
