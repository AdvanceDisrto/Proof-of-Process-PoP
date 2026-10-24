import json

from tools.epidemic_calibration import calibrate, fit_bass_baseline


def test_external_calibration_is_behavioral_and_can_quarantine():
    result = calibrate()

    assert result["observed_points"] == 17
    assert len(result["eGi"]["predicted"]) == 17
    assert result["eGi"]["rmse"] >= 0.0
    assert result["result"] in {"CALIBRATED", "QUARANTINED"}

    # Current model is intentionally not promoted merely because the harness runs.
    if result["result"] == "QUARANTINED":
        assert result["eGi_calibration_tier"] == "ACTION_REQUIRED"


def test_baseline_is_available_on_same_observed_curve():
    result = calibrate()
    assert 'baseline' in result
    assert result['baseline']['rmse'] >= 0.0
    assert result['comparison']['eGi_minus_baseline_rmse'] == round(result['eGi']['rmse'] - result['baseline']['rmse'], 6)


def test_calibration_does_not_promote_ckm_specific_eGi_parameters():
    result = calibrate()
    assert 'kappa' in result['identifiability']['not_identifiable']
    assert 'mutation' in result['identifiability']['not_identifiable']
    assert result['eGi_calibration_tier'] == 'ACTION_REQUIRED'


def test_positive_control_promotes_known_good_variant():
    from tools.epidemic_calibration import positive_control
    result = positive_control()
    assert result["criterion_pass"] is True
    assert result["promotion"] == "VERIFIED_PROCESS"
    assert result["eGi_rmse"] < result["baseline_rmse"]


def test_ckm_delta_has_deterministic_90_percent_ci_excluding_zero():
    result = calibrate()
    ci = result["comparison"]["bootstrap_90_ci"]
    assert ci["confidence_level"] == 0.9
    assert ci["lower"] > 0.0
    assert ci["upper"] > ci["lower"]
    assert ci["excludes_zero"] is True


def test_external_ground_truth_positive_control_discriminates_models():
    from tools.epidemic_calibration import external_ground_truth_positive_control
    result = external_ground_truth_positive_control()
    assert result["source_process"] == "Bass"
    assert result["recovered_ground_truth"] is True
    assert result["discriminates_known_process"] is True
    assert result["criterion_pass"] is True


def test_symmetric_external_ground_truth_control_reports_both_directions():
    from tools.epidemic_calibration import symmetric_external_ground_truth_control
    result = symmetric_external_ground_truth_control()
    assert result["bass_truth_direction"]["pass"] is True
    assert result["eGi_truth_direction"]["pass"] is True
    assert result["bidirectional"] is True
    assert result["tier_claim"] == "FIT_DISCRIMINATION_BIDIRECTIONAL"


def test_external_bass_control_records_fit_provenance_not_oracle_claim():
    from tools.epidemic_calibration import external_ground_truth_positive_control
    result = external_ground_truth_positive_control()
    assert result["fit_method"] == "deterministic_grid_search_over_preregistered_p_q_grid"
    assert result["fit_resolution"]["p"] == 0.001
    assert result["fit_resolution"]["q"] == 0.01
    assert isinstance(result["reported_p_equals_ground_truth"], bool)
    assert isinstance(result["reported_q_equals_ground_truth"], bool)
    assert result["p_absolute_error"] >= 0.0
    assert result["q_absolute_error"] >= 0.0


def test_symmetric_control_records_fit_provenance_and_generator_scope():
    from tools.epidemic_calibration import symmetric_external_ground_truth_control
    result = symmetric_external_ground_truth_control()
    assert result["fit_provenance"]["Bass"]["method"] == "deterministic_grid_search_over_preregistered_p_q_grid"
    assert result["fit_provenance"]["eGi"]["method"] == "deterministic_grid_search_over_effective_transmission_and_delta"
    assert set(result["eGi_truth_direction"]["eGi_fit"]["parameters"]) == {"effective_transmission", "delta"}
    assert result["off_grid_truth_control"]["truth_alignment"] == "OFF_GRID"
    assert result["off_grid_truth_control"]["Bass_absolute_errors"]["p"] <= 0.01
    assert result["off_grid_truth_control"]["Bass_absolute_errors"]["q"] <= 0.01
    assert result["off_grid_truth_control"]["eGi_absolute_errors"]["effective_transmission"] <= 0.01
    assert result["off_grid_truth_control"]["eGi_absolute_errors"]["delta"] <= 0.01
    assert result["generator_scope"]["implementation"] == "actual simulate() eGi recurrence"
    assert "kappa" in result["generator_scope"]["inactive_in_current_simulator"]
    assert "mutation" in result["generator_scope"]["inactive_in_current_simulator"]


def test_mechanism_active_control_activates_distinctive_dynamics():
    from tools.epidemic_calibration import symmetric_external_ground_truth_control
    result = symmetric_external_ground_truth_control()
    control = result["mechanism_active_control"]
    assert control["generator"] == "simulate_mechanism_active"
    assert set(control["active_mechanisms"]) == {"receipt_weighting", "quarantine_feedback", "mutation"}
    assert control["pass"] is True
    assert control["eGi_mechanism_fit"]["rmse"] < control["Bass_fit"]["rmse"]
