"""Deterministic heuristic execution-plan adapter."""
from .jcs import jcs, sha
PRECISION_ORDER = {"int8": 0, "fp16": 1, "fp32": 2, "fp64": 3}

def plan_for(device: dict, task: dict) -> dict:
    max_batch, cores = device["limits"]["max_batch"], device["compute"]["cores"]
    batch = min(max_batch, task.get("data_size", max_batch))
    parallel = min(task.get("parallel_preference", 1), cores, 16)
    precision = device["precision"]
    requested = task.get("min_precision", "fp32")
    if PRECISION_ORDER.get(precision, 0) < PRECISION_ORDER.get(requested, 0):
        return {"spec": "buddy-plan/1.0", "feasible": False,
                "reason": f"device precision {precision} < required {requested}"}
    variant = "small" if device["class"] in ("phone", "tv") else "medium" if device["class"] == "laptop" else "large"
    plan = {"spec": "buddy-plan/1.0", "precision": precision, "batch": batch,
            "parallel": parallel, "model_variant": variant, "feasible": True}
    plan["plan_hash"] = sha(jcs(plan))
    return plan
