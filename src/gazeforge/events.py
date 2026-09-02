"""Probabilistic and classical eye-event classification."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline

from ._features import kinematic_features
from .exceptions import ModelCompatibilityError, SchemaError
from .schema import infer_sampling_rate_hz

_EVENT_FEATURES = (
    "x_px",
    "y_px",
    "pupil",
    "gaze_missing",
    "pupil_missing",
    "velocity_px_s",
    "acceleration_px_s2",
    "velocity_roll_mean",
    "velocity_roll_std",
)


def _safe_label(label: object) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(label).strip().lower()).strip("_")
    return text or "unknown"


def _build_event_features(
    data: pd.DataFrame,
    *,
    sampling_rate_hz: float,
    rolling_window_ms: float = 80.0,
) -> pd.DataFrame:
    base = kinematic_features(data, sampling_rate_hz=sampling_rate_hz)
    window = max(2, int(round(float(sampling_rate_hz) * rolling_window_ms / 1000.0)))
    velocity = base["velocity_px_s"]
    groups = [data["participant_id"], data["trial_id"]]
    base["velocity_roll_mean"] = velocity.groupby(groups, sort=False).transform(
        lambda s: s.rolling(window, min_periods=1, center=True).mean()
    )
    base["velocity_roll_std"] = velocity.groupby(groups, sort=False).transform(
        lambda s: s.rolling(window, min_periods=1, center=True).std(ddof=0)
    )
    return base[list(_EVENT_FEATURES)]


@dataclass(slots=True)
class EventModel:
    """A fitted probabilistic event classifier plus compatibility metadata."""

    estimator: Pipeline
    sampling_rate_hz: float
    feature_names: tuple[str, ...]
    classes: tuple[str, ...]
    model_name: str = "RandomForestEventClassifier"
    model_version: str = "0.1"
    trained_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    metadata: dict[str, Any] = field(default_factory=dict)


def train_event_classifier(
    data: pd.DataFrame,
    *,
    label_col: str = "event_label",
    sampling_rate_hz: float | None = None,
    random_state: int = 42,
    n_estimators: int = 300,
    rolling_window_ms: float = 80.0,
) -> EventModel:
    """Fit a probabilistic event model to labelled samples.

    This function fits a model; it deliberately does not report validation performance.
    Scientific evaluation should use participant-held-out and, where applicable,
    stimulus/dataset-held-out test data.
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
    features = _build_event_features(
        data, sampling_rate_hz=rate, rolling_window_ms=rolling_window_ms
    )

    estimator = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=int(n_estimators),
                    class_weight="balanced_subsample",
                    random_state=random_state,
                    n_jobs=-1,
                    min_samples_leaf=2,
                ),
            ),
        ]
    )
    estimator.fit(features, labels)

    classes = tuple(str(c) for c in estimator.named_steps["classifier"].classes_)
    return EventModel(
        estimator=estimator,
        sampling_rate_hz=rate,
        feature_names=tuple(features.columns),
        classes=classes,
        metadata={
            "training_rows": int(len(data)),
            "rolling_window_ms": float(rolling_window_ms),
            "random_state": int(random_state),
            "n_estimators": int(n_estimators),
        },
    )


def ai_classify_events(
    data: pd.DataFrame,
    model: EventModel,
    *,
    sampling_rate_hz: float | None = None,
    min_confidence: float = 0.60,
    sampling_rate_tolerance: float = 0.10,
) -> pd.DataFrame:
    """Classify samples with probabilities and enforce sampling-rate compatibility."""
    rate = (
        float(sampling_rate_hz)
        if sampling_rate_hz is not None
        else infer_sampling_rate_hz(data)
    )
    relative_error = abs(rate - model.sampling_rate_hz) / model.sampling_rate_hz
    if relative_error > float(sampling_rate_tolerance):
        raise ModelCompatibilityError(
            "Event model sampling-rate mismatch: "
            f"model={model.sampling_rate_hz:.3f} Hz, data={rate:.3f} Hz, "
            f"tolerance={sampling_rate_tolerance:.1%}."
        )

    rolling_window_ms = float(model.metadata.get("rolling_window_ms", 80.0))
    features = _build_event_features(
        data, sampling_rate_hz=rate, rolling_window_ms=rolling_window_ms
    )
    proba = model.estimator.predict_proba(features)
    classifier = model.estimator.named_steps["classifier"]
    classes = [str(c) for c in classifier.classes_]

    max_idx = np.argmax(proba, axis=1)
    max_prob = proba[np.arange(len(proba)), max_idx]
    labels = np.asarray(classes, dtype=object)[max_idx]
    labels = np.where(max_prob >= float(min_confidence), labels, "uncertain")

    out = data.copy()
    for i, label in enumerate(classes):
        out[f"p_event_{_safe_label(label)}"] = proba[:, i]
    out["event_confidence"] = max_prob
    out["predicted_event"] = labels
    out["event_model"] = model.model_name
    out["event_model_version"] = model.model_version
    out["event_model_sampling_rate_hz"] = model.sampling_rate_hz
    return out


def ivt_classify_events(
    data: pd.DataFrame,
    *,
    sampling_rate_hz: float | None = None,
    velocity_threshold_px_s: float = 1000.0,
) -> pd.DataFrame:
    """Transparent I-VT-style baseline in pixel coordinates."""
    rate = (
        float(sampling_rate_hz)
        if sampling_rate_hz is not None
        else infer_sampling_rate_hz(data)
    )
    features = kinematic_features(data, sampling_rate_hz=rate)
    labels = np.where(
        features["gaze_missing"].to_numpy(bool),
        "noise",
        np.where(
            features["velocity_px_s"].fillna(0).to_numpy() > velocity_threshold_px_s,
            "saccade",
            "fixation",
        ),
    )
    out = data.copy()
    out["predicted_event"] = labels
    out["event_confidence"] = 1.0
    out["event_model"] = "I-VT"
    out["event_model_version"] = "deterministic"
    return out


def evaluate_event_predictions(
    y_true: pd.Series | np.ndarray,
    y_pred: pd.Series | np.ndarray,
) -> dict[str, Any]:
    """Return classification metrics and a labelled confusion matrix."""
    true = np.asarray(y_true).astype(str)
    pred = np.asarray(y_pred).astype(str)
    labels = sorted(set(true) | set(pred))
    report = classification_report(true, pred, labels=labels, output_dict=True, zero_division=0)
    matrix = confusion_matrix(true, pred, labels=labels)
    return {
        "labels": labels,
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
    }
