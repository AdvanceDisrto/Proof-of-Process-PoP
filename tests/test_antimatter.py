import math

from tools.antimatter_simulator import closed_form, emit_receipt


def test_closed_form_0_10c():
    result = closed_form(0.10, 0.60)
    assert abs(result["mass_ratio_one_way"] - 1.182020875) < 1e-4
    assert abs(result["proper_time_accel_years"] - 0.0972) < 1e-3


def test_closed_form_0_20c():
    result = closed_form(0.20, 0.60)
    assert abs(result["mass_ratio_one_way"] - 1.401982898) < 1e-4
    assert abs(result["mass_fraction_round_trip"] - 0.4915) < 1e-3


def test_photon_rocket_limit():
    result = closed_form(0.10, 1.0)
    assert abs(result["mass_ratio_one_way"] - 1.105541597) < 1e-4


def test_mass_fraction_increases_with_dv():
    low = closed_form(0.10, 0.60)
    high = closed_form(0.20, 0.60)
    assert high["mass_fraction_round_trip"] > low["mass_fraction_round_trip"]


def test_proper_time_matches_1g():
    result = closed_form(0.10, 0.60)
    days = result["proper_time_accel_years"] * 365.25
    assert abs(days - 35.5) < 0.5


def test_receipt_stays_action_required(tmp_path):
    receipt = emit_receipt(
        str(tmp_path / "antimatter_receipt.json"),
        [{"name": "test", "delta_v_c": 0.10, "effective_beta": 0.60}],
    )
    assert receipt["physical_gate"] == "ACTION_REQUIRED"
    assert receipt["state"] in ("VERIFIED_PROCESS", "ACTION_REQUIRED")
    assert receipt["model"]["beta_eff_is_assumption"] is True
    assert any("Scaled antimatter" in item for item in receipt["does_not_prove"])


def test_high_velocity_monotonicity():
    values = [closed_form(v, 0.60)["mass_ratio_one_way"] for v in (0.10, 0.20, 0.50)]
    assert values == sorted(values)
