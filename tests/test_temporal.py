import numpy as np
import pandas as pd
import pytest

from gazeforge import (
    ai_classify_events_context,
    dataset_holdout_context_event_validate,
    grouped_context_event_cross_validate,
    ivt_classify_events,
    simulate_gaze,
    train_context_event_classifier,
)
from gazeforge.exceptions import ModelCompatibilityError


def _labelled_data():
    data = simulate_gaze(
        n_participants=3,
        n_trials=2,
        samples_per_trial=80,
        sampling_rate_hz=60,
        random_state=17,
    )
    baseline = ivt_classify_events(
        data,
        sampling_rate_hz=60,
        velocity_threshold_px_s=700,
    )
    data["event_label"] = baseline["predicted_event"].replace({"noise": "fixation"})
    data.loc[data.index[::30], "event_label"] = "saccade"
    return data


def test_context_model_probabilities_and_metadata():
    data = _labelled_data()
    model = train_context_event_classifier(
        data,
        sampling_rate_hz=60,
        context_radius_ms=50,
        hidden_layer_sizes=(16,),
        solver="lbfgs",
        max_iter=60,
    )
    out = ai_classify_events_context(
        data,
        model,
        sampling_rate_hz=60,
        min_confidence=0.0,
    )
    probability_cols = [col for col in out.columns if col.startswith("p_event_")]
    assert probability_cols
    assert np.allclose(out[probability_cols].sum(axis=1), 1.0)
    assert model.context_radius_samples == 3
    assert (out["event_context_radius_samples"] == 3).all()


def test_context_windows_do_not_cross_trial_boundary():
    data = _labelled_data()
    model = train_context_event_classifier(
        data,
        sampling_rate_hz=60,
        context_radius_ms=50,
        hidden_layer_sizes=(8,),
        solver="lbfgs",
        max_iter=120,
    )
    original = ai_classify_events_context(data, model, sampling_rate_hz=60, min_confidence=0.0)

    changed = data.copy()
    first_trial = changed["trial_id"].iloc[0]
    mask = changed["trial_id"] != first_trial
    changed.loc[mask, "x_px"] = changed.loc[mask, "x_px"] + 10000
    changed_out = ai_classify_events_context(
        changed,
        model,
        sampling_rate_hz=60,
        min_confidence=0.0,
    )
    first_mask = data["trial_id"] == first_trial
    probability_cols = [col for col in original.columns if col.startswith("p_event_")]
    assert np.allclose(
        original.loc[first_mask, probability_cols],
        changed_out.loc[first_mask, probability_cols],
    )


def test_context_model_sampling_rate_guardrail():
    data = _labelled_data()
    model = train_context_event_classifier(
        data,
        sampling_rate_hz=60,
        hidden_layer_sizes=(8,),
        solver="lbfgs",
        max_iter=120,
    )
    with pytest.raises(ModelCompatibilityError):
        ai_classify_events_context(data, model, sampling_rate_hz=250)


def test_context_model_accepts_duplicate_dataframe_indices():
    data = _labelled_data().copy()
    data.index = np.arange(len(data)) // 2
    model = train_context_event_classifier(
        data,
        sampling_rate_hz=60,
        context_radius_ms=50,
        hidden_layer_sizes=(8,),
        solver="lbfgs",
        max_iter=120,
    )
    out = ai_classify_events_context(
        data,
        model,
        sampling_rate_hz=60,
        min_confidence=0.0,
    )
    assert len(out) == len(data)
    assert out.index.equals(data.index)
    assert out["predicted_event"].notna().all()


def test_grouped_context_validation_holds_participants_out():
    data = _labelled_data()
    result = grouped_context_event_cross_validate(
        data,
        sampling_rate_hz=60,
        n_splits=3,
        context_radius_ms=35,
        hidden_layer_sizes=(8,),
        solver="lbfgs",
        max_iter=400,
    )
    assert len(result.predictions) == len(data)
    assert result.metrics["validation_design"]["design"] == "group_kfold_temporal_context"
    assert result.folds["n_test_groups"].ge(1).all()


def test_dataset_holdout_context_validation_is_exhaustive():
    parts = []
    for dataset_index, dataset_id in enumerate(("A", "B", "C")):
        part = simulate_gaze(
            n_participants=2,
            n_trials=1,
            samples_per_trial=50,
            sampling_rate_hz=60,
            random_state=90 + dataset_index,
        )
        part["participant_id"] = f"{dataset_id}_" + part["participant_id"].astype(str)
        baseline = ivt_classify_events(part, sampling_rate_hz=60, velocity_threshold_px_s=700)
        part["event_label"] = baseline["predicted_event"].replace({"noise": "fixation"})
        part.loc[part.index[::25], "event_label"] = "saccade"
        part["dataset_id"] = dataset_id
        parts.append(part)
    data = pd.concat(parts, ignore_index=True)
    result = dataset_holdout_context_event_validate(
        data,
        sampling_rate_hz=60,
        context_radius_ms=35,
        hidden_layer_sizes=(8,),
        solver="lbfgs",
        max_iter=400,
    )
    assert len(result.predictions) == len(data)
    assert set(result.folds["held_out_dataset"]) == {"A", "B", "C"}
    assert result.metrics["validation_design"]["design"] == (
        "leave_one_dataset_out_temporal_context"
    )
