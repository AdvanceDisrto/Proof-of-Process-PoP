"""iTensor eight-stage local execution pipeline.

Strictly scoped to deterministic adapters. Cryptographic proofs establish
authorship/integrity, not semantic truth, hardware execution, or external time.
No production key creation. Each caller supplies pinned public keys and a signer.
"""
from __future__ import annotations
import json
from integrations.eil_production_trust import canonical,digest,verify_sig

class PipelineBlocked(Exception):
    pass

def signed_record(body,signer,public_key):
    signature=signer(canonical(body))
    if not isinstance(signature,bytes) or len(signature)!=64:
        raise PipelineBlocked("BAD_SIGNER_OUTPUT")
    return {"body":body,"hash":digest(canonical(body)),
            "signature_hex":signature.hex(),"public_key_hex":public_key}

def validate_record(record,pinned_key):
    try:
        return (record["public_key_hex"]==pinned_key
                and record["hash"]==digest(canonical(record["body"]))
                and verify_sig(record["body"],record["signature_hex"],pinned_key))
    except (KeyError,TypeError,ValueError):
        return False

class EightStagePipeline:
    """Request signer/operator enrollment is required before ANY adapter call.

    Adapter registry is explicit; adapters receive only validated args.
    No network or arbitrary shell execution is built in.
    """
    def __init__(self,policy,operator_pubkey,receipt_pubkey,sign_receipt,adapters):
        self.policy=policy
        self.operator_pubkey=operator_pubkey
        self.receipt_pubkey=receipt_pubkey
        self.sign_receipt=sign_receipt
        self.adapters=dict(adapters)
    def run(self,authorization,command,expected_parent=None):
        # Stage 1: signed authorization. No user-supplied override allowed.
        if not validate_record(authorization,self.operator_pubkey):
            raise PipelineBlocked("UNTRUSTED_OPERATOR_AUTHORIZATION")
        auth=authorization["body"]
        if auth.get("schema")!="ipqr/operator-authorization/v1":
            raise PipelineBlocked("INVALID_AUTH_SCHEMA")
        # Stage 2: structured command rather than arbitrary code.
        if not isinstance(command,dict) or set(command)!={"operation","arguments","request_id"}:
            raise PipelineBlocked("INVALID_COMMAND_SHAPE")
        operation=command["operation"]
        if not isinstance(operation,str) or not isinstance(command["arguments"],dict):
            raise PipelineBlocked("INVALID_COMMAND_TYPES")
        # Stage 3: per-command scope + policy binding.
        if auth.get("operation")!=operation or auth.get("request_id")!=command["request_id"]:
            raise PipelineBlocked("COMMAND_NOT_AUTHORIZED")
        if auth.get("arguments_hash")!=digest(canonical(command["arguments"])):
            raise PipelineBlocked("ARGUMENTS_NOT_AUTHORIZED")
        if auth.get("parent")!=expected_parent:
            raise PipelineBlocked("PARENT_SCOPE_MISMATCH")
        if self.policy.get("enabled") is not True or operation not in self.policy.get("allow_operations",[]):
            raise PipelineBlocked("POLICY_DENIED")
        if operation not in self.adapters:
            raise PipelineBlocked("ADAPTER_UNAVAILABLE")
        # Stage 4: explicit adapter execution, after authorization.
        result=self.adapters[operation](dict(command["arguments"]))
        if not isinstance(result,dict):
            raise PipelineBlocked("ADAPTER_RESULT_NOT_JSON_OBJECT")
        # Stage 5: canonical evidence binds full args/results; no external attestation.
        body={"schema":"ipqr/itensor-local-execution-receipt/v1",
              "request_id":command["request_id"],"operation":operation,
              "authorization_hash":authorization["hash"],"parent":expected_parent,
              "arguments_hash":digest(canonical(command["arguments"])),
              "result_hash":digest(canonical(result)),"result":result,
              "evidence_scope":"LOCAL_ADAPTER_OBSERVATION"}
        receipt=signed_record(body,self.sign_receipt,self.receipt_pubkey)
        # Stage 6: independent signature verification against pinned key.
        if not validate_record(receipt,self.receipt_pubkey):
            raise PipelineBlocked("RECEIPT_SIGNATURE_REJECTED")
        # Stage 7: local chain link validated; external anchor is NOT supplied.
        if body["parent"]!=expected_parent or body["authorization_hash"]!=authorization["hash"]:
            raise PipelineBlocked("CHAIN_LINK_REJECTED")
        # Stage 8: inspectable export, truthful status.
        return {"status":"LOCAL_INTEGRITY_VERIFIED","authorization":authorization,
                "receipt":receipt,"chain_parent":expected_parent,
                "external_anchor":None,"production_trust":"UNVERIFIED",
                "truth_boundary":{"proves":["signed operator authorization was checked against pinned public key",
                    "local adapter response was captured and signed"],
                    "does_not_prove":["external source identity","hardware attestation",
                    "external timestamp","Bitcoin anchoring","semantic correctness"]}}
def byte_width_adapter(args):
    if args!={"unit":"byte"}:
        raise PipelineBlocked("INVALID_BYTE_WIDTH_ARGUMENTS")
    return {"unit":"byte","bits":8,"method":"DEFINITION_OF_OCTET"}
