"""Visual-angle geometry and angular gaze kinematics."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from .exceptions import SchemaError


def pixels_to_visual_angle_deg(
    pixels: float | Sequence[float] | np.ndarray,
    *,
    physical_extent: float,
    pixel_extent: float,
    viewing_distance: float,
) -> np.ndarray:
    """Convert a pixel extent to degrees of visual angle.

    ``physical_extent`` and ``viewing_distance`` may use any shared physical length unit. The
    conversion follows the geometry used by Lund2013's ``pixels2degrees.m`` helper:
    ``2 * atan((pixels * physical_extent / pixel_extent) / (2 * viewing_distance))``.
    """
    if physical_extent <= 0 or pixel_extent <= 0 or viewing_distance <= 0:
        raise ValueError("Screen extents and viewing distance must be positive.")
    values = np.asarray(pixels, dtype=float)
    physical = values * (float(physical_extent) / float(pixel_extent))
    return np.degrees(2.0 * np.arctan(physical / (2.0 * float(viewing_distance))))


def angular_kinematic_features(
    data: pd.DataFrame,
    *,
    sampling_rate_hz: float | None = None,
    group_cols: tuple[str, ...] = ("participant_id", "trial_id"),
    timestamp_col: str = "timestamp_ms",
    x_col: str = "x_px",
    y_col: str = "y_px",
    screen_width_px_col: str = "screen_width_px",
    screen_height_px_col: str = "screen_height_px",
    screen_width_physical_col: str = "screen_width_physical",
    screen_height_physical_col: str = "screen_height_physical",
    view_distance_physical_col: str = "view_distance_physical",
) -> pd.DataFrame:
    """Compute boundary-safe sample displacement and angular velocity in degrees/second.

    Physical screen dimensions and viewing distance must use the same length unit. Geometry is
    required to be invariant within each participant/trial group; GazeForge refuses to average
    conflicting geometry metadata.
    """
    geometry_cols = (
        screen_width_px_col,
        screen_height_px_col,
        screen_width_physical_col,
        screen_height_physical_col,
        view_distance_physical_col,
    )
    required = [*group_cols, timestamp_col, x_col, y_col, *geometry_cols]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise SchemaError(f"Angular kinematics are missing columns: {missing}")

    out = pd.DataFrame(index=data.index)
    out["dx_px"] = np.nan
    out["dy_px"] = np.nan
    out["dx_deg"] = np.nan
    out["dy_deg"] = np.nan
    out["angular_displacement_deg"] = np.nan
    out["angular_velocity_deg_s"] = np.nan
    out["dt_ms"] = np.nan
    out["gaze_missing"] = (
        pd.to_numeric(data[x_col], errors="coerce").isna()
        | pd.to_numeric(data[y_col], errors="coerce").isna()
    ).astype(float)

    grouping = group_cols[0] if len(group_cols) == 1 else list(group_cols)
    for _, positions in data.groupby(grouping, sort=False, dropna=False).indices.items():
        positions = np.asarray(positions, dtype=int)
        group = data.iloc[positions]
        geometry: dict[str, float] = {}
        for col in geometry_cols:
            values = pd.to_numeric(group[col], errors="coerce").dropna().unique()
            if len(values) != 1 or not np.isfinite(values[0]) or float(values[0]) <= 0:
                raise SchemaError(
                    f"Angular kinematics require one positive invariant {col!r} per group."
                )
            geometry[col] = float(values[0])

        timestamps = pd.to_numeric(group[timestamp_col], errors="coerce").to_numpy(dtype=float)
        x = pd.to_numeric(group[x_col], errors="coerce").to_numpy(dtype=float)
        y = pd.to_numeric(group[y_col], errors="coerce").to_numpy(dtype=float)
        dt_ms = np.diff(timestamps, prepend=np.nan)
        if sampling_rate_hz is not None:
            fallback = 1000.0 / float(sampling_rate_hz)
            dt_ms = np.where((dt_ms <= 0) | ~np.isfinite(dt_ms), fallback, dt_ms)

        dx_px = np.diff(x, prepend=np.nan)
        dy_px = np.diff(y, prepend=np.nan)
        dx_deg = pixels_to_visual_angle_deg(
            dx_px,
            physical_extent=geometry[screen_width_physical_col],
            pixel_extent=geometry[screen_width_px_col],
            viewing_distance=geometry[view_distance_physical_col],
        )
        dy_deg = pixels_to_visual_angle_deg(
            dy_px,
            physical_extent=geometry[screen_height_physical_col],
            pixel_extent=geometry[screen_height_px_col],
            viewing_distance=geometry[view_distance_physical_col],
        )
        displacement = np.hypot(dx_deg, dy_deg)
        with np.errstate(divide="ignore", invalid="ignore"):
            velocity = displacement / (dt_ms / 1000.0)

        out.iloc[positions, out.columns.get_loc("dx_px")] = dx_px
        out.iloc[positions, out.columns.get_loc("dy_px")] = dy_px
        out.iloc[positions, out.columns.get_loc("dx_deg")] = dx_deg
        out.iloc[positions, out.columns.get_loc("dy_deg")] = dy_deg
        out.iloc[positions, out.columns.get_loc("angular_displacement_deg")] = displacement
        out.iloc[positions, out.columns.get_loc("angular_velocity_deg_s")] = velocity
        out.iloc[positions, out.columns.get_loc("dt_ms")] = dt_ms

    out.replace([np.inf, -np.inf], np.nan, inplace=True)
    return out
