"""Strict, deterministic, ASCII-only receipt metadata and source scope.

This receipt is a bounded cross-application *manifest*, not ipqr1 by itself.
No human/legal/medical/physical truth is inferred from signatures.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
from dataclasses import dataclass, field, asdict

class ContractError(ValueError): pass

TIERS = frozenset({
    "SYNTHETIC", "SOFTWARE_OBSERVED", "HARDWARE_UNATTESTED",
    "HARDWARE_SIGNATURE_VERIFIED", "EXTERNAL_WITNESS_REVIEWED"})
VERDICTS = frozenset({"PASS_BOUNDED_CLAIM", "REFUTED_BOUNDED_CLAIM", "UNRESOLVED"})
STATUS = frozenset({"PASS_SOFTWARE", "PENDING_PHYSICAL", "FAIL_CLOSED", "ACTION_REQUIRED"})
SHA = re.compile(r"[0-9a-f]{64}\Z")
ID = re.compile(r"[a-zA-Z0-9_.:/-]{2,120}\Z")


def canonical(value: object) -> bytes:
    """Stable, UTF8 encoding. Disallows NaN, Infinity, and implicit floats in proof values."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf8")


def sha256(raw: bytes) -> str:
    if not isinstance(raw, bytes):raise ContractError("digest requires raw bytes")
    return hashlib.sha256(raw).hexdigest()


def bytes_hash_object(obj: object) -> str:
    return sha256(canonical(obj))


def nonsecret_text(s: str, label: str, max_length: int = 200) -> str:
    if type(s) is not str or not 1 <= len(s) <= max_length:
        raise ContractError(f"{label}: invalid text length")
    if any(ord(c) < 32 or ord(c) == 127 for c in s):
        raise ContractError(f"{label}: control character")
    return s


@dataclass(frozen=True)
class ClaimRecord:
    event_id: str
    subject: str
    assertion_kind: str
    verdict: str
    source_tier: str
    evidence_sha256: str
    issuer_key_id: str
    sequence: int
    issued_at: int
    expires_at: int
    limitations: tuple[str, ...]
    observed_micro_units: int | None = None
    maximum_micro_units: int | None = None

    def __post_init__(self):
        for name in ("event_id", "issuer_key_id"):
            if not ID.fullmatch(getattr(self,name)):
                raise ContractError(f"unsafe {name}")
        nonsecret_text(self.subject,"subject")
        if self.assertion_kind not in ("INTEGER_LTE", "DECLARED_UNASSESSED"):
            raise ContractError("no arbitrary natural language claims allowed")
        if self.verdict not in VERDICTS or self.source_tier not in TIERS:
            raise ContractError("unknown claim or provenance tier")
        if not SHA.fullmatch(self.evidence_sha256):raise ContractError("invalid evidence digest")
        if type(self.sequence) is not int or not 1<=self.sequence<=2**63-1:
            raise ContractError("invalid sequence")
        if type(self.issued_at) is not int or type(self.expires_at) is not int or self.issued_at<0 or not 0<self.expires_at-self.issued_at<=86400:
            raise ContractError("expires within 24h required")
        if type(self.limitations) is not tuple or not 1<=len(self.limitations)<=12:
            raise ContractError("limitations are mandatory")
        for s in self.limitations:nonsecret_text(s,"limitation",256)
        if self.assertion_kind=="INTEGER_LTE":
            for x in (self.observed_micro_units,self.maximum_micro_units):
                if type(x) is not int or not -(10**12)<=x<=10**12:
                    raise ContractError("bounded integer measurements only")
            expected="PASS_BOUNDED_CLAIM" if self.observed_micro_units<=self.maximum_micro_units else "REFUTED_BOUNDED_CLAIM"
            if self.verdict != expected:raise ContractError("asserted verdict conflicts with bounded comparison")
        else:
            if self.verdict!="UNRESOLVED" or self.observed_micro_units is not None or self.maximum_micro_units is not None:
                raise ContractError("unassessed claim cannot claim proof")

    def to_dict(self) -> dict:
        data=asdict(self)
        data["limitations"]=list(self.limitations)
        return data
