import numpy as np
import pytest

from gazeforge import (
    ai_classify_events,
    evaluate_event_predictions,
    ivt_classify_events,
    simulate_gaze,
    train_event_classifier,
)
from gazeforge.exceptions import ModelCompatibilityError


def _label_synthetic(data):
    baseline = ivt_classify_events(data, sampling_rate_hz=60, velocity_threshold_px_s=700)
    labelled = data.copy()
    labelled["event_label"] = baseline["predicted_event"].replace({"noise": "fixation"})
    labelled.loc[labelled.index[::45], "event_label"] = "saccade"
    return labelled


def test_train_and_classify_events_probabilities_sum():
    data = simulate_gaze(n_participants=3, n_trials=2, samples_per_trial=120, sampling_rate_hz=60)
    labelled = _label_synthetic(data)
    model = train_event_classifier(labelled, sampling_rate_hz=60, n_estimators=50)
    out = ai_classify_events(data, model, sampling_rate_hz=60, min_confidence=0.0)
    probability_cols = [c for c in out.columns if c.startswith("p_event_")]
    assert probability_cols
    assert np.allclose(out[probability_cols].sum(axis=1), 1.0)
    assert set(out["predicted_event"]).issubset(set(model.classes))


def test_sampling_rate_guardrail():
    data = simulate_gaze(n_participants=2, n_trials=2, samples_per_trial=90, sampling_rate_hz=60)
    model = train_event_classifier(_label_synthetic(data), sampling_rate_hz=60, n_estimators=30)
    with pytest.raises(ModelCompatibilityError):
        ai_classify_events(data, model, sampling_rate_hz=250)


def test_event_evaluation_shape():
    metrics = evaluate_event_predictions(["f", "f", "s"], ["f", "s", "s"])
    assert metrics["labels"] == ["f", "s"]
    assert len(metrics["confusion_matrix"]) == 2
