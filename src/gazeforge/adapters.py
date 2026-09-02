"""Adapters from common eye-tracking tables into the GazeForge canonical schema."""

from __future__ import annotations

from typing import Literal

import pandas as pd

from .exceptions import SchemaError
from .schema import GazeFrame, canonicalize_gaze


def adapt_gazepoint_samples(
    data: pd.DataFrame,
    *,
    screen_size_px: tuple[int, int],
    participant_col: str = "USER_FILE",
    trial_col: str = "MEDIA_ID",
    timestamp_col: str = "TIME",
    x_col: str = "BPOGX",
    y_col: str = "BPOGY",
    pupil_col: str | None = None,
    validity_col: str | None = None,
    time_unit: Literal["seconds", "milliseconds"] = "seconds",
    coordinates: Literal["normalized", "pixels"] = "normalized",
    sampling_rate_hz: float | None = None,
) -> GazeFrame:
    """Adapt Gazepoint-style sample exports using explicitly declared column semantics.

    Gazepoint point-of-gaze coordinates are commonly exported as fractions of screen size.
    This adapter therefore defaults to ``coordinates="normalized"`` and requires the screen
    dimensions so the canonical representation is in pixels.

    Column names remain configurable because Gazepoint export variants and upstream packages
    may expose different gaze/fixation fields.
    """
    required = [participant_col, trial_col, timestamp_col, x_col, y_col]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise SchemaError(f"Gazepoint adapter is missing source columns: {missing}")

    frame = pd.DataFrame(
        {
            "participant_id": data[participant_col],
            "trial_id": data[trial_col],
            "timestamp_ms": pd.to_numeric(data[timestamp_col], errors="coerce"),
            "x_px": pd.to_numeric(data[x_col], errors="coerce"),
            "y_px": pd.to_numeric(data[y_col], errors="coerce"),
        },
        index=data.index,
    )

    if time_unit == "seconds":
        frame["timestamp_ms"] = frame["timestamp_ms"] * 1000.0
    elif time_unit != "milliseconds":
        raise ValueError("time_unit must be 'seconds' or 'milliseconds'.")

    if coordinates == "normalized":
        width, height = screen_size_px
        frame["x_px"] = frame["x_px"] * float(width)
        frame["y_px"] = frame["y_px"] * float(height)
    elif coordinates != "pixels":
        raise ValueError("coordinates must be 'normalized' or 'pixels'.")

    if pupil_col is not None:
        if pupil_col not in data.columns:
            raise SchemaError(f"Requested pupil column is missing: {pupil_col!r}")
        frame["pupil"] = pd.to_numeric(data[pupil_col], errors="coerce")

    if validity_col is not None:
        if validity_col not in data.columns:
            raise SchemaError(f"Requested validity column is missing: {validity_col!r}")
        frame["validity"] = data[validity_col]

    return canonicalize_gaze(
        frame,
        sampling_rate_hz=sampling_rate_hz,
        screen_size_px=screen_size_px,
        metadata={
            "adapter": "gazepoint",
            "source_columns": {
                "participant_id": participant_col,
                "trial_id": trial_col,
                "timestamp_ms": timestamp_col,
                "x_px": x_col,
                "y_px": y_col,
                "pupil": pupil_col,
                "validity": validity_col,
            },
            "source_time_unit": time_unit,
            "source_coordinates": coordinates,
        },
    )


def adapt_processed_table(
    data: pd.DataFrame,
    *,
    participant_col: str,
    trial_col: str,
    timestamp_col: str,
    x_col: str,
    y_col: str,
    pupil_col: str | None = None,
    validity_col: str | None = None,
    timestamp_scale_to_ms: float = 1.0,
    coordinate_scale: tuple[float, float] = (1.0, 1.0),
    sampling_rate_hz: float | None = None,
    screen_size_px: tuple[int, int] | None = None,
    source_name: str = "processed_table",
) -> GazeFrame:
    """Adapt an eyeprocesspy/gpbiometricspy/custom processed table without guessing columns."""
    required = [participant_col, trial_col, timestamp_col, x_col, y_col]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise SchemaError(f"{source_name} adapter is missing source columns: {missing}")

    frame = pd.DataFrame(
        {
            "participant_id": data[participant_col],
            "trial_id": data[trial_col],
            "timestamp_ms": pd.to_numeric(data[timestamp_col], errors="coerce")
            * float(timestamp_scale_to_ms),
            "x_px": pd.to_numeric(data[x_col], errors="coerce") * float(coordinate_scale[0]),
            "y_px": pd.to_numeric(data[y_col], errors="coerce") * float(coordinate_scale[1]),
        },
        index=data.index,
    )
    if pupil_col is not None:
        if pupil_col not in data.columns:
            raise SchemaError(f"Requested pupil column is missing: {pupil_col!r}")
        frame["pupil"] = pd.to_numeric(data[pupil_col], errors="coerce")
    if validity_col is not None:
        if validity_col not in data.columns:
            raise SchemaError(f"Requested validity column is missing: {validity_col!r}")
        frame["validity"] = data[validity_col]

    return canonicalize_gaze(
        frame,
        sampling_rate_hz=sampling_rate_hz,
        screen_size_px=screen_size_px,
        metadata={
            "adapter": source_name,
            "timestamp_scale_to_ms": float(timestamp_scale_to_ms),
            "coordinate_scale": tuple(float(v) for v in coordinate_scale),
        },
    )
