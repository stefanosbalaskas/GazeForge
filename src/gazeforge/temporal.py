"""Sampling-rate-aware temporal-context models for eye-event classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .events import _build_event_features, _safe_label
from .exceptions import ModelCompatibilityError, SchemaError
from .schema import infer_sampling_rate_hz


def _context_matrix(
    data: pd.DataFrame,
    *,
    sampling_rate_hz: float,
    context_radius_ms: float,
    rolling_window_ms: float = 80.0,
    group_cols: tuple[str, ...] = ("participant_id", "trial_id"),
) -> tuple[np.ndarray, tuple[str, ...], int]:
    """Build flattened, boundary-safe temporal feature windows around every sample."""
    if context_radius_ms < 0:
        raise ValueError("context_radius_ms must be non-negative.")
    missing = [col for col in group_cols if col not in data.columns]
    if missing:
        raise SchemaError(f"Temporal context requires grouping columns: {missing}")

    # Work positionally so duplicate/non-unique DataFrame indices cannot corrupt temporal windows.
    working = data.reset_index(drop=True)
    base = _build_event_features(
        working,
        sampling_rate_hz=sampling_rate_hz,
        rolling_window_ms=rolling_window_ms,
    )
    feature_names = tuple(str(col) for col in base.columns)
    radius = max(0, int(round(float(sampling_rate_hz) * context_radius_ms / 1000.0)))
    width = 2 * radius + 1
    output = np.full((len(working), width * len(feature_names)), np.nan, dtype=float)

    for positions in working.groupby(
        list(group_cols), sort=False, dropna=False
    ).indices.values():
        positions = np.asarray(positions, dtype=int)
        values = base.iloc[positions][list(feature_names)].to_numpy(dtype=float)
        if radius:
            padded = np.pad(values, ((radius, radius), (0, 0)), mode="edge")
        else:
            padded = values
        group_matrix = np.empty((len(values), width * len(feature_names)), dtype=float)
        for row in range(len(values)):
            group_matrix[row] = padded[row : row + width].reshape(-1)
        output[positions] = group_matrix

    expanded_names = tuple(
        f"lag_{offset:+d}__{feature}"
        for offset in range(-radius, radius + 1)
        for feature in feature_names
    )
    return output, expanded_names, radius


@dataclass(slots=True)
class TemporalContextModel:
    """A fitted context-window neural event classifier plus compatibility metadata."""

    estimator: Pipeline
    sampling_rate_hz: float
    context_radius_ms: float
    context_radius_samples: int
    feature_names: tuple[str, ...]
    classes: tuple[str, ...]
    model_name: str = "ContextMLPEventClassifier"
    model_version: str = "0.1"
    trained_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    metadata: dict[str, Any] = field(default_factory=dict)


def train_context_event_classifier(
    data: pd.DataFrame,
    *,
    label_col: str = "event_label",
    sampling_rate_hz: float | None = None,
    context_radius_ms: float = 50.0,
    rolling_window_ms: float = 80.0,
    hidden_layer_sizes: tuple[int, ...] = (64, 32),
    solver: str = "adam",
    max_iter: int = 200,
    random_state: int = 42,
) -> TemporalContextModel:
    """Fit an MLP to temporal windows without crossing participant/trial boundaries.

    This is the first temporal-context baseline, not a claim that an MLP is scientifically
    superior to I-VT, Random Forest, temporal CNN, or transformer alternatives. Performance must
    be established under participant- and dataset-held-out validation.
    """
    if label_col not in data.columns:
        raise SchemaError(f"Missing event label column: {label_col!r}.")
    labels = data[label_col].astype(str)
    if labels.nunique() < 2:
        raise SchemaError("At least two event classes are required for training.")

    rate = (
        float(sampling_rate_hz)
        if sampling_rate_hz is not None
        else infer_sampling_rate_hz(data)
    )
    matrix, feature_names, radius = _context_matrix(
        data,
        sampling_rate_hz=rate,
        context_radius_ms=context_radius_ms,
        rolling_window_ms=rolling_window_ms,
    )
    estimator = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scaler", StandardScaler()),
            (
                "classifier",
                MLPClassifier(
                    hidden_layer_sizes=hidden_layer_sizes,
                    solver=solver,
                    max_iter=int(max_iter),
                    random_state=int(random_state),
                    early_stopping=False,
                ),
            ),
        ]
    )
    estimator.fit(matrix, labels)
    classes = tuple(str(value) for value in estimator.named_steps["classifier"].classes_)
    return TemporalContextModel(
        estimator=estimator,
        sampling_rate_hz=rate,
        context_radius_ms=float(context_radius_ms),
        context_radius_samples=radius,
        feature_names=feature_names,
        classes=classes,
        metadata={
            "training_rows": int(len(data)),
            "rolling_window_ms": float(rolling_window_ms),
            "hidden_layer_sizes": tuple(int(v) for v in hidden_layer_sizes),
            "solver": solver,
            "max_iter": int(max_iter),
            "random_state": int(random_state),
        },
    )


def ai_classify_events_context(
    data: pd.DataFrame,
    model: TemporalContextModel,
    *,
    sampling_rate_hz: float | None = None,
    min_confidence: float = 0.60,
    sampling_rate_tolerance: float = 0.10,
) -> pd.DataFrame:
    """Classify samples using temporal context with probabilities and an abstention threshold."""
    rate = (
        float(sampling_rate_hz)
        if sampling_rate_hz is not None
        else infer_sampling_rate_hz(data)
    )
    relative_error = abs(rate - model.sampling_rate_hz) / model.sampling_rate_hz
    if relative_error > float(sampling_rate_tolerance):
        raise ModelCompatibilityError(
            "Temporal event model sampling-rate mismatch: "
            f"model={model.sampling_rate_hz:.3f} Hz, data={rate:.3f} Hz, "
            f"tolerance={sampling_rate_tolerance:.1%}."
        )

    matrix, feature_names, radius = _context_matrix(
        data,
        sampling_rate_hz=rate,
        context_radius_ms=model.context_radius_ms,
        rolling_window_ms=float(model.metadata.get("rolling_window_ms", 80.0)),
    )
    if feature_names != model.feature_names or radius != model.context_radius_samples:
        raise ModelCompatibilityError("Temporal feature layout does not match the fitted model.")

    probabilities = model.estimator.predict_proba(matrix)
    classifier = model.estimator.named_steps["classifier"]
    classes = [str(value) for value in classifier.classes_]
    max_index = np.argmax(probabilities, axis=1)
    confidence = probabilities[np.arange(len(probabilities)), max_index]
    labels = np.asarray(classes, dtype=object)[max_index]
    labels = np.where(confidence >= float(min_confidence), labels, "uncertain")

    out = data.copy()
    for i, label in enumerate(classes):
        out[f"p_event_{_safe_label(label)}"] = probabilities[:, i]
    out["event_confidence"] = confidence
    out["predicted_event"] = labels
    out["event_model"] = model.model_name
    out["event_model_version"] = model.model_version
    out["event_model_sampling_rate_hz"] = model.sampling_rate_hz
    out["event_context_radius_ms"] = model.context_radius_ms
    out["event_context_radius_samples"] = model.context_radius_samples
    return out
