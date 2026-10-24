"""Pre-registered external calibration tester for Epidemic Genesis.

The tester compares the fixed eGi candidate to a standard Bass-style diffusion
baseline on the same observed curve. CKM constrains diffusion only; it does not
identify eGi-specific parameters such as kappa or mutation.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from tools.epidemic_genesis import EpidemicParameters

FIXTURE = Path("evidence/epidemic_calibration/ckm_physicians_innovation_curve.json")
PREREG = Path("evidence/epidemic_calibration/preregistration_v1.json")


def simulate(params: EpidemicParameters, steps: int, *, initial_adopted: float = 0.10) -> list[float]:
    susceptible = max(0.0, 1.0 - initial_adopted)
    exposed = 0.0
    adopted = max(0.0, min(1.0, initial_adopted))
    retained = 0.0
    out: list[float] = []
    for _ in range(steps):
        out.append(adopted + retained)
        force = (
            params.beta * params.contacts * susceptible * adopted
            * params.fidelity * params.trust
        )
        new_exposed = min(susceptible, max(0.0, force))
        susceptible -= new_exposed
        exposed += new_exposed
        trial = min(exposed, max(0.0, params.alpha * exposed))
        exposed -= trial
        accepted = min(trial, max(0.0, params.gamma * trial))
        retained_now = min(
            max(0.0, adopted),
            max(0.0, params.delta * max(0.0, adopted)),
        )
        adopted += accepted - retained_now
        retained += retained_now
    return out


def simulate_bass(p: float, q: float, steps: int, *, initial_adopted: float = 0.10) -> list[float]:
    """Discrete Bass comparator with fixed initial adoption."""
    f = max(0.0, min(1.0, initial_adopted))
    out: list[float] = []
    for _ in range(steps):
        out.append(f)
        f = min(1.0, f + (1.0 - f) * (p + q * f))
    return out


def rmse(actual: Iterable[float], observed: Iterable[float]) -> float:
    pairs = list(zip(actual, observed))
    return (sum((a - b) ** 2 for a, b in pairs) / len(pairs)) ** 0.5


def fit_bass_baseline(observed: list[float]) -> tuple[dict, float, list[float]]:
    prereg = json.loads(PREREG.read_text())["ckm_case"]["baseline"]
    p0, p1, ps = prereg["p_grid"]
    q0, q1, qs = prereg["q_grid"]
    best_error = float("inf")
    best = (p0, q0)
    best_pred: list[float] = []
    p = p0
    while p <= p1 + 1e-12:
        q = q0
        while q <= q1 + 1e-12:
            pred = simulate_bass(p, q, len(observed))
            error = rmse(pred, observed)
            if error < best_error:
                best_error = error
                best = (p, q)
                best_pred = pred
            q += qs
        p += ps
    return {"p": best[0], "q": best[1]}, best_error, best_pred


def calibrate() -> dict:
    fixture = json.loads(FIXTURE.read_text())
    prereg = json.loads(PREREG)["ckm_case"]
    observed = [row["fraction"] for row in fixture["curve"]]

    params = EpidemicParameters(**prereg["eGi_parameters_fixed"])
    predicted = simulate(params, len(observed), initial_adopted=0.10)
    error = rmse(predicted, observed)
    baseline_params, baseline_error, baseline_pred = fit_bass_baseline(observed)
    threshold = prereg["threshold"]

    return {
        "spec": "innovulis-epidemic-genesis-calibration/2.0",
        "fixture": str(FIXTURE),
        "preregistration": str(PREREG),
        "observed_points": len(observed),
        "eGi": {
            "parameters": asdict(params),
            "predicted": [round(v, 6) for v in predicted],
            "rmse": round(error, 6),
            "criterion_pass": error <= threshold,
        },
        "baseline": {
            "model": "discrete Bass-style diffusion recurrence",
            "parameters": baseline_params,
            "predicted": [round(v, 6) for v in baseline_pred],
            "rmse": round(baseline_error, 6),
            "criterion_pass": baseline_error <= threshold,
        },
        "comparison": {
            "eGi_minus_baseline_rmse": round(error - baseline_error, 6),
            "interpretation": (
                "eGi is better than baseline on this curve."
                if error < baseline_error
                else "eGi is not better than baseline on this curve."
            )
        },
        "identifiability": prereg["identifiability"],
        "criterion": {"threshold": threshold, "threshold_status": prereg["threshold_status"]},
        "post_quarantine_protocol": prereg["post_quarantine_protocol"],
        "result": "CALIBRATED" if error <= threshold else "QUARANTINED",
        "eGi_calibration_tier": "VERIFIED_PROCESS" if error <= threshold else "ACTION_REQUIRED",
        "diffusion_submodel_tier": "VERIFIED_PROCESS" if baseline_error <= threshold else "ACTION_REQUIRED",
        "physical_gate": "ACTION_REQUIRED",
        "interpretation": (
            "eGi candidate met the pre-registered threshold."
            if error <= threshold
            else "eGi candidate failed the pre-registered threshold; this is a diffusion-submodel "
                 "calibration result, not a verdict on eGi-specific parameters that CKM cannot identify."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(calibrate(), indent=2, sort_keys=True))
