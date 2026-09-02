import numpy as np
import pandas as pd
import pytest

from gazeforge import (
    ai_flag_anomalies,
    canonicalize_gaze,
    infer_sampling_rate_hz,
    score_trial_quality,
    simulate_gaze,
)
from gazeforge.exceptions import SchemaError


def test_canonicalize_and_infer_60hz():
    data = simulate_gaze(n_participants=2, n_trials=2, samples_per_trial=80, sampling_rate_hz=60)
    inferred = infer_sampling_rate_hz(data)
    assert inferred == pytest.approx(60.0, rel=1e-6)
    gaze = canonicalize_gaze(data)
    assert gaze.sampling_rate_hz == pytest.approx(60.0, rel=1e-6)
    assert list(gaze.data.columns[:5]) == [
        "participant_id",
        "trial_id",
        "timestamp_ms",
        "x_px",
        "y_px",
    ]


def test_canonicalize_mapping():
    data = pd.DataFrame(
        {
            "pid": ["p"] * 3,
            "trial": ["t"] * 3,
            "time": [0, 10, 20],
            "gx": [1, 2, 3],
            "gy": [4, 5, 6],
        }
    )
    gaze = canonicalize_gaze(
        data,
        column_map={
            "participant_id": "pid",
            "trial_id": "trial",
            "timestamp_ms": "time",
            "x_px": "gx",
            "y_px": "gy",
        },
    )
    assert gaze.sampling_rate_hz == pytest.approx(100)


def test_missing_required_columns_raise():
    with pytest.raises(SchemaError):
        canonicalize_gaze(pd.DataFrame({"x_px": [1]}), sampling_rate_hz=60)


def test_anomaly_flags_do_not_remove_samples():
    data = simulate_gaze(n_participants=2, n_trials=2, samples_per_trial=90)
    out = ai_flag_anomalies(data, sampling_rate_hz=60, contamination=0.05)
    assert len(out) == len(data)
    assert {"qc_flag", "qc_anomaly_score"}.issubset(out.columns)
    assert out["qc_flag"].dtype == bool


def test_trial_quality_is_bounded():
    data = simulate_gaze(n_participants=2, n_trials=3, samples_per_trial=60)
    data.loc[:4, ["x_px", "y_px"]] = np.nan
    out = ai_flag_anomalies(data, sampling_rate_hz=60, contamination=0.05)
    quality = score_trial_quality(out, screen_size_px=(1920, 1080))
    assert len(quality) == 6
    assert quality["quality_score"].between(0, 1).all()
