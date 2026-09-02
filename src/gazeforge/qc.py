"""Auditable quality control and anomaly scoring."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

from ._features import kinematic_features
from .exceptions import SchemaError
from .provenance import AuditTrail


def ai_flag_anomalies(
    data: pd.DataFrame,
    *,
    sampling_rate_hz: float | None = None,
    contamination: float | str = "auto",
    random_state: int = 42,
    trail: AuditTrail | None = None,
) -> pd.DataFrame:
    """Flag unusual samples with Isolation Forest without deleting or rewriting samples."""
    features = kinematic_features(data, sampling_rate_hz=sampling_rate_hz)
    model_features = features[
        [
            "x_px",
            "y_px",
            "pupil",
            "gaze_missing",
            "pupil_missing",
            "velocity_px_s",
            "acceleration_px_s2",
        ]
    ].copy()

    usable = [c for c in model_features.columns if not model_features[c].isna().all()]
    if not usable:
        raise SchemaError("No usable numeric gaze features were available for anomaly detection.")

    estimator = make_pipeline(
        SimpleImputer(strategy="median"),
        IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=200,
            n_jobs=-1,
        ),
    )
    estimator.fit(model_features[usable])
    forest = estimator.named_steps["isolationforest"]
    transformed = estimator.named_steps["simpleimputer"].transform(model_features[usable])

    decision = forest.decision_function(transformed)
    prediction = forest.predict(transformed)

    out = data.copy()
    out["qc_anomaly_score"] = -decision
    out["qc_flag"] = prediction == -1
    out["qc_model"] = "IsolationForest"
    out["qc_model_version"] = "sklearn"

    if trail is not None:
        trail.add(
            operation="ai_flag_anomalies",
            input_data=data,
            output_data=out,
            parameters={
                "sampling_rate_hz": sampling_rate_hz,
                "contamination": contamination,
                "random_state": random_state,
                "features": usable,
            },
            model_name="IsolationForest",
            model_version="sklearn",
        )
    return out


def score_trial_quality(
    data: pd.DataFrame,
    *,
    screen_size_px: tuple[int, int] | None = None,
    group_cols: tuple[str, ...] = ("participant_id", "trial_id"),
) -> pd.DataFrame:
    """Summarise missingness, bounds, anomaly rate, and temporal gaps per trial."""
    required = [*group_cols, "timestamp_ms", "x_px", "y_px"]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise SchemaError(f"Missing columns for trial quality scoring: {missing}")

    rows: list[dict[str, object]] = []
    for keys, part in data.groupby(list(group_cols), sort=False, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        x = pd.to_numeric(part["x_px"], errors="coerce")
        y = pd.to_numeric(part["y_px"], errors="coerce")
        missing_rate = float((x.isna() | y.isna()).mean())

        offscreen_rate = 0.0
        if screen_size_px is not None:
            width, height = screen_size_px
            valid = x.notna() & y.notna()
            if valid.any():
                offscreen_rate = float(
                    ((x[valid] < 0) | (x[valid] > width) | (y[valid] < 0) | (y[valid] > height)).mean()
                )

        anomaly_rate = float(part["qc_flag"].mean()) if "qc_flag" in part else 0.0
        ts = pd.to_numeric(part["timestamp_ms"], errors="coerce").sort_values()
        dt = ts.diff()
        positive_dt = dt[dt > 0]
        median_dt = float(positive_dt.median()) if not positive_dt.empty else np.nan
        if positive_dt.empty or not np.isfinite(median_dt) or median_dt <= 0:
            gap_rate = 0.0
        else:
            gap_rate = float((positive_dt > 2.5 * median_dt).mean())

        penalty = 0.50 * missing_rate + 0.20 * offscreen_rate + 0.20 * anomaly_rate + 0.10 * gap_rate
        quality = float(np.clip(1.0 - penalty, 0.0, 1.0))

        row = {col: value for col, value in zip(group_cols, keys, strict=True)}
        row.update(
            n_samples=int(len(part)),
            missing_rate=missing_rate,
            offscreen_rate=offscreen_rate,
            anomaly_rate=anomaly_rate,
            large_gap_rate=gap_rate,
            quality_score=quality,
        )
        rows.append(row)

    return pd.DataFrame(rows)


def detect_calibration_drift(
    data: pd.DataFrame,
    *,
    expected_x_col: str,
    expected_y_col: str,
    threshold_px: float = 100.0,
    group_cols: tuple[str, ...] = ("participant_id", "trial_id"),
) -> pd.DataFrame:
    """Score drift only when known calibration/reference target coordinates are supplied."""
    required = [*group_cols, "x_px", "y_px", expected_x_col, expected_y_col]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise SchemaError(f"Calibration drift requires reference-target columns; missing: {missing}")

    out = data.copy()
    dx = pd.to_numeric(out["x_px"], errors="coerce") - pd.to_numeric(
        out[expected_x_col], errors="coerce"
    )
    dy = pd.to_numeric(out["y_px"], errors="coerce") - pd.to_numeric(
        out[expected_y_col], errors="coerce"
    )
    out["calibration_error_px"] = np.hypot(dx, dy)
    out["calibration_drift_flag"] = out["calibration_error_px"] > float(threshold_px)
    return out
