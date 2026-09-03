from types import SimpleNamespace

import pandas as pd
import pytest

import gazeforge.lund_sensitivity as lund_sensitivity
from gazeforge.exceptions import SchemaError
from gazeforge.sampling_sensitivity import SamplingSensitivityResult


def _gaze(n_participants: int = 3):
    rows = []
    for participant in range(n_participants):
        for sample in range(20):
            rows.append(
                {
                    "participant_id": f"P{participant + 1:02d}",
                    "trial_id": f"trial_{participant + 1}",
                    "timestamp_ms": sample * 2.0,
                    "x_px": 500.0 + sample,
                    "y_px": 300.0,
                    "event_label": "fixation" if sample < 12 else "saccade",
                }
            )
    return SimpleNamespace(data=pd.DataFrame(rows), sampling_rate_hz=500.0)


def _sensitivity_result():
    settings = pd.DataFrame(
        [
            {
                "setting_key": "rate=60|purity=0.75",
                "target_sampling_rate_hz": 60.0,
                "min_label_purity": 0.75,
                "ambiguous_fraction": 0.05,
                "comparison_status": "ok",
            }
        ]
    )
    metrics = pd.DataFrame(
        [
            {
                "setting_key": "rate=60|purity=0.75",
                "model": "RandomForest",
                "accuracy_mean": 0.80,
                "event_f1_mean": 0.70,
            }
        ]
    )
    return SamplingSensitivityResult(
        settings=settings,
        model_metrics=metrics,
        design={
            "design": "sampling_rate_by_label_purity_sensitivity",
            "target_sampling_rates_hz": [120.0, 90.0, 60.0, 30.0],
            "min_label_purities": [0.6, 0.75, 0.9],
            "excluded_labels": ["ambiguous", "undefined", "unlabelled"],
        },
        report_fingerprint_sha256="b" * 64,
    )


def test_lund_sensitivity_builds_derived_human_report(monkeypatch):
    calls = {}
    monkeypatch.setattr(
        lund_sensitivity,
        "load_lund2013_directory",
        lambda *args, **kwargs: _gaze(3),
    )

    def fake_sensitivity(data, **kwargs):
        calls.update(kwargs)
        return _sensitivity_result()

    monkeypatch.setattr(
        lund_sensitivity,
        "evaluate_sampling_purity_sensitivity",
        fake_sensitivity,
    )
    run = lund_sensitivity.run_lund2013_sampling_sensitivity(
        "/tmp/lund",
        annotator="RA",
        n_splits=5,
    )
    assert calls["n_splits"] == 3
    assert calls["ivt_velocity_threshold_px_s"] is None
    assert calls["ivt_velocity_threshold_deg_s"] == 45.0
    assert run.dataset_card.annotation_origin == "expert-manual"
    assert run.dataset_card.sampling_origin == "resampled"
    assert run.dataset_card.reference_strength == "derived-human-reference"
    assert run.report["protocol"]["annotator"] == "RA"
    assert run.report["protocol"]["comparison_folds"] == 3
    assert run.report["metrics"]["sensitivity_fingerprint_sha256"] == "b" * 64
    assert len(run.report["report_fingerprint_sha256"]) == 64


def test_lund_sensitivity_forwards_grid(monkeypatch):
    monkeypatch.setattr(
        lund_sensitivity,
        "load_lund2013_directory",
        lambda *args, **kwargs: _gaze(2),
    )
    captured = {}

    def fake_sensitivity(data, **kwargs):
        captured.update(kwargs)
        result = _sensitivity_result()
        result.design["target_sampling_rates_hz"] = list(kwargs["target_sampling_rates_hz"])
        result.design["min_label_purities"] = list(kwargs["min_label_purities"])
        return result

    monkeypatch.setattr(
        lund_sensitivity,
        "evaluate_sampling_purity_sensitivity",
        fake_sensitivity,
    )
    lund_sensitivity.run_lund2013_sampling_sensitivity(
        "/tmp/lund",
        target_sampling_rates_hz=(100.0, 60.0),
        min_label_purities=(0.7, 0.9),
        n_splits=2,
    )
    assert captured["target_sampling_rates_hz"] == (100.0, 60.0)
    assert captured["min_label_purities"] == (0.7, 0.9)


def test_lund_sensitivity_requires_two_participants(monkeypatch):
    monkeypatch.setattr(
        lund_sensitivity,
        "load_lund2013_directory",
        lambda *args, **kwargs: _gaze(1),
    )
    with pytest.raises(SchemaError, match="At least two participant folds"):
        lund_sensitivity.run_lund2013_sampling_sensitivity("/tmp/lund")
