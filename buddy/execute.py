"""Deterministic compute task whose result depends on selected precision."""
import hashlib
from .jcs import jcs, sha

def _expand(seed_str: str, n: int) -> list[float]:
    buf = hashlib.sha256(f"{seed_str}:{n}".encode()).digest()
    values: list[float] = []
    while len(values) < n:
        for b in buf:
            values.append(b / 255.0)
            if len(values) >= n: break
        buf = hashlib.sha256(buf).digest()
    return values

def run_task(task: dict, plan: dict) -> dict:
    if not plan.get("feasible"):
        return {"error": plan.get("reason", "infeasible"), "output_hash": None}
    n, precision, batch = task.get("size", 128), plan["precision"], plan["batch"]
    seed_str = task.get("seed", "buddy-task")
    values = _expand(seed_str, n)
    half = n // 2
    a, b = values[:half], values[half:2*half]
    if precision == "fp64":
        result = sum(x*y for x, y in zip(a,b))
    elif precision == "fp32":
        result = round(sum(round(x*y, 6) for x,y in zip(a,b)), 6)
    else:
        result = sum(int(x*127)*int(y*127) for x,y in zip(a,b))
    output = {"result": result, "precision": precision, "batch": batch, "n": n, "mode": "dot_product"}
    return {"output": output, "input_hash": sha(jcs({"seed": seed_str, "n": n})),
            "output_hash": sha(jcs(output))}
