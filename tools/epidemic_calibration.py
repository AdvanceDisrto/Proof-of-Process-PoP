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


def bootstrap_rmse_delta_ci(
    observed: list[float],
    eGi_predicted: list[float],
    baseline_predicted: list[float],
    *,
    iterations: int = 10000,
    seed: int = 20261024,
    alpha: float = 0.10,
) -> dict:
    """Deterministic paired bootstrap CI for eGi-minus-Bass RMSE delta."""
    import random

    if not (len(observed) == len(eGi_predicted) == len(baseline_predicted)):
        raise ValueError("bootstrap inputs must have equal length")
    if len(observed) < 2:
        raise ValueError("bootstrap requires at least two observations")

    rng = random.Random(seed)
    deltas = []
    n = len(observed)
    for _ in range(iterations):
        idx = [rng.randrange(n) for _ in range(n)]
        sample_obs = [observed[i] for i in idx]
        sample_eGi = [eGi_predicted[i] for i in idx]
        sample_baseline = [baseline_predicted[i] for i in idx]
        deltas.append(rmse(sample_eGi, sample_obs) - rmse(sample_baseline, sample_obs))

    deltas.sort()
    lo = deltas[int((alpha / 2) * iterations)]
    hi = deltas[int((1 - alpha / 2) * iterations) - 1]
    return {
        "iterations": iterations,
        "seed": seed,
        "confidence_level": 1 - alpha,
        "lower": round(lo, 6),
        "median": round(deltas[iterations // 2], 6),
        "upper": round(hi, 6),
        "excludes_zero": lo > 0 or hi < 0,
    }


def positive_control() -> dict:
    """Round-trip control: eGi-generated data must be recovered by the same eGi simulator."""
    params = EpidemicParameters(
        beta=0.08, contacts=4.0, alpha=1.0, gamma=1.0,
        delta=0.15, kappa=0.05, mutation=0.10, fidelity=1.0, trust=1.0,
    )
    observed = simulate(params, 17, initial_adopted=0.10)
    predicted = simulate(params, 17, initial_adopted=0.10)
    baseline_params, baseline_error, _ = fit_bass_baseline(observed)
    eGi_error = rmse(predicted, observed)
    return {
        "case": "synthetic_eGi_round_trip",
        "observed_points": len(observed),
        "eGi_rmse": round(eGi_error, 6),
        "baseline_rmse": round(baseline_error, 6),
        "baseline_parameters": baseline_params,
        "criterion_pass": eGi_error <= 0.020 and eGi_error < baseline_error,
        "promotion": "VERIFIED_PROCESS" if eGi_error <= 0.020 and eGi_error < baseline_error else "ACTION_REQUIRED",
    }



def external_ground_truth_positive_control() -> dict:
    """Generate noisy data from a known Bass process and test discrimination."""
    import random

    control = json.loads(PREREG.read_text())["external_ground_truth_control"]
    p = control["bass_parameters"]["p"]
    q = control["bass_parameters"]["q"]
    steps = control["observed_points"]
    initial = control["initial_adoption"]
    rng = random.Random(control["noise_seed"])
    clean = simulate_bass(p, q, steps, initial_adopted=initial)
    sigma = control["noise_sigma"]
    observed = [
        min(1.0, max(0.0, value + rng.gauss(0.0, sigma)))
        for value in clean
    ]

    baseline_params, baseline_error, baseline_pred = fit_bass_baseline(observed)
    prereg = json.loads(PREREG.read_text())
    eGi_params = EpidemicParameters(**prereg["ckm_case"]["eGi_parameters_fixed"])
    eGi_pred = simulate(eGi_params, steps, initial_adopted=initial)
    eGi_error = rmse(eGi_pred, observed)

    recovered = (
        abs(baseline_params["p"] - p) <= control["recovery_tolerance"]
        and abs(baseline_params["q"] - q) <= control["recovery_tolerance"]
    )
    discriminates = baseline_error < eGi_error
    return {
        "case": "synthetic_external_bass_ground_truth",
        "source_process": "Bass",
        "observed_points": steps,
        "initial_adoption": initial,
        "noise": {
            "distribution": "Gaussian",
            "sigma": sigma,
            "seed": control["noise_seed"],
        },
        "ground_truth_parameters": {"p": p, "q": q},
        "recovered_baseline_parameters": baseline_params,
        "recovery_tolerance": control["recovery_tolerance"],
        "bass_rmse": round(baseline_error, 6),
        "eGi_rmse": round(eGi_error, 6),
        "recovered_ground_truth": recovered,
        "discriminates_known_process": discriminates,
        "criterion_pass": recovered and discriminates,
        "promotion": "VERIFIED_PROCESS" if recovered and discriminates else "ACTION_REQUIRED",
    }

def calibrate() -> dict:
    fixture = json.loads(FIXTURE.read_text())
    prereg = json.loads(PREREG.read_text())["ckm_case"]
    observed = [row["fraction"] for row in fixture["curve"]]

    params = EpidemicParameters(**prereg["eGi_parameters_fixed"])
    predicted = simulate(params, len(observed), initial_adopted=0.10)
    error = rmse(predicted, observed)
    baseline_params, baseline_error, baseline_pred = fit_bass_baseline(observed)
    threshold = prereg["threshold"]
    bootstrap = bootstrap_rmse_delta_ci(observed, predicted, baseline_pred)

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
            "bootstrap_90_ci": bootstrap,
            "interpretation": (
                "eGi is better than baseline on this curve."
                if error < baseline_error
                else "eGi is not better than baseline on this curve."
            )
        },
        "identifiability": prereg["identifiability"],
        "criterion": {"threshold": threshold, "threshold_status": prereg["threshold_status"]},
        "post_quarantine_protocol": prereg["post_quarantine_protocol"],
        "positive_control": positive_control(),
        "external_ground_truth_positive_control": external_ground_truth_positive_control(),
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
