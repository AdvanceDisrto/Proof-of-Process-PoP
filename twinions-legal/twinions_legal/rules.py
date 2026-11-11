"""Versioned 18-slot LEGAL *INTAKE* workflow, never a judicial ruling.

Only seven slot names are supplied by the user. Unnamed slots stay
UNDEFINED. This tool must never invent the user's other 11 gate definitions.
"""
from __future__ import annotations
from dataclasses import dataclass

VERSION = "twinions-legal-intake/0.1"
KNOWN_GATES: dict[int, str] = {
    1: "Intake",
    2: "Conflict check",
    5: "Favorable termination",
    7: "Lack of probable cause",
    8: "Malice / improper purpose",
    14: "Due process notice",
    18: "Due process reply logged",
}
GATES = tuple({"gate": i, "name": KNOWN_GATES.get(i, "UNDEFINED — counsel must supply"),
               "definition_source": "user_supplied" if i in KNOWN_GATES else "not_provided"}
              for i in range(1, 19))
GATE_STATUSES = frozenset(("NOT_REVIEWED", "EVIDENCE_ATTACHED", "CONTESTED", "MISSING"))


def evaluate(gate_rows: list[dict], notice: bool, reply: bool, counsel: bool) -> dict:
    """Only case-file completeness, not SAT proof of a legal element."""
    if len(gate_rows) != 18 or [x["gate"] for x in gate_rows] != list(range(1, 19)):
        raise ValueError("Exactly 18 ordered gates are required")
    undefined = [x["gate"] for x in gate_rows if x["definition_source"] == "not_provided"]
    missing = [x["gate"] for x in gate_rows if x["status"] in ("NOT_REVIEWED", "MISSING")]
    contested = [x["gate"] for x in gate_rows if x["status"] == "CONTESTED"]
    reasons = []
    if undefined: reasons.append("GATE_DEFINITIONS_INCOMPLETE")
    if missing: reasons.append("GATE_EVIDENCE_INCOMPLETE")
    if contested: reasons.append("CONTESTED_EVIDENCE_REQUIRES_COUNSEL")
    if not notice: reasons.append("NOTICE_DOCUMENTATION_MISSING")
    if not reply: reasons.append("REPLY_OPPORTUNITY_NOT_DOCUMENTED")
    if not counsel: reasons.append("COUNSEL_REVIEW_NOT_RECORDED")
    return {
        "outcome": "DRAFT_FOR_COUNSEL" if not reasons else "EVIDENCE_REVIEW_REQUIRED",
        "reasons": reasons,
        "undefined_gates": undefined,
        "missing_gates": missing,
        "contested_gates": contested,
        "legal_merits_verdict": "NOT_DETERMINED",
        "filing_authorization": "NOT_GRANTED",
        "does_not_prove": ["criminal or civil liability", "malice", "medical facts",
                           "independence or completeness of evidence", "court admissibility"],
    }
