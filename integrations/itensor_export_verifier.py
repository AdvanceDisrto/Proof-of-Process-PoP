"""Offline independent verifier for the iTensor local receipt export.

Requires independently supplied operator/receipt public keys and operation policy.
This is NOT production identity, proof of execution or an external time anchor.
"""
from __future__ import annotations
import re
from integrations.eil_production_trust import canonical,digest,verify_sig

def verify_export(bundle, operator_pubkey, receipt_pubkey, allowed_operations,
                  *, expected_parent=None, seen_requests=None):
    def reject(reason):
        return {"verdict":"REJECT","reason":reason,"scope":"LOCAL_EXPORT_INTEGRITY_ONLY"}
    try:
        if not isinstance(bundle,dict) or set(bundle)!={"status","authorization","receipt",
                "chain_parent","external_anchor","production_trust","truth_boundary"}:
            return reject("BUNDLE_STRUCTURE")
        if bundle["status"]!="LOCAL_INTEGRITY_VERIFIED" or bundle["production_trust"]!="UNVERIFIED":
            return reject("STATUS_PROMOTION_ATTEMPT")
        if bundle["external_anchor"] is not None:
            return reject("UNVERIFIED_EXTERNAL_ANCHOR")
        for pin in (operator_pubkey,receipt_pubkey):
            if not isinstance(pin,str) or not re.fullmatch("[0-9a-f]{64}",pin):
                return reject("MISSING_TRUST_PIN")
        if operator_pubkey==receipt_pubkey:
            return reject("SIGNER_ROLES_NOT_DISTINCT")
        if not isinstance(allowed_operations,(set,frozenset,list,tuple)) or not allowed_operations:
            return reject("POLICY_MISSING")
        auth=bundle["authorization"];receipt=bundle["receipt"]
        for record,pin in ((auth,operator_pubkey),(receipt,receipt_pubkey)):
            if not isinstance(record,dict) or set(record)!={"body","hash","signature_hex","public_key_hex"}:
                return reject("RECORD_STRUCTURE")
            if record["public_key_hex"]!=pin or record["hash"]!=digest(canonical(record["body"])):
                return reject("RECORD_HASH_OR_PIN")
            if not verify_sig(record["body"],record["signature_hex"],pin):
                return reject("SIGNATURE_INVALID")
        a=auth["body"];r=receipt["body"]
        if a.get("schema")!="ipqr/operator-authorization/v1":
            return reject("AUTH_SCHEMA")
        if r.get("schema")!="ipqr/itensor-local-execution-receipt/v1":
            return reject("RECEIPT_SCHEMA")
        if not isinstance(a.get("request_id"),str) or not a["request_id"]:
            return reject("REQUEST_ID")
        if not isinstance(a.get("arguments_hash"),str) or not re.fullmatch("sha256:[0-9a-f]{64}",a["arguments_hash"]):
            return reject("ARGUMENTS_HASH")
        if a.get("operation") not in allowed_operations:
            return reject("OPERATION_DENIED")
        if (r.get("request_id")!=a["request_id"] or r.get("operation")!=a["operation"]
            or r.get("arguments_hash")!=a["arguments_hash"]
            or r.get("authorization_hash")!=auth["hash"]):
            return reject("AUTHORIZATION_BINDING")
        if bundle["chain_parent"]!=expected_parent or a.get("parent")!=expected_parent or r.get("parent")!=expected_parent:
            return reject("PARENT_BINDING")
        if r.get("evidence_scope")!="LOCAL_ADAPTER_OBSERVATION":
            return reject("EVIDENCE_SCOPE")
        if not isinstance(r.get("result"),dict) or r.get("result_hash")!=digest(canonical(r["result"])):
            return reject("OUTPUT_HASH")
        if seen_requests is not None and a["request_id"] in seen_requests:
            return reject("REQUEST_REPLAY")
        return {"verdict":"ACCEPT_LOCAL_INTEGRITY","request_id":a["request_id"],
                "receipt_hash":receipt["hash"],"external_anchor":None,
                "production_trust":"UNVERIFIED","scope":"LOCAL_EXPORT_INTEGRITY_ONLY"}
    except (ValueError,KeyError,TypeError,OverflowError,AttributeError):
        return reject("INVALID_DATA")
