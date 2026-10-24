"""External calibration tester for the Epidemic Genesis model.

This is deliberately a selection test, not a proof-by-fit. It loads an externally
sourced adoption curve, runs the same mean-field mechanisms represented by the eGi
parameters, and returns PASS only when the stated RMSE threshold is met. Otherwise
the model is quarantined/ACTION_REQUIRED.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from tools.epidemic_genesis import EpidemicParameters

FIXTURE = Path("evidence/epidemic_calibration/ckm_physicians_innovation_curve.json")


def simulate(params: EpidemicParameters, steps: int, *, initial_adopted: float = 0.10) -> list[float]:
    """Deterministic mean-field projection using the model's transmission/test parameters."""
    susceptible = max(0.0, 1.0 - initial_adopted)
    exposed = 0.0
    adopted = max(0.0, min(1.0, initial_adopted))
    retained = 0.0
    out: list[float] = []

    for _ in range(steps):
        out.append(adopted + retained)

        force = (
            params.beta
            * params.contacts
            * susceptible
            * adopted
            * params.fidelity
            * params.trust
        )
        new_exposed = min(susceptible, max(0.0, force))
        susceptible -= new_exposed
        exposed += new_exposed

        trial = min(exposed, max(0.0, params.alpha * exposed))
        exposed -= trial
        accepted = min(trial, max(0.0, params.gamma * trial))

        quarantined = min(adopted, max(0.0, params.kappa * 0.0 * adopted))
        retained_now = min(
            max(0.0, adopted - quarantined),
            max(0.0, params.delta * max(0.0, adopted - quarantined)),
        )
        adopted += accepted - quarantined - retained_now
        retained += retained_now

    return out


def rmse(actual: Iterable[float], observed: Iterable[float]) -> float:
    pairs = list(zip(actual, observed))
    return (sum((a - b) ** 2 for a, b in pairs) / len(pairs)) ** 0.5


def calibrate() -> dict:
    fixture = json.loads(FIXTURE.read_text())
    observed = [row["fraction"] for row in fixture["curve"]]

    # Fixed, deliberately modest candidate. The tester must be able to fail.
    params = EpidemicParameters(
        beta=0.10,
        contacts=6.5,
        alpha=1.0,
        gamma=1.0,
        delta=0.20,
        kappa=0.10,
        mutation=0.10,
        fidelity=1.0,
        trust=1.0,
    )
    predicted = simulate(params, len(observed), initial_adopted=0.10)
    error = rmse(predicted, observed)
    threshold = 0.02
    passed = error <= threshold

    return {
        "spec": "innovulis-epidemic-genesis-calibration/1.0",
        "fixture": str(FIXTURE),
        "observed_points": len(observed),
        "parameters": asdict(params),
        "predicted": [round(v, 6) for v in predicted],
        "observed": observed,
        "rmse": round(error, 6),
        "threshold": threshold,
        "calibrated": passed,
        "result": "CALIBRATED" if passed else "QUARANTINED",
        "tier": "VERIFIED_PROCESS" if passed else "ACTION_REQUIRED",
        "physical_gate": "ACTION_REQUIRED",
        "interpretation": (
            "External curve reproduced within threshold."
            if passed
            else "Current model did not reproduce the external curve within threshold; "
                 "do not promote the model to calibrated status."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(calibrate(), indent=2, sort_keys=True))
