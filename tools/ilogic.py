"""iLogic: closed, fail-closed tier derivation with truth/attestation axes."""
import hashlib, json, time
from dataclasses import dataclass, asdict
from tools.mmr_pipeline import MerkleMountainRange

ESTABLISHED, OPEN, REFUTED, CONTRADICTORY = "ESTABLISHED", "OPEN", "REFUTED", "CONTRADICTORY"
ATTESTED, UNATTESTED = "ATTESTED", "UNATTESTED"
MODE_EVIDENCE, MODE_LAW = "evidence", "law"

def jcs(o): return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()
def sha(b): return "sha256:" + hashlib.sha256(b).hexdigest()

@dataclass(frozen=True)
class Claim:
    id: str
    subject: str
    predicate: str
    polarity: int
    status: str
    attestation: str
    artifact_sha: str | None = None

@dataclass(frozen=True)
class Rule:
    name: str
    mode: str
    premises: tuple
    subject: str
    predicate: str
    conclusion_attested: bool = False
    axioms: tuple = ()

class LogicError(Exception):
    pass

class Engine:
    def __init__(self, claims):
        self.claims = {}
        for c in claims:
            if c.status not in (ESTABLISHED, OPEN, REFUTED, CONTRADICTORY):
                raise LogicError(f"bad status {c.status}")
            if c.attestation not in (ATTESTED, UNATTESTED):
                raise LogicError(f"bad attestation {c.attestation}")
            self.claims[c.id] = c
        self.derived = {}

    def _check_contradictions(self, pool=None):
        pool = list(self.claims.values()) if pool is None else pool
        by_key = {}
        for c in pool:
            by_key.setdefault((c.subject, c.predicate), []).append(c)
        for group in by_key.values():
            positives = [c for c in group if c.polarity == 1 and c.status == ESTABLISHED]
            negatives = [c for c in group if c.polarity == -1 and c.status == ESTABLISHED]
            if positives and negatives:
                for c in positives + negatives:
                    self.claims[c.id] = Claim(**{**asdict(c), "status": CONTRADICTORY})

    @staticmethod
    def _meet(statuses):
        if not statuses:
            raise LogicError("rule has no premises")
        if CONTRADICTORY in statuses: return CONTRADICTORY
        if REFUTED in statuses: return REFUTED
        if all(s == ESTABLISHED for s in statuses): return ESTABLISHED
        return OPEN

    def apply(self, rule):
        if rule.mode not in (MODE_EVIDENCE, MODE_LAW):
            raise LogicError(f"unknown mode {rule.mode}")
        for pid in rule.premises:
            if pid not in self.claims:
                raise LogicError(f"rule {rule.name} references absent claim {pid}")
        if rule.mode == MODE_LAW and not rule.axioms:
            raise LogicError(f"law rule {rule.name} has no certified axioms")
        prem = [self.claims[p] for p in rule.premises]
        status = self._meet([p.status for p in prem])
        all_att = all(p.attestation == ATTESTED for p in prem)
        attested = ATTESTED if all_att and rule.conclusion_attested else UNATTESTED
        if rule.mode == MODE_LAW and status == ESTABLISHED:
            tier = "LAW"
        elif status == ESTABLISHED:
            tier = "VERIFIED_PROCESS"
        elif status == REFUTED:
            tier = "REFUTED"
        elif status == CONTRADICTORY:
            tier = "CONTRADICTION"
        else:
            tier = "ACTION_REQUIRED"
        gate = "MEASURED_PASS" if tier == "LAW" and attested == ATTESTED else "ACTION_REQUIRED"
        cid = "d:" + sha(jcs({"rule": rule.name, "premises": list(rule.premises), "s": rule.subject, "p": rule.predicate}))[:16]
        concl = Claim(cid, rule.subject, rule.predicate, 1, status, attested)
        self.derived[cid] = {"claim": asdict(concl), "tier": tier, "gate": gate,
                             "rule": rule.name, "mode": rule.mode, "premises": list(rule.premises),
                             "axioms": list(rule.axioms)}
        return self.derived[cid]

    def receipt(self):
        mmr = MerkleMountainRange()
        for cid in sorted(self.derived):
            mmr.append(jcs(self.derived[cid]))
        for cid in sorted(self.claims):
            mmr.append(jcs(asdict(self.claims[cid])))
        return {"spec": "innovulis-ilogic/1.0", "issued_utc": time.time(),
                "derivations": [self.derived[k] for k in sorted(self.derived)],
                "claim_count": len(self.claims), "derived_count": len(self.derived),
                "derivation_mmr_root": mmr.root(), "physical_gate": "ACTION_REQUIRED"}
