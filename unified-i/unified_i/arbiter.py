"""Buddy/Twinions safety shim: policy checks only, no free-text truth oracle."""
from __future__ import annotations
from dataclasses import dataclass

class UnsupportedClaim(ValueError):pass


def bounded_integer_verdict(observed:int, maximum:int)->dict:
    if type(observed) is not int or type(maximum) is not int or any(abs(x)>10**12 for x in (observed,maximum)):
        raise UnsupportedClaim("integer bounds required")
    return {"status":"PASS_BOUNDED_CLAIM" if observed<=maximum else "REFUTED_BOUNDED_CLAIM",
            "rule":"integer_lte",
            "mathematical_scope":"comparison over declared input integers",
            "factual_truth":"NOT_ESTABLISHED",
            "source_authenticity":"NOT_ESTABLISHED"}


def audit_free_text(claim:str):
    if type(claim) is not str or not 1<=len(claim)<=4000:
        raise UnsupportedClaim("bounded claim text required")
    return {"status":"UNRESOLVED","reason":"No trusted evidence-derived formal proposition supplied",
            "solver_has_certified_facts":False,
            "filing_authorized":False,"clinical_decision_authorized":False}


def twinions_compare(claims:list[dict])->dict:
    from twinions_legal.arbiter import compare_claims
    result=compare_claims(claims)
    if result["factual_verdict"]!="UNDETERMINED":
        raise UnsupportedClaim("comparison produced an unsupported factual verdict")
    return result
