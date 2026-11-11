"""Fail-closed QoW to PoP adapter. Uses the existing PoP Domain and Merkle logic."""
import hashlib
import json
import re
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

def canonical(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

def validate_qow(receipt, pinned_pubkey, independent_recheck):
    """The supplied callback MUST independently execute Z3; no verdict echo."""
    if not callable(independent_recheck):
        raise ValueError("independent Z3 recheck required")
    body = receipt["body"]
    actual = "sha256:" + hashlib.sha256(canonical(body)).hexdigest()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", receipt["receipt_hash"]) or actual != receipt["receipt_hash"]:
        raise ValueError("QoW receipt hash mismatch")
    if body.get("issuer_pubkey_hex") != pinned_pubkey:
        raise ValueError("issuer public key is not pinned")
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(pinned_pubkey)).verify(
        bytes.fromhex(receipt["signature"]), canonical(body))
    if body.get("verdict") != "PROVEN_TRUE":
        raise ValueError("unproven QoW claim cannot promote PoP")
    check = independent_recheck(receipt)
    if not isinstance(check, dict) or check.get("ok") is not True or check.get("verdict") != "PROVEN_TRUE":
        raise ValueError("independent Z3 recheck failed")
    return {"qow_receipt_hash": actual, "claim_id": body["claim_id"],
            "verdict": "PROVEN_TRUE", "parent_hashes": body.get("parent_hashes", []),
            "issuer_pubkey_hex": pinned_pubkey}

async def qow_domain_receipt(receipt, pinned_pubkey, independent_recheck):
    """PoP signs the domain envelope; failed checks yield FAILED/INCOMPLETE."""
    from proof.parallel_pop import Domain
    async def work():
        return {"state": "VERIFIED_PROCESS",
                "qow": validate_qow(receipt, pinned_pubkey, independent_recheck),
                "does_not_prove": ["physical truth", "TEE execution", "SMT proof certificate"]}
    return await Domain("QUANTUM_OF_WORK").execute(work)
