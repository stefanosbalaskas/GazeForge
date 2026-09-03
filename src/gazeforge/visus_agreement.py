"""Conditional human-human dynamic-AOI agreement for audited VISUS sources."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from .benchmarks import BenchmarkDatasetCard, benchmark_fingerprint, build_benchmark_report
from .dynamic_aoi import DynamicAOIKeyframe, map_fixations_to_dynamic_aois
from .dynamic_evaluation import DynamicAOIEvaluation, evaluate_dynamic_aoi_tracks
from .evaluation import fixation_assignment_agreement
from .exceptions import BenchmarkIntegrityError, SchemaError
from .provenance import fingerprint_frame
from .visus_audit import VisusSourceAuditRun


@dataclass(slots=True)
class VisusDynamicAOIHumanAgreementRun:
    """Bidirectional dynamic-AOI agreement between two verified independent streams."""

    directional_summary: pd.DataFrame
    per_stimulus: pd.DataFrame
    per_timestamp: pd.DataFrame
    matches: pd.DataFrame
    fixation_assignment: dict[str, Any] | None
    report: dict[str, Any]


def _verify_audit(audit: VisusSourceAuditRun) -> None:
    if not isinstance(audit, VisusSourceAuditRun):
        raise TypeError("audit must be a VisusSourceAuditRun instance.")
    if audit.report.get("status") != "verified":
        raise BenchmarkIntegrityError("VISUS source audit is not verified.")

    report_fingerprint = str(audit.report.get("report_fingerprint_sha256", ""))
    body = {
        key: value
        for key, value in audit.report.items()
        if key != "report_fingerprint_sha256"
    }
    if len(report_fingerprint) != 64 or benchmark_fingerprint(body) != report_fingerprint:
        raise BenchmarkIntegrityError("VISUS source-audit report fingerprint does not revalidate.")

    spec_fingerprint = str(audit.report.get("spec_fingerprint_sha256", ""))
    if benchmark_fingerprint(audit.spec.to_dict()) != spec_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS source-audit specification fingerprint does not revalidate."
        )

    manifest = [asdict(item.record) for item in audit.files]
    expected = str(audit.report.get("inventory", {}).get("manifest_fingerprint_sha256", ""))
    if benchmark_fingerprint(manifest) != expected:
        raise BenchmarkIntegrityError("VISUS source manifest fingerprint does not revalidate.")


def _require_independence(audit: VisusSourceAuditRun) -> None:
    provenance = audit.report.get("annotation_provenance", {})
    if provenance.get("human_human_agreement_ready") is not True:
        raise BenchmarkIntegrityError(
            "VISUS human-human agreement is blocked until the source audit explicitly verifies "
            "separately recoverable independent annotation streams."
        )
    if audit.spec.independent_annotation_streams_verified is not True:
        raise BenchmarkIntegrityError(
            "VISUS specification does not verify independent annotation streams."
        )


def _audited_stimuli(audit: VisusSourceAuditRun) -> list[str]:
    values = audit.report.get("identity", {}).get("stimulus_ids", [])
    stimuli = sorted(str(value) for value in values)
    if not stimuli:
        raise BenchmarkIntegrityError(
            "VISUS source audit contains no verified stimulus identities."
        )
    return stimuli


def _require_exact_keys(
    mapping: Mapping[str, Any],
    stimuli: Sequence[str],
    *,
    name: str,
) -> None:
    observed = {str(key) for key in mapping}
    expected = set(stimuli)
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    if missing or extra:
        raise SchemaError(
            f"VISUS {name} must exactly cover the audited stimuli: "
            f"missing={missing}, extra={extra}."
        )


def _require_streams(
    audit: VisusSourceAuditRun,
    stimuli: Sequence[str],
    *,
    left_stream_id: str,
    right_stream_id: str,
) -> tuple[str, str]:
    left = str(left_stream_id).strip()
    right = str(right_stream_id).strip()
    if not left or not right:
        raise ValueError("VISUS human-human stream identifiers cannot be empty.")
    if left == right:
        raise ValueError("VISUS human-human agreement requires two distinct annotation streams.")

    streams = audit.report.get("annotation_provenance", {}).get("streams_by_stimulus", {})
    missing_left = [stimulus for stimulus in stimuli if left not in streams.get(stimulus, [])]
    missing_right = [stimulus for stimulus in stimuli if right not in streams.get(stimulus, [])]
    if missing_left or missing_right:
        raise SchemaError(
            "Selected VISUS independent streams must both be manifested for every audited "
            f"stimulus: missing_left={missing_left}, missing_right={missing_right}."
        )
    return left, right


def _keyframes(
    frames: Sequence[DynamicAOIKeyframe],
    *,
    stream_id: str,
    stimulus_id: str,
) -> list[DynamicAOIKeyframe]:
    values = list(frames)
    if not values:
        raise SchemaError(
            f"VISUS stream {stream_id!r} has no keyframes for stimulus {stimulus_id!r}."
        )
    if not all(isinstance(frame, DynamicAOIKeyframe) for frame in values):
        raise TypeError("VISUS human-reference mappings require DynamicAOIKeyframe objects.")
    return values


def _grid(values: Sequence[float], *, stimulus_id: str) -> np.ndarray:
    grid = np.asarray(values, dtype=float)
    if grid.ndim != 1 or grid.size == 0 or not np.isfinite(grid).all():
        raise ValueError(
            f"VISUS timestamp grid for {stimulus_id!r} must be finite and one-dimensional."
        )
    if len(np.unique(grid)) != len(grid) or np.any(np.diff(grid) <= 0):
        raise ValueError(
            f"VISUS timestamp grid for {stimulus_id!r} must be unique and increasing."
        )
    return grid


def _aggregate(evaluations: Mapping[str, DynamicAOIEvaluation]) -> dict[str, Any]:
    summaries = [evaluation.summary for evaluation in evaluations.values()]
    tp = sum(int(summary["true_positive"]) for summary in summaries)
    fp = sum(int(summary["false_positive"]) for summary in summaries)
    fn = sum(int(summary["false_negative"]) for summary in summaries)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0

    ious: list[float] = []
    semantic: list[bool] = []
    for evaluation in evaluations.values():
        matched = evaluation.matches.loc[evaluation.matches["status"] == "matched"]
        ious.extend(matched["iou"].astype(float).tolist())
        semantic.extend(matched["label_match"].astype(bool).tolist())

    return {
        "stimulus_count": len(evaluations),
        "n_timestamps": sum(int(summary["n_timestamps"]) for summary in summaries),
        "n_empty_timestamps": sum(
            int(summary["n_empty_timestamps"]) for summary in summaries
        ),
        "predicted_track_timepoints": sum(
            int(summary["predicted_track_timepoints"]) for summary in summaries
        ),
        "reference_track_timepoints": sum(
            int(summary["reference_track_timepoints"]) for summary in summaries
        ),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "mean_matched_iou": float(np.mean(ious)) if ious else 0.0,
        "semantic_label_accuracy_matched": float(np.mean(semantic)) if semantic else 0.0,
    }


def _fixation_agreement(
    fixations_by_stimulus: Mapping[str, pd.DataFrame],
    left_by_stimulus: Mapping[str, Sequence[DynamicAOIKeyframe]],
    right_by_stimulus: Mapping[str, Sequence[DynamicAOIKeyframe]],
    *,
    stimuli: Sequence[str],
    max_interpolation_gap_ms: float,
    overlap_rule: str,
) -> dict[str, Any]:
    left_parts: list[pd.DataFrame] = []
    right_parts: list[pd.DataFrame] = []
    per_stimulus: list[dict[str, Any]] = []
    fingerprints: list[dict[str, str]] = []

    for stimulus_id in stimuli:
        fixations = fixations_by_stimulus[stimulus_id].copy()
        required = ["timestamp_ms", "x_px", "y_px"]
        missing = [column for column in required if column not in fixations.columns]
        if missing:
            raise SchemaError(
                f"VISUS fixation table for {stimulus_id!r} is missing columns: {missing}"
            )
        if fixations.empty:
            raise SchemaError(f"VISUS fixation table for {stimulus_id!r} is empty.")
        fingerprints.append(
            {"stimulus_id": stimulus_id, "fingerprint_sha256": fingerprint_frame(fixations)}
        )

        fixations["__visus_fixation_index"] = np.arange(len(fixations), dtype=int)
        left_map = map_fixations_to_dynamic_aois(
            fixations,
            left_by_stimulus[stimulus_id],
            max_interpolation_gap_ms=max_interpolation_gap_ms,
            overlap_rule=overlap_rule,
        )
        right_map = map_fixations_to_dynamic_aois(
            fixations,
            right_by_stimulus[stimulus_id],
            max_interpolation_gap_ms=max_interpolation_gap_ms,
            overlap_rule=overlap_rule,
        )
        left_keys = left_map[["__visus_fixation_index", "aoi_label"]].copy()
        right_keys = right_map[["__visus_fixation_index", "aoi_label"]].copy()
        left_keys.insert(0, "stimulus_id", stimulus_id)
        right_keys.insert(0, "stimulus_id", stimulus_id)
        left_parts.append(left_keys)
        right_parts.append(right_keys)

        single = fixation_assignment_agreement(
            left_keys,
            right_keys,
            key_cols=("stimulus_id", "__visus_fixation_index"),
            label_col="aoi_label",
        )
        per_stimulus.append(
            {
                "stimulus_id": stimulus_id,
                "n_aligned_fixations": int(single["n_aligned_fixations"]),
                "exact_agreement": float(single["exact_agreement"]),
                "cohen_kappa": float(single["cohen_kappa"]),
            }
        )

    combined = fixation_assignment_agreement(
        pd.concat(left_parts, ignore_index=True),
        pd.concat(right_parts, ignore_index=True),
        key_cols=("stimulus_id", "__visus_fixation_index"),
        label_col="aoi_label",
    )
    return {
        **combined,
        "per_stimulus": per_stimulus,
        "fixation_table_fingerprints": fingerprints,
        "max_interpolation_gap_ms": float(max_interpolation_gap_ms),
        "overlap_rule": overlap_rule,
    }


def _json_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records")


def run_visus_dynamic_aoi_human_agreement(
    audit: VisusSourceAuditRun,
    *,
    left_by_stimulus: Mapping[str, Sequence[DynamicAOIKeyframe]],
    right_by_stimulus: Mapping[str, Sequence[DynamicAOIKeyframe]],
    timestamps_by_stimulus: Mapping[str, Sequence[float]],
    left_stream_id: str,
    right_stream_id: str,
    timestamp_grid_basis: str,
    max_interpolation_gap_ms: float,
    min_iou: float = 0.50,
    require_label_match: bool = True,
    fixations_by_stimulus: Mapping[str, pd.DataFrame] | None = None,
    overlap_rule: str = "highest_confidence",
    include_matches: bool = False,
) -> VisusDynamicAOIHumanAgreementRun:
    """Measure agreement only between independently verified VISUS AOI streams.

    The ordinary single curated VISUS stream is intentionally insufficient. The source audit must
    first establish separately recoverable independent streams. Metrics are then computed in both
    reference directions so neither human stream is treated as error-free ground truth.
    """
    _verify_audit(audit)
    _require_independence(audit)

    basis = str(timestamp_grid_basis).strip()
    if not basis:
        raise ValueError("timestamp_grid_basis cannot be empty.")
    gap = float(max_interpolation_gap_ms)
    if not np.isfinite(gap) or gap < 0:
        raise ValueError("max_interpolation_gap_ms must be finite and non-negative.")
    threshold = float(min_iou)
    if not np.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("min_iou must be finite and in [0, 1].")

    stimuli = _audited_stimuli(audit)
    left_stream, right_stream = _require_streams(
        audit,
        stimuli,
        left_stream_id=left_stream_id,
        right_stream_id=right_stream_id,
    )
    _require_exact_keys(left_by_stimulus, stimuli, name="left annotation mapping")
    _require_exact_keys(right_by_stimulus, stimuli, name="right annotation mapping")
    _require_exact_keys(timestamps_by_stimulus, stimuli, name="timestamp grids")
    if fixations_by_stimulus is not None:
        _require_exact_keys(fixations_by_stimulus, stimuli, name="fixation tables")
        coordinate_unit = str(audit.spec.coordinate_unit).strip().lower()
        if coordinate_unit not in {"pixel", "pixels", "px"}:
            raise SchemaError(
                "VISUS fixation-assignment agreement currently requires audited pixel coordinates."
            )

    left: dict[str, list[DynamicAOIKeyframe]] = {}
    right: dict[str, list[DynamicAOIKeyframe]] = {}
    grids: dict[str, np.ndarray] = {}
    input_ledger: list[dict[str, Any]] = []
    for stimulus_id in stimuli:
        left[stimulus_id] = _keyframes(
            left_by_stimulus[stimulus_id],
            stream_id=left_stream,
            stimulus_id=stimulus_id,
        )
        right[stimulus_id] = _keyframes(
            right_by_stimulus[stimulus_id],
            stream_id=right_stream,
            stimulus_id=stimulus_id,
        )
        grids[stimulus_id] = _grid(
            timestamps_by_stimulus[stimulus_id],
            stimulus_id=stimulus_id,
        )
        input_ledger.append(
            {
                "stimulus_id": stimulus_id,
                "left_stream_fingerprint_sha256": benchmark_fingerprint(
                    [asdict(frame) for frame in left[stimulus_id]]
                ),
                "right_stream_fingerprint_sha256": benchmark_fingerprint(
                    [asdict(frame) for frame in right[stimulus_id]]
                ),
                "timestamp_grid_fingerprint_sha256": benchmark_fingerprint(
                    [float(value) for value in grids[stimulus_id]]
                ),
                "n_timestamps": int(len(grids[stimulus_id])),
            }
        )

    direction_specs = (
        ("left_to_right", left_stream, right_stream, left, right),
        ("right_to_left", right_stream, left_stream, right, left),
    )
    directional_rows: list[dict[str, Any]] = []
    stimulus_rows: list[dict[str, Any]] = []
    timestamp_parts: list[pd.DataFrame] = []
    match_parts: list[pd.DataFrame] = []

    for direction, predicted_stream, reference_stream, predicted, reference in direction_specs:
        evaluations: dict[str, DynamicAOIEvaluation] = {}
        for stimulus_id in stimuli:
            evaluation = evaluate_dynamic_aoi_tracks(
                predicted[stimulus_id],
                reference[stimulus_id],
                timestamps_ms=grids[stimulus_id],
                max_interpolation_gap_ms=gap,
                min_iou=threshold,
                require_label_match=bool(require_label_match),
            )
            evaluations[stimulus_id] = evaluation
            stimulus_rows.append(
                {
                    "direction": direction,
                    "predicted_stream_id": predicted_stream,
                    "reference_stream_id": reference_stream,
                    "stimulus_id": stimulus_id,
                    **dict(evaluation.summary),
                }
            )
            timestamps = evaluation.per_timestamp.copy()
            timestamps.insert(0, "stimulus_id", stimulus_id)
            timestamps.insert(0, "direction", direction)
            timestamp_parts.append(timestamps)
            if include_matches and not evaluation.matches.empty:
                matched = evaluation.matches.copy()
                matched.insert(0, "stimulus_id", stimulus_id)
                matched.insert(0, "direction", direction)
                match_parts.append(matched)

        directional_rows.append(
            {
                "direction": direction,
                "predicted_stream_id": predicted_stream,
                "reference_stream_id": reference_stream,
                **_aggregate(evaluations),
            }
        )

    directional_summary = pd.DataFrame(directional_rows)
    per_stimulus = pd.DataFrame(stimulus_rows)
    per_timestamp = pd.concat(timestamp_parts, ignore_index=True)
    matches = (
        pd.concat(match_parts, ignore_index=True)
        if match_parts
        else pd.DataFrame(
            columns=[
                "direction",
                "stimulus_id",
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

    fixation_assignment: dict[str, Any] | None = None
    if fixations_by_stimulus is not None:
        fixation_assignment = _fixation_agreement(
            fixations_by_stimulus,
            left,
            right,
            stimuli=stimuli,
            max_interpolation_gap_ms=gap,
            overlap_rule=overlap_rule,
        )

    card = BenchmarkDatasetCard(
        name=f"VISUS-{left_stream}-vs-{right_stream}",
        version=audit.spec.dataset_version,
        source=audit.spec.source,
        license=audit.spec.license,
        task="independent-human dynamic-AOI agreement",
        sampling_rates_hz=[float(audit.spec.published_eye_sampling_rate_hz)],
        participant_count=int(audit.spec.published_participant_count),
        stimulus_count=len(stimuli),
        split_unit="stimulus_id",
        validation_scope="audited-source-independent-human-dynamic-aoi-agreement",
        annotation_origin="human-manual",
        sampling_origin="native",
        reference_strength="human-reference",
        human_annotator_count=2,
        reference_description=(
            f"Two independently verified recoverable VISUS AOI streams: {left_stream!r} and "
            f"{right_stream!r}. Neither stream is treated as error-free ground truth."
        ),
        notes=[
            "Agreement is computed in both directional reference assignments.",
            (
                "The source audit must independently verify stream independence before this "
                "runner works."
            ),
            "Timestamp grids are external and identical across both directional evaluations.",
            "Human-human agreement describes annotation variability, not model performance.",
        ],
    )
    metrics: dict[str, Any] = {
        "directional_summary": _json_records(directional_summary),
        "per_stimulus": _json_records(per_stimulus),
        "per_timestamp": _json_records(per_timestamp),
        "fixation_assignment_agreement": fixation_assignment,
    }
    if include_matches:
        metrics["matches"] = _json_records(matches)

    protocol = {
        "evaluation_type": "visus-independent-human-dynamic-aoi-agreement",
        "source_audit_report_fingerprint_sha256": audit.report[
            "report_fingerprint_sha256"
        ],
        "source_audit_spec_fingerprint_sha256": audit.report["spec_fingerprint_sha256"],
        "source_manifest_fingerprint_sha256": audit.report["inventory"][
            "manifest_fingerprint_sha256"
        ],
        "independent_annotation_streams_verified": True,
        "independence_verification_basis": audit.spec.independent_annotation_streams_basis,
        "left_stream_id": left_stream,
        "right_stream_id": right_stream,
        "directional_reference_assignments": ["left_to_right", "right_to_left"],
        "timestamp_grid_basis": basis,
        "timestamp_grid_explicit": True,
        "input_fingerprints": input_ledger,
        "max_interpolation_gap_ms": gap,
        "temporal_extrapolation": False,
        "min_iou": threshold,
        "require_label_match": bool(require_label_match),
        "complete_audited_stimulus_coverage_required": True,
        "fixation_assignment_enabled": fixations_by_stimulus is not None,
        "human_agreement_reference_not_ground_truth": True,
        "claim_limits": [
            "Human-human agreement quantifies annotation variability and is not ground truth.",
            (
                "This runner cannot establish that independent VISUS streams exist; the audit "
                "must do so."
            ),
            (
                "No empirical agreement claim exists until real independently verified inputs "
                "are frozen."
            ),
        ],
    }
    report = build_benchmark_report(
        benchmark=card,
        metrics=metrics,
        model={},
        protocol=protocol,
    )
    return VisusDynamicAOIHumanAgreementRun(
        directional_summary=directional_summary,
        per_stimulus=per_stimulus,
        per_timestamp=per_timestamp,
        matches=matches,
        fixation_assignment=fixation_assignment,
        report=report,
    )
