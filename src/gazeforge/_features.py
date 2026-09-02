"""Internal sample-level feature engineering."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .exceptions import SchemaError


def kinematic_features(
    data: pd.DataFrame,
    *,
    sampling_rate_hz: float | None = None,
    group_cols: tuple[str, ...] = ("participant_id", "trial_id"),
) -> pd.DataFrame:
    """Return deterministic kinematic features without modifying the input."""
    required = [*group_cols, "timestamp_ms", "x_px", "y_px"]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise SchemaError(f"Missing columns for kinematic features: {missing}")

    out = pd.DataFrame(index=data.index)
    out["x_px"] = pd.to_numeric(data["x_px"], errors="coerce")
    out["y_px"] = pd.to_numeric(data["y_px"], errors="coerce")
    if "pupil" in data:
        out["pupil"] = pd.to_numeric(data["pupil"], errors="coerce")
    else:
        out["pupil"] = np.nan

    out["gaze_missing"] = (out["x_px"].isna() | out["y_px"].isna()).astype(float)
    out["pupil_missing"] = out["pupil"].isna().astype(float)
    out["dt_ms"] = np.nan
    out["velocity_px_s"] = np.nan
    out["acceleration_px_s2"] = np.nan

    for _, idx in data.groupby(list(group_cols), sort=False, dropna=False).groups.items():
        idx = pd.Index(idx)
        ts = pd.to_numeric(data.loc[idx, "timestamp_ms"], errors="coerce").to_numpy(float)
        x = out.loc[idx, "x_px"].to_numpy(float)
        y = out.loc[idx, "y_px"].to_numpy(float)

        dt_ms = np.diff(ts, prepend=np.nan)
        if sampling_rate_hz is not None:
            fallback = 1000.0 / float(sampling_rate_hz)
            dt_ms = np.where((dt_ms <= 0) | ~np.isfinite(dt_ms), fallback, dt_ms)

        dist = np.hypot(np.diff(x, prepend=np.nan), np.diff(y, prepend=np.nan))
        with np.errstate(divide="ignore", invalid="ignore"):
            velocity = dist / (dt_ms / 1000.0)
            acceleration = np.diff(velocity, prepend=np.nan) / (dt_ms / 1000.0)

        out.loc[idx, "dt_ms"] = dt_ms
        out.loc[idx, "velocity_px_s"] = velocity
        out.loc[idx, "acceleration_px_s2"] = acceleration

    out.replace([np.inf, -np.inf], np.nan, inplace=True)
    return out
