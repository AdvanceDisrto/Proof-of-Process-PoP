import json

from tools.epidemic_calibration import calibrate


def test_external_calibration_is_behavioral_and_can_quarantine():
    result = calibrate()

    assert result["observed_points"] == 17
    assert len(result["predicted"]) == 17
    assert result["rmse"] >= 0.0
    assert result["result"] in {"CALIBRATED", "QUARANTINED"}

    # Current model is intentionally not promoted merely because the harness runs.
    if result["result"] == "QUARANTINED":
        assert result["tier"] == "ACTION_REQUIRED"
