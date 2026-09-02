"""Calibration diagnostics for probabilistic eye-event predictions."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

from .exceptions import SchemaError


def _probability_columns(
    predictions: pd.DataFrame,
    *,
    prefix: str = "p_event_",
) -> list[str]:
    cols = [col for col in predictions.columns if col.startswith(prefix)]
    if not cols:
        raise SchemaError(f"No probability columns with prefix {prefix!r} were found.")
    return cols


def _labels_from_probability_columns(
    probability_cols: Sequence[str],
    *,
    prefix: str = "p_event_",
) -> list[str]:
    return [str(col)[len(prefix) :] for col in probability_cols]


def multiclass_brier_score(
    y_true: Sequence[object] | pd.Series | np.ndarray,
    probabilities: pd.DataFrame | np.ndarray,
    *,
    labels: Sequence[str] | None = None,
) -> float:
    """Return the mean multiclass Brier score (lower is better)."""
    true = np.asarray(y_true).astype(str)
    if isinstance(probabilities, pd.DataFrame):
        matrix = probabilities.to_numpy(dtype=float)
        inferred = [str(col) for col in probabilities.columns]
        labels = inferred if labels is None else [str(v) for v in labels]
    else:
        matrix = np.asarray(probabilities, dtype=float)
        if labels is None:
            raise ValueError("labels are required when probabilities are supplied as an array.")
        labels = [str(v) for v in labels]

    if matrix.ndim != 2 or matrix.shape[0] != len(true):
        raise ValueError("probabilities must be a 2D matrix aligned with y_true.")
    if matrix.shape[1] != len(labels):
        raise ValueError("The number of probability columns must match labels.")
    if np.any(matrix < 0) or np.any(matrix > 1):
        raise ValueError("Probabilities must be in [0, 1].")
    if not np.allclose(matrix.sum(axis=1), 1.0, atol=1e-6):
        raise ValueError("Each probability row must sum to 1.")

    label_to_index = {label: i for i, label in enumerate(labels)}
    unknown = sorted(set(true) - set(label_to_index))
    if unknown:
        raise ValueError(f"y_true contains labels absent from probability columns: {unknown}")

    target = np.zeros_like(matrix, dtype=float)
    target[np.arange(len(true)), [label_to_index[value] for value in true]] = 1.0
    return float(np.mean(np.sum((matrix - target) ** 2, axis=1)))


def top_label_calibration_table(
    predictions: pd.DataFrame,
    *,
    true_label_col: str = "event_label",
    probability_prefix: str = "p_event_",
    n_bins: int = 10,
) -> pd.DataFrame:
    """Bin top-label confidence and compare confidence with empirical accuracy."""
    if true_label_col not in predictions.columns:
        raise SchemaError(f"Missing true-label column: {true_label_col!r}")
    if n_bins < 2:
        raise ValueError("n_bins must be at least 2.")

    probability_cols = _probability_columns(predictions, prefix=probability_prefix)
    labels = _labels_from_probability_columns(probability_cols, prefix=probability_prefix)
    matrix = predictions[probability_cols].to_numpy(dtype=float)
    if not np.allclose(matrix.sum(axis=1), 1.0, atol=1e-6):
        raise ValueError("Each probability row must sum to 1.")

    top_index = np.argmax(matrix, axis=1)
    confidence = matrix[np.arange(len(matrix)), top_index]
    predicted_label = np.asarray(labels, dtype=object)[top_index].astype(str)
    true_label = predictions[true_label_col].astype(str).to_numpy()
    correct = predicted_label == true_label

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    # Include confidence=1 in the final bin.
    bin_index = np.clip(np.digitize(confidence, edges[1:-1], right=False), 0, n_bins - 1)
    rows: list[dict[str, Any]] = []
    for i in range(n_bins):
        mask = bin_index == i
        n = int(mask.sum())
        rows.append(
            {
                "bin": i + 1,
                "lower": float(edges[i]),
                "upper": float(edges[i + 1]),
                "n": n,
                "mean_confidence": float(confidence[mask].mean()) if n else np.nan,
                "accuracy": float(correct[mask].mean()) if n else np.nan,
            }
        )
    return pd.DataFrame(rows)


def expected_calibration_error(
    predictions: pd.DataFrame,
    *,
    true_label_col: str = "event_label",
    probability_prefix: str = "p_event_",
    n_bins: int = 10,
) -> float:
    """Return weighted top-label expected calibration error (ECE)."""
    table = top_label_calibration_table(
        predictions,
        true_label_col=true_label_col,
        probability_prefix=probability_prefix,
        n_bins=n_bins,
    )
    total = int(table["n"].sum())
    if total == 0:
        raise ValueError("Cannot compute calibration error for an empty prediction table.")
    nonempty = table[table["n"] > 0]
    gap = (nonempty["accuracy"] - nonempty["mean_confidence"]).abs()
    weights = nonempty["n"] / total
    return float((gap * weights).sum())


def selective_accuracy_curve(
    predictions: pd.DataFrame,
    *,
    true_label_col: str = "event_label",
    confidence_col: str = "event_confidence",
    predicted_label_col: str = "predicted_event",
    thresholds: Sequence[float] = (0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95),
) -> pd.DataFrame:
    """Report accuracy-versus-coverage as low-confidence samples are abstained from."""
    required = [true_label_col, confidence_col, predicted_label_col]
    missing = [col for col in required if col not in predictions.columns]
    if missing:
        raise SchemaError(f"Selective-accuracy input is missing columns: {missing}")

    confidence = pd.to_numeric(predictions[confidence_col], errors="coerce")
    truth = predictions[true_label_col].astype(str)
    predicted = predictions[predicted_label_col].astype(str)
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        threshold = float(threshold)
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("All confidence thresholds must be in [0, 1].")
        retained = confidence >= threshold
        n = int(retained.sum())
        rows.append(
            {
                "confidence_threshold": threshold,
                "n_retained": n,
                "coverage": float(retained.mean()),
                "accuracy": float((truth[retained] == predicted[retained]).mean())
                if n
                else np.nan,
            }
        )
    return pd.DataFrame(rows)


def evaluate_event_calibration(
    predictions: pd.DataFrame,
    *,
    true_label_col: str = "event_label",
    probability_prefix: str = "p_event_",
    n_bins: int = 10,
) -> dict[str, Any]:
    """Return Brier score, ECE, calibration bins, and confidence/coverage diagnostics."""
    probability_cols = _probability_columns(predictions, prefix=probability_prefix)
    labels = _labels_from_probability_columns(probability_cols, prefix=probability_prefix)
    if true_label_col not in predictions.columns:
        raise SchemaError(f"Missing true-label column: {true_label_col!r}")

    table = top_label_calibration_table(
        predictions,
        true_label_col=true_label_col,
        probability_prefix=probability_prefix,
        n_bins=n_bins,
    )
    return {
        "multiclass_brier_score": multiclass_brier_score(
            predictions[true_label_col],
            predictions[probability_cols],
            labels=labels,
        ),
        "expected_calibration_error": expected_calibration_error(
            predictions,
            true_label_col=true_label_col,
            probability_prefix=probability_prefix,
            n_bins=n_bins,
        ),
        "calibration_table": table.to_dict(orient="records"),
        "selective_accuracy": selective_accuracy_curve(
            predictions,
            true_label_col=true_label_col,
        ).to_dict(orient="records"),
    }
