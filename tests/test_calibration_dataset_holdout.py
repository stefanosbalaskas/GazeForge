import numpy as np
import pandas as pd
import pytest

from gazeforge import (
    dataset_holdout_event_validate,
    evaluate_event_calibration,
    expected_calibration_error,
    ivt_classify_events,
    multiclass_brier_score,
    selective_accuracy_curve,
    simulate_gaze,
    top_label_calibration_table,
)
from gazeforge.exceptions import SchemaError


def _probability_fixture():
    return pd.DataFrame(
        {
            "event_label": ["fixation", "saccade", "fixation", "saccade"],
            "predicted_event": ["fixation", "saccade", "saccade", "saccade"],
            "event_confidence": [0.9, 0.8, 0.6, 0.7],
            "p_event_fixation": [0.9, 0.2, 0.4, 0.3],
            "p_event_saccade": [0.1, 0.8, 0.6, 0.7],
        }
    )


def test_multiclass_brier_and_ece_are_bounded():
    data = _probability_fixture()
    score = multiclass_brier_score(
        data["event_label"],
        data[["p_event_fixation", "p_event_saccade"]],
        labels=["fixation", "saccade"],
    )
    assert 0 <= score <= 2
    ece = expected_calibration_error(data, n_bins=4)
    assert 0 <= ece <= 1


def test_calibration_table_and_selective_curve():
    data = _probability_fixture()
    table = top_label_calibration_table(data, n_bins=5)
    assert table["n"].sum() == len(data)
    curve = selective_accuracy_curve(data, thresholds=(0.0, 0.75, 0.95))
    assert curve.loc[0, "coverage"] == pytest.approx(1.0)
    assert curve.loc[2, "coverage"] == pytest.approx(0.0)
    report = evaluate_event_calibration(data, n_bins=5)
    assert "multiclass_brier_score" in report
    assert "selective_accuracy" in report


def test_brier_rejects_non_normalized_probabilities():
    with pytest.raises(ValueError):
        multiclass_brier_score(
            ["a"],
            np.array([[0.8, 0.8]]),
            labels=["a", "b"],
        )


def _dataset_fixture():
    parts = []
    for dataset_index, dataset_id in enumerate(("D1", "D2", "D3")):
        part = simulate_gaze(
            n_participants=2,
            n_trials=2,
            samples_per_trial=60,
            sampling_rate_hz=60,
            random_state=40 + dataset_index,
        )
        part["participant_id"] = f"{dataset_id}_" + part["participant_id"].astype(str)
        part["dataset_id"] = dataset_id
        baseline = ivt_classify_events(
            part,
            sampling_rate_hz=60,
            velocity_threshold_px_s=700,
        )
        part["event_label"] = baseline["predicted_event"].replace({"noise": "fixation"})
        part.loc[part.index[::30], "event_label"] = "saccade"
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def test_dataset_holdout_validation_is_exhaustive():
    data = _dataset_fixture()
    result = dataset_holdout_event_validate(
        data,
        sampling_rate_hz=60,
        n_estimators=20,
    )
    assert len(result.predictions) == len(data)
    assert set(result.folds["held_out_dataset"]) == {"D1", "D2", "D3"}
    assert result.metrics["validation_design"]["design"] == "leave_one_dataset_out"


def test_dataset_holdout_rejects_participant_leakage():
    data = _dataset_fixture()
    data.loc[data["dataset_id"] == "D2", "participant_id"] = "shared"
    data.loc[data["dataset_id"] == "D1", "participant_id"] = "shared"
    with pytest.raises(SchemaError):
        dataset_holdout_event_validate(data, sampling_rate_hz=60, n_estimators=10)
