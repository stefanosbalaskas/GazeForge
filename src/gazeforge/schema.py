"""Canonical, vendor-neutral gaze schema."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .exceptions import SchemaError

REQUIRED_COLUMNS = ("participant_id", "trial_id", "timestamp_ms", "x_px", "y_px")
OPTIONAL_COLUMNS = ("pupil", "validity")


@dataclass(slots=True)
class GazeFrame:
    """Validated canonical gaze samples plus recording metadata."""

    data: pd.DataFrame
    sampling_rate_hz: float
    screen_size_px: tuple[int, int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def copy(self) -> "GazeFrame":
        """Return an independent copy."""
        return GazeFrame(
            data=self.data.copy(),
            sampling_rate_hz=float(self.sampling_rate_hz),
            screen_size_px=self.screen_size_px,
            metadata=dict(self.metadata),
        )


def infer_sampling_rate_hz(
    data: pd.DataFrame,
    *,
    timestamp_col: str = "timestamp_ms",
    group_cols: tuple[str, ...] = ("participant_id", "trial_id"),
) -> float:
    """Infer sampling rate from the median positive within-trial timestamp interval."""
    missing = [c for c in (timestamp_col, *group_cols) if c not in data.columns]
    if missing:
        raise SchemaError(f"Cannot infer sampling rate; missing columns: {missing}")

    deltas: list[np.ndarray] = []
    for _, part in data.groupby(list(group_cols), sort=False, dropna=False):
        ts = pd.to_numeric(part[timestamp_col], errors="coerce").to_numpy(dtype=float)
        ts = np.sort(ts[np.isfinite(ts)])
        if ts.size > 1:
            dt = np.diff(ts)
            dt = dt[dt > 0]
            if dt.size:
                deltas.append(dt)

    if not deltas:
        raise SchemaError(
            "Cannot infer sampling rate from non-increasing or insufficient timestamps."
        )

    median_dt_ms = float(np.median(np.concatenate(deltas)))
    if not np.isfinite(median_dt_ms) or median_dt_ms <= 0:
        raise SchemaError("Inferred timestamp interval is invalid.")
    return 1000.0 / median_dt_ms


def canonicalize_gaze(
    data: pd.DataFrame,
    *,
    column_map: Mapping[str, str] | None = None,
    sampling_rate_hz: float | None = None,
    screen_size_px: tuple[int, int] | None = None,
    metadata: Mapping[str, Any] | None = None,
    sort: bool = True,
) -> GazeFrame:
    """Convert a table to GazeForge's canonical sample schema.

    ``column_map`` maps canonical names to source-column names, for example
    ``{"timestamp_ms": "TIME", "x_px": "BPOGX", "y_px": "BPOGY"}``.
    """
    if not isinstance(data, pd.DataFrame):
        raise SchemaError("data must be a pandas DataFrame.")

    frame = data.copy()
    if column_map:
        reverse = {source: canonical for canonical, source in column_map.items()}
        frame = frame.rename(columns=reverse)

    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise SchemaError(
            "Missing canonical gaze columns: "
            f"{missing}. Required columns are {list(REQUIRED_COLUMNS)}."
        )

    for col in ("timestamp_ms", "x_px", "y_px", "pupil"):
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")

    if frame["timestamp_ms"].isna().any():
        raise SchemaError("timestamp_ms contains missing or non-numeric values.")

    if sort:
        frame = frame.sort_values(
            ["participant_id", "trial_id", "timestamp_ms"], kind="stable"
        ).reset_index(drop=True)

    rate = (
        float(sampling_rate_hz)
        if sampling_rate_hz is not None
        else infer_sampling_rate_hz(frame)
    )
    if not np.isfinite(rate) or rate <= 0:
        raise SchemaError("sampling_rate_hz must be finite and positive.")

    if screen_size_px is not None:
        width, height = screen_size_px
        if width <= 0 or height <= 0:
            raise SchemaError("screen_size_px must contain positive width and height.")

    return GazeFrame(
        data=frame,
        sampling_rate_hz=rate,
        screen_size_px=screen_size_px,
        metadata=dict(metadata or {}),
    )
