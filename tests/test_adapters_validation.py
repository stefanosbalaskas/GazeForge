import pandas as pd
import pytest

from gazeforge import (
    adapt_gazepoint_samples,
    adapt_processed_table,
    assert_no_group_leakage,
    grouped_event_cross_validate,
    grouped_holdout_indices,
    ivt_classify_events,
    simulate_gaze,
)
from gazeforge.exceptions import SchemaError


def test_gazepoint_adapter_scales_time_and_coordinates():
    raw = pd.DataFrame(
        {
            "USER_FILE": ["p1", "p1", "p1"],
            "MEDIA_ID": ["m1", "m1", "m1"],
            "TIME": [0.0, 1 / 60, 2 / 60],
            "BPOGX": [0.25, 0.50, 0.75],
            "BPOGY": [0.50, 0.50, 0.50],
        }
    )
    gaze = adapt_gazepoint_samples(raw, screen_size_px=(1920, 1080))
    assert gaze.data.loc[1, "timestamp_ms"] == pytest.approx(1000 / 60)
    assert gaze.data.loc[1, "x_px"] == pytest.approx(960)
    assert gaze.data.loc[1, "y_px"] == pytest.approx(540)
    assert gaze.sampling_rate_hz == pytest.approx(60)


def test_processed_adapter_requires_explicit_columns():
    raw = pd.DataFrame(
        {
            "subject": ["p1"] * 3,
            "trial": ["t1"] * 3,
            "time": [0, 10, 20],
            "gx": [1, 2, 3],
            "gy": [4, 5, 6],
        }
    )
    gaze = adapt_processed_table(
        raw,
        participant_col="subject",
        trial_col="trial",
        timestamp_col="time",
        x_col="gx",
        y_col="gy",
    )
    assert gaze.sampling_rate_hz == pytest.approx(100)


def test_group_holdout_has_no_participant_overlap():
    data = simulate_gaze(n_participants=6, n_trials=2, samples_per_trial=30)
    train_idx, test_idx = grouped_holdout_indices(data, test_size=0.33)
    train = data.iloc[train_idx]
    test = data.iloc[test_idx]
    assert_no_group_leakage(train, test)


def test_leakage_guard_raises():
    train = pd.DataFrame({"participant_id": ["p1", "p2"]})
    test = pd.DataFrame({"participant_id": ["p2", "p3"]})
    with pytest.raises(SchemaError):
        assert_no_group_leakage(train, test)


def test_grouped_event_cross_validation():
    data = simulate_gaze(
        n_participants=4,
        n_trials=2,
        samples_per_trial=70,
        sampling_rate_hz=60,
    )
    baseline = ivt_classify_events(data, sampling_rate_hz=60, velocity_threshold_px_s=700)
    data["event_label"] = baseline["predicted_event"].replace({"noise": "fixation"})
    data.loc[data.index[::35], "event_label"] = "saccade"

    result = grouped_event_cross_validate(
        data,
        n_splits=2,
        sampling_rate_hz=60,
        n_estimators=30,
    )
    assert len(result.predictions) == len(data)
    assert len(result.folds) == 2
    assert result.metrics["validation_design"]["group_col"] == "participant_id"
