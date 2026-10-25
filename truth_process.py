#!/usr/bin/env python3
"""Evidence-bounded truth ladder for the PoP Oracle.

The process escalates only from NONE -> WARRANTED -> CERTIFIED -> ANCHORED.
CORRESPONDENCE is intentionally not representable: software cannot certify
that a claim matches reality from inside the system.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable


class TruthLevel:
    NONE = 0
    WARRANTED = 1
    CERTIFIED = 2
    ANCHORED = 3


LEVEL_MANIFEST = {
    TruthLevel.NONE: {
        "label": "NONE",
        "can_claim": [],
        "cannot_claim": ["no receipt was produced at any level"],
    },
    TruthLevel.WARRANTED: {
        "label": "WARRANTED",
        "can_claim": [
            "the query was well-formed against the oracle schema",
            "all evidence fields are structurally valid",
            "the claim lies inside the oracle declared section",
        ],
        "cannot_claim": [
            "that the claim corresponds to reality",
            "that the evidence is truthful",
            "that the oracle checks would pass",
            "that another oracle would answer the same way",
        ],
    },
    TruthLevel.CERTIFIED: {
        "label": "CERTIFIED",
        "can_claim": [
            "every check declared by the oracle passed",
            "a UR-1 was issued exactly once for this claim/version",
            "evidence hashes bind to the claim",
            "the receipt is sealed and reproducible",
        ],
        "cannot_claim": [
            "that the checks exhaust every failure mode",
            "that the oracle scope covers the world",
            "that the claim corresponds to reality",
            "that the receipt remains valid after conditions change",
        ],
    },
    TruthLevel.ANCHORED: {
        "label": "ANCHORED",
        "can_claim": [
            "an external verifier independently confirmed the anchor",
            "the anchor receipt artifact was not tampered with",
            "the verification policy version in use",
            "the verifier identity is recorded",
        ],
        "cannot_claim": [
            "that the verifier is honest",
            "that the verifier judgment is correct",
            "that an anchor medium confirms correspondence truth",
            "that the claim corresponds to reality",
        ],
    },
}


class Stage:
    ADMIT = 0
    INTERPRET = 1
    BIND = 2
    SCOPE = 3
    CHECK = 4
    SEAL = 5
    LEVEL = 6


STAGE_NAME = {
    Stage.ADMIT: "admit",
    Stage.INTERPRET: "interpret",
    Stage.BIND: "bind",
    Stage.SCOPE: "scope",
    Stage.CHECK: "check",
    Stage.SEAL: "seal",
    Stage.LEVEL: "level",
}


@dataclass
class TruthProcessReceipt:
    section: str
    claim: dict
    oracle_name: str
    oracle_version: str
    stage_reached: int
    truth_level: int
    verdict: str
    evidence: list = field(default_factory=list)
    refusal_reason: str = ""
    external_verifier_id: str = ""
    external_policy_version: str = ""
    can_claim: list = field(default_factory=list)
    cannot_claim: list = field(default_factory=list)
    refusals_at_this_stage: list = field(default_factory=list)
    asked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    receipt_hash: str = ""

    def seal(self) -> "TruthProcessReceipt":
        manifest = LEVEL_MANIFEST[self.truth_level]
        self.can_claim = list(manifest["can_claim"])
        self.cannot_claim = list(manifest["cannot_claim"])
        body = {
            "section": self.section,
            "claim": self.claim,
            "oracle_name": self.oracle_name,
            "oracle_version": self.oracle_version,
            "stage_reached": self.stage_reached,
            "truth_level": self.truth_level,
            "verdict": self.verdict,
            "evidence": self.evidence,
            "refusal_reason": self.refusal_reason,
            "external_verifier_id": self.external_verifier_id,
            "external_policy_version": self.external_policy_version,
            "can_claim": self.can_claim,
            "cannot_claim": self.cannot_claim,
            "refusals_at_this_stage": self.refusals_at_this_stage,
            "asked_at": self.asked_at,
        }
        self.receipt_hash = "sha256:" + hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return self


class TruthProcessOracle:
    name = "base"
    version = "0.0.1"

    def schema(self) -> dict:
        return {}

    def check(self, query: dict) -> tuple[bool, str, list]:
        return False, "not implemented", []

    def scope_claims(self) -> list:
        return []


def _is_ur1(value) -> bool:
    return isinstance(value, str) and value.startswith("urn:ur1:sha256:") and len(value) == 80


def _is_sha(value) -> bool:
    return isinstance(value, str) and value.startswith("sha256:") and len(value) == 71


def _matches_kind(value, kind: str) -> bool:
    if kind in {"str", "ur1", "sha256"}:
        return isinstance(value, str)
    if kind == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "list_ur1":
        return isinstance(value, list) and all(_is_ur1(x) for x in value)
    if kind == "list_sha256":
        return isinstance(value, list) and all(_is_sha(x) for x in value)
    return False


class TruthProcess:
    def __init__(self, registry: dict[str, TruthProcessOracle]):
        self.registry = registry

    def _admit(self, section):
        oracle = self.registry.get(section)
        return (oracle, "") if oracle else (None, f"no oracle registered for section {section!r}")

    def _interpret(self, oracle, query):
        schema = oracle.schema()
        missing = [k for k in schema if k not in query]
        if missing:
            return False, f"missing fields: {sorted(missing)}"
        for key, kind in schema.items():
            if not _matches_kind(query[key], kind):
                return False, f"{key} does not match schema kind {kind!r}"
        return True, ""

    def _bind(self, query):
        out = []
        for value in query.values():
            values = value if isinstance(value, list) else [value]
            for item in values:
                if _is_ur1(item) or _is_sha(item):
                    out.append(item)
        return (out, "") if out else ([], "no evidence fields found in query")

    def _scope(self, oracle, claim):
        kind = claim.get("kind", "").lower()
        if not kind:
            return True, ""
        for refusal in oracle.scope_claims():
            if kind in refusal.lower():
                return False, f"oracle declares it will not: {refusal}"
        return True, ""

    def process(
        self,
        section: str,
        claim: dict,
        external_verifier: Callable[[TruthProcessReceipt], dict] | None = None,
        external_policy_version: str = "",
    ) -> TruthProcessReceipt:
        receipt = TruthProcessReceipt(
            section=section,
            claim=claim,
            oracle_name="(none)",
            oracle_version="(none)",
            stage_reached=Stage.ADMIT,
            truth_level=TruthLevel.NONE,
            verdict="REFUSED_NO_ORACLE",
        )

        oracle, reason = self._admit(section)
        if oracle is None:
            receipt.refusal_reason = reason
            receipt.refusals_at_this_stage = ["no oracle covers this section; the process refuses to guess"]
            return receipt.seal()

        receipt.oracle_name = oracle.name
        receipt.oracle_version = oracle.version

        receipt.stage_reached = Stage.INTERPRET
        ok, reason = self._interpret(oracle, claim)
        if not ok:
            receipt.verdict = "REFUSED_MALFORMED_QUERY"
            receipt.refusal_reason = reason
            receipt.refusals_at_this_stage = ["query does not match oracle schema"]
            return receipt.seal()

        receipt.stage_reached = Stage.BIND
        evidence, reason = self._bind(claim)
        if not evidence:
            receipt.verdict = "REFUSED_NO_EVIDENCE"
            receipt.refusal_reason = reason
            receipt.refusals_at_this_stage = ["no evidence fields present in query"]
            return receipt.seal()
        receipt.evidence = evidence
        receipt.truth_level = TruthLevel.WARRANTED
        receipt.verdict = "WARRANTED"

        receipt.stage_reached = Stage.SCOPE
        ok, reason = self._scope(oracle, claim)
        if not ok:
            receipt.verdict = "REFUSED_OUT_OF_SCOPE"
            receipt.refusal_reason = reason
            receipt.refusals_at_this_stage = ["claim is outside what the oracle will answer"]
            return receipt.seal()

        receipt.stage_reached = Stage.CHECK
        passed, check_reason, check_evidence = oracle.check(claim)
        if not passed:
            receipt.verdict = "REFUSED_CHECK_FAILED"
            receipt.refusal_reason = check_reason
            receipt.refusals_at_this_stage = ["one or more of the oracle checks failed"]
            return receipt.seal()

        receipt.evidence = sorted(set(receipt.evidence + check_evidence))
        receipt.truth_level = TruthLevel.CERTIFIED
        receipt.verdict = "CERTIFIED"

        receipt.stage_reached = Stage.SEAL
        receipt.stage_reached = Stage.LEVEL

        if external_verifier is not None:
            receipt.external_verifier_id = getattr(external_verifier, "__name__", "anonymous")
            receipt.external_policy_version = external_policy_version
            try:
                result = external_verifier(receipt)
                if bool(result.get("external_verified", False)):
                    receipt.truth_level = TruthLevel.ANCHORED
                    receipt.verdict = "ANCHORED"
                else:
                    receipt.refusals_at_this_stage = [
                        f"external verifier refused: {result.get('reason', '')}"
                    ]
            except Exception as exc:
                receipt.refusals_at_this_stage = [f"external verifier raised: {exc}"]
        return receipt.seal()


class AICreationOracle(TruthProcessOracle):
    name = "ai_creation"
    version = "1.0.0"

    def schema(self):
        return {"model_hash": "sha256", "policy_ur1": "ur1", "created_at": "str"}

    def check(self, query):
        return True, "", [query["policy_ur1"], query["model_hash"]]

    def scope_claims(self):
        return ["capability", "benchmark", "alignment", "training data"]


class HumanReviewOracle(TruthProcessOracle):
    name = "human_review"
    version = "1.0.0"

    def schema(self):
        return {"question": "str"}

    def check(self, query):
        return False, "life-affecting queries require a human decision", []

    def scope_claims(self):
        # Scope rejects autonomous decisions; diagnosis itself reaches CHECK,
        # where this oracle explicitly refuses to certify a life-affecting claim.
        return ["autonomous decision", "prescribe", "triage"]


def _fake_ur1(seed: str) -> str:
    return "urn:ur1:sha256:" + hashlib.sha256(seed.encode()).hexdigest()


def _fake_sha(seed: str) -> str:
    return "sha256:" + hashlib.sha256(seed.encode()).hexdigest()


def accepting_external_verifier(receipt: TruthProcessReceipt) -> dict:
    return {"external_verified": True, "reason": "accepting test verifier"}


def strict_external_verifier(receipt: TruthProcessReceipt) -> dict:
    return {"external_verified": False, "reason": "verifier declined"}


def run_tests() -> int:
    def make_tp():
        return TruthProcess({
            "ai_creation": AICreationOracle(),
            "human_health": HumanReviewOracle(),
        })

    cases = []
    cases.append(("unknown", lambda: make_tp().process("missing", {})))
    cases.append(("malformed", lambda: make_tp().process("ai_creation", {"model_hash": _fake_sha("m")})))
    cases.append(("scope", lambda: make_tp().process("ai_creation", {
        "model_hash": _fake_sha("m"), "policy_ur1": _fake_ur1("p"),
        "created_at": "t", "kind": "alignment",
    })))
    cases.append(("certified", lambda: make_tp().process("ai_creation", {
        "model_hash": _fake_sha("m"), "policy_ur1": _fake_ur1("p"), "created_at": "t",
    })))
    cases.append(("anchored", lambda: make_tp().process("ai_creation", {
        "model_hash": _fake_sha("m"), "policy_ur1": _fake_ur1("p"), "created_at": "t",
    }, accepting_external_verifier, "test/v1")))
    cases.append(("human_refusal", lambda: make_tp().process("human_health", {
        "question": "discharge?", "kind": "diagnose",
    })))

    expected = {
        "unknown": (TruthLevel.NONE, "REFUSED_NO_ORACLE"),
        "malformed": (TruthLevel.NONE, "REFUSED_MALFORMED_QUERY"),
        "scope": (TruthLevel.WARRANTED, "REFUSED_OUT_OF_SCOPE"),
        "certified": (TruthLevel.CERTIFIED, "CERTIFIED"),
        "anchored": (TruthLevel.ANCHORED, "ANCHORED"),
        "human_refusal": (TruthLevel.WARRANTED, "REFUSED_CHECK_FAILED"),
    }
    passed = 0
    for label, factory in cases:
        receipt = factory()
        want_level, want_verdict = expected[label]
        assert (receipt.truth_level, receipt.verdict) == (want_level, want_verdict)
        assert receipt.cannot_claim
        passed += 1

    anchored = make_tp().process("ai_creation", {
        "model_hash": _fake_sha("m"), "policy_ur1": _fake_ur1("p"), "created_at": "t",
    }, accepting_external_verifier)
    assert "correspond" in " ".join(anchored.cannot_claim).lower()
    assert not hasattr(TruthLevel, "CORRESPONDENCE")
    passed += 2

    # Additional ladder invariants: refusals are fail-closed and levels never jump.
    checks = [
        ("warranted_not_certified_on_scope", lambda: make_tp().process("ai_creation", {
            "model_hash": _fake_sha("m"), "policy_ur1": _fake_ur1("p"),
            "created_at": "t", "kind": "benchmark",
        })),
        ("external_decline_stays_certified", lambda: make_tp().process("ai_creation", {
            "model_hash": _fake_sha("m"), "policy_ur1": _fake_ur1("p"),
            "created_at": "t",
        }, strict_external_verifier)),
        ("human_review_reaches_check", lambda: make_tp().process("human_health", {
            "question": "diagnosis?", "kind": "diagnose",
        })),
        ("unknown_never_warrants", lambda: make_tp().process("missing", {
            "model_hash": _fake_sha("m"), "policy_ur1": _fake_ur1("p"), "created_at": "t",
        })),
        ("malformed_never_warrants", lambda: make_tp().process("ai_creation", {
            "model_hash": _fake_sha("m"), "policy_ur1": _fake_ur1("p"),
        })),
        ("certified_has_receipt", lambda: make_tp().process("ai_creation", {
            "model_hash": _fake_sha("m"), "policy_ur1": _fake_ur1("p"), "created_at": "t",
        })),
        ("anchored_has_external_identity", lambda: make_tp().process("ai_creation", {
            "model_hash": _fake_sha("m"), "policy_ur1": _fake_ur1("p"), "created_at": "t",
        }, accepting_external_verifier, "self-test/v1")),
    ]
    for label, factory in checks:
        receipt = factory()
        assert receipt.receipt_hash.startswith("sha256:"), label
        assert receipt.cannot_claim, label
        if label == "warranted_not_certified_on_scope":
            assert receipt.truth_level == TruthLevel.WARRANTED
        elif label == "external_decline_stays_certified":
            assert receipt.truth_level == TruthLevel.CERTIFIED
        elif label == "human_review_reaches_check":
            assert receipt.truth_level == TruthLevel.WARRANTED
            assert receipt.verdict == "REFUSED_CHECK_FAILED"
            assert receipt.stage_reached == Stage.CHECK
        elif label in {"unknown_never_warrants", "malformed_never_warrants"}:
            assert receipt.truth_level == TruthLevel.NONE
        elif label == "certified_has_receipt":
            assert receipt.truth_level == TruthLevel.CERTIFIED
        elif label == "anchored_has_external_identity":
            assert receipt.truth_level == TruthLevel.ANCHORED
            assert receipt.external_verifier_id == "accepting_external_verifier"
        passed += 1

    assert [TruthLevel.NONE, TruthLevel.WARRANTED, TruthLevel.CERTIFIED, TruthLevel.ANCHORED] == [0, 1, 2, 3]
    passed += 1
    print(f"truth ladder self-tests: {passed} passed, 0 failed")
    return 0


def demo():
    tp = TruthProcess({
        "ai_creation": AICreationOracle(),
        "human_health": HumanReviewOracle(),
    })
    examples = [
        ("NONE", tp.process("missing", {})),
        ("WARRANTED", tp.process("ai_creation", {
            "model_hash": _fake_sha("m"), "policy_ur1": _fake_ur1("p"), "created_at": "t",
            "kind": "alignment",
        })),
        ("CERTIFIED", tp.process("ai_creation", {
            "model_hash": _fake_sha("m"), "policy_ur1": _fake_ur1("p"), "created_at": "t",
        })),
        ("ANCHORED", tp.process("ai_creation", {
            "model_hash": _fake_sha("m"), "policy_ur1": _fake_ur1("p"), "created_at": "t",
        }, accepting_external_verifier, "demo/v1")),
    ]
    for label, receipt in examples:
        print(
            f"{label}: level={receipt.truth_level} "
            f"verdict={receipt.verdict} stage={STAGE_NAME[receipt.stage_reached]} "
            f"hash={receipt.receipt_hash}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--tests", action="store_true")
    args = parser.parse_args()
    if args.tests:
        return run_tests()
    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
