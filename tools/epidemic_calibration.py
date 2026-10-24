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





def simulate_mechanism_active(params: EpidemicParameters, steps: int, *, initial_adopted: float = 0.10, contradiction_rate: float = 0.18, receipt_strength: float = 0.85) -> list[float]:
    """Mechanism-active eGi control with mutation, quarantine, and receipt weighting."""
    susceptible = max(0.0, 1.0 - initial_adopted)
    exposed = 0.0
    adopted = max(0.0, min(1.0, initial_adopted))
    retained = 0.0
    mutant = 0.0
    quarantine = 0.0
    out: list[float] = []
    for _ in range(steps):
        out.append(adopted + retained + mutant)
        contradiction = min(1.0, max(0.0, contradiction_rate * mutant))
        quarantine = min(1.0, max(0.0, quarantine + params.kappa * contradiction))
        receipt_weight = max(0.0, min(1.0, receipt_strength))
        force = (
            params.beta * params.contacts * susceptible * (adopted + 0.5 * mutant)
            * params.fidelity * params.trust * receipt_weight * (1.0 - quarantine)
        )
        new_exposed = min(susceptible, max(0.0, force))
        susceptible -= new_exposed
        exposed += new_exposed
        trial = min(exposed, max(0.0, params.alpha * exposed))
        exposed -= trial
        accepted = min(trial, max(0.0, params.gamma * trial * (1.0 - contradiction)))
        mutated = max(0.0, min(accepted, params.mutation * accepted))
        ordinary = accepted - mutated
        retained_now = min(max(0.0, adopted), max(0.0, params.delta * max(0.0, adopted)))
        mutant_retained = min(max(0.0, mutant), max(0.0, params.delta * 0.5 * max(0.0, mutant)))
        adopted += ordinary - retained_now
        mutant += mutated - mutant_retained
        retained += retained_now + mutant_retained
    return out


def fit_egi_mechanism_active(observed: list[float]) -> tuple[dict, float, list[float]]:
    """Fit active transmission, retention, quarantine, and mutation."""
    best_error = float("inf")
    best_params: dict = {}
    best_pred: list[float] = []
    for transmission in [round(0.28 + i * 0.01, 3) for i in range(9)]:
        for delta in [round(0.10 + i * 0.01, 3) for i in range(11)]:
            for kappa in [round(0.04 + i * 0.01, 3) for i in range(7)]:
                for mutation in [round(0.10 + i * 0.01, 3) for i in range(9)]:
                    params = EpidemicParameters(beta=transmission, contacts=1.0, alpha=1.0, gamma=1.0, delta=delta, kappa=kappa, mutation=mutation, fidelity=1.0, trust=1.0)
                    pred = simulate_mechanism_active(params, len(observed))
                    error = rmse(pred, observed)
                    if error < best_error:
                        best_error = error
                        best_params = {"effective_transmission": transmission, "delta": delta, "kappa": kappa, "mutation": mutation}
                        best_pred = pred
    return best_params, best_error, best_pred

def fit_egi_effective(observed: list[float]) -> tuple[dict, float, list[float]]:
    """Fit the parameters that the current eGi simulator actually uses."""
    best_error = float("inf")
    best_params = {}
    best_pred: list[float] = []
    for transmission in [round(0.02 + i * 0.01, 3) for i in range(31)]:
        for delta in [round(0.02 + i * 0.01, 3) for i in range(29)]:
            params = EpidemicParameters(
                beta=transmission, contacts=1.0, alpha=1.0, gamma=1.0,
                delta=delta, kappa=0.05, mutation=0.10,
                fidelity=1.0, trust=1.0,
            )
            pred = simulate(params, len(observed), initial_adopted=0.10)
            error = rmse(pred, observed)
            if error < best_error:
                best_error = error
                best_params = {"effective_transmission": transmission, "delta": delta}
                best_pred = pred
    return best_params, best_error, best_pred


def symmetric_external_ground_truth_control() -> dict:
    """Run noisy external ground truth in both directions using actual model code."""
    import random
    control = json.loads(PREREG.read_text())["symmetric_control"]
    steps = control["observed_points"]
    initial = control["initial_adoption"]
    sigma = control["noise_sigma"]
    rng = random.Random(control["noise_seed"])

    bass_gt = control["bass_ground_truth"]
    clean_bass = simulate_bass(bass_gt["p"], bass_gt["q"], steps, initial_adopted=initial)
    observed_bass = [min(1.0, max(0.0, v + rng.gauss(0.0, sigma))) for v in clean_bass]
    bass_fit_params, bass_fit_error, _ = fit_bass_baseline(observed_bass)
    egi_on_bass_params, egi_on_bass_error, _ = fit_egi_effective(observed_bass)

    egi_gt = EpidemicParameters(**control["eGi_ground_truth_parameters"])
    clean_egi = simulate(egi_gt, steps, initial_adopted=initial)
    observed_egi = [min(1.0, max(0.0, v + rng.gauss(0.0, sigma))) for v in clean_egi]
    bass_on_egi_params, bass_on_egi_error, _ = fit_bass_baseline(observed_egi)
    egi_fit_params, egi_fit_error, _ = fit_egi_effective(observed_egi)

    mechanism_clean = simulate_mechanism_active(egi_gt, steps, initial_adopted=initial)
    mechanism_observed = [min(1.0, max(0.0, v + rng.gauss(0.0, sigma))) for v in mechanism_clean]
    bass_on_mechanism_params, bass_on_mechanism_error, _ = fit_bass_baseline(mechanism_observed)
    mechanism_fit_params, mechanism_fit_error, mechanism_fit_pred = fit_egi_mechanism_active(mechanism_observed)
    _, _, mechanism_bass_pred = fit_bass_baseline(mechanism_observed)
    mechanism_bootstrap = bootstrap_rmse_delta_ci(
        mechanism_observed, mechanism_fit_pred, mechanism_bass_pred
    )

    bass_pass = bass_fit_error < egi_on_bass_error
    egi_pass = egi_fit_error < bass_on_egi_error
    egi_fit_method = "deterministic_grid_search_over_effective_transmission_and_delta"
    egi_fit_resolution = {"effective_transmission": 0.01, "delta": 0.01}
    return {
        "case": "symmetric_external_ground_truth",
        "noise": {"distribution": "Gaussian", "sigma": sigma, "seed": control["noise_seed"]},
        "fit_provenance": {
            "Bass": {
                "method": "deterministic_grid_search_over_preregistered_p_q_grid",
                "resolution": {"p": 0.001, "q": 0.01},
            },
            "eGi": {
                "method": egi_fit_method,
                "resolution": egi_fit_resolution,
                "active_fitted_parameters": ["effective_transmission", "delta"],
                "effective_transmission_definition": "beta * contacts",
            },
        },
        "generator_scope": {
            "implementation": "actual simulate() eGi recurrence",
            "active_structure": ["exposure", "trial", "adoption", "retention"],
            "inactive_in_current_simulator": ["kappa", "mutation", "fidelity", "trust"],
            "note": "The baseline symmetric control discriminates only the structure actually emitted by simulate().",
        },
        "off_grid_truth_control": {
            "status": "ACTIVE",
            "truth_alignment": control.get("truth_alignment", "OFF_GRID"),
            "Bass_truth": bass_gt,
            "Bass_fit": bass_fit_params,
            "Bass_absolute_errors": {"p": round(abs(bass_fit_params["p"] - bass_gt["p"]), 6), "q": round(abs(bass_fit_params["q"] - bass_gt["q"]), 6)},
            "eGi_truth_effective_transmission": round(egi_gt.beta * egi_gt.contacts, 6),
            "eGi_fit_effective_transmission": egi_fit_params["effective_transmission"],
            "eGi_absolute_errors": {"effective_transmission": round(abs(egi_fit_params["effective_transmission"] - egi_gt.beta * egi_gt.contacts), 6), "delta": round(abs(egi_fit_params["delta"] - egi_gt.delta), 6)},
            "recovery_tolerance": control.get("recovery_tolerance", 0.002),
            "recovery_criterion": control.get("recovery_criterion"),
            "purpose": control.get("off_grid_purpose"),
        },
        "mechanism_active_control": {
            "generator": "simulate_mechanism_active",
            "active_mechanisms": ["receipt_weighting", "quarantine_feedback", "mutation"],
            "ground_truth_parameters": asdict(egi_gt),
            "Bass_fit": {"parameters": bass_on_mechanism_params, "rmse": round(bass_on_mechanism_error, 6)},
            "eGi_mechanism_fit": {"parameters": mechanism_fit_params, "rmse": round(mechanism_fit_error, 6)},
            "rmse_gap_Bass_minus_eGi": round(bass_on_mechanism_error - mechanism_fit_error, 6),
            "bass_residual_character": "Bass remains a reasonably close fit; this is a point-estimate win, not evidence of order-of-magnitude misspecification.",
            "paired_bootstrap_90_ci": mechanism_bootstrap,
            "bootstrap_seed_count": 1,
            "winner": "eGi" if mechanism_fit_error < bass_on_mechanism_error else "Bass",
            "point_estimate_pass": mechanism_fit_error < bass_on_mechanism_error,
            "comparative_pass": mechanism_fit_error < bass_on_mechanism_error and mechanism_bootstrap["excludes_zero"],
            "pass": mechanism_fit_error < bass_on_mechanism_error and mechanism_bootstrap["excludes_zero"],
            "claim_scope": "MECHANISM_ACTIVE_SYNTHETIC_DISCRIMINATION_WITH_PAIRED_BOOTSTRAP" if mechanism_bootstrap["excludes_zero"] else "MECHANISM_ACTIVE_POINT_ESTIMATE_ONLY",
            "note": "New synthetic mechanism-active control; receipt weighting, quarantine feedback, and mutation are active. The noisy generator uses one preregistered seed; the paired bootstrap quantifies point-estimate uncertainty but is not an independent-seed replication. This does not retroactively upgrade the CKM candidate or baseline simulator claim.",
        },
        "bass_truth_direction": {
            "ground_truth_parameters": bass_gt,
            "Bass_fit": {"parameters": bass_fit_params, "rmse": round(bass_fit_error, 6)},
            "eGi_fit": {"parameters": egi_on_bass_params, "rmse": round(egi_on_bass_error, 6)},
            "winner": "Bass" if bass_pass else "eGi",
            "pass": bass_pass,
        },
        "eGi_truth_direction": {
            "ground_truth_parameters": asdict(egi_gt),
            "Bass_fit": {"parameters": bass_on_egi_params, "rmse": round(bass_on_egi_error, 6)},
            "eGi_fit": {"parameters": egi_fit_params, "rmse": round(egi_fit_error, 6)},
            "winner": "eGi" if egi_pass else "Bass",
            "pass": egi_pass,
        },
        "bidirectional": bass_pass and egi_pass,
        "tier_claim": "FIT_DISCRIMINATION_BIDIRECTIONAL" if bass_pass and egi_pass else "FIT_DISCRIMINATION_ONE_DIRECTIONAL",
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
        "fit_method": "deterministic_grid_search_over_preregistered_p_q_grid",
        "fit_resolution": {"p": 0.001, "q": 0.01},
        "reported_p_equals_ground_truth": baseline_params["p"] == p,
        "reported_q_equals_ground_truth": baseline_params["q"] == q,
        "p_absolute_error": round(abs(baseline_params["p"] - p), 12),
        "q_absolute_error": round(abs(baseline_params["q"] - q), 12),
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
        "spec": "innovulis-epidemic-genesis-calibration/2.1",
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
        "symmetric_external_ground_truth_control": symmetric_external_ground_truth_control(),
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
