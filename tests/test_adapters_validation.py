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


def test_gazepoint_adapter_rejects_missing_required_source_columns():
    raw = pd.DataFrame(
        {
            "USER_FILE": ["p1", "p1"],
            "MEDIA_ID": ["m1", "m1"],
            "TIME": [0.0, 0.01],
            "BPOGX": [0.2, 0.3],
        }
    )

    with pytest.raises(SchemaError, match="missing source columns"):
        adapt_gazepoint_samples(raw, screen_size_px=(1920, 1080))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"time_unit": "minutes"}, "time_unit must be"),
        ({"coordinates": "degrees"}, "coordinates must be"),
    ],
)
def test_gazepoint_adapter_rejects_unknown_units(kwargs, message):
    raw = pd.DataFrame(
        {
            "USER_FILE": ["p1", "p1"],
            "MEDIA_ID": ["m1", "m1"],
            "TIME": [0.0, 10.0],
            "BPOGX": [100.0, 110.0],
            "BPOGY": [200.0, 210.0],
        }
    )

    with pytest.raises(ValueError, match=message):
        adapt_gazepoint_samples(
            raw,
            screen_size_px=(1920, 1080),
            sampling_rate_hz=100,
            **kwargs,
        )


def test_gazepoint_adapter_preserves_pixel_milliseconds_and_optional_columns():
    raw = pd.DataFrame(
        {
            "USER_FILE": ["p1", "p1"],
            "MEDIA_ID": ["m1", "m1"],
            "TIME": [0.0, 10.0],
            "BPOGX": [100.0, 110.0],
            "BPOGY": [200.0, 210.0],
            "PUPIL": ["3.1", "3.2"],
            "VALID": [1, 0],
        }
    )

    gaze = adapt_gazepoint_samples(
        raw,
        screen_size_px=(1920, 1080),
        pupil_col="PUPIL",
        validity_col="VALID",
        time_unit="milliseconds",
        coordinates="pixels",
        sampling_rate_hz=100,
    )

    assert gaze.data["timestamp_ms"].tolist() == [0.0, 10.0]
    assert gaze.data["x_px"].tolist() == [100.0, 110.0]
    assert gaze.data["y_px"].tolist() == [200.0, 210.0]
    assert gaze.data["pupil"].tolist() == [3.1, 3.2]
    assert gaze.data["validity"].tolist() == [1, 0]
    assert gaze.metadata["adapter"] == "gazepoint"
    assert gaze.metadata["source_time_unit"] == "milliseconds"
    assert gaze.metadata["source_coordinates"] == "pixels"


@pytest.mark.parametrize(("column_arg", "column_name"), [("pupil_col", "PUPIL"), ("validity_col", "VALID")])
def test_gazepoint_adapter_rejects_requested_missing_optional_columns(column_arg, column_name):
    raw = pd.DataFrame(
        {
            "USER_FILE": ["p1", "p1"],
            "MEDIA_ID": ["m1", "m1"],
            "TIME": [0.0, 0.01],
            "BPOGX": [0.2, 0.3],
            "BPOGY": [0.4, 0.5],
        }
    )

    with pytest.raises(SchemaError, match="Requested .* column is missing"):
        adapt_gazepoint_samples(
            raw,
            screen_size_px=(1920, 1080),
            sampling_rate_hz=100,
            **{column_arg: column_name},
        )


def test_processed_adapter_applies_scales_optional_columns_and_metadata():
    raw = pd.DataFrame(
        {
            "subject": ["p1", "p1"],
            "trial": ["t1", "t1"],
            "time_s": [0.0, 0.02],
            "gx_norm": [0.25, 0.50],
            "gy_norm": [0.50, 0.75],
            "pupil_raw": ["3.0", "3.5"],
            "valid_raw": ["ok", "bad"],
        }
    )

    gaze = adapt_processed_table(
        raw,
        participant_col="subject",
        trial_col="trial",
        timestamp_col="time_s",
        x_col="gx_norm",
        y_col="gy_norm",
        pupil_col="pupil_raw",
        validity_col="valid_raw",
        timestamp_scale_to_ms=1000.0,
        coordinate_scale=(1920.0, 1080.0),
        sampling_rate_hz=50.0,
        screen_size_px=(1920, 1080),
        source_name="custom_export",
    )

    assert gaze.data["timestamp_ms"].tolist() == [0.0, 20.0]
    assert gaze.data["x_px"].tolist() == [480.0, 960.0]
    assert gaze.data["y_px"].tolist() == [540.0, 810.0]
    assert gaze.data["pupil"].tolist() == [3.0, 3.5]
    assert gaze.data["validity"].tolist() == ["ok", "bad"]
    assert gaze.metadata == {
        "adapter": "custom_export",
        "timestamp_scale_to_ms": 1000.0,
        "coordinate_scale": (1920.0, 1080.0),
    }


def test_processed_adapter_rejects_missing_required_source_columns():
    raw = pd.DataFrame(
        {
            "subject": ["p1", "p1"],
            "trial": ["t1", "t1"],
            "time": [0.0, 10.0],
            "gx": [100.0, 110.0],
        }
    )

    with pytest.raises(SchemaError, match="processed_table adapter is missing source columns"):
        adapt_processed_table(
            raw,
            participant_col="subject",
            trial_col="trial",
            timestamp_col="time",
            x_col="gx",
            y_col="gy",
        )


@pytest.mark.parametrize(("column_arg", "column_name"), [("pupil_col", "PUPIL"), ("validity_col", "VALID")])
def test_processed_adapter_rejects_requested_missing_optional_columns(column_arg, column_name):
    raw = pd.DataFrame(
        {
            "subject": ["p1", "p1"],
            "trial": ["t1", "t1"],
            "time": [0.0, 10.0],
            "gx": [100.0, 110.0],
            "gy": [200.0, 210.0],
        }
    )

    with pytest.raises(SchemaError, match="Requested .* column is missing"):
        adapt_processed_table(
            raw,
            participant_col="subject",
            trial_col="trial",
            timestamp_col="time",
            x_col="gx",
            y_col="gy",
            sampling_rate_hz=100,
            **{column_arg: column_name},
        )

