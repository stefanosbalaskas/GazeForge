"""Post-hoc stratified metrics for leakage-safe out-of-fold event predictions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score

from .calibration import evaluate_event_calibration
from .event_evaluation import evaluate_sample_event_predictions
from .exceptions import SchemaError

_METRIC_NAMES = (
    "accuracy",
    "balanced_accuracy",
    "macro_f1",
    "multiclass_brier_score",
    "expected_calibration_error",
    "event_precision",
    "event_recall",
    "event_f1",
    "event_mean_matched_iou",
    "event_mean_abs_onset_error_ms",
    "event_mean_abs_offset_error_ms",
    "event_mean_abs_duration_error_ms",
)


@dataclass(slots=True)
class StratifiedEventPerformance:
    """Fold-wise and aggregate metrics computed from fixed out-of-fold predictions."""

    fold_metrics: pd.DataFrame
    summary: pd.DataFrame
    design: dict[str, Any]


def _classification_metrics(
    truth: pd.Series | np.ndarray,
    predicted: pd.Series | np.ndarray,
) -> dict[str, float]:
    true = np.asarray(truth).astype(str)
    pred = np.asarray(predicted).astype(str)
    return {
        "accuracy": float(accuracy_score(true, pred)),
        "balanced_accuracy": float(
            recall_score(
                true,
                pred,
                labels=sorted(set(true)),
                average="macro",
                zero_division=0,
            )
        ),
        "macro_f1": float(f1_score(true, pred, average="macro", zero_division=0)),
    }


def _calibration_input(predictions: pd.DataFrame) -> pd.DataFrame | None:
    probability_cols = [
        column for column in predictions.columns if column.startswith("p_event_")
    ]
    active = [column for column in probability_cols if predictions[column].notna().any()]
    if not active:
        return None
    if predictions[active].isna().any().any():
        raise SchemaError(
            "Stratified probabilistic predictions contain partially missing probability values."
        )
    inactive = [column for column in probability_cols if column not in active]
    return predictions.drop(columns=inactive)


def _metric_values(
    predictions: pd.DataFrame,
    *,
    label_col: str,
    sampling_rate_hz: float,
    calibration_bins: int,
    include_event_level_metrics: bool,
    event_group_cols: tuple[str, ...],
    event_min_iou: float,
    event_excluded_labels: tuple[str, ...],
) -> dict[str, float]:
    row: dict[str, float] = {
        **_classification_metrics(
            predictions[label_col],
            predictions["predicted_event"],
        ),
        "multiclass_brier_score": np.nan,
        "expected_calibration_error": np.nan,
        "event_precision": np.nan,
        "event_recall": np.nan,
        "event_f1": np.nan,
        "event_mean_matched_iou": np.nan,
        "event_mean_abs_onset_error_ms": np.nan,
        "event_mean_abs_offset_error_ms": np.nan,
        "event_mean_abs_duration_error_ms": np.nan,
    }
    if include_event_level_metrics:
        event_result = evaluate_sample_event_predictions(
            predictions,
            true_label_col=label_col,
            predicted_label_col="predicted_event",
            group_cols=event_group_cols,
            sampling_rate_hz=sampling_rate_hz,
            excluded_labels=event_excluded_labels,
            min_iou=event_min_iou,
        )
        row["event_precision"] = float(event_result.summary["precision"])
        row["event_recall"] = float(event_result.summary["recall"])
        row["event_f1"] = float(event_result.summary["f1"])
        row["event_mean_matched_iou"] = float(
            event_result.summary["mean_matched_iou"]
        )
        row["event_mean_abs_onset_error_ms"] = float(
            event_result.summary["mean_abs_onset_error_ms"]
        )
        row["event_mean_abs_offset_error_ms"] = float(
            event_result.summary["mean_abs_offset_error_ms"]
        )
        row["event_mean_abs_duration_error_ms"] = float(
            event_result.summary["mean_abs_duration_error_ms"]
        )

    calibration_input = _calibration_input(predictions)
    if calibration_input is not None:
        calibration = evaluate_event_calibration(
            calibration_input,
            true_label_col=label_col,
            n_bins=calibration_bins,
        )
        row["multiclass_brier_score"] = float(calibration["multiclass_brier_score"])
        row["expected_calibration_error"] = float(
            calibration["expected_calibration_error"]
        )
    return row


def _validate_event_strata(
    predictions: pd.DataFrame,
    *,
    stratify_col: str,
    model_col: str,
    fold_col: str,
    event_group_cols: tuple[str, ...],
) -> None:
    keys = [model_col, fold_col, *event_group_cols]
    grouped = predictions.groupby(keys, sort=False, dropna=False)[stratify_col]
    counts = grouped.nunique(dropna=False)
    if (counts > 1).any():
        raise SchemaError(
            "Event-level stratification requires each model/fold event group to belong "
            "to exactly one stratum."
        )


def _summary_table(
    fold_metrics: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    stratify_col: str,
    model_col: str,
    group_col: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (model, stratum), part in fold_metrics.groupby(
        ["model", "stratum"],
        sort=True,
        dropna=False,
    ):
        prediction_part = predictions.loc[
            (predictions[model_col].astype(str) == str(model))
            & (predictions[stratify_col].astype(str) == str(stratum))
        ]
        row: dict[str, Any] = {
            "model": str(model),
            "stratum": str(stratum),
            "n_folds": int(part["fold"].nunique()),
            "n_test_rows_total": int(len(prediction_part)),
            "n_test_groups_unique": int(prediction_part[group_col].astype(str).nunique()),
        }
        for metric in _METRIC_NAMES:
            values = pd.to_numeric(part[metric], errors="coerce")
            valid = values.dropna()
            row[f"{metric}_n_folds"] = int(len(valid))
            row[f"{metric}_mean"] = float(valid.mean()) if len(valid) else np.nan
            row[f"{metric}_std"] = (
                float(valid.std(ddof=1))
                if len(valid) > 1
                else 0.0 if len(valid) == 1 else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_event_predictions_by_stratum(
    predictions: pd.DataFrame,
    *,
    stratify_col: str,
    label_col: str = "event_label",
    model_col: str = "comparison_model",
    fold_col: str = "validation_fold",
    group_col: str = "participant_id",
    sampling_rate_hz: float,
    calibration_bins: int = 10,
    include_event_level_metrics: bool = True,
    event_group_cols: tuple[str, ...] = ("participant_id", "trial_id"),
    event_min_iou: float = 0.50,
    event_excluded_labels: tuple[str, ...] = (
        "ambiguous",
        "unlabelled",
        "undefined",
        "abstain",
    ),
) -> StratifiedEventPerformance:
    """Summarize fixed out-of-fold predictions by a declared analysis stratum.

    This function never fits or refits a model. It is intended for post-hoc descriptive validation
    of predictions that were already generated under a leakage-safe validation design. Fold-level
    metrics are computed first and then summarized, preserving fold-to-fold variability.
    """
    required = [
        stratify_col,
        label_col,
        "predicted_event",
        model_col,
        fold_col,
        group_col,
    ]
    if include_event_level_metrics:
        required.extend(event_group_cols)
    missing = sorted({column for column in required if column not in predictions.columns})
    if missing:
        raise SchemaError(f"Stratified prediction metrics require columns: {missing}")
    if predictions.empty:
        raise ValueError("predictions must contain at least one row.")
    for column in (stratify_col, model_col, fold_col, group_col):
        if predictions[column].isna().any():
            raise SchemaError(
                f"Stratified prediction column {column!r} cannot contain missing values."
            )
    if calibration_bins < 2:
        raise ValueError("calibration_bins must be at least 2.")
    if not 0.0 <= float(event_min_iou) <= 1.0:
        raise ValueError("event_min_iou must be in [0, 1].")
    rate = float(sampling_rate_hz)
    if not np.isfinite(rate) or rate <= 0:
        raise ValueError("sampling_rate_hz must be finite and positive.")
    if include_event_level_metrics:
        _validate_event_strata(
            predictions,
            stratify_col=stratify_col,
            model_col=model_col,
            fold_col=fold_col,
            event_group_cols=event_group_cols,
        )

    rows: list[dict[str, Any]] = []
    grouped = predictions.groupby(
        [model_col, fold_col, stratify_col],
        sort=True,
        dropna=False,
    )
    for (model, fold, stratum), part in grouped:
        rows.append(
            {
                "model": str(model),
                "fold": int(fold),
                "stratum": str(stratum),
                "n_test_rows": int(len(part)),
                "n_test_groups": int(part[group_col].astype(str).nunique()),
                "n_reference_classes": int(part[label_col].astype(str).nunique()),
                **_metric_values(
                    part,
                    label_col=label_col,
                    sampling_rate_hz=rate,
                    calibration_bins=calibration_bins,
                    include_event_level_metrics=include_event_level_metrics,
                    event_group_cols=event_group_cols,
                    event_min_iou=event_min_iou,
                    event_excluded_labels=event_excluded_labels,
                ),
            }
        )
    fold_metrics = pd.DataFrame(rows)
    summary = _summary_table(
        fold_metrics,
        predictions,
        stratify_col=stratify_col,
        model_col=model_col,
        group_col=group_col,
    )
    design = {
        "design": "posthoc_out_of_fold_stratified_event_performance",
        "stratify_col": stratify_col,
        "label_col": label_col,
        "model_col": model_col,
        "fold_col": fold_col,
        "group_col": group_col,
        "sampling_rate_hz": rate,
        "calibration_bins": int(calibration_bins),
        "include_event_level_metrics": bool(include_event_level_metrics),
        "event_group_cols": list(event_group_cols),
        "event_min_iou": float(event_min_iou),
        "event_excluded_labels": list(event_excluded_labels),
        "models_refit_by_stratum": False,
    }
    return StratifiedEventPerformance(
        fold_metrics=fold_metrics,
        summary=summary,
        design=design,
    )
