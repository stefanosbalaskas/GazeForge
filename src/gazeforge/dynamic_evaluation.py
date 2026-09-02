"""Evaluation of time-varying AOI tracks against human or model references."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .aoi import AOI
from .benchmarks import BenchmarkDatasetCard, build_benchmark_report
from .dynamic_aoi import (
    DynamicAOIKeyframe,
    interpolate_dynamic_aoi,
    map_fixations_to_dynamic_aois,
)
from .evaluation import fixation_assignment_agreement, match_aois
from .exceptions import SchemaError


@dataclass(slots=True)
class DynamicAOIEvaluation:
    """Geometry/semantic metrics and timestamp-level matches for dynamic AOI tracks."""

    summary: dict[str, Any]
    per_timestamp: pd.DataFrame
    matches: pd.DataFrame


def _tracks(keyframes: Sequence[DynamicAOIKeyframe]) -> dict[str, list[DynamicAOIKeyframe]]:
    grouped: dict[str, list[DynamicAOIKeyframe]] = {}
    for frame in keyframes:
        grouped.setdefault(frame.aoi_id, []).append(frame)
    return grouped


def dynamic_aoi_snapshot(
    keyframes: Sequence[DynamicAOIKeyframe],
    timestamp_ms: float,
    *,
    max_interpolation_gap_ms: float = 100.0,
) -> list[AOI]:
    """Resolve all available dynamic AOI tracks into static AOIs at one timestamp.

    Geometry outside a track's observed range, or across a bracketing gap larger than
    ``max_interpolation_gap_ms``, is omitted rather than extrapolated.
    """
    t = float(timestamp_ms)
    if not np.isfinite(t):
        raise ValueError("timestamp_ms must be finite.")
    if max_interpolation_gap_ms < 0:
        raise ValueError("max_interpolation_gap_ms must be non-negative.")

    snapshot: list[AOI] = []
    grouped = _tracks(keyframes)
    for aoi_id in sorted(grouped):
        geometry = interpolate_dynamic_aoi(
            grouped[aoi_id],
            t,
            max_gap_ms=float(max_interpolation_gap_ms),
        )
        if geometry is None:
            continue
        snapshot.append(
            AOI(
                aoi_id=geometry.aoi_id,
                label=geometry.label,
                xmin=geometry.xmin,
                ymin=geometry.ymin,
                xmax=geometry.xmax,
                ymax=geometry.ymax,
                confidence=geometry.confidence,
                source=geometry.source,
                model_name=geometry.model_name,
                model_version=geometry.model_version,
            )
        )
    return snapshot


def evaluate_dynamic_aoi_tracks(
    predicted: Sequence[DynamicAOIKeyframe],
    reference: Sequence[DynamicAOIKeyframe],
    *,
    timestamps_ms: Sequence[float],
    max_interpolation_gap_ms: float = 100.0,
    min_iou: float = 0.50,
    require_label_match: bool = False,
) -> DynamicAOIEvaluation:
    """Evaluate dynamic AOI geometry/semantics on an explicit timestamp grid.

    The evaluation grid is supplied by the caller rather than inferred from prediction timestamps.
    This prevents a model from improving apparent coverage by choosing when it emits keyframes.
    Empty timestamps contribute no true/false detections but are counted in coverage diagnostics.
    """
    if not 0.0 <= min_iou <= 1.0:
        raise ValueError("min_iou must be in [0, 1].")

    timestamps = np.asarray(timestamps_ms, dtype=float)
    if timestamps.ndim != 1 or timestamps.size == 0:
        raise ValueError("timestamps_ms must contain a one-dimensional evaluation grid.")
    if not np.isfinite(timestamps).all():
        raise ValueError("timestamps_ms must be a finite one-dimensional sequence.")
    if len(np.unique(timestamps)) != len(timestamps):
        raise ValueError("timestamps_ms must not contain duplicates.")
    if np.any(np.diff(timestamps) <= 0):
        raise ValueError("timestamps_ms must be strictly increasing.")

    match_frames: list[pd.DataFrame] = []
    rows: list[dict[str, Any]] = []
    all_matched_ious: list[float] = []
    all_matched_semantic: list[bool] = []
    total_tp = 0
    total_fp = 0
    total_fn = 0
    predicted_timepoints = 0
    reference_timepoints = 0

    for timestamp in timestamps:
        pred = dynamic_aoi_snapshot(
            predicted,
            float(timestamp),
            max_interpolation_gap_ms=max_interpolation_gap_ms,
        )
        ref = dynamic_aoi_snapshot(
            reference,
            float(timestamp),
            max_interpolation_gap_ms=max_interpolation_gap_ms,
        )
        predicted_timepoints += len(pred)
        reference_timepoints += len(ref)
        matched = match_aois(
            pred,
            ref,
            min_iou=min_iou,
            require_label_match=require_label_match,
        )
        if not matched.empty:
            matched = matched.copy()
            matched.insert(0, "timestamp_ms", float(timestamp))
            match_frames.append(matched)
            status = matched["status"]
            tp = int((status == "matched").sum())
            fp = int((status == "false_positive").sum())
            fn = int((status == "false_negative").sum())
            accepted = matched.loc[status == "matched"]
            all_matched_ious.extend(accepted["iou"].astype(float).tolist())
            all_matched_semantic.extend(accepted["label_match"].astype(bool).tolist())
        else:
            tp = fp = fn = 0
        total_tp += tp
        total_fp += fp
        total_fn += fn
        rows.append(
            {
                "timestamp_ms": float(timestamp),
                "n_predicted": int(len(pred)),
                "n_reference": int(len(ref)),
                "true_positive": tp,
                "false_positive": fp,
                "false_negative": fn,
                "mean_matched_iou": (
                    float(np.mean(all_matched_ious[-tp:])) if tp else np.nan
                ),
            }
        )

    precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 1.0
    recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    per_timestamp = pd.DataFrame(rows)
    matches = (
        pd.concat(match_frames, ignore_index=True)
        if match_frames
        else pd.DataFrame(
            columns=[
                "timestamp_ms",
                "predicted_aoi_id",
                "reference_aoi_id",
                "predicted_label",
                "reference_label",
                "label_match",
                "iou",
                "status",
            ]
        )
    )
    summary = {
        "n_timestamps": int(len(timestamps)),
        "n_empty_timestamps": int(
            ((per_timestamp["n_predicted"] == 0) & (per_timestamp["n_reference"] == 0)).sum()
        ),
        "predicted_track_timepoints": int(predicted_timepoints),
        "reference_track_timepoints": int(reference_timepoints),
        "true_positive": int(total_tp),
        "false_positive": int(total_fp),
        "false_negative": int(total_fn),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "mean_matched_iou": float(np.mean(all_matched_ious)) if all_matched_ious else 0.0,
        "semantic_label_accuracy_matched": (
            float(np.mean(all_matched_semantic)) if all_matched_semantic else 0.0
        ),
        "min_iou": float(min_iou),
        "require_label_match": bool(require_label_match),
        "max_interpolation_gap_ms": float(max_interpolation_gap_ms),
    }
    return DynamicAOIEvaluation(
        summary=summary,
        per_timestamp=per_timestamp,
        matches=matches,
    )


def dynamic_fixation_assignment_agreement(
    fixations: pd.DataFrame,
    left: Sequence[DynamicAOIKeyframe],
    right: Sequence[DynamicAOIKeyframe],
    *,
    timestamp_col: str = "timestamp_ms",
    x_col: str = "x_px",
    y_col: str = "y_px",
    max_interpolation_gap_ms: float = 100.0,
    overlap_rule: str = "highest_confidence",
) -> dict[str, Any]:
    """Compare two dynamic-AOI references through their fixation assignments."""
    required = [timestamp_col, x_col, y_col]
    missing = [col for col in required if col not in fixations.columns]
    if missing:
        raise SchemaError(f"Dynamic fixation agreement requires fixation columns: {missing}")

    key = "__gazeforge_fixation_index"
    if key in fixations.columns:
        raise SchemaError(f"Reserved internal fixation key already exists: {key}")
    indexed = fixations.copy()
    indexed[key] = np.arange(len(indexed), dtype=int)
    left_map = map_fixations_to_dynamic_aois(
        indexed,
        left,
        timestamp_col=timestamp_col,
        x_col=x_col,
        y_col=y_col,
        max_interpolation_gap_ms=max_interpolation_gap_ms,
        overlap_rule=overlap_rule,
    )
    right_map = map_fixations_to_dynamic_aois(
        indexed,
        right,
        timestamp_col=timestamp_col,
        x_col=x_col,
        y_col=y_col,
        max_interpolation_gap_ms=max_interpolation_gap_ms,
        overlap_rule=overlap_rule,
    )
    metrics = fixation_assignment_agreement(
        left_map,
        right_map,
        key_cols=(key,),
        label_col="aoi_label",
    )
    return {
        **metrics,
        "max_interpolation_gap_ms": float(max_interpolation_gap_ms),
        "overlap_rule": overlap_rule,
    }


def build_dynamic_aoi_benchmark_report(
    evaluation: DynamicAOIEvaluation,
    *,
    benchmark: BenchmarkDatasetCard,
    model: dict[str, Any] | None = None,
    protocol: dict[str, Any] | None = None,
    fixation_agreement: dict[str, Any] | None = None,
    include_matches: bool = False,
) -> dict[str, Any]:
    """Build a deterministic benchmark report for dynamic AOI evaluation.

    Timestamp-level metrics are retained so aggregate IoU/F1 values can be audited. Full matching
    rows are optional because long video benchmarks can generate large artifacts.
    """
    metrics: dict[str, Any] = {
        "dynamic_aoi_summary": dict(evaluation.summary),
        "per_timestamp": (
            evaluation.per_timestamp.astype(object)
            .where(pd.notna(evaluation.per_timestamp), None)
            .to_dict(orient="records")
        ),
    }
    if fixation_agreement is not None:
        metrics["fixation_assignment_agreement"] = dict(fixation_agreement)
    if include_matches:
        metrics["matches"] = (
            evaluation.matches.astype(object)
            .where(pd.notna(evaluation.matches), None)
            .to_dict(orient="records")
        )
    merged_protocol = {
        "evaluation_type": "dynamic-aoi-track",
        "timestamp_grid_explicit": True,
        **dict(protocol or {}),
    }
    return build_benchmark_report(
        benchmark=benchmark,
        metrics=metrics,
        model=model,
        protocol=merged_protocol,
    )
