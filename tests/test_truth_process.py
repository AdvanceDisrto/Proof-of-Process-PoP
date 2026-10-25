from truth_process import (
    AICreationOracle,
    HumanReviewOracle,
    STAGE_NAME,
    TruthLevel,
    TruthProcess,
    accepting_external_verifier,
    _fake_sha,
    _fake_ur1,
)


def oracle():
    return TruthProcess({
        "ai_creation": AICreationOracle(),
        "human_health": HumanReviewOracle(),
    })


def ai_claim(**extra):
    value = {
        "model_hash": _fake_sha("model"),
        "policy_ur1": _fake_ur1("policy"),
        "created_at": "2026-10-25T00:00:00Z",
    }
    value.update(extra)
    return value


def test_unknown_section_is_none():
    r = oracle().process("missing", {})
    assert r.truth_level == TruthLevel.NONE
    assert r.stage_reached == 0
    assert r.verdict == "REFUSED_NO_ORACLE"


def test_malformed_query_is_none():
    r = oracle().process("ai_creation", {"model_hash": _fake_sha("model")})
    assert r.truth_level == TruthLevel.NONE
    assert r.verdict == "REFUSED_MALFORMED_QUERY"


def test_valid_evidence_reaches_warranted():
    r = oracle().process("ai_creation", ai_claim(kind="alignment"))
    assert r.truth_level == TruthLevel.WARRANTED
    assert r.verdict == "REFUSED_OUT_OF_SCOPE"
    assert r.stage_reached == 3
    assert r.cannot_claim


def test_certified_requires_oracle_checks():
    r = oracle().process("ai_creation", ai_claim())
    assert r.truth_level == TruthLevel.CERTIFIED
    assert r.verdict == "CERTIFIED"
    assert r.stage_reached == 6
    assert r.cannot_claim


def test_external_verifier_can_reach_anchored():
    r = oracle().process("ai_creation", ai_claim(), accepting_external_verifier, "test/v1")
    assert r.truth_level == TruthLevel.ANCHORED
    assert r.verdict == "ANCHORED"
    assert r.external_verifier_id == "accepting_external_verifier"
    assert r.external_policy_version == "test/v1"
    assert "correspond" in " ".join(r.cannot_claim).lower()


def test_external_decline_stays_certified():
    def decline(_):
        return {"external_verified": False, "reason": "declined"}

    r = oracle().process("ai_creation", ai_claim(), decline)
    assert r.truth_level == TruthLevel.CERTIFIED
    assert r.verdict == "CERTIFIED"
    assert r.refusals_at_this_stage


def test_human_health_is_warranted_but_not_certified():
    r = oracle().process("human_health", {"question": "diagnosis?", "evidence_hash": _fake_sha("human-review-evidence"), "kind": "diagnose"})
    assert r.truth_level == TruthLevel.WARRANTED
    assert r.verdict == "REFUSED_CHECK_FAILED"


def test_no_correspondence_rung_exists():
    assert not hasattr(TruthLevel, "CORRESPONDENCE")
    assert max(TruthLevel.NONE, TruthLevel.WARRANTED, TruthLevel.CERTIFIED, TruthLevel.ANCHORED) == 3


def test_receipt_hash_present_and_manifest_nonempty():
    r = oracle().process("ai_creation", ai_claim())
    assert r.receipt_hash.startswith("sha256:")
    assert r.cannot_claim
    assert STAGE_NAME[r.stage_reached] == "level"
