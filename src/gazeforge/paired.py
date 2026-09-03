"""Matched-fold descriptive differences for event-model validation metrics."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd

from .exceptions import SchemaError

_METRIC_DIRECTIONS: dict[str, int] = {
    "accuracy": 1,
    "balanced_accuracy": 1,
    "macro_f1": 1,
    "multiclass_brier_score": -1,
    "expected_calibration_error": -1,
    "event_precision": 1,
    "event_recall": 1,
    "event_f1": 1,
    "event_mean_matched_iou": 1,
    "event_mean_abs_onset_error_ms": -1,
    "event_mean_abs_offset_error_ms": -1,
    "event_mean_abs_duration_error_ms": -1,
}


@dataclass(slots=True)
class PairedModelDifferences:
    """Per-fold paired deltas plus descriptive summaries for every model pair."""

    deltas: pd.DataFrame
    summary: pd.DataFrame
    design: dict[str, Any]


def _validate_fold_table(
    fold_metrics: pd.DataFrame,
    *,
    model_col: str,
    fold_col: str,
) -> None:
    missing = [column for column in (model_col, fold_col) if column not in fold_metrics.columns]
    if missing:
        raise SchemaError(f"Paired model differences require columns: {missing}")
    if fold_metrics.empty:
        raise ValueError("fold_metrics must contain at least one row.")
    if fold_metrics[[model_col, fold_col]].isna().any().any():
        raise SchemaError("Model and fold identifiers cannot be missing.")
    if fold_metrics.duplicated([model_col, fold_col]).any():
        raise SchemaError("Each model/fold combination must appear at most once.")


def _metric_direction(metric: str) -> int:
    if metric not in _METRIC_DIRECTIONS:
        raise ValueError(
            f"No performance direction is registered for metric {metric!r}; "
            "supply only supported metrics."
        )
    return _METRIC_DIRECTIONS[metric]


def _empty_summary_row(
    *,
    model_a: str,
    model_b: str,
    metric: str,
    direction: int,
) -> dict[str, Any]:
    return {
        "model_a": model_a,
        "model_b": model_b,
        "metric": metric,
        "better_direction": "higher" if direction > 0 else "lower",
        "n_paired_folds": 0,
        "mean_delta_a_minus_b": np.nan,
        "median_delta_a_minus_b": np.nan,
        "std_delta_a_minus_b": np.nan,
        "min_delta_a_minus_b": np.nan,
        "max_delta_a_minus_b": np.nan,
        "mean_improvement_for_a": np.nan,
        "wins_model_a": 0,
        "ties": 0,
        "wins_model_b": 0,
    }


def paired_model_metric_differences(
    fold_metrics: pd.DataFrame,
    *,
    model_col: str = "model",
    fold_col: str = "fold",
    metrics: tuple[str, ...] | None = None,
    tie_tolerance: float = 1e-12,
) -> PairedModelDifferences:
    """Compare model metrics on exactly matched folds without inferential p-values.

    Raw deltas are always ``model_a - model_b``. ``improvement_for_a`` multiplies the raw delta by
    the registered metric direction so positive values always mean model A performed better. The
    function is deliberately descriptive: cross-validation folds share training data and are not
    treated as independent replicates for hypothesis tests or confidence intervals.
    """
    _validate_fold_table(fold_metrics, model_col=model_col, fold_col=fold_col)
    tolerance = float(tie_tolerance)
    if not np.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tie_tolerance must be finite and non-negative.")

    model_order = [str(value) for value in pd.unique(fold_metrics[model_col].astype(str))]
    if len(model_order) < 2:
        raise ValueError("At least two models are required for paired differences.")

    selected_metrics = (
        tuple(metric for metric in _METRIC_DIRECTIONS if metric in fold_metrics.columns)
        if metrics is None
        else tuple(str(metric) for metric in metrics)
    )
    if not selected_metrics:
        raise ValueError("No supported comparison metrics were selected.")
    missing_metrics = [metric for metric in selected_metrics if metric not in fold_metrics.columns]
    if missing_metrics:
        raise SchemaError(f"Paired comparison metrics are missing: {missing_metrics}")
    for metric in selected_metrics:
        _metric_direction(metric)

    delta_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for model_a, model_b in combinations(model_order, 2):
        left = fold_metrics.loc[
            fold_metrics[model_col].astype(str) == model_a,
            [fold_col, *selected_metrics],
        ].copy()
        right = fold_metrics.loc[
            fold_metrics[model_col].astype(str) == model_b,
            [fold_col, *selected_metrics],
        ].copy()
        paired = left.merge(
            right,
            on=fold_col,
            how="inner",
            suffixes=("_a", "_b"),
            validate="one_to_one",
        )

        for metric in selected_metrics:
            direction = _metric_direction(metric)
            a = pd.to_numeric(paired[f"{metric}_a"], errors="coerce")
            b = pd.to_numeric(paired[f"{metric}_b"], errors="coerce")
            valid = a.notna() & b.notna()
            fold_values = paired.loc[valid, fold_col].to_numpy()
            value_a = a.loc[valid].to_numpy(dtype=float)
            value_b = b.loc[valid].to_numpy(dtype=float)
            delta_values = value_a - value_b
            improvement_values = delta_values * float(direction)

            for fold, a_value, b_value, raw_delta, oriented in zip(
                fold_values,
                value_a,
                value_b,
                delta_values,
                improvement_values,
                strict=True,
            ):
                outcome = (
                    "tie"
                    if abs(float(oriented)) <= tolerance
                    else "model_a" if float(oriented) > 0 else "model_b"
                )
                delta_rows.append(
                    {
                        "model_a": model_a,
                        "model_b": model_b,
                        "fold": fold,
                        "metric": metric,
                        "better_direction": "higher" if direction > 0 else "lower",
                        "value_model_a": float(a_value),
                        "value_model_b": float(b_value),
                        "delta_a_minus_b": float(raw_delta),
                        "improvement_for_a": float(oriented),
                        "outcome": outcome,
                    }
                )

            if not len(delta_values):
                summary_rows.append(
                    _empty_summary_row(
                        model_a=model_a,
                        model_b=model_b,
                        metric=metric,
                        direction=direction,
                    )
                )
                continue

            outcomes = np.where(
                np.abs(improvement_values) <= tolerance,
                "tie",
                np.where(improvement_values > 0, "model_a", "model_b"),
            )
            summary_rows.append(
                {
                    "model_a": model_a,
                    "model_b": model_b,
                    "metric": metric,
                    "better_direction": "higher" if direction > 0 else "lower",
                    "n_paired_folds": int(len(delta_values)),
                    "mean_delta_a_minus_b": float(np.mean(delta_values)),
                    "median_delta_a_minus_b": float(np.median(delta_values)),
                    "std_delta_a_minus_b": (
                        float(np.std(delta_values, ddof=1))
                        if len(delta_values) > 1
                        else 0.0
                    ),
                    "min_delta_a_minus_b": float(np.min(delta_values)),
                    "max_delta_a_minus_b": float(np.max(delta_values)),
                    "mean_improvement_for_a": float(np.mean(improvement_values)),
                    "wins_model_a": int((outcomes == "model_a").sum()),
                    "ties": int((outcomes == "tie").sum()),
                    "wins_model_b": int((outcomes == "model_b").sum()),
                }
            )

    deltas = pd.DataFrame(delta_rows)
    summary = pd.DataFrame(summary_rows)
    design = {
        "design": "matched_cross_validation_fold_descriptive_differences",
        "model_col": model_col,
        "fold_col": fold_col,
        "model_order": model_order,
        "metrics": list(selected_metrics),
        "metric_directions": {
            metric: "higher" if _metric_direction(metric) > 0 else "lower"
            for metric in selected_metrics
        },
        "delta_definition": "model_a_minus_model_b",
        "improvement_definition": "positive_means_model_a_better",
        "tie_tolerance": tolerance,
        "inferential_p_values": False,
        "confidence_intervals": False,
        "folds_treated_as_independent_replicates": False,
    }
    return PairedModelDifferences(
        deltas=deltas,
        summary=summary,
        design=design,
    )
