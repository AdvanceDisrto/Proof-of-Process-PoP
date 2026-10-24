import hashlib, json, time

CAP = 1.15

def jcs(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()

def sha(b):
    return "sha256:" + hashlib.sha256(b).hexdigest()

def state(s):
    return getattr(s, "name", str(s)).upper()

def _levels(raw):
    if hasattr(raw, "__dict__") and not isinstance(raw, dict):
        raw = raw.__dict__
    levels = raw.get("levels") or raw.get("level_results") or raw.get("results") or []
    if levels:
        return levels
    envs = raw.get("environments") or []
    if not envs:
        return []
    env = envs[0] if isinstance(envs[0], dict) else {}
    runs = env.get("runs") or []
    if not runs:
        return []
    run = runs[-1]
    acts = run.get("level_actions") or []
    bases = run.get("level_baseline_actions") or []
    completed = int(run.get("levels_completed", 0) or 0)
    return [
        {
            "level": i + 1,
            "state": "WIN" if i < completed else run.get("state", "UNKNOWN"),
            "actions": int(a or 0),
            "human_baseline": bases[i] if i < len(bases) else None,
        }
        for i, a in enumerate(acts)
    ]

def level_rhae(h, a, s):
    if s != "WIN":
        return 0.0, "not_won"
    if h is None:
        return 0.0, "no_baseline"
    if a <= 0:
        return 0.0, "no_actions"
    return min((h / a) ** 2, CAP), "ok"

def build(raw, game, baseline):
    rows = []
    for i, x in enumerate(_levels(raw), 1):
        if hasattr(x, "__dict__") and not isinstance(x, dict):
            x = x.__dict__
        level = int(x.get("level", i))
        actions = int(x.get("actions", x.get("action_count", 0)) or 0)
        s = state(x.get("state", "UNKNOWN"))
        h = x.get("human_baseline")
        if h is None:
            h = baseline.get(str(level))
        rhae, why = level_rhae(h, actions, s)
        rows.append({
            "game": game,
            "level": level,
            "state": s,
            "agent_actions": actions,
            "human_baseline": h,
            "rhae": round(rhae, 6),
            "rhae_reason": why,
            "tier": "VERIFIED_PROCESS" if why == "ok" else "ACTION_REQUIRED",
            "gate": "ACTION_REQUIRED",
        })
    num = sum(x["level"] * x["rhae"] for x in rows)
    den = sum(x["level"] for x in rows) or 1
    receipt = {
        "spec": "innovulis-arc-agi-3/1.0",
        "issued_utc": time.time(),
        "game": game,
        "levels": rows,
        "game_rhae_weighted": round(num / den, 6),
        "levels_completed": sum(x["tier"] == "VERIFIED_PROCESS" for x in rows),
        "levels_total": len(rows),
        "physical_gate": "ACTION_REQUIRED",
        "the_central_rule": "A level that did not WIN is not a solved level.",
    }
    receipt["receipt_sha256"] = sha(jcs(receipt))
    return receipt

def verify(r):
    errors = []
    body = {k: v for k, v in r.items() if k != "receipt_sha256"}
    if sha(jcs(body)) != r.get("receipt_sha256"):
        errors.append("receipt_sha256_mismatch")
    rows = r.get("levels", [])
    for x in rows:
        expected_rhae, why = level_rhae(
            x.get("human_baseline"),
            int(x.get("agent_actions", 0)),
            x.get("state"),
        )
        if abs(expected_rhae - x.get("rhae", -1)) > 1e-9:
            errors.append(f"rhae_mismatch:{x.get('level')}")
        expected_tier = "VERIFIED_PROCESS" if why == "ok" else "ACTION_REQUIRED"
        if x.get("tier") != expected_tier:
            errors.append(f"tier_mismatch:{x.get('level')}")
        if x.get("gate") != "ACTION_REQUIRED":
            errors.append(f"gate_open:{x.get('level')}")
    num = sum(x["level"] * x["rhae"] for x in rows)
    den = sum(x["level"] for x in rows) or 1
    if abs(num / den - r.get("game_rhae_weighted", -1)) > 1e-6:
        errors.append("weighted_rhae_mismatch")
    if sum(x.get("tier") == "VERIFIED_PROCESS" for x in rows) != r.get("levels_completed"):
        errors.append("levels_completed_mismatch")
    if r.get("physical_gate") != "ACTION_REQUIRED":
        errors.append("physical_gate_not_closed")
    return {"ok": not errors, "errors": errors}
