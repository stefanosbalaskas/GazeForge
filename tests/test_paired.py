import numpy as np
import pandas as pd
import pytest

from gazeforge.exceptions import SchemaError
from gazeforge.paired import paired_model_metric_differences


def _fold_metrics():
    return pd.DataFrame(
        [
            {
                "model": "I-VT",
                "fold": 1,
                "accuracy": 0.70,
                "macro_f1": 0.62,
                "multiclass_brier_score": np.nan,
            },
            {
                "model": "RandomForest",
                "fold": 1,
                "accuracy": 0.80,
                "macro_f1": 0.72,
                "multiclass_brier_score": 0.24,
            },
            {
                "model": "ContextMLP",
                "fold": 1,
                "accuracy": 0.78,
                "macro_f1": 0.72,
                "multiclass_brier_score": 0.30,
            },
            {
                "model": "I-VT",
                "fold": 2,
                "accuracy": 0.72,
                "macro_f1": 0.64,
                "multiclass_brier_score": np.nan,
            },
            {
                "model": "RandomForest",
                "fold": 2,
                "accuracy": 0.82,
                "macro_f1": 0.75,
                "multiclass_brier_score": 0.22,
            },
            {
                "model": "ContextMLP",
                "fold": 2,
                "accuracy": 0.82,
                "macro_f1": 0.73,
                "multiclass_brier_score": 0.28,
            },
        ]
    )


def _summary_row(result, model_a, model_b, metric):
    row = result.summary.loc[
        (result.summary["model_a"] == model_a)
        & (result.summary["model_b"] == model_b)
        & (result.summary["metric"] == metric)
    ]
    assert len(row) == 1
    return row.iloc[0]


def test_paired_differences_preserve_model_order_and_higher_is_better_semantics():
    result = paired_model_metric_differences(
        _fold_metrics(),
        metrics=("accuracy", "macro_f1"),
    )

    assert result.design["model_order"] == ["I-VT", "RandomForest", "ContextMLP"]
    pairs = list(
        result.summary[["model_a", "model_b"]].drop_duplicates().itertuples(
            index=False,
            name=None,
        )
    )
    assert pairs == [
        ("I-VT", "RandomForest"),
        ("I-VT", "ContextMLP"),
        ("RandomForest", "ContextMLP"),
    ]
    row = _summary_row(result, "RandomForest", "ContextMLP", "accuracy")
    assert row["mean_delta_a_minus_b"] == pytest.approx(0.01)
    assert row["mean_improvement_for_a"] == pytest.approx(0.01)
    assert row["wins_model_a"] == 1
    assert row["ties"] == 1
    assert row["wins_model_b"] == 0


def test_lower_is_better_keeps_raw_delta_but_orients_improvement():
    result = paired_model_metric_differences(
        _fold_metrics(),
        metrics=("multiclass_brier_score",),
    )

    row = _summary_row(
        result,
        "RandomForest",
        "ContextMLP",
        "multiclass_brier_score",
    )
    assert row["better_direction"] == "lower"
    assert row["mean_delta_a_minus_b"] == pytest.approx(-0.06)
    assert row["mean_improvement_for_a"] == pytest.approx(0.06)
    assert row["wins_model_a"] == 2
    assert row["wins_model_b"] == 0


def test_missing_calibration_values_create_zero_pair_summary_not_fake_scores():
    result = paired_model_metric_differences(
        _fold_metrics(),
        metrics=("multiclass_brier_score",),
    )

    ivt_rf = _summary_row(
        result,
        "I-VT",
        "RandomForest",
        "multiclass_brier_score",
    )
    rf_context = _summary_row(
        result,
        "RandomForest",
        "ContextMLP",
        "multiclass_brier_score",
    )
    assert ivt_rf["n_paired_folds"] == 0
    assert np.isnan(ivt_rf["mean_delta_a_minus_b"])
    assert rf_context["n_paired_folds"] == 2


def test_tie_tolerance_controls_win_tie_loss_classification():
    data = pd.DataFrame(
        [
            {"model": "A", "fold": 1, "accuracy": 0.8000},
            {"model": "B", "fold": 1, "accuracy": 0.8005},
            {"model": "A", "fold": 2, "accuracy": 0.8100},
            {"model": "B", "fold": 2, "accuracy": 0.8000},
        ]
    )
    result = paired_model_metric_differences(
        data,
        metrics=("accuracy",),
        tie_tolerance=0.001,
    )
    row = result.summary.iloc[0]
    assert row["wins_model_a"] == 1
    assert row["ties"] == 1
    assert row["wins_model_b"] == 0


def test_duplicate_model_fold_rows_are_rejected():
    data = pd.concat([_fold_metrics(), _fold_metrics().iloc[[0]]], ignore_index=True)
    with pytest.raises(SchemaError, match="at most once"):
        paired_model_metric_differences(data, metrics=("accuracy",))


def test_models_must_have_identical_fold_coverage():
    data = _fold_metrics().loc[
        ~((_fold_metrics()["model"] == "ContextMLP") & (_fold_metrics()["fold"] == 2))
    ]
    with pytest.raises(SchemaError, match="identical validation-fold coverage"):
        paired_model_metric_differences(data, metrics=("accuracy",))


def test_paired_difference_design_refuses_cv_inference_claims():
    result = paired_model_metric_differences(
        _fold_metrics(),
        metrics=("accuracy",),
    )
    assert result.design["inferential_p_values"] is False
    assert result.design["confidence_intervals"] is False
    assert result.design["folds_treated_as_independent_replicates"] is False
    assert result.design["delta_definition"] == "model_a_minus_model_b"
    assert result.design["improvement_definition"] == "positive_means_model_a_better"
