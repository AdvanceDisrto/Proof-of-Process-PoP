"""Bind an inference observation into the existing PoP Ed25519 domain receipt.

Records signature integrity, NOT model checkpoint identity, factual correctness,
hardware attestation, LIVE-root linkage, or an ML-DSA dual signature.
"""
from core.crypto import canonical, sha, public_hex, sign
from proof.parallel_pop import DomainReceipt, verify_domain
from integrations.frontier_evidence import digest

def sign_inference_observation(observation: dict, signing_key) -> DomainReceipt:
    if observation.get("verification_state") != "UNVERIFIED_INFERENCE":
        raise ValueError("Only unverified inference observations are accepted")
    supplied_hash = observation.get("observation_sha256")
    original = {k: v for k, v in observation.items() if k != "observation_sha256"}
    if supplied_hash != digest(original):
        raise ValueError("Observation integrity mismatch")
    if not observation.get("output_sha256") or not observation.get("prompt_sha256"):
        raise ValueError("Missing observed request/response hashes")
    body = {
        "spec": "innovulis-parallel-domain/1.0",
        "domain": "INFERENCE_OBSERVATION",
        "state": "ACTION_REQUIRED",
        "payload": original,
        "observation_sha256": supplied_hash,
        "signer": "ed25519:" + public_hex(signing_key),
        "proves": ["trusted signer attested to this exact observation payload"],
        "does_not_prove": [
            "provider identity or checkpoint weights",
            "truth or correctness of generated text",
            "TEE quote or hardware-rooted provenance",
            "external Bitcoin anchoring or ML-DSA dual signature",
        ],
    }
    envelope = DomainReceipt(body=body, signature=sign(signing_key, body), receipt_id=sha(canonical(body)))
    if not verify_domain(envelope):
        raise RuntimeError("PoP receipt self-verification failed")
    return envelope
