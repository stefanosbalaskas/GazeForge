"""Dynamic semantic AOIs for video and moving-interface eye-tracking stimuli."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
import pandas as pd

from .exceptions import SchemaError
from .provenance import AuditTrail


@dataclass(frozen=True, slots=True)
class DynamicAOIKeyframe:
    """Timestamped rectangular geometry for one semantic AOI track."""

    aoi_id: str
    label: str
    timestamp_ms: float
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    confidence: float = 1.0
    source: str = "manual"
    model_name: str | None = None
    model_version: str | None = None

    def __post_init__(self) -> None:
        if not np.isfinite(self.timestamp_ms):
            raise ValueError("Dynamic AOI timestamp_ms must be finite.")
        if self.xmax <= self.xmin or self.ymax <= self.ymin:
            raise ValueError("Dynamic AOI bounds must satisfy xmax > xmin and ymax > ymin.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Dynamic AOI confidence must be between 0 and 1.")


class DynamicAOIProvider(Protocol):
    """Protocol implemented by detection/tracking engines for moving AOIs."""

    model_name: str
    model_version: str

    def track(self, stimulus: Any, labels: Sequence[str]) -> list[DynamicAOIKeyframe]:
        """Return timestamped AOI keyframes for tracked semantic regions."""


@dataclass
class CallableDynamicAOIProvider:
    """Adapter for custom local dynamic-AOI detectors and trackers."""

    tracker: Callable[[Any, Sequence[str]], Iterable[DynamicAOIKeyframe]]
    model_name: str = "custom-dynamic"
    model_version: str = "unspecified"

    def track(self, stimulus: Any, labels: Sequence[str]) -> list[DynamicAOIKeyframe]:
        """Run the supplied detector/tracker."""
        return list(self.tracker(stimulus, labels))


def detect_dynamic_aois(
    stimulus: Any,
    *,
    labels: Sequence[str],
    provider: DynamicAOIProvider,
    min_confidence: float = 0.10,
) -> list[DynamicAOIKeyframe]:
    """Generate dynamic semantic AOI keyframes with an explicit confidence threshold."""
    if not labels:
        raise ValueError("At least one semantic label is required.")
    if not 0.0 <= min_confidence <= 1.0:
        raise ValueError("min_confidence must be in [0, 1].")
    keyframes = provider.track(stimulus, labels)
    return [frame for frame in keyframes if frame.confidence >= min_confidence]


def dynamic_aois_to_frame(keyframes: Sequence[DynamicAOIKeyframe]) -> pd.DataFrame:
    """Convert timestamped AOI geometry to a reviewable long-format table."""
    return pd.DataFrame(
        [
            {
                "aoi_id": frame.aoi_id,
                "label": frame.label,
                "timestamp_ms": frame.timestamp_ms,
                "xmin": frame.xmin,
                "ymin": frame.ymin,
                "xmax": frame.xmax,
                "ymax": frame.ymax,
                "confidence": frame.confidence,
                "source": frame.source,
                "model_name": frame.model_name,
                "model_version": frame.model_version,
            }
            for frame in keyframes
        ]
    )


def _sorted_track(keyframes: Sequence[DynamicAOIKeyframe]) -> list[DynamicAOIKeyframe]:
    if not keyframes:
        return []
    aoi_ids = {frame.aoi_id for frame in keyframes}
    if len(aoi_ids) != 1:
        raise ValueError("Interpolation requires keyframes from exactly one AOI track.")
    ordered = sorted(keyframes, key=lambda frame: frame.timestamp_ms)
    times = [frame.timestamp_ms for frame in ordered]
    if len(set(times)) != len(times):
        raise ValueError("A dynamic AOI track cannot contain duplicate keyframe timestamps.")
    labels = {frame.label for frame in ordered}
    if len(labels) != 1:
        raise ValueError("A dynamic AOI track must retain one semantic label between keyframes.")
    return ordered


def interpolate_dynamic_aoi(
    keyframes: Sequence[DynamicAOIKeyframe],
    timestamp_ms: float,
    *,
    max_gap_ms: float = 100.0,
) -> DynamicAOIKeyframe | None:
    """Return exact/interpolated AOI geometry without temporal extrapolation.

    Interpolation is only permitted when the requested timestamp lies between two keyframes and
    the bracketing interval does not exceed ``max_gap_ms``. Requests outside the observed track
    range always return ``None``.
    """
    if max_gap_ms < 0:
        raise ValueError("max_gap_ms must be non-negative.")
    t = float(timestamp_ms)
    if not np.isfinite(t):
        return None
    ordered = _sorted_track(keyframes)
    if not ordered:
        return None

    times = np.asarray([frame.timestamp_ms for frame in ordered], dtype=float)
    exact = np.flatnonzero(np.isclose(times, t, rtol=0.0, atol=1e-9))
    if exact.size:
        return ordered[int(exact[0])]
    if t < times[0] or t > times[-1]:
        return None

    right = int(np.searchsorted(times, t, side="right"))
    left = right - 1
    before = ordered[left]
    after = ordered[right]
    gap = after.timestamp_ms - before.timestamp_ms
    if gap <= 0 or gap > float(max_gap_ms):
        return None

    weight = (t - before.timestamp_ms) / gap
    same_model = (
        before.model_name == after.model_name and before.model_version == after.model_version
    )
    return DynamicAOIKeyframe(
        aoi_id=before.aoi_id,
        label=before.label,
        timestamp_ms=t,
        xmin=before.xmin + weight * (after.xmin - before.xmin),
        ymin=before.ymin + weight * (after.ymin - before.ymin),
        xmax=before.xmax + weight * (after.xmax - before.xmax),
        ymax=before.ymax + weight * (after.ymax - before.ymax),
        confidence=before.confidence + weight * (after.confidence - before.confidence),
        source="interpolated",
        model_name=before.model_name if same_model else None,
        model_version=before.model_version if same_model else None,
    )


def map_fixations_to_dynamic_aois(
    fixations: pd.DataFrame,
    keyframes: Sequence[DynamicAOIKeyframe],
    *,
    timestamp_col: str = "timestamp_ms",
    x_col: str = "x_px",
    y_col: str = "y_px",
    max_interpolation_gap_ms: float = 100.0,
    overlap_rule: str = "highest_confidence",
    trail: AuditTrail | None = None,
) -> pd.DataFrame:
    """Map timestamped fixations to dynamic AOIs without extrapolating track geometry."""
    required = [timestamp_col, x_col, y_col]
    missing = [col for col in required if col not in fixations.columns]
    if missing:
        raise SchemaError(f"Dynamic AOI mapping requires fixation columns: {missing}")
    if overlap_rule not in {"highest_confidence", "smallest_area", "first"}:
        raise ValueError("overlap_rule must be highest_confidence, smallest_area, or first.")

    tracks: dict[str, list[DynamicAOIKeyframe]] = {}
    for frame in keyframes:
        tracks.setdefault(frame.aoi_id, []).append(frame)
    tracks = {aoi_id: _sorted_track(track) for aoi_id, track in tracks.items()}

    out = fixations.copy()
    assigned: list[DynamicAOIKeyframe | None] = []
    temporal_source: list[str | None] = []

    timestamps = pd.to_numeric(out[timestamp_col], errors="coerce")
    xs = pd.to_numeric(out[x_col], errors="coerce")
    ys = pd.to_numeric(out[y_col], errors="coerce")
    for timestamp, x, y in zip(timestamps, xs, ys, strict=True):
        candidates: list[DynamicAOIKeyframe] = []
        if np.isfinite(timestamp) and np.isfinite(x) and np.isfinite(y):
            for track in tracks.values():
                geometry = interpolate_dynamic_aoi(
                    track,
                    float(timestamp),
                    max_gap_ms=max_interpolation_gap_ms,
                )
                if geometry is None:
                    continue
                if geometry.xmin <= x <= geometry.xmax and geometry.ymin <= y <= geometry.ymax:
                    candidates.append(geometry)

        if not candidates:
            chosen = None
        elif overlap_rule == "highest_confidence":
            chosen = max(
                candidates,
                key=lambda frame: (
                    frame.confidence,
                    -(frame.xmax - frame.xmin) * (frame.ymax - frame.ymin),
                ),
            )
        elif overlap_rule == "smallest_area":
            chosen = min(
                candidates,
                key=lambda frame: (frame.xmax - frame.xmin) * (frame.ymax - frame.ymin),
            )
        else:
            chosen = candidates[0]

        assigned.append(chosen)
        temporal_source.append(None if chosen is None else chosen.source)

    out["aoi_id"] = [None if frame is None else frame.aoi_id for frame in assigned]
    out["aoi_label"] = [None if frame is None else frame.label for frame in assigned]
    out["aoi_confidence"] = [np.nan if frame is None else frame.confidence for frame in assigned]
    out["aoi_source"] = temporal_source
    out["aoi_model_name"] = [None if frame is None else frame.model_name for frame in assigned]
    out["aoi_model_version"] = [
        None if frame is None else frame.model_version for frame in assigned
    ]
    out["aoi_geometry_timestamp_ms"] = [
        np.nan if frame is None else frame.timestamp_ms for frame in assigned
    ]

    if trail is not None:
        trail.add(
            operation="map_fixations_to_dynamic_aois",
            input_data=fixations,
            output_data=out,
            parameters={
                "timestamp_col": timestamp_col,
                "x_col": x_col,
                "y_col": y_col,
                "max_interpolation_gap_ms": float(max_interpolation_gap_ms),
                "overlap_rule": overlap_rule,
                "n_keyframes": len(keyframes),
                "n_tracks": len(tracks),
            },
        )
    return out
