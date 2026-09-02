"""Leakage-safe comparison of classical and learned eye-event classifiers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.model_selection import GroupKFold

from .calibration import evaluate_event_calibration
from .events import (
    ai_classify_events,
    ivt_classify_events,
    ivt_classify_events_angular,
    train_event_classifier,
)
from .exceptions import SchemaError
from .schema import infer_sampling_rate_hz
from .temporal import ai_classify_events_context, train_context_event_classifier
from .validation import assert_no_group_leakage


@dataclass(slots=True)
class EventModelComparison:
    """Predictions, fold metrics, and aggregate summaries for matched validation folds."""

    predictions: pd.DataFrame
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


def _fold_metric_row(
    predictions: pd.DataFrame,
    *,
    model_name: str,
    fold: int,
    label_col: str,
    n_train_rows: int,
    n_test_rows: int,
    n_train_groups: int,
    n_test_groups: int,
    calibration_bins: int,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "model": model_name,
        "fold": int(fold),
        "n_train_rows": int(n_train_rows),
        "n_test_rows": int(n_test_rows),
        "n_train_groups": int(n_train_groups),
        "n_test_groups": int(n_test_groups),
        **_classification_metrics(predictions[label_col], predictions["predicted_event"]),
        "multiclass_brier_score": np.nan,
        "expected_calibration_error": np.nan,
    }
    probability_cols = [col for col in predictions.columns if col.startswith("p_event_")]
    if probability_cols:
        calibration = evaluate_event_calibration(
            predictions,
            true_label_col=label_col,
            n_bins=calibration_bins,
        )
        row["multiclass_brier_score"] = float(calibration["multiclass_brier_score"])
        row["expected_calibration_error"] = float(
            calibration["expected_calibration_error"]
        )
    return row


def _comparison_summary(fold_metrics: pd.DataFrame) -> pd.DataFrame:
    metric_cols = [
        "accuracy",
        "balanced_accuracy",
        "macro_f1",
        "multiclass_brier_score",
        "expected_calibration_error",
    ]
    rows: list[dict[str, Any]] = []
    for model_name, part in fold_metrics.groupby("model", sort=False):
        row: dict[str, Any] = {
            "model": model_name,
            "n_folds": int(part["fold"].nunique()),
        }
        for metric in metric_cols:
            values = pd.to_numeric(part[metric], errors="coerce")
            valid = values.dropna()
            row[f"{metric}_mean"] = float(valid.mean()) if len(valid) else np.nan
            row[f"{metric}_std"] = (
                float(valid.std(ddof=1)) if len(valid) > 1 else 0.0 if len(valid) == 1 else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


def compare_event_models_grouped(
    data: pd.DataFrame,
    *,
    label_col: str = "event_label",
    group_col: str = "participant_id",
    n_splits: int = 5,
    sampling_rate_hz: float | None = None,
    ivt_velocity_threshold_px_s: float | None = 1000.0,
    ivt_velocity_threshold_deg_s: float | None = None,
    min_confidence: float = 0.0,
    random_state: int = 42,
    n_estimators: int = 200,
    context_radius_ms: float = 50.0,
    rolling_window_ms: float = 80.0,
    hidden_layer_sizes: tuple[int, ...] = (64, 32),
    temporal_solver: str = "adam",
    temporal_max_iter: int = 200,
    calibration_bins: int = 10,
) -> EventModelComparison:
    """Compare I-VT, Random Forest, and temporal MLP on identical group-held-out folds.

    Each learned model is fitted from scratch within every fold. All three methods are evaluated on
    the exact same test rows. Calibration metrics are reported only for probabilistic learned
    models; deterministic I-VT receives missing calibration values rather than fabricated scores.
    """
    for col in (label_col, group_col):
        if col not in data.columns:
            raise SchemaError(f"Missing comparison column: {col!r}")
    groups = data[group_col].astype(str)
    n_groups = groups.nunique()
    if n_splits < 2 or n_splits > n_groups:
        raise ValueError("n_splits must be between 2 and the number of unique groups.")
    if calibration_bins < 2:
        raise ValueError("calibration_bins must be at least 2.")

    rate = (
        float(sampling_rate_hz)
        if sampling_rate_hz is not None
        else infer_sampling_rate_hz(data)
    )
    splitter = GroupKFold(n_splits=int(n_splits))
    prediction_parts: list[pd.DataFrame] = []
    metric_rows: list[dict[str, Any]] = []

    for fold, (train_idx, test_idx) in enumerate(
        splitter.split(data, y=data[label_col], groups=groups),
        start=1,
    ):
        train = data.iloc[train_idx].copy()
        test = data.iloc[test_idx].copy()
        assert_no_group_leakage(train, test, group_cols=(group_col,))
        test_positions = np.asarray(test_idx, dtype=int)

        if ivt_velocity_threshold_deg_s is not None:
            ivt = ivt_classify_events_angular(
                test,
                sampling_rate_hz=rate,
                velocity_threshold_deg_s=ivt_velocity_threshold_deg_s,
            )
        elif ivt_velocity_threshold_px_s is not None:
            ivt = ivt_classify_events(
                test,
                sampling_rate_hz=rate,
                velocity_threshold_px_s=ivt_velocity_threshold_px_s,
            )
        else:
            raise ValueError(
                "Provide either ivt_velocity_threshold_deg_s or ivt_velocity_threshold_px_s."
            )
        rf_model = train_event_classifier(
            train,
            label_col=label_col,
            sampling_rate_hz=rate,
            random_state=int(random_state) + fold,
            n_estimators=int(n_estimators),
            rolling_window_ms=rolling_window_ms,
        )
        rf = ai_classify_events(
            test,
            rf_model,
            sampling_rate_hz=rate,
            min_confidence=min_confidence,
        )
        context_model = train_context_event_classifier(
            train,
            label_col=label_col,
            sampling_rate_hz=rate,
            context_radius_ms=context_radius_ms,
            rolling_window_ms=rolling_window_ms,
            hidden_layer_sizes=hidden_layer_sizes,
            solver=temporal_solver,
            max_iter=temporal_max_iter,
            random_state=int(random_state) + fold,
        )
        context = ai_classify_events_context(
            test,
            context_model,
            sampling_rate_hz=rate,
            min_confidence=min_confidence,
        )

        model_predictions = (
            ("I-VT", ivt),
            ("RandomForest", rf),
            ("ContextMLP", context),
        )
        for model_name, predicted in model_predictions:
            predicted = predicted.copy()
            predicted["comparison_model"] = model_name
            predicted["validation_fold"] = fold
            predicted["validation_group_col"] = group_col
            predicted["comparison_row_position"] = test_positions
            prediction_parts.append(predicted)
            metric_rows.append(
                _fold_metric_row(
                    predicted,
                    model_name=model_name,
                    fold=fold,
                    label_col=label_col,
                    n_train_rows=len(train),
                    n_test_rows=len(test),
                    n_train_groups=train[group_col].nunique(),
                    n_test_groups=test[group_col].nunique(),
                    calibration_bins=calibration_bins,
                )
            )

    predictions = pd.concat(prediction_parts, ignore_index=True)
    predictions = predictions.sort_values(
        ["validation_fold", "comparison_model", "comparison_row_position"],
        kind="stable",
    ).reset_index(drop=True)
    fold_metrics = pd.DataFrame(metric_rows)
    summary = _comparison_summary(fold_metrics)
    design = {
        "design": "matched_group_kfold_model_comparison",
        "group_col": group_col,
        "n_splits": int(n_splits),
        "sampling_rate_hz": rate,
        "models": ["I-VT", "RandomForest", "ContextMLP"],
        "random_state": int(random_state),
        "ivt_velocity_unit": "deg/s" if ivt_velocity_threshold_deg_s is not None else "px/s",
        "ivt_velocity_threshold_deg_s": (
            float(ivt_velocity_threshold_deg_s)
            if ivt_velocity_threshold_deg_s is not None
            else None
        ),
        "ivt_velocity_threshold_px_s": (
            float(ivt_velocity_threshold_px_s)
            if ivt_velocity_threshold_deg_s is None and ivt_velocity_threshold_px_s is not None
            else None
        ),
        "context_radius_ms": float(context_radius_ms),
        "rolling_window_ms": float(rolling_window_ms),
        "calibration_bins": int(calibration_bins),
    }
    return EventModelComparison(
        predictions=predictions,
        fold_metrics=fold_metrics,
        summary=summary,
        design=design,
    )
