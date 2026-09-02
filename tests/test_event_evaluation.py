import numpy as np
import pandas as pd
import pytest

from gazeforge.event_evaluation import (
    evaluate_event_intervals,
    evaluate_sample_event_predictions,
    samples_to_event_intervals,
    temporal_event_iou,
)
from gazeforge.exceptions import SchemaError


def _samples(labels, *, trial="T1", timestamps=None):
    if timestamps is None:
        timestamps = np.arange(len(labels), dtype=float) * 10.0
    return pd.DataFrame(
        {
            "participant_id": "P1",
            "trial_id": trial,
            "timestamp_ms": timestamps,
            "event_label": labels,
        }
    )


def test_samples_to_events_uses_half_open_intervals():
    data = _samples(["fixation", "fixation", "saccade", "saccade"])
    events = samples_to_event_intervals(data, sampling_rate_hz=100.0)
    assert events["event_label"].tolist() == ["fixation", "saccade"]
    assert events["start_ms"].tolist() == [0.0, 20.0]
    assert events["end_ms"].tolist() == [20.0, 40.0]
    assert events["duration_ms"].tolist() == [20.0, 20.0]
    assert events["n_samples"].tolist() == [2, 2]


def test_excluded_labels_remain_hard_event_separators():
    data = _samples(["fixation", "ambiguous", "fixation"])
    events = samples_to_event_intervals(data, sampling_rate_hz=100.0)
    assert events["event_label"].tolist() == ["fixation", "fixation"]
    assert events["event_index"].tolist() == [1, 2]
    assert events["start_ms"].tolist() == [0.0, 20.0]


def test_large_timestamp_gap_splits_same_label():
    data = _samples(["fixation", "fixation", "fixation"], timestamps=[0.0, 10.0, 50.0])
    events = samples_to_event_intervals(data, sampling_rate_hz=100.0, max_gap_factor=1.5)
    assert len(events) == 2
    assert events["n_samples"].tolist() == [2, 1]


def test_segmentation_rejects_non_monotonic_timestamps():
    data = _samples(["fixation", "fixation"], timestamps=[10.0, 10.0])
    with pytest.raises(SchemaError, match="strictly increasing"):
        samples_to_event_intervals(data, sampling_rate_hz=100.0)


def test_temporal_event_iou_matches_expected_overlap():
    assert temporal_event_iou(0.0, 20.0, 10.0, 30.0) == pytest.approx(1.0 / 3.0)


def test_perfect_event_match_has_perfect_metrics():
    reference = samples_to_event_intervals(
        _samples(["fixation", "fixation", "saccade", "saccade"]),
        sampling_rate_hz=100.0,
    )
    result = evaluate_event_intervals(reference.copy(), reference, min_iou=0.5)
    assert result.summary["precision"] == 1.0
    assert result.summary["recall"] == 1.0
    assert result.summary["f1"] == 1.0
    assert result.summary["mean_matched_iou"] == 1.0
    assert result.summary["mean_abs_onset_error_ms"] == 0.0
    assert set(result.per_class["f1"]) == {1.0}


def test_matching_never_crosses_trial_boundaries():
    reference = samples_to_event_intervals(
        pd.concat(
            [
                _samples(["fixation", "fixation"], trial="T1"),
                _samples(["saccade", "saccade"], trial="T2"),
            ],
            ignore_index=True,
        ),
        sampling_rate_hz=100.0,
    )
    predicted = reference.copy()
    predicted["trial_id"] = predicted["trial_id"].map({"T1": "T2", "T2": "T1"})
    result = evaluate_event_intervals(predicted, reference, min_iou=0.5)
    assert result.summary["true_positive"] == 0
    assert result.summary["false_positive"] == 2
    assert result.summary["false_negative"] == 2


def test_boundary_shift_reports_iou_and_timing_error():
    reference = pd.DataFrame(
        [
            {
                "participant_id": "P1",
                "trial_id": "T1",
                "event_index": 1,
                "event_label": "fixation",
                "start_ms": 0.0,
                "end_ms": 100.0,
                "duration_ms": 100.0,
                "n_samples": 10,
            }
        ]
    )
    predicted = reference.copy()
    predicted.loc[0, "start_ms"] = 10.0
    predicted.loc[0, "end_ms"] = 90.0
    predicted.loc[0, "duration_ms"] = 80.0
    result = evaluate_event_intervals(predicted, reference, min_iou=0.5)
    assert result.summary["mean_matched_iou"] == pytest.approx(0.8)
    assert result.summary["mean_abs_onset_error_ms"] == 10.0
    assert result.summary["mean_abs_offset_error_ms"] == 10.0
    assert result.summary["mean_abs_duration_error_ms"] == 20.0


def test_sample_prediction_convenience_keeps_ambiguity_as_separator():
    data = _samples(["fixation", "ambiguous", "fixation"])
    data["predicted_event"] = ["fixation", "ambiguous", "fixation"]
    result = evaluate_sample_event_predictions(data, sampling_rate_hz=100.0)
    assert len(result.reference_events) == 2
    assert len(result.predicted_events) == 2
    assert result.summary["f1"] == 1.0
    assert result.design["excluded_labels"] == ["ambiguous", "undefined", "unlabelled"]
