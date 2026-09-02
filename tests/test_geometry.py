import numpy as np
import pandas as pd
import pytest

from gazeforge import (
    angular_kinematic_features,
    ivt_classify_events_angular,
    pixels_to_visual_angle_deg,
)
from gazeforge.exceptions import SchemaError


def _geometry_fixture():
    return pd.DataFrame(
        {
            "participant_id": ["P1"] * 4,
            "trial_id": ["T1"] * 4,
            "timestamp_ms": [0.0, 100.0, 200.0, 300.0],
            "x_px": [100.0, 101.0, 201.0, np.nan],
            "y_px": [100.0, 100.0, 100.0, np.nan],
            "screen_width_px": 1920.0,
            "screen_height_px": 1080.0,
            "screen_width_physical": 530.0,
            "screen_height_physical": 300.0,
            "view_distance_physical": 650.0,
        }
    )


def test_pixels_to_visual_angle_matches_lund_formula():
    result = pixels_to_visual_angle_deg(
        1.0,
        physical_extent=530.0,
        pixel_extent=1920.0,
        viewing_distance=650.0,
    )
    expected = np.degrees(2 * np.arctan((530.0 / 1920.0) / (2 * 650.0)))
    assert float(result) == pytest.approx(expected)


def test_angular_kinematics_are_boundary_safe_and_axis_aware():
    data = _geometry_fixture()
    features = angular_kinematic_features(data, sampling_rate_hz=10)
    assert np.isnan(features.loc[0, "angular_velocity_deg_s"])
    assert features.loc[1, "angular_velocity_deg_s"] > 0
    assert features.loc[2, "angular_velocity_deg_s"] > features.loc[1, "angular_velocity_deg_s"]


def test_angular_ivt_uses_degrees_per_second_and_marks_missing_noise():
    out = ivt_classify_events_angular(
        _geometry_fixture(),
        sampling_rate_hz=10,
        velocity_threshold_deg_s=5.0,
    )
    assert out.loc[0, "predicted_event"] == "fixation"
    assert out.loc[2, "predicted_event"] == "saccade"
    assert out.loc[3, "predicted_event"] == "noise"
    assert (out["event_velocity_threshold_deg_s"] == 5.0).all()


def test_angular_kinematics_refuse_conflicting_geometry_within_trial():
    data = _geometry_fixture()
    data.loc[1, "view_distance_physical"] = 700.0
    with pytest.raises(SchemaError):
        angular_kinematic_features(data, sampling_rate_hz=10)
