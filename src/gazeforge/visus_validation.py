"""Source-audit-aware model-human dynamic-AOI validation for VISUS."""

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
from .visus_audit import VisusSourceAuditRun


@dataclass(slots=True)
class VisusDynamicAOIModelValidationRun:
    """Per-stimulus model-human evaluations and a deterministic benchmark report."""

    per_stimulus: pd.DataFrame
    per_timestamp: pd.DataFrame
    matches: pd.DataFrame
    fixation_assignment: dict[str, Any] | None
    report: dict[str, Any]


def _resolved(value: str) -> bool:
    text = str(value).strip()
    upper = text.upper()
    return bool(text) and "REPLACE" not in upper and "VERIFY" not in upper


def _verify_audit_integrity(audit: VisusSourceAuditRun) -> None:
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

    manifest_rows = [asdict(item.record) for item in audit.files]
    expected_manifest = str(
        audit.report.get("inventory", {}).get("manifest_fingerprint_sha256", "")
    )
    if benchmark_fingerprint(manifest_rows) != expected_manifest:
        raise BenchmarkIntegrityError("VISUS source manifest fingerprint does not revalidate.")


def _audited_stimuli(audit: VisusSourceAuditRun) -> list[str]:
    stimuli = [str(value) for value in audit.report.get("identity", {}).get("stimulus_ids", [])]
    if not stimuli:
        raise BenchmarkIntegrityError(
            "VISUS source audit contains no verified stimulus identities."
        )
    return sorted(stimuli)


def _validate_exact_keys(
    mapping: Mapping[str, Any],
    expected: Sequence[str],
    *,
    name: str,
) -> None:
    observed = {str(key) for key in mapping}
    expected_set = set(expected)
    missing = sorted(expected_set - observed)
    extra = sorted(observed - expected_set)
    if missing or extra:
        raise SchemaError(
            f"VISUS {name} must exactly cover the audited stimuli: "
            f"missing={missing}, extra={extra}."
        )


def _validate_reference_stream(
    audit: VisusSourceAuditRun,
    *,
    reference_stream_id: str,
    stimuli: Sequence[str],
) -> None:
    stream_id = str(reference_stream_id).strip()
    if not stream_id:
        raise ValueError("reference_stream_id cannot be empty.")
    streams = audit.report.get("annotation_provenance", {}).get("streams_by_stimulus", {})
    missing = [stimulus for stimulus in stimuli if stream_id not in streams.get(stimulus, [])]
    if missing:
        raise SchemaError(
            "Selected VISUS reference stream is not manifested for every audited stimulus: "
            f"missing={missing}."
        )


def _validate_keyframes(
    frames: Sequence[DynamicAOIKeyframe],
    *,
    kind: str,
    stimulus_id: str,
    model_name: str,
    model_version: str,
) -> list[DynamicAOIKeyframe]:
    values = list(frames)
    if kind == "reference" and not values:
        raise SchemaError(f"VISUS reference keyframes are empty for stimulus {stimulus_id!r}.")
    for frame in values:
        if not isinstance(frame, DynamicAOIKeyframe):
            raise TypeError(
                f"VISUS {kind} keyframes for {stimulus_id!r} must be DynamicAOIKeyframe objects."
            )
        if kind == "predicted":
            if frame.model_name is not None and frame.model_name != model_name:
                raise SchemaError(
                    f"Predicted VISUS keyframe model_name mismatch for {stimulus_id!r}."
                )
            if frame.model_version is not None and frame.model_version != model_version:
                raise SchemaError(
                    f"Predicted VISUS keyframe model_version mismatch for {stimulus_id!r}."
                )
    return values


def _json_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records")


def _aggregate_evaluations(
    evaluations: Mapping[str, DynamicAOIEvaluation],
) -> dict[str, Any]:
    summaries = [evaluation.summary for evaluation in evaluations.values()]
    tp = int(sum(int(summary["true_positive"]) for summary in summaries))
    fp = int(sum(int(summary["false_positive"]) for summary in summaries))
    fn = int(sum(int(summary["false_negative"]) for summary in summaries))
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0

    matched_iou: list[float] = []
    matched_semantic: list[bool] = []
    for evaluation in evaluations.values():
        accepted = evaluation.matches.loc[evaluation.matches["status"] == "matched"]
        if not accepted.empty:
            matched_iou.extend(accepted["iou"].astype(float).tolist())
            matched_semantic.extend(accepted["label_match"].astype(bool).tolist())

    return {
        "stimulus_count": int(len(evaluations)),
        "n_timestamps": int(sum(int(summary["n_timestamps"]) for summary in summaries)),
        "n_empty_timestamps": int(
            sum(int(summary["n_empty_timestamps"]) for summary in summaries)
        ),
        "predicted_track_timepoints": int(
            sum(int(summary["predicted_track_timepoints"]) for summary in summaries)
        ),
        "reference_track_timepoints": int(
            sum(int(summary["reference_track_timepoints"]) for summary in summaries)
        ),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "mean_matched_iou": float(np.mean(matched_iou)) if matched_iou else 0.0,
        "semantic_label_accuracy_matched": (
            float(np.mean(matched_semantic)) if matched_semantic else 0.0
        ),
    }


def _combined_fixation_assignment(
    fixations_by_stimulus: Mapping[str, pd.DataFrame],
    predicted_by_stimulus: Mapping[str, Sequence[DynamicAOIKeyframe]],
    reference_by_stimulus: Mapping[str, Sequence[DynamicAOIKeyframe]],
    *,
    stimuli: Sequence[str],
    max_interpolation_gap_ms: float,
    overlap_rule: str,
) -> dict[str, Any]:
    left_parts: list[pd.DataFrame] = []
    right_parts: list[pd.DataFrame] = []
    per_stimulus: list[dict[str, Any]] = []

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

        fixations["__visus_fixation_index"] = np.arange(len(fixations), dtype=int)
        predicted = map_fixations_to_dynamic_aois(
            fixations,
            predicted_by_stimulus[stimulus_id],
            max_interpolation_gap_ms=max_interpolation_gap_ms,
            overlap_rule=overlap_rule,
        )
        reference = map_fixations_to_dynamic_aois(
            fixations,
            reference_by_stimulus[stimulus_id],
            max_interpolation_gap_ms=max_interpolation_gap_ms,
            overlap_rule=overlap_rule,
        )

        predicted_keys = predicted[["__visus_fixation_index", "aoi_label"]].copy()
        reference_keys = reference[["__visus_fixation_index", "aoi_label"]].copy()
        predicted_keys.insert(0, "stimulus_id", stimulus_id)
        reference_keys.insert(0, "stimulus_id", stimulus_id)
        left_parts.append(predicted_keys)
        right_parts.append(reference_keys)

        single = fixation_assignment_agreement(
            predicted_keys,
            reference_keys,
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
        "max_interpolation_gap_ms": float(max_interpolation_gap_ms),
        "overlap_rule": overlap_rule,
    }


def run_visus_dynamic_aoi_model_validation(
    audit: VisusSourceAuditRun,
    *,
    predicted_by_stimulus: Mapping[str, Sequence[DynamicAOIKeyframe]],
    reference_by_stimulus: Mapping[str, Sequence[DynamicAOIKeyframe]],
    timestamps_by_stimulus: Mapping[str, Sequence[float]],
    reference_stream_id: str,
    model_name: str,
    model_version: str,
    timestamp_grid_basis: str,
    max_interpolation_gap_ms: float,
    min_iou: float = 0.50,
    require_label_match: bool = True,
    fixations_by_stimulus: Mapping[str, pd.DataFrame] | None = None,
    overlap_rule: str = "highest_confidence",
    include_matches: bool = False,
) -> VisusDynamicAOIModelValidationRun:
    """Evaluate one explicit model against one audited VISUS human-reference stream.

    Predictions and references use canonical ``DynamicAOIKeyframe`` objects. Timestamp grids are
    supplied explicitly and must cover every audited stimulus, preventing prediction emission times
    from becoming the evaluation grid. This function orchestrates deterministic model-human
    evaluation only; it does not parse the historical VISUS XML/video formats or create empirical
    evidence without a separately verified source audit.
    """
    _verify_audit_integrity(audit)
    if not _resolved(model_name) or not _resolved(model_version):
        raise ValueError("VISUS model_name and model_version must be explicit resolved values.")
    if not _resolved(timestamp_grid_basis):
        raise ValueError("timestamp_grid_basis must explicitly describe the supplied grid.")

    gap = float(max_interpolation_gap_ms)
    if not np.isfinite(gap) or gap < 0:
        raise ValueError("max_interpolation_gap_ms must be finite and non-negative.")
    threshold = float(min_iou)
    if not np.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("min_iou must be finite and in [0, 1].")

    stimuli = _audited_stimuli(audit)
    _validate_reference_stream(
        audit,
        reference_stream_id=reference_stream_id,
        stimuli=stimuli,
    )
    _validate_exact_keys(predicted_by_stimulus, stimuli, name="predictions")
    _validate_exact_keys(reference_by_stimulus, stimuli, name="references")
    _validate_exact_keys(timestamps_by_stimulus, stimuli, name="timestamp grids")
    if fixations_by_stimulus is not None:
        _validate_exact_keys(fixations_by_stimulus, stimuli, name="fixation tables")
        coordinate_unit = str(audit.spec.coordinate_unit).strip().lower()
        if coordinate_unit not in {"pixel", "pixels", "px"}:
            raise SchemaError(
                "VISUS fixation-assignment validation currently requires audited pixel coordinates."
            )

    evaluations: dict[str, DynamicAOIEvaluation] = {}
    prepared_predictions: dict[str, list[DynamicAOIKeyframe]] = {}
    prepared_references: dict[str, list[DynamicAOIKeyframe]] = {}
    timestamp_ledgers: list[dict[str, Any]] = []
    per_stimulus_rows: list[dict[str, Any]] = []
    per_timestamp_parts: list[pd.DataFrame] = []
    match_parts: list[pd.DataFrame] = []

    for stimulus_id in stimuli:
        predicted = _validate_keyframes(
            predicted_by_stimulus[stimulus_id],
            kind="predicted",
            stimulus_id=stimulus_id,
            model_name=model_name,
            model_version=model_version,
        )
        reference = _validate_keyframes(
            reference_by_stimulus[stimulus_id],
            kind="reference",
            stimulus_id=stimulus_id,
            model_name=model_name,
            model_version=model_version,
        )
        timestamps = np.asarray(timestamps_by_stimulus[stimulus_id], dtype=float)
        evaluation = evaluate_dynamic_aoi_tracks(
            predicted,
            reference,
            timestamps_ms=timestamps,
            max_interpolation_gap_ms=gap,
            min_iou=threshold,
            require_label_match=bool(require_label_match),
        )
        evaluations[stimulus_id] = evaluation
        prepared_predictions[stimulus_id] = predicted
        prepared_references[stimulus_id] = reference

        row = {"stimulus_id": stimulus_id, **dict(evaluation.summary)}
        per_stimulus_rows.append(row)

        per_timestamp = evaluation.per_timestamp.copy()
        per_timestamp.insert(0, "stimulus_id", stimulus_id)
        per_timestamp_parts.append(per_timestamp)

        if include_matches and not evaluation.matches.empty:
            matches = evaluation.matches.copy()
            matches.insert(0, "stimulus_id", stimulus_id)
            match_parts.append(matches)

        timestamp_ledgers.append(
            {
                "stimulus_id": stimulus_id,
                "n_timestamps": int(len(timestamps)),
                "first_timestamp_ms": float(timestamps[0]),
                "last_timestamp_ms": float(timestamps[-1]),
                "timestamp_grid_fingerprint_sha256": benchmark_fingerprint(
                    [float(value) for value in timestamps]
                ),
            }
        )

    per_stimulus = pd.DataFrame(per_stimulus_rows)
    per_timestamp = pd.concat(per_timestamp_parts, ignore_index=True)
    matches = (
        pd.concat(match_parts, ignore_index=True)
        if match_parts
        else pd.DataFrame(
            columns=[
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
        fixation_assignment = _combined_fixation_assignment(
            fixations_by_stimulus,
            prepared_predictions,
            prepared_references,
            stimuli=stimuli,
            max_interpolation_gap_ms=gap,
            overlap_rule=overlap_rule,
        )

    aggregate = _aggregate_evaluations(evaluations)
    audit_fingerprint = str(audit.report["report_fingerprint_sha256"])
    spec_fingerprint = str(audit.report["spec_fingerprint_sha256"])
    manifest_fingerprint = str(audit.report["inventory"]["manifest_fingerprint_sha256"])

    card = BenchmarkDatasetCard(
        name=f"VISUS-{reference_stream_id}",
        version=audit.spec.dataset_version,
        source=audit.spec.source,
        license=audit.spec.license,
        task="dynamic video AOI detection and fixation-to-AOI assignment",
        sampling_rates_hz=[float(audit.spec.published_eye_sampling_rate_hz)],
        participant_count=int(audit.spec.published_participant_count),
        stimulus_count=len(stimuli),
        split_unit="stimulus_id",
        validation_scope="audited-source-model-human-dynamic-aoi",
        annotation_origin="human-manual",
        sampling_origin="native",
        reference_strength="human-reference",
        human_annotator_count=1,
        reference_description=(
            f"Explicit audited VISUS AOI reference stream {reference_stream_id!r}; the published "
            "two-contributor curation process is not interpreted as two independent references."
        ),
        notes=[
            "Every audited stimulus must be represented in predictions, references, and grids.",
            "Timestamp grids are explicit external inputs, never inferred from model emissions.",
            "No temporal extrapolation is performed beyond observed AOI keyframes.",
            "Human-human reliability is outside this model-human validation report.",
        ],
    )

    metrics: dict[str, Any] = {
        "dynamic_aoi_summary": aggregate,
        "per_stimulus": _json_records(per_stimulus),
        "per_timestamp": _json_records(per_timestamp),
        "fixation_assignment_agreement": fixation_assignment,
    }
    if include_matches:
        metrics["matches"] = _json_records(matches)

    protocol = {
        "evaluation_type": "visus-audited-model-human-dynamic-aoi",
        "source_audit_report_fingerprint_sha256": audit_fingerprint,
        "source_audit_spec_fingerprint_sha256": spec_fingerprint,
        "source_manifest_fingerprint_sha256": manifest_fingerprint,
        "reference_stream_id": str(reference_stream_id),
        "timestamp_grid_explicit": True,
        "timestamp_grid_basis": str(timestamp_grid_basis),
        "timestamp_grids": timestamp_ledgers,
        "max_interpolation_gap_ms": gap,
        "temporal_extrapolation": False,
        "min_iou": threshold,
        "require_label_match": bool(require_label_match),
        "complete_audited_stimulus_coverage_required": True,
        "fixation_assignment_enabled": fixations_by_stimulus is not None,
        "human_human_agreement_claimed": False,
        "claim_limits": [
            "This report compares one model with one selected audited human-reference stream.",
            "The published two-contributor curation process is not treated as independent labels.",
            "No empirical VISUS performance claim exists until real audited inputs are frozen.",
        ],
    }
    report = build_benchmark_report(
        benchmark=card,
        metrics=metrics,
        model={"name": str(model_name), "version": str(model_version)},
        protocol=protocol,
    )
    return VisusDynamicAOIModelValidationRun(
        per_stimulus=per_stimulus,
        per_timestamp=per_timestamp,
        matches=matches,
        fixation_assignment=fixation_assignment,
        report=report,
    )
