import numpy as np

from gazeforge import compare_event_models_grouped, ivt_classify_events, simulate_gaze


def _comparison_fixture():
    data = simulate_gaze(
        n_participants=4,
        n_trials=2,
        samples_per_trial=60,
        sampling_rate_hz=60,
        random_state=121,
    )
    baseline = ivt_classify_events(
        data,
        sampling_rate_hz=60,
        velocity_threshold_px_s=700,
    )
    data["event_label"] = baseline["predicted_event"].replace({"noise": "fixation"})
    data.loc[data.index[::25], "event_label"] = "saccade"
    return data


def test_model_comparison_uses_identical_test_rows():
    data = _comparison_fixture()
    result = compare_event_models_grouped(
        data,
        n_splits=2,
        sampling_rate_hz=60,
        n_estimators=20,
        context_radius_ms=35,
        hidden_layer_sizes=(8,),
        temporal_solver="lbfgs",
        temporal_max_iter=250,
        calibration_bins=5,
    )
    assert set(result.summary["model"]) == {"I-VT", "RandomForest", "ContextMLP"}
    assert len(result.predictions) == 3 * len(data)
    for fold in result.fold_metrics["fold"].unique():
        part = result.predictions[result.predictions["validation_fold"] == fold]
        row_sets = {
            model: tuple(sorted(model_part["comparison_row_position"].astype(int)))
            for model, model_part in part.groupby("comparison_model")
        }
        assert len(set(row_sets.values())) == 1


def test_model_comparison_reports_calibration_only_for_probabilistic_models():
    data = _comparison_fixture()
    result = compare_event_models_grouped(
        data,
        n_splits=2,
        sampling_rate_hz=60,
        n_estimators=15,
        context_radius_ms=35,
        hidden_layer_sizes=(8,),
        temporal_solver="lbfgs",
        temporal_max_iter=250,
        calibration_bins=4,
    )
    ivt = result.fold_metrics[result.fold_metrics["model"] == "I-VT"]
    learned = result.fold_metrics[result.fold_metrics["model"] != "I-VT"]
    assert ivt["multiclass_brier_score"].isna().all()
    assert ivt["expected_calibration_error"].isna().all()
    assert learned["multiclass_brier_score"].notna().all()
    assert learned["expected_calibration_error"].notna().all()
    assert np.isfinite(learned["macro_f1"]).all()
    assert result.fold_metrics["event_f1"].between(0, 1).all()
    assert result.fold_metrics["event_mean_matched_iou"].between(0, 1).all()


def test_model_comparison_summary_has_fold_mean_and_spread():
    result = compare_event_models_grouped(
        _comparison_fixture(),
        n_splits=2,
        sampling_rate_hz=60,
        n_estimators=15,
        context_radius_ms=35,
        hidden_layer_sizes=(8,),
        temporal_solver="lbfgs",
        temporal_max_iter=250,
    )
    assert (result.summary["n_folds"] == 2).all()
    for metric in ("accuracy", "balanced_accuracy", "macro_f1", "event_f1"):
        assert result.summary[f"{metric}_mean"].between(0, 1).all()
        assert result.summary[f"{metric}_std"].ge(0).all()
