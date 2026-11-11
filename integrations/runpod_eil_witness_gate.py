"""Read-only independent witness gate for RunPod EiL CUDA observations.

The verifier trusts only an OUT-OF-BAND PINNED iTensor root/policy, checks an
independently enrolled witness role's Ed25519 signature, and independently
recomputes challenged arithmetic. It never authenticates RunPod tenancy,
physical silicon, the witness's independence, or the real world.
"""
from __future__ import annotations
import json
from integrations.eil_production_trust import ProductionGate, canonical, digest, verify_sig
from integrations.runpod_eil_gpu import verify as check_cuda, SCHEMA

WITNESS_SCHEMA="ipqr/runpod-inference-witness/v1"
ROLE="inference_witness"

def assess(gpu_observation, witness_receipt, *, root_path, policy_path,
           root_pin, policy_pin, expected_nonce, seen_challenges=None):
    def blocked(reason):
        return {"verdict":"BLOCKED","reason":reason,"production_trust":"UNVERIFIED"}
    try:
        gate=ProductionGate(root_path,policy_path,root_pin,policy_pin)
        policy=gate.authority()
        if not isinstance(expected_nonce,str) or not expected_nonce:
            return blocked("CHALLENGE_REQUIRED")
        if seen_challenges is None:
            return blocked("REPLAY_REGISTRY_REQUIRED")
        if expected_nonce in seen_challenges:
            return blocked("REPLAY_DETECTED")
        if not isinstance(gpu_observation,dict):
            return blocked("OBSERVATION_MISSING")
        checked=check_cuda(gpu_observation,expected_nonce)
        if checked.get("verdict")!="CHALLENGED_ARITHMETIC_MATCH":
            return blocked("GPU_OBSERVATION_INVALID")
        if not isinstance(witness_receipt,dict) or set(witness_receipt)!={"body","signature_hex","public_key_hex"}:
            return blocked("WITNESS_SHAPE")
        body=witness_receipt["body"]
        if not isinstance(body,dict) or set(body)!={"schema","role","nonce","observation_hash",
                        "observed_output_hash","claim_scope","authority_root_sha256"}:
            return blocked("WITNESS_BODY_SHAPE")
        if (body["schema"]!=WITNESS_SCHEMA or body["role"]!=ROLE
            or body["claim_scope"]!="INDEPENDENT_REVIEW_OF_UNATTESTED_CUDA_REPORT"
            or body["nonce"]!=expected_nonce
            or body["authority_root_sha256"]!=root_pin
            or body["observation_hash"]!=digest(canonical(gpu_observation))
            or body["observed_output_hash"]!=gpu_observation["output_sha256"]):
            return blocked("WITNESS_BINDING")
        pinned_key=policy["role_pubkeys"][ROLE]
        if witness_receipt["public_key_hex"]!=pinned_key or not verify_sig(body,
                  witness_receipt["signature_hex"],pinned_key):
            return blocked("WITNESS_UNTRUSTED_OR_INVALID_SIGNATURE")
        if policy.get("allow_gpu_development_observation") is not True:
            return blocked("POLICY_DOES_NOT_ALLOW_GPU_REVIEW")
        # The registry must be durable and atomic in production. Do not claim a
        # nonce was consumed: this function only reads the supplied registry.
        return {"verdict":"SIGNED_DEVELOPMENT_WITNESS_VALID",
                "observation_hash":digest(canonical(gpu_observation)),
                "witness_key":pinned_key,
                "replay_registry_mode":"READ_ONLY_CHECK",
                "gpu_hardware_attested":False,
                "provider_authenticated":False,
                "witness_independence_proven":False,
                "production_trust":"UNVERIFIED"}
    except (OSError,ValueError,TypeError,KeyError,IndexError,AttributeError) as error:
        return blocked("AUTHORITY_OR_INPUT_ERROR:"+type(error).__name__)
