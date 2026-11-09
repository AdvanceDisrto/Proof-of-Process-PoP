"""Deterministic contradiction detection between claims; never chooses medical/legal truth."""
from __future__ import annotations
from .ledger import digest, canonical


def compare_claims(claims: list[dict]) -> dict:
    if not 2 <= len(claims) <= 12:raise ValueError("provide 2–12 explicit claims")
    cleaned=[]
    for c in claims:
        if set(c)!={"source","question_id","answer"}:
            raise ValueError("only bounded explicit assertions accepted")
        if any(type(c[x]) is not str or not 1 <= len(c[x]) <= 256 for x in c):
            raise ValueError("invalid assertion")
        cleaned.append(c)
    by_question={}
    for c in cleaned:
        by_question.setdefault(c["question_id"],set()).add(c["answer"].strip().casefold())
    conflicts=sorted(k for k,v in by_question.items() if len(v)>1)
    return {"status":"CONFLICT_DETECTED" if conflicts else "NO_TEXTUAL_CONFLICT_DETECTED",
            "conflicting_question_ids":conflicts,"claims_sha256":digest(canonical(cleaned)),
            "factual_verdict":"UNDETERMINED",
            "limitations":["different answers are not necessarily mutually exclusive",
                           "agreement does not prove factual accuracy",
                           "model output is not authenticated by this comparison"]}
