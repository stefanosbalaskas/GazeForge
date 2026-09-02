import numpy as np
import pandas as pd
import pytest

from gazeforge import resample_labeled_gaze


def _high_rate_fixture():
    timestamps = np.arange(0.0, 200.0, 2.0)  # 500 Hz
    labels = np.where(timestamps < 100.0, "fixation", "saccade")
    return pd.DataFrame(
        {
            "participant_id": "P1",
            "trial_id": "T1",
            "timestamp_ms": timestamps,
            "x_px": timestamps * 2,
            "y_px": 100 + timestamps,
            "pupil": 3.0,
            "event_label": labels,
        }
    )


def test_resampling_targets_60_hz_and_reports_provenance():
    result = resample_labeled_gaze(_high_rate_fixture(), target_sampling_rate_hz=60)
    assert result.report["source_sampling_rate_hz"] == pytest.approx(500.0)
    assert result.report["target_sampling_rate_hz"] == 60
    assert result.report["target_rows"] == len(result.data)
    diffs = np.diff(result.data["timestamp_ms"])
    assert np.median(diffs) == pytest.approx(1000 / 60)
    assert {"benchmark_label_purity", "benchmark_label_ambiguous"} <= set(result.data)


def test_resampling_marks_event_boundaries_ambiguous_when_purity_is_insufficient():
    result = resample_labeled_gaze(
        _high_rate_fixture(),
        target_sampling_rate_hz=60,
        min_label_purity=0.9,
    )
    near_boundary = result.data.loc[(result.data["timestamp_ms"] - 100).abs().idxmin()]
    assert bool(near_boundary["benchmark_label_ambiguous"])
    assert near_boundary["event_label"] == "ambiguous"


def test_resampling_does_not_bridge_large_missing_coordinate_gap():
    data = _high_rate_fixture()
    data.loc[(data["timestamp_ms"] >= 70) & (data["timestamp_ms"] <= 130), "x_px"] = np.nan
    result = resample_labeled_gaze(
        data,
        target_sampling_rate_hz=60,
        max_interpolation_gap_ms=20,
    )
    middle = result.data.loc[(result.data["timestamp_ms"] - 100).abs().idxmin()]
    assert np.isnan(middle["x_px"])


def test_resampling_refuses_upsampling_as_benchmark_downsampling():
    with pytest.raises(ValueError):
        resample_labeled_gaze(_high_rate_fixture(), target_sampling_rate_hz=1000)


def test_resampling_carries_invariant_trial_provenance():
    data = _high_rate_fixture()
    data["annotator"] = "RA"
    data["stimulus_type"] = "image"
    data["dataset_id"] = "Lund2013"
    data["source_file"] = "P1_image_labelled_RA.mat"
    result = resample_labeled_gaze(data, target_sampling_rate_hz=60)
    assert set(result.data["annotator"]) == {"RA"}
    assert set(result.data["stimulus_type"]) == {"image"}
    assert set(result.data["dataset_id"]) == {"Lund2013"}
    assert set(result.data["source_file"]) == {"P1_image_labelled_RA.mat"}


def test_resampling_refuses_non_invariant_carried_metadata():
    data = _high_rate_fixture()
    data["stimulus_type"] = "image"
    data.loc[data.index[-1], "stimulus_type"] = "video"
    from gazeforge.exceptions import SchemaError

    with pytest.raises(SchemaError):
        resample_labeled_gaze(data, target_sampling_rate_hz=60)
