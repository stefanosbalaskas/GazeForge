"""Leakage-aware validation utilities for learned gaze models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, GroupShuffleSplit

from .events import ai_classify_events, evaluate_event_predictions, train_event_classifier
from .exceptions import SchemaError
from .schema import infer_sampling_rate_hz
from .temporal import ai_classify_events_context, train_context_event_classifier


@dataclass(slots=True)
class ValidationResult:
    """Grouped cross-validation predictions, fold metadata, and aggregate metrics."""

    predictions: pd.DataFrame
    folds: pd.DataFrame
    metrics: dict[str, Any]


def grouped_holdout_indices(
    data: pd.DataFrame,
    *,
    group_col: str = "participant_id",
    test_size: float = 0.20,
    random_state: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Return one train/test split with groups strictly isolated between partitions."""
    if group_col not in data.columns:
        raise SchemaError(f"Missing grouping column: {group_col!r}")
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=float(test_size),
        random_state=int(random_state),
    )
    train_idx, test_idx = next(splitter.split(data, groups=data[group_col]))
    return train_idx, test_idx


def assert_no_group_leakage(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    group_cols: tuple[str, ...] = ("participant_id",),
) -> None:
    """Raise if any protected grouping unit appears in both train and test."""
    for col in group_cols:
        if col not in train.columns or col not in test.columns:
            raise SchemaError(f"Missing leakage-check column: {col!r}")
        overlap = set(train[col].dropna().astype(str)) & set(test[col].dropna().astype(str))
        if overlap:
            preview = sorted(overlap)[:5]
            raise SchemaError(
                f"Group leakage detected in {col!r}: {len(overlap)} overlapping values; "
                f"examples={preview}"
            )


def grouped_event_cross_validate(
    data: pd.DataFrame,
    *,
    label_col: str = "event_label",
    group_col: str = "participant_id",
    n_splits: int = 5,
    sampling_rate_hz: float | None = None,
    min_confidence: float = 0.0,
    random_state: int = 42,
    n_estimators: int = 200,
) -> ValidationResult:
    """Evaluate event classification with participant/group-held-out folds.

    This function intentionally fits a fresh model inside every fold. It never trains on samples
    from a group that is present in that fold's test partition.
    """
    for col in (label_col, group_col):
        if col not in data.columns:
            raise SchemaError(f"Missing cross-validation column: {col!r}")

    groups = data[group_col].astype(str)
    n_groups = groups.nunique()
    if n_splits < 2 or n_splits > n_groups:
        raise ValueError("n_splits must be between 2 and the number of unique groups.")

    rate = (
        float(sampling_rate_hz)
        if sampling_rate_hz is not None
        else infer_sampling_rate_hz(data)
    )
    splitter = GroupKFold(n_splits=int(n_splits))
    prediction_parts: list[pd.DataFrame] = []
    fold_rows: list[dict[str, Any]] = []

    for fold, (train_idx, test_idx) in enumerate(
        splitter.split(data, y=data[label_col], groups=groups),
        start=1,
    ):
        train = data.iloc[train_idx].copy()
        test = data.iloc[test_idx].copy()
        assert_no_group_leakage(train, test, group_cols=(group_col,))

        model = train_event_classifier(
            train,
            label_col=label_col,
            sampling_rate_hz=rate,
            random_state=int(random_state) + fold,
            n_estimators=int(n_estimators),
        )
        predicted = ai_classify_events(
            test,
            model,
            sampling_rate_hz=rate,
            min_confidence=min_confidence,
        )
        predicted["validation_fold"] = fold
        predicted["validation_group_col"] = group_col
        prediction_parts.append(predicted)

        fold_rows.append(
            {
                "fold": fold,
                "n_train_rows": len(train),
                "n_test_rows": len(test),
                "n_train_groups": train[group_col].nunique(),
                "n_test_groups": test[group_col].nunique(),
                "test_groups": tuple(sorted(test[group_col].astype(str).unique())),
            }
        )

    predictions = pd.concat(prediction_parts, ignore_index=True)
    metrics = evaluate_event_predictions(
        predictions[label_col],
        predictions["predicted_event"],
    )
    metrics["validation_design"] = {
        "group_col": group_col,
        "n_splits": int(n_splits),
        "sampling_rate_hz": rate,
        "random_state": int(random_state),
    }
    return ValidationResult(
        predictions=predictions,
        folds=pd.DataFrame(fold_rows),
        metrics=metrics,
    )


def dataset_holdout_event_validate(
    data: pd.DataFrame,
    *,
    dataset_col: str = "dataset_id",
    participant_col: str = "participant_id",
    label_col: str = "event_label",
    sampling_rate_hz: float | None = None,
    min_confidence: float = 0.0,
    random_state: int = 42,
    n_estimators: int = 200,
    require_disjoint_participants: bool = True,
) -> ValidationResult:
    """Leave each dataset out in turn to measure cross-dataset generalisation.

    A fresh model is trained for every held-out dataset. When
    ``require_disjoint_participants=True``, the function refuses a split in which participant IDs
    occur in both train and test, preventing identity leakage across dataset labels.
    """
    required = [dataset_col, participant_col, label_col]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise SchemaError(f"Dataset-held-out validation is missing columns: {missing}")

    datasets = sorted(data[dataset_col].dropna().astype(str).unique())
    if len(datasets) < 2:
        raise ValueError("At least two datasets are required for dataset-held-out validation.")

    rate = (
        float(sampling_rate_hz)
        if sampling_rate_hz is not None
        else infer_sampling_rate_hz(data)
    )
    prediction_parts: list[pd.DataFrame] = []
    fold_rows: list[dict[str, Any]] = []

    dataset_values = data[dataset_col].astype(str)
    for fold, held_out in enumerate(datasets, start=1):
        test = data.loc[dataset_values == held_out].copy()
        train = data.loc[dataset_values != held_out].copy()
        if require_disjoint_participants:
            assert_no_group_leakage(train, test, group_cols=(participant_col,))

        model = train_event_classifier(
            train,
            label_col=label_col,
            sampling_rate_hz=rate,
            random_state=int(random_state) + fold,
            n_estimators=int(n_estimators),
        )
        predicted = ai_classify_events(
            test,
            model,
            sampling_rate_hz=rate,
            min_confidence=min_confidence,
        )
        predicted["validation_fold"] = fold
        predicted["held_out_dataset"] = held_out
        prediction_parts.append(predicted)
        fold_rows.append(
            {
                "fold": fold,
                "held_out_dataset": held_out,
                "n_train_rows": int(len(train)),
                "n_test_rows": int(len(test)),
                "n_train_datasets": int(train[dataset_col].nunique()),
                "n_test_participants": int(test[participant_col].nunique()),
            }
        )

    predictions = pd.concat(prediction_parts, ignore_index=True)
    metrics = evaluate_event_predictions(
        predictions[label_col],
        predictions["predicted_event"],
    )
    metrics["validation_design"] = {
        "design": "leave_one_dataset_out",
        "dataset_col": dataset_col,
        "participant_col": participant_col,
        "n_datasets": len(datasets),
        "sampling_rate_hz": rate,
        "require_disjoint_participants": bool(require_disjoint_participants),
    }
    return ValidationResult(
        predictions=predictions,
        folds=pd.DataFrame(fold_rows),
        metrics=metrics,
    )


def grouped_context_event_cross_validate(
    data: pd.DataFrame,
    *,
    label_col: str = "event_label",
    group_col: str = "participant_id",
    n_splits: int = 5,
    sampling_rate_hz: float | None = None,
    min_confidence: float = 0.0,
    random_state: int = 42,
    context_radius_ms: float = 50.0,
    rolling_window_ms: float = 80.0,
    hidden_layer_sizes: tuple[int, ...] = (64, 32),
    solver: str = "adam",
    max_iter: int = 200,
) -> ValidationResult:
    """Evaluate the temporal-context event model with group-held-out folds."""
    for col in (label_col, group_col):
        if col not in data.columns:
            raise SchemaError(f"Missing cross-validation column: {col!r}")

    groups = data[group_col].astype(str)
    n_groups = groups.nunique()
    if n_splits < 2 or n_splits > n_groups:
        raise ValueError("n_splits must be between 2 and the number of unique groups.")

    rate = (
        float(sampling_rate_hz)
        if sampling_rate_hz is not None
        else infer_sampling_rate_hz(data)
    )
    splitter = GroupKFold(n_splits=int(n_splits))
    prediction_parts: list[pd.DataFrame] = []
    fold_rows: list[dict[str, Any]] = []

    for fold, (train_idx, test_idx) in enumerate(
        splitter.split(data, y=data[label_col], groups=groups),
        start=1,
    ):
        train = data.iloc[train_idx].copy()
        test = data.iloc[test_idx].copy()
        assert_no_group_leakage(train, test, group_cols=(group_col,))

        model = train_context_event_classifier(
            train,
            label_col=label_col,
            sampling_rate_hz=rate,
            context_radius_ms=context_radius_ms,
            rolling_window_ms=rolling_window_ms,
            hidden_layer_sizes=hidden_layer_sizes,
            solver=solver,
            max_iter=max_iter,
            random_state=int(random_state) + fold,
        )
        predicted = ai_classify_events_context(
            test,
            model,
            sampling_rate_hz=rate,
            min_confidence=min_confidence,
        )
        predicted["validation_fold"] = fold
        predicted["validation_group_col"] = group_col
        prediction_parts.append(predicted)
        fold_rows.append(
            {
                "fold": fold,
                "n_train_rows": len(train),
                "n_test_rows": len(test),
                "n_train_groups": train[group_col].nunique(),
                "n_test_groups": test[group_col].nunique(),
                "test_groups": tuple(sorted(test[group_col].astype(str).unique())),
            }
        )

    predictions = pd.concat(prediction_parts, ignore_index=True)
    metrics = evaluate_event_predictions(
        predictions[label_col],
        predictions["predicted_event"],
    )
    metrics["validation_design"] = {
        "design": "group_kfold_temporal_context",
        "group_col": group_col,
        "n_splits": int(n_splits),
        "sampling_rate_hz": rate,
        "random_state": int(random_state),
        "context_radius_ms": float(context_radius_ms),
        "rolling_window_ms": float(rolling_window_ms),
    }
    return ValidationResult(
        predictions=predictions,
        folds=pd.DataFrame(fold_rows),
        metrics=metrics,
    )


def dataset_holdout_context_event_validate(
    data: pd.DataFrame,
    *,
    dataset_col: str = "dataset_id",
    participant_col: str = "participant_id",
    label_col: str = "event_label",
    sampling_rate_hz: float | None = None,
    min_confidence: float = 0.0,
    random_state: int = 42,
    context_radius_ms: float = 50.0,
    rolling_window_ms: float = 80.0,
    hidden_layer_sizes: tuple[int, ...] = (64, 32),
    solver: str = "adam",
    max_iter: int = 200,
    require_disjoint_participants: bool = True,
) -> ValidationResult:
    """Evaluate temporal-context events by leaving each dataset out in turn."""
    required = [dataset_col, participant_col, label_col]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise SchemaError(f"Dataset-held-out validation is missing columns: {missing}")

    datasets = sorted(data[dataset_col].dropna().astype(str).unique())
    if len(datasets) < 2:
        raise ValueError("At least two datasets are required for dataset-held-out validation.")

    rate = (
        float(sampling_rate_hz)
        if sampling_rate_hz is not None
        else infer_sampling_rate_hz(data)
    )
    prediction_parts: list[pd.DataFrame] = []
    fold_rows: list[dict[str, Any]] = []
    dataset_values = data[dataset_col].astype(str)

    for fold, held_out in enumerate(datasets, start=1):
        test = data.loc[dataset_values == held_out].copy()
        train = data.loc[dataset_values != held_out].copy()
        if require_disjoint_participants:
            assert_no_group_leakage(train, test, group_cols=(participant_col,))

        model = train_context_event_classifier(
            train,
            label_col=label_col,
            sampling_rate_hz=rate,
            context_radius_ms=context_radius_ms,
            rolling_window_ms=rolling_window_ms,
            hidden_layer_sizes=hidden_layer_sizes,
            solver=solver,
            max_iter=max_iter,
            random_state=int(random_state) + fold,
        )
        predicted = ai_classify_events_context(
            test,
            model,
            sampling_rate_hz=rate,
            min_confidence=min_confidence,
        )
        predicted["validation_fold"] = fold
        predicted["held_out_dataset"] = held_out
        prediction_parts.append(predicted)
        fold_rows.append(
            {
                "fold": fold,
                "held_out_dataset": held_out,
                "n_train_rows": int(len(train)),
                "n_test_rows": int(len(test)),
                "n_train_datasets": int(train[dataset_col].nunique()),
                "n_test_participants": int(test[participant_col].nunique()),
            }
        )

    predictions = pd.concat(prediction_parts, ignore_index=True)
    metrics = evaluate_event_predictions(
        predictions[label_col],
        predictions["predicted_event"],
    )
    metrics["validation_design"] = {
        "design": "leave_one_dataset_out_temporal_context",
        "dataset_col": dataset_col,
        "participant_col": participant_col,
        "n_datasets": len(datasets),
        "sampling_rate_hz": rate,
        "require_disjoint_participants": bool(require_disjoint_participants),
        "context_radius_ms": float(context_radius_ms),
        "rolling_window_ms": float(rolling_window_ms),
    }
    return ValidationResult(
        predictions=predictions,
        folds=pd.DataFrame(fold_rows),
        metrics=metrics,
    )
