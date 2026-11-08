"""Host-side conservative PoPC-PU admission predicate; not a hardware PUF or SMT engine."""
from dataclasses import dataclass
import hashlib
import re
from .codec import canonical


@dataclass(frozen=True)
class GateInputs:
    externally_verified_math: bool
    meter_fresh: bool
    meter_calibrated: bool
    energy_interval_in_spec: bool
    thermal_ok: bool
    signer_ready: bool
    consent: bool
    source_authenticated: bool

    def __post_init__(self):
        if any(type(getattr(self,k)) is not bool for k in self.__dataclass_fields__):
            raise ValueError("all gate inputs must be explicit booleans")


def popc_admission(g:GateInputs,claim_hash:str):
    if type(claim_hash) is not str or not re.fullmatch(r"[0-9a-f]{64}",claim_hash):
        raise ValueError("canonical SHA-256 hex digest required")
    ok=(claim_hash != "0"*64) and all(getattr(g,k) for k in g.__dataclass_fields__)
    return {"admit_to_signer":ok,
            "gate_input_commitment_sha256":hashlib.sha256(canonical({**g.__dict__,"claim_sha256":claim_hash})).hexdigest(),
            "status":"SIGN_REQUEST_ELIGIBLE_UNATTESTED" if ok else "SIGN_REQUEST_BLOCKED",
            "does_not_prove":["hardware-authenticated meter", "Landauer minimum work", "secure-element private key access", "uncounterfeitable physics", "silicon proof execution"]}
