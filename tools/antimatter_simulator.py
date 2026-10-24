#!/usr/bin/env python3
"""Deterministic antimatter-beamed-core physics model and evidence receipt.

The model is an idealized relativistic rocket calculation. It does not claim
that an antimatter engine, charged-pion magnetic nozzle, or sustained 1-g burn
has been physically demonstrated.
"""
import datetime as dt
import json
import math
import subprocess
import sys
from pathlib import Path

C = 299792458.0
G = 9.80665
SEC_PER_YEAR = 31557600.0


def closed_form(delta_v_c: float, beta_eff: float) -> dict:
    rapidity = math.atanh(delta_v_c)
    mass_ratio_one = math.exp(rapidity / beta_eff)
    mass_ratio_round_trip = mass_ratio_one * mass_ratio_one
    mass_fraction_round_trip = 1.0 - (1.0 / mass_ratio_round_trip)
    proper_time_years = (C / G) * rapidity / SEC_PER_YEAR
    coordinate_time_years = (
        (C / G) * (delta_v_c / math.sqrt(1.0 - delta_v_c * delta_v_c))
        / SEC_PER_YEAR
    )
    return {
        "delta_v_c": delta_v_c,
        "effective_beta": beta_eff,
        "mass_ratio_one_way": mass_ratio_one,
        "mass_ratio_round_trip": mass_ratio_round_trip,
        "mass_fraction_round_trip": mass_fraction_round_trip,
        "proper_time_accel_years": proper_time_years,
        "coordinate_time_accel_years": coordinate_time_years,
    }


def c_kernel(delta_v_c: float, beta_eff: float) -> dict | None:
    executable = Path("build/antimatter_kernel")
    if not executable.exists():
        return None

    result = subprocess.run(
        [str(executable), f"{delta_v_c:.17g}", f"{beta_eff:.17g}"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def emit_receipt(out_path: str, scenarios: list[dict]) -> dict:
    cross_checks = []
    for scenario in scenarios:
        expected = closed_form(
            scenario["delta_v_c"], scenario["effective_beta"]
        )
        observed = c_kernel(
            scenario["delta_v_c"], scenario["effective_beta"]
        )

        if observed is None:
            cross_checks.append({
                "scenario": scenario["name"],
                "max_divergence": None,
                "pass": False,
                "reason": "C kernel not built or execution failed",
            })
            continue

        divergences = {
            key: abs(expected[key] - observed[key])
            for key in expected
        }
        max_divergence = max(divergences.values())
        cross_checks.append({
            "scenario": scenario["name"],
            "max_divergence": max_divergence,
            "pass": max_divergence < 1e-9,
        })

    all_pass = bool(cross_checks) and all(
        check["pass"] is True for check in cross_checks
    )

    receipt = {
        "spec": "innovulis-antimatter-evidence/1.0",
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "surface": "antimatter-beamed-core-starship",
        "state": "VERIFIED_PROCESS" if all_pass else "ACTION_REQUIRED",
        "model": {
            "type": "idealized_relativistic_rocket",
            "equation": "M0/Mf = exp(atanh(delta_v/c) / beta_eff)",
            "beta_eff_is_assumption": True,
            "beta_eff_note": (
                "0.60 is a model input for the charged-pion beamed-core "
                "scenario; it is not a measured engine property."
            ),
        },
        "physics_scenarios": [
            closed_form(
                scenario["delta_v_c"], scenario["effective_beta"]
            ) | {"name": scenario["name"]}
            for scenario in scenarios
        ],
        "c_vs_python_cross_check": cross_checks,
        "proves": [
            "The bounded relativistic rocket model is implemented in C and Python.",
            "The C implementation matches the Python closed form to the recorded tolerance.",
            "The 1-g proper-time and Earth-frame coordinate-time equations are evaluated.",
        ],
        "does_not_prove": [
            "Scaled antimatter production or storage.",
            "A physical magnetic nozzle capable of directing charged pions at the assumed effective exhaust velocity.",
            "A sustained 1-g antimatter burn.",
            "A fabricated antimatter-beamed-core engine.",
            "An Alpha Centauri transit time as an experimentally demonstrated capability.",
            "Physical silicon execution, hardware attestation, or measured energy.",
        ],
        "physical_gate": "ACTION_REQUIRED",
        "the_central_rule": "The receipt can record reality; it cannot manufacture reality.",
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(
        json.dumps(receipt, indent=2) + "\n",
        encoding="utf-8",
    )
    return receipt


if __name__ == "__main__":
    scenarios = [
        {"name": "alpha_centauri_0.10c", "delta_v_c": 0.10, "effective_beta": 0.60},
        {"name": "alpha_centauri_0.20c", "delta_v_c": 0.20, "effective_beta": 0.60},
        {"name": "optimistic_0.20c_beta0.8", "delta_v_c": 0.20, "effective_beta": 0.80},
        {"name": "sublight_0.50c", "delta_v_c": 0.50, "effective_beta": 0.60},
    ]
    output = sys.argv[1] if len(sys.argv) > 1 else "evidence/antimatter_evidence_receipt.json"
    print(json.dumps(emit_receipt(output, scenarios), indent=2))
