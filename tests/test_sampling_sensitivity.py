from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gazeforge.sampling_sensitivity as sensitivity


def _source_data(*, n_participants=2):
    parts = []
    for participant in range(n_participants):
        n = 120
        timestamps = np.arange(n, dtype=float) * (1000.0 / 240.0)
        labels = np.where(np.arange(n) % 40 < 24, "fixation", "saccade")
        parts.append(
            pd.DataFrame(
                {
                    "participant_id": f"P{participant + 1:02d}",
                    "trial_id": "trial",
                    "timestamp_ms": timestamps,
                    "x_px": 500.0 + np.arange(n) + participant,
                    "y_px": 300.0 + np.sin(np.arange(n) / 8.0),
                    "event_label": labels,
                }
            )
        )
    return pd.concat(parts, ignore_index=True)


def _fake_comparison(monkeypatch, calls):
    def fake(data, **kwargs):
        assert not data["benchmark_label_ambiguous"].any()
        assert "ambiguous" not in set(data["event_label"])
        assert "unlabelled" not in set(data["event_label"])
        assert "undefined" not in set(data["event_label"])
        calls.append((kwargs["sampling_rate_hz"], len(data)))
        return SimpleNamespace(
            summary=pd.DataFrame(
                [
                    {
                        "model": "RandomForest",
                        "n_folds": kwargs["n_splits"],
                        "accuracy_mean": 0.8,
                        "event_f1_mean": 0.7,
                        "event_mean_matched_iou_mean": 0.6,
                    }
                ]
            )
        )

    monkeypatch.setattr(sensitivity, "compare_event_models_grouped", fake)


def test_grid_records_settings_and_excludes_non_analysis_rows(monkeypatch):
    calls = []
    _fake_comparison(monkeypatch, calls)
    result = sensitivity.evaluate_sampling_purity_sensitivity(
        _source_data(),
        target_sampling_rates_hz=(120.0, 60.0),
        min_label_purities=(0.60, 0.90),
        source_sampling_rate_hz=240.0,
        n_splits=2,
    )
    assert len(result.settings) == 4
    assert set(result.settings["comparison_status"]) == {"ok"}
    assert len(result.model_metrics) == 4
    assert len(calls) == 4
    assert set(result.model_metrics["target_sampling_rate_hz"]) == {60.0, 120.0}
    assert result.design["excluded_rows_used_for_modelling"] is False
    assert result.design["excluded_labels"] == ["ambiguous", "undefined", "unlabelled"]
    assert all(result.settings["retained_fraction_of_target"].between(0.0, 1.0))


def test_grid_order_and_fingerprint_are_deterministic(monkeypatch):
    calls = []
    _fake_comparison(monkeypatch, calls)
    kwargs = {
        "target_sampling_rates_hz": (60.0, 120.0, 60.0),
        "min_label_purities": (0.90, 0.60, 0.90),
        "source_sampling_rate_hz": 240.0,
        "n_splits": 2,
    }
    first = sensitivity.evaluate_sampling_purity_sensitivity(_source_data(), **kwargs)
    second = sensitivity.evaluate_sampling_purity_sensitivity(_source_data(), **kwargs)
    assert first.design["target_sampling_rates_hz"] == [120.0, 60.0]
    assert first.design["min_label_purities"] == [0.6, 0.9]
    assert first.report_fingerprint_sha256 == second.report_fingerprint_sha256
    pd.testing.assert_frame_equal(first.settings, second.settings)
    pd.testing.assert_frame_equal(first.model_metrics, second.model_metrics)


def test_invalid_target_rate_is_rejected():
    with pytest.raises(ValueError, match="lower than the source rate"):
        sensitivity.evaluate_sampling_purity_sensitivity(
            _source_data(),
            target_sampling_rates_hz=(240.0,),
            source_sampling_rate_hz=240.0,
            n_splits=2,
        )


def test_invalid_purity_is_rejected():
    with pytest.raises(ValueError, match="min_label_purity"):
        sensitivity.evaluate_sampling_purity_sensitivity(
            _source_data(),
            target_sampling_rates_hz=(60.0,),
            min_label_purities=(0.0,),
            source_sampling_rate_hz=240.0,
            n_splits=2,
        )


def test_non_evaluable_setting_is_kept_without_model_call(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Model comparison should not run for an insufficient-group setting.")

    monkeypatch.setattr(sensitivity, "compare_event_models_grouped", fail_if_called)
    result = sensitivity.evaluate_sampling_purity_sensitivity(
        _source_data(n_participants=1),
        target_sampling_rates_hz=(60.0,),
        min_label_purities=(0.75,),
        source_sampling_rate_hz=240.0,
        n_splits=2,
    )
    assert len(result.settings) == 1
    row = result.settings.iloc[0]
    assert row["comparison_status"] == "not_evaluable"
    assert row["comparison_reason"] == "insufficient_groups_for_requested_splits"
    assert result.model_metrics.empty


def test_lund_style_unlabelled_rows_are_excluded_after_resampling(monkeypatch):
    calls = []
    _fake_comparison(monkeypatch, calls)
    source = _source_data()
    source.loc[source.index % 20 < 5, "event_label"] = "unlabelled"
    result = sensitivity.evaluate_sampling_purity_sensitivity(
        source,
        target_sampling_rates_hz=(60.0,),
        min_label_purities=(0.75,),
        source_sampling_rate_hz=240.0,
        n_splits=2,
    )
    assert len(calls) == 1
    assert result.settings.loc[0, "excluded_rows_after_resampling"] > 0
