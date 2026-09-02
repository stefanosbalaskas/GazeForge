"""Transparent resampling utilities for lower-rate eye-movement benchmarks."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .exceptions import SchemaError
from .schema import infer_sampling_rate_hz


@dataclass(slots=True)
class BenchmarkResamplingResult:
    """Resampled labelled gaze data plus a machine-readable resampling report."""

    data: pd.DataFrame
    report: dict[str, Any]


def _interpolate_with_gap_limit(
    timestamps: np.ndarray,
    values: np.ndarray,
    target_times: np.ndarray,
    *,
    max_gap_ms: float,
) -> np.ndarray:
    output = np.full(len(target_times), np.nan, dtype=float)
    finite = np.isfinite(timestamps) & np.isfinite(values)
    source_t = timestamps[finite]
    source_v = values[finite]
    if not len(source_t):
        return output

    order = np.argsort(source_t, kind="stable")
    source_t = source_t[order]
    source_v = source_v[order]
    unique_t, unique_index = np.unique(source_t, return_index=True)
    source_t = unique_t
    source_v = source_v[unique_index]

    for i, target in enumerate(target_times):
        exact = np.flatnonzero(np.isclose(source_t, target, rtol=0.0, atol=1e-9))
        if exact.size:
            output[i] = source_v[int(exact[0])]
            continue
        right = int(np.searchsorted(source_t, target, side="right"))
        left = right - 1
        if left < 0 or right >= len(source_t):
            continue
        gap = source_t[right] - source_t[left]
        if gap <= 0 or gap > max_gap_ms:
            continue
        weight = (target - source_t[left]) / gap
        output[i] = source_v[left] + weight * (source_v[right] - source_v[left])
    return output


def _majority_label_window(
    timestamps: np.ndarray,
    labels: np.ndarray,
    target_times: np.ndarray,
    *,
    target_period_ms: float,
    min_label_purity: float,
    ambiguous_label: str,
) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    output_labels: list[str] = []
    purity = np.full(len(target_times), np.nan, dtype=float)
    source_counts = np.zeros(len(target_times), dtype=int)
    ambiguous = np.ones(len(target_times), dtype=bool)
    half_window = target_period_ms / 2.0

    for i, target in enumerate(target_times):
        if i == len(target_times) - 1:
            mask = (timestamps >= target - half_window) & (timestamps <= target + half_window)
        else:
            mask = (timestamps >= target - half_window) & (timestamps < target + half_window)
        selected = labels[mask]
        selected = selected[pd.notna(selected)]
        source_counts[i] = int(len(selected))
        if not len(selected):
            output_labels.append(ambiguous_label)
            continue

        values, counts = np.unique(selected.astype(str), return_counts=True)
        order = np.argsort(counts)[::-1]
        top_count = int(counts[order[0]])
        tied = int((counts == top_count).sum()) > 1
        top_purity = top_count / len(selected)
        purity[i] = float(top_purity)
        if tied or top_purity < min_label_purity:
            output_labels.append(ambiguous_label)
            continue
        output_labels.append(str(values[order[0]]))
        ambiguous[i] = False

    return output_labels, purity, source_counts, ambiguous


def resample_labeled_gaze(
    data: pd.DataFrame,
    *,
    target_sampling_rate_hz: float = 60.0,
    label_col: str = "event_label",
    timestamp_col: str = "timestamp_ms",
    group_cols: tuple[str, ...] = ("participant_id", "trial_id"),
    continuous_cols: Sequence[str] = ("x_px", "y_px", "pupil"),
    carry_cols: Sequence[str] = (
        "annotator",
        "stimulus_type",
        "dataset_id",
        "source_file",
        "screen_width_px",
        "screen_height_px",
        "screen_width_physical",
        "screen_height_physical",
        "view_distance_physical",
    ),
    min_label_purity: float = 0.75,
    ambiguous_label: str = "ambiguous",
    max_interpolation_gap_ms: float | None = None,
    source_sampling_rate_hz: float | None = None,
) -> BenchmarkResamplingResult:
    """Resample expert-labelled gaze to a lower rate with explicit boundary uncertainty.

    Continuous signals are linearly interpolated only across short valid gaps. Event labels are
    assigned by majority vote within one target-sample window. Windows with tied labels or purity
    below ``min_label_purity`` are marked as ``ambiguous_label`` instead of silently forcing an
    event identity near a source annotation boundary.
    """
    required = [timestamp_col, label_col, *group_cols]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise SchemaError(f"Benchmark resampling is missing columns: {missing}")
    if not 0.0 < float(target_sampling_rate_hz):
        raise ValueError("target_sampling_rate_hz must be positive.")
    if not 0.0 < float(min_label_purity) <= 1.0:
        raise ValueError("min_label_purity must be in (0, 1].")

    source_rate = (
        float(source_sampling_rate_hz)
        if source_sampling_rate_hz is not None
        else infer_sampling_rate_hz(
            data,
            timestamp_col=timestamp_col,
            group_cols=group_cols,
        )
    )
    target_rate = float(target_sampling_rate_hz)
    if target_rate >= source_rate:
        raise ValueError(
            "Benchmark resampling requires target_sampling_rate_hz to be lower than the source "
            "sampling rate."
        )

    target_period_ms = 1000.0 / target_rate
    gap_limit = (
        float(max_interpolation_gap_ms)
        if max_interpolation_gap_ms is not None
        else 2.0 * target_period_ms
    )
    if gap_limit <= 0:
        raise ValueError("max_interpolation_gap_ms must be positive.")

    available_continuous = [col for col in continuous_cols if col in data.columns]
    available_carry = [col for col in carry_cols if col in data.columns and col not in group_cols]
    output_parts: list[pd.DataFrame] = []
    group_reports: list[dict[str, Any]] = []

    grouping = group_cols[0] if len(group_cols) == 1 else list(group_cols)
    for group_key, group in data.groupby(grouping, sort=False, dropna=False):
        group = group.sort_values(timestamp_col, kind="stable").reset_index(drop=True)
        timestamps = pd.to_numeric(group[timestamp_col], errors="coerce").to_numpy(dtype=float)
        finite_timestamps = timestamps[np.isfinite(timestamps)]
        if len(finite_timestamps) < 2:
            continue
        start = float(finite_timestamps.min())
        stop = float(finite_timestamps.max())
        target_times = np.arange(start, stop + 0.5 * target_period_ms, target_period_ms)
        target_times = target_times[target_times <= stop + 1e-9]

        labels = group[label_col].to_numpy(dtype=object)
        assigned, purity, source_counts, ambiguous = _majority_label_window(
            timestamps,
            labels,
            target_times,
            target_period_ms=target_period_ms,
            min_label_purity=float(min_label_purity),
            ambiguous_label=ambiguous_label,
        )
        out = pd.DataFrame({timestamp_col: target_times, label_col: assigned})

        key_tuple = group_key if isinstance(group_key, tuple) else (group_key,)
        for col, value in zip(group_cols, key_tuple, strict=True):
            out[col] = value
        for col in available_carry:
            values = group[col].dropna().unique()
            if len(values) > 1:
                raise SchemaError(
                    f"Cannot carry non-invariant metadata column {col!r} within group {key_tuple}."
                )
            out[col] = values[0] if len(values) else np.nan
        for col in available_continuous:
            values = pd.to_numeric(group[col], errors="coerce").to_numpy(dtype=float)
            out[col] = _interpolate_with_gap_limit(
                timestamps,
                values,
                target_times,
                max_gap_ms=gap_limit,
            )

        out["benchmark_label_purity"] = purity
        out["benchmark_label_source_samples"] = source_counts
        out["benchmark_label_ambiguous"] = ambiguous
        out["source_sampling_rate_hz"] = source_rate
        out["target_sampling_rate_hz"] = target_rate
        output_parts.append(out)
        group_reports.append(
            {
                "group": tuple(str(value) for value in key_tuple),
                "source_rows": int(len(group)),
                "target_rows": int(len(out)),
                "ambiguous_rows": int(ambiguous.sum()),
                "ambiguous_fraction": float(ambiguous.mean()) if len(out) else np.nan,
            }
        )

    if not output_parts:
        raise SchemaError("No groups contained enough timestamped samples to resample.")
    output = pd.concat(output_parts, ignore_index=True)
    report = {
        "method": "linear_coordinates_majority_window_labels",
        "source_sampling_rate_hz": source_rate,
        "target_sampling_rate_hz": target_rate,
        "target_period_ms": target_period_ms,
        "min_label_purity": float(min_label_purity),
        "ambiguous_label": ambiguous_label,
        "max_interpolation_gap_ms": gap_limit,
        "source_rows": int(len(data)),
        "target_rows": int(len(output)),
        "n_groups": int(len(group_reports)),
        "ambiguous_rows": int(output["benchmark_label_ambiguous"].sum()),
        "ambiguous_fraction": float(output["benchmark_label_ambiguous"].mean()),
        "mean_label_purity": float(output["benchmark_label_purity"].mean(skipna=True)),
        "group_reports": group_reports,
    }
    return BenchmarkResamplingResult(data=output, report=report)
