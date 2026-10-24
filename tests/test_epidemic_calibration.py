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
        assert result["tier"] == "ACTION_REQUIRED"


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
