"""i™ iWay local adapter contract into existing CIH KRDID receipt API.

A narrow, non-deploying reference: 24 Linux labels, static ARC fixture,
geometry, consent gate and honest measurement metadata. No vendor API, live
LLM, untrusted code execution, TEE, device attestation or sanctions clearance.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
import time
import tracemalloc

PROFILE_NAMES = (
    "Ubuntu", "CentOS", "Debian", "Fedora", "Slackware", "Mint",
    "Xubuntu", "Arch", "openSUSE", "RedHat", "Slackel", "PureOS",
    "Mageia", "PCLinuxOS", "Puppy", "Zorin", "BunsenLabs", "Kubuntu",
    "Manjaro", "Neptune", "Bodhi", "Netrunner", "Kali", "Lubuntu",
)
assert len(PROFILE_NAMES) == len(set(PROFILE_NAMES)) == 24
SCHEMA = "innovulis.iway.local-spu-ispu-v1"
FIXTURE_RULES = ("invert_01", "identity", "horizontal_flip", "vertical_flip")
POLICIES = {
    "US": {"policy": "US_TEST_LABEL_v1", "residency": "NOT_ENFORCED"},
    "DE": {"policy": "EU_TEST_LABEL_v1", "residency": "NOT_ENFORCED"},
    "FR": {"policy": "EU_TEST_LABEL_v1", "residency": "NOT_ENFORCED"},
    "GB": {"policy": "UK_TEST_LABEL_v1", "residency": "NOT_ENFORCED"},
    "JP": {"policy": "JP_TEST_LABEL_v1", "residency": "NOT_ENFORCED"},
    "SG": {"policy": "SG_TEST_LABEL_v1", "residency": "NOT_ENFORCED"},
}


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def policy_hash(country):
    if country not in POLICIES:
        raise ValueError("NO_REVIEWED_ROUTE_LABEL")
    return digest(POLICIES[country])


def linux_inventory():
    return {"names": list(PROFILE_NAMES), "count": 24,
            "inventory_sha256": digest(list(PROFILE_NAMES)),
            "runtime_tested": 0, "deployed": 0, "profile_scope": "LABELS_ONLY"}


def identify_os_release(text):
    """Parse OS data WITHOUT eval/source/install. A string is not hardware proof."""
    if not isinstance(text, str) or len(text.encode("utf-8")) > 16384 or "\x00" in text:
        raise ValueError("INVALID_OS_RELEASE")
    fields = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        k, sep, v = line.partition("=")
        if not sep or not re.fullmatch("[A-Z][A-Z0-9_]*", k) or k in fields:
            raise ValueError("MALFORMED_OS_RELEASE")
        fields[k] = v.strip().strip('"').strip("'")
    distro = fields.get("NAME", "")
    match = next((name for name in PROFILE_NAMES if name.lower() == distro.lower()), None)
    return {"os_id": fields.get("ID", ""), "declared_profile": match,
            "level": "SELF_REPORTED_PROFILE_ONLY" if match else "NOT_EXACTLY_IDENTIFIED",
            "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "hardware_identity": "NOT_ATTESTED"}


def grid_ok(g):
    return isinstance(g, list) and 1 <= len(g) <= 30 and all(
        isinstance(row, list) and len(row) == len(g[0]) and 1 <= len(row) <= 30
        and all(type(v) is int and 0 <= v <= 9 for v in row) for row in g)


def transform(g, rule):
    if rule == "invert_01":
        if any(v not in (0, 1) for row in g for v in row):
            return None
        return [[1-v for v in row] for row in g]
    if rule == "identity":
        return [row[:] for row in g]
    if rule == "horizontal_flip":
        return [row[::-1] for row in g]
    if rule == "vertical_flip":
        return [row[:] for row in g[::-1]]
    return None


def static_arc(task):
    """Bounded DSL candidate search; NOT ARC-AGI-3 or unknown benchmark score."""
    pairs, tests = task.get("train"), task.get("test")
    if not isinstance(pairs, list) or not 1 <= len(pairs) <= 10 or not isinstance(tests, list) or not 1 <= len(tests) <= 3:
        return {"status": "REFUSED", "reason": "INVALID_ARC_STRUCTURE"}
    if any(not isinstance(p, dict) or not grid_ok(p.get("input")) or not grid_ok(p.get("output")) for p in pairs):
        return {"status": "REFUSED", "reason": "INVALID_TRAIN_GRID"}
    if any(not isinstance(t, dict) or not grid_ok(t.get("input")) for t in tests):
        return {"status": "REFUSED", "reason": "INVALID_TEST_GRID"}
    choices = []
    for rule in FIXTURE_RULES:
        if all(transform(p["input"], rule) == p["output"] for p in pairs):
            predictions = [transform(t["input"], rule) for t in tests]
            if all(grid_ok(prediction) for prediction in predictions):
                choices.append((rule, predictions))
    if not choices:
        return {"status": "REFUSED", "reason": "NO_RULE_MATCHED"}
    if len({digest(p) for _, p in choices}) != 1:
        return {"status": "REFUSED", "reason": "AMBIGUOUS_TEST_PREDICTIONS",
                "candidate_rules": [r for r, _ in choices]}
    if any("output" in t and t["output"] != choices[0][1][i] for i, t in enumerate(tests)):
        return {"status": "REFUSED", "reason": "PUBLIC_FIXTURE_MISMATCH"}
    return {"status": "TRAINING_AND_CONSENSUS_ONLY",
            "candidate_rules": [r for r, _ in choices],
            "predictions": choices[0][1], "scored_official_benchmark": False}


def geometry_arc(task):
    r, a, unit = task.get("radius"), task.get("angle"), task.get("unit")
    if type(r) not in (int, float) or type(a) not in (int, float) or not (
        math.isfinite(r) and math.isfinite(a) and r > 0 and a >= 0):
        return {"status": "REFUSED", "reason": "INVALID_GEOMETRY"}
    if unit not in ("degrees", "radians"):
        return {"status": "REFUSED", "reason": "INVALID_ANGLE_UNIT"}
    if a > (360 if unit == "degrees" else 2*math.pi):
        return {"status": "REFUSED", "reason": "MORE_THAN_ONE_REVOLUTION"}
    return {"status": "FORMULA_EVALUATED",
            "arc_length": r*a*math.pi/180 if unit == "degrees" else r*a,
            "unit": unit, "formula": "s=r*theta; theta in radians"}


def local_work(task_type, task, *, os_release_text, country,
               context_source, accepted_policy_sha256, training_opt_in=False):
    """Evidence-gated local work only. No third-party provider calls."""
    start_wall, start_cpu = time.perf_counter_ns(), time.process_time_ns()
    tracemalloc.start()
    _, old_peak = tracemalloc.get_traced_memory()
    if country not in POLICIES or context_source != "OPERATOR_TEST_FIXTURE":
        state, result = "REFUSED", {"reason": "JURISDICTION_CONTEXT_NOT_VERIFIED"}
    elif policy_hash(country) != accepted_policy_sha256:
        state, result = "REFUSED", {"reason": "POLICY_CONSENT_DIGEST_MISMATCH"}
    elif task_type == "ARC_GRID":
        result = static_arc(task)
        state = "EXECUTED" if result["status"] == "TRAINING_AND_CONSENSUS_ONLY" else "REFUSED"
    elif task_type == "ARC_LENGTH":
        result = geometry_arc(task)
        state = "EXECUTED" if result["status"] == "FORMULA_EVALUATED" else "REFUSED"
    else:
        state, result = "REFUSED", {"reason": "UNSUPPORTED_TASK"}
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    work = {
        "schema": SCHEMA,
        "stages": ["ROUTING", "AUDITING", "VERIFYING", "MEASURING", "SEALING"],
        "task_type": task_type, "task_digest_sha256": digest(task),
        "result": result, "status": state,
        "jurisdiction": {"claimed": country, "source": context_source,
                         "policy_hash": policy_hash(country) if country in POLICIES else None,
                         "legal_effect": "NONE_TEST_FIXTURE"},
        "consent": {"policy_digest_matched": country in POLICIES and
                    accepted_policy_sha256 == policy_hash(country),
                    "user_consent_proven": False,
                    "training_opt_in": training_opt_in is True and state == "EXECUTED",
                    "training_ingestion": "NOT_CONNECTED"},
        "node": identify_os_release(os_release_text),
        "linux_profiles": linux_inventory()["inventory_sha256"],
        "measurement": {"wall_elapsed_ns": time.perf_counter_ns()-start_wall,
                        "cpu_process_elapsed_ns": time.process_time_ns()-start_cpu,
                        "tracemalloc_python_peak_bytes": max(0, peak-old_peak),
                        "cpu_cycles": {"status":"NOT_MEASURED", "value":None},
                        "energy_joules": {"status":"NOT_MEASURED", "value":None}},
        "provider": "LOCAL_SOFTWARE_CPU_ONLY",
        "cloud_deployed": False, "gpu_attested": False,
        "arc_agi3": "NOT_EXECUTED",
        "ots_bitcoin": "NOT_ANCHORED",
        "does_not_prove": ["source truth", "hardware identity", "legal compliance",
                           "physical energy consumption", "24 real deployed Linux nodes",
                           "official ARC benchmark performance"],
    }
    return work


def to_existing_cih_request(evidence):
    """Prepare, but do not sign or submit, the real /api/v1/receipts schema."""
    return {
        "claim": "Local iWay software work; not independently verified physical execution",
        "evidence": evidence,
        "expected_evidence_sha256": digest(evidence),
        "source_id": "iway-local-contract",
        "parent_receipt_hashes": [],
    }
