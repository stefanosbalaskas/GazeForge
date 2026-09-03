"""Rate-aware human-human agreement for audited Gaze-in-the-Wild label streams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .benchmarks import BenchmarkDatasetCard, benchmark_fingerprint, build_benchmark_report
from .evaluation import sample_label_agreement
from .event_evaluation import (
    EventLevelEvaluation,
    evaluate_event_intervals,
    samples_to_event_intervals,
)
from .exceptions import BenchmarkIntegrityError, SchemaError
from .gaze_in_wild_audit import (
    GazeInWildAuditedFile,
    GazeInWildSourceAuditRun,
)

_KEYS = ("participant_id", "trial_id", "timestamp_ms")
_GAZE_COLUMNS = ("x_px", "y_px", "validity", "confidence")


@dataclass(slots=True)
class GazeInWildLabellerAgreementRun:
    """Aligned audited streams and pooled rate-aware human-human agreement evidence."""

    audit: GazeInWildSourceAuditRun
    aligned: pd.DataFrame
    per_trial: pd.DataFrame
    left_reference_events: EventLevelEvaluation
    right_reference_events: EventLevelEvaluation
    report: dict[str, Any]


def _verify_audit_integrity(audit: GazeInWildSourceAuditRun) -> None:
    if not isinstance(audit, GazeInWildSourceAuditRun):
        raise TypeError("audit must be a GazeInWildSourceAuditRun instance.")
    if audit.report.get("status") != "verified":
        raise BenchmarkIntegrityError("Gaze-in-the-Wild source audit is not verified.")
    fingerprint = str(audit.report.get("report_fingerprint_sha256", ""))
    body = {
        key: value
        for key, value in audit.report.items()
        if key != "report_fingerprint_sha256"
    }
    if len(fingerprint) != 64 or benchmark_fingerprint(body) != fingerprint:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild source-audit report fingerprint does not revalidate."
        )
    spec_fingerprint = str(audit.report.get("spec_fingerprint_sha256", ""))
    if benchmark_fingerprint(audit.spec.to_dict()) != spec_fingerprint:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild source-audit specification fingerprint does not revalidate."
        )
    for item in audit.files:
        metadata = item.gaze.metadata
        if metadata.get("source_audit_status") != "verified":
            raise BenchmarkIntegrityError("An audited gaze stream lost its verified audit status.")
        if metadata.get("source_audit_report_fingerprint_sha256") != fingerprint:
            raise BenchmarkIntegrityError(
                "An audited gaze stream does not match the source-audit report fingerprint."
            )
        if metadata.get("source_audit_spec_fingerprint_sha256") != spec_fingerprint:
            raise BenchmarkIntegrityError(
                "An audited gaze stream does not match the source-audit specification fingerprint."
            )


def _labeller_index(
    audit: GazeInWildSourceAuditRun,
    labeller_id: int,
) -> dict[tuple[str, str], GazeInWildAuditedFile]:
    selected = {
        (item.record.participant_id, item.record.trial_id): item
        for item in audit.files
        if item.record.labeller_id == labeller_id
    }
    if not selected:
        raise SchemaError(f"No audited Gaze-in-the-Wild files exist for labeller {labeller_id}.")
    return selected


def _numeric_equal(left: pd.Series, right: pd.Series) -> bool:
    left_values = pd.to_numeric(left, errors="coerce").to_numpy(dtype=float)
    right_values = pd.to_numeric(right, errors="coerce").to_numpy(dtype=float)
    return bool(
        np.all(np.isclose(left_values, right_values, equal_nan=True, rtol=0.0, atol=1e-9))
    )


def _align_trial(
    left: GazeInWildAuditedFile,
    right: GazeInWildAuditedFile,
) -> pd.DataFrame:
    left_frame = left.gaze.data
    right_frame = right.gaze.data
    required = [*_KEYS, *_GAZE_COLUMNS, "event_label"]
    for name, frame in (("left", left_frame), ("right", right_frame)):
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise SchemaError(f"{name} Gaze-in-the-Wild stream is missing columns: {missing}")
        if frame.duplicated(list(_KEYS)).any():
            raise SchemaError(f"{name} Gaze-in-the-Wild stream has duplicate sample keys.")

    aligned = left_frame[required].merge(
        right_frame[required],
        on=list(_KEYS),
        how="inner",
        suffixes=("_left", "_right"),
        validate="one_to_one",
    )
    if len(aligned) != len(left_frame) or len(aligned) != len(right_frame):
        raise SchemaError(
            "Gaze-in-the-Wild labeller agreement requires complete one-to-one sample alignment; "
            f"left_rows={len(left_frame)}, right_rows={len(right_frame)}, "
            f"aligned_rows={len(aligned)}."
        )
    for coordinate in ("x_px", "y_px", "confidence"):
        if not _numeric_equal(aligned[f"{coordinate}_left"], aligned[f"{coordinate}_right"]):
            raise SchemaError(
                "Gaze-in-the-Wild labeller streams do not contain identical underlying gaze: "
                f"{coordinate} differs after alignment."
            )
    if not aligned["validity_left"].astype(bool).equals(
        aligned["validity_right"].astype(bool)
    ):
        raise SchemaError(
            "Gaze-in-the-Wild labeller streams do not contain identical validity masks."
        )
    return aligned.sort_values(list(_KEYS), kind="stable").reset_index(drop=True)


def _agreement_frames(
    aligned: pd.DataFrame,
    *,
    mask: pd.Series | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    subset = aligned if mask is None else aligned.loc[mask]
    if subset.empty:
        raise SchemaError("No paired samples remain for Gaze-in-the-Wild agreement.")
    left = subset[[*_KEYS, "event_label_left"]].rename(
        columns={"event_label_left": "event_label"}
    )
    right = subset[[*_KEYS, "event_label_right"]].rename(
        columns={"event_label_right": "event_label"}
    )
    return left, right


def _analysis_mask(
    aligned: pd.DataFrame,
    *,
    excluded_labels: tuple[str, ...],
    exclude_invalid_tracking: bool,
) -> pd.Series:
    excluded = {str(label).strip().lower() for label in excluded_labels}
    left_labels = aligned["event_label_left"].astype(str).str.strip().str.lower()
    right_labels = aligned["event_label_right"].astype(str).str.strip().str.lower()
    retained = ~left_labels.isin(excluded) & ~right_labels.isin(excluded)
    if exclude_invalid_tracking:
        retained &= aligned["validity_left"].astype(bool)
        retained &= aligned["validity_right"].astype(bool)
    return retained


def _event_input(
    aligned: pd.DataFrame,
    *,
    label_column: str,
    exclude_invalid_tracking: bool,
) -> pd.DataFrame:
    frame = aligned[[*_KEYS, label_column, "validity_left", "validity_right"]].copy()
    if exclude_invalid_tracking:
        invalid = ~frame["validity_left"].astype(bool) | ~frame["validity_right"].astype(bool)
        frame.loc[invalid, label_column] = "unlabelled"
    return frame[[*_KEYS, label_column]]


def _event_metrics(result: EventLevelEvaluation) -> dict[str, Any]:
    clean = result.per_class.astype(object).where(pd.notna(result.per_class), None)
    return {
        "summary": dict(result.summary),
        "per_class": clean.to_dict(orient="records"),
        "design": dict(result.design),
    }


def run_gaze_in_wild_labeller_agreement(
    audit: GazeInWildSourceAuditRun,
    *,
    left_labeller: int,
    right_labeller: int,
    excluded_labels: tuple[str, ...] = ("unlabelled",),
    exclude_invalid_tracking: bool = True,
    event_min_iou: float = 0.50,
    require_complete_overlap: bool = True,
) -> GazeInWildLabellerAgreementRun:
    """Compare two human labellers only after the Gaze-in-the-Wild source audit passes.

    Each shared participant/trial is segmented at its own timestamp-inferred sampling rate before
    event intervals are pooled in milliseconds. This avoids inventing one nominal cadence for a
    distributed snapshot whose files may differ. Invalid tracking samples can be retained as hard
    event separators while being excluded from analysis-label agreement.
    """
    _verify_audit_integrity(audit)
    left_id = int(left_labeller)
    right_id = int(right_labeller)
    if left_id <= 0 or right_id <= 0:
        raise ValueError("left_labeller and right_labeller must be positive integers.")
    if left_id == right_id:
        raise ValueError("Human-human agreement requires two distinct labellers.")
    min_iou = float(event_min_iou)
    if not np.isfinite(min_iou) or not 0.0 <= min_iou <= 1.0:
        raise ValueError("event_min_iou must be finite and in [0, 1].")

    left_index = _labeller_index(audit, left_id)
    right_index = _labeller_index(audit, right_id)
    left_trials = set(left_index)
    right_trials = set(right_index)
    shared = sorted(left_trials & right_trials)
    if not shared:
        raise SchemaError("The selected Gaze-in-the-Wild labellers share no audited trials.")
    left_only = sorted(left_trials - right_trials)
    right_only = sorted(right_trials - left_trials)
    if require_complete_overlap and (left_only or right_only):
        raise SchemaError(
            "Complete labeller overlap is required for frozen agreement; "
            f"left_only={left_only}, right_only={right_only}."
        )

    aligned_parts: list[pd.DataFrame] = []
    left_event_parts: list[pd.DataFrame] = []
    right_event_parts: list[pd.DataFrame] = []
    trial_rows: list[dict[str, Any]] = []
    event_excluded = tuple(
        sorted(
            {
                *(str(label).strip().lower() for label in excluded_labels),
                *( ["unlabelled"] if exclude_invalid_tracking else [] ),
            }
        )
    )

    for identity in shared:
        left_item = left_index[identity]
        right_item = right_index[identity]
        left_rate = float(left_item.gaze.sampling_rate_hz)
        right_rate = float(right_item.gaze.sampling_rate_hz)
        if not np.isclose(left_rate, right_rate, rtol=1e-9, atol=1e-9):
            raise SchemaError(
                "Paired Gaze-in-the-Wild labeller files imply different sampling rates for "
                f"{identity!r}: left={left_rate:.9g}, right={right_rate:.9g}."
            )
        aligned = _align_trial(left_item, right_item)
        aligned_parts.append(aligned)
        all_left, all_right = _agreement_frames(aligned)
        all_agreement = sample_label_agreement(all_left, all_right)
        retained = _analysis_mask(
            aligned,
            excluded_labels=excluded_labels,
            exclude_invalid_tracking=exclude_invalid_tracking,
        )
        analysis_left, analysis_right = _agreement_frames(aligned, mask=retained)
        analysis_agreement = sample_label_agreement(analysis_left, analysis_right)

        left_samples = _event_input(
            aligned,
            label_column="event_label_left",
            exclude_invalid_tracking=exclude_invalid_tracking,
        )
        right_samples = _event_input(
            aligned,
            label_column="event_label_right",
            exclude_invalid_tracking=exclude_invalid_tracking,
        )
        left_events = samples_to_event_intervals(
            left_samples,
            label_col="event_label_left",
            sampling_rate_hz=left_rate,
            excluded_labels=event_excluded,
        )
        right_events = samples_to_event_intervals(
            right_samples,
            label_col="event_label_right",
            sampling_rate_hz=left_rate,
            excluded_labels=event_excluded,
        )
        left_event_parts.append(left_events)
        right_event_parts.append(right_events)
        trial_rows.append(
            {
                "participant_id": identity[0],
                "trial_id": identity[1],
                "sampling_rate_hz": left_rate,
                "n_aligned_samples": int(len(aligned)),
                "analysis_retained_samples": int(retained.sum()),
                "analysis_retained_fraction": float(retained.mean()),
                "all_label_exact_agreement": all_agreement["exact_agreement"],
                "all_label_cohen_kappa": all_agreement["cohen_kappa"],
                "analysis_label_exact_agreement": analysis_agreement["exact_agreement"],
                "analysis_label_cohen_kappa": analysis_agreement["cohen_kappa"],
                "left_event_count": int(len(left_events)),
                "right_event_count": int(len(right_events)),
            }
        )

    aligned_all = pd.concat(aligned_parts, ignore_index=True)
    all_left, all_right = _agreement_frames(aligned_all)
    sample_all = sample_label_agreement(all_left, all_right)
    analysis_retained = _analysis_mask(
        aligned_all,
        excluded_labels=excluded_labels,
        exclude_invalid_tracking=exclude_invalid_tracking,
    )
    analysis_left, analysis_right = _agreement_frames(aligned_all, mask=analysis_retained)
    sample_analysis = sample_label_agreement(analysis_left, analysis_right)
    sample_analysis.update(
        {
            "n_excluded_pairwise_samples": int((~analysis_retained).sum()),
            "retained_fraction": float(analysis_retained.mean()),
            "excluded_labels": sorted(
                {str(label).strip().lower() for label in excluded_labels}
            ),
            "exclude_invalid_tracking": bool(exclude_invalid_tracking),
        }
    )

    left_events_all = pd.concat(left_event_parts, ignore_index=True)
    right_events_all = pd.concat(right_event_parts, ignore_index=True)
    left_reference_events = evaluate_event_intervals(
        predicted=right_events_all,
        reference=left_events_all,
        min_iou=min_iou,
        require_label_match=True,
    )
    right_reference_events = evaluate_event_intervals(
        predicted=left_events_all,
        reference=right_events_all,
        min_iou=min_iou,
        require_label_match=True,
    )
    per_trial = pd.DataFrame(trial_rows).sort_values(
        ["participant_id", "trial_id"], kind="stable"
    ).reset_index(drop=True)
    rates = sorted({float(value) for value in per_trial["sampling_rate_hz"]})

    report_fingerprint = str(audit.report["report_fingerprint_sha256"])
    card = BenchmarkDatasetCard(
        name=f"{audit.spec.dataset_name}-labeller-agreement",
        version=audit.spec.dataset_version,
        source=audit.spec.source,
        license=audit.spec.license,
        task="audited human-human sample-label and event-boundary agreement",
        sampling_rates_hz=rates,
        participant_count=int(aligned_all["participant_id"].nunique()),
        stimulus_count=int(len(shared)),
        split_unit="participant_id/trial_id",
        validation_scope="audited-source-file-human-agreement",
        annotation_origin="human-manual",
        sampling_origin="native",
        reference_strength="human-reference",
        human_annotator_count=int(audit.report["identity"]["labeller_count"]),
        reference_description=(
            "Paired human manual event labels from source-audited Gaze-in-the-Wild streams."
        ),
        notes=[
            "No GazeForge resampling is used for the human-human agreement result.",
            "Each trial is segmented using its own timestamp-inferred source-file cadence.",
            "Published hardware rate is retained as provenance rather than imposed on file data.",
            "Neither human labeller is treated as error-free; event metrics are bidirectional.",
            "This evidence is not Gazepoint GP3-specific validation.",
        ],
    )
    protocol = {
        "left_labeller_id": left_id,
        "right_labeller_id": right_id,
        "event_min_iou": min_iou,
        "excluded_labels": sorted(
            {str(label).strip().lower() for label in excluded_labels}
        ),
        "exclude_invalid_tracking": bool(exclude_invalid_tracking),
        "event_separator_labels": list(event_excluded),
        "require_complete_overlap": bool(require_complete_overlap),
        "shared_trial_count": len(shared),
        "left_only_trials": [list(identity) for identity in left_only],
        "right_only_trials": [list(identity) for identity in right_only],
        "sample_alignment": "complete_one_to_one_participant_trial_timestamp_per_shared_trial",
        "underlying_gaze_identity_reverified": True,
        "resampling": None,
        "sampling_rate_policy": "timestamp_inferred_per_trial_before_event_pooling_in_ms",
        "source_audit_report_fingerprint_sha256": report_fingerprint,
        "source_audit_spec_fingerprint_sha256": audit.report["spec_fingerprint_sha256"],
        "label_manifest_fingerprint_sha256": audit.report["label_inventory"][
            "manifest_fingerprint_sha256"
        ],
        "process_manifest_fingerprint_sha256": audit.report["process_inventory"][
            "manifest_fingerprint_sha256"
        ],
    }
    clean_trial = per_trial.astype(object).where(pd.notna(per_trial), None)
    metrics = {
        "sample_agreement_all_labels": sample_all,
        "sample_agreement_analysis_labels": sample_analysis,
        "event_agreement_left_as_reference": _event_metrics(left_reference_events),
        "event_agreement_right_as_reference": _event_metrics(right_reference_events),
        "per_trial": clean_trial.to_dict(orient="records"),
        "n_aligned_samples": int(len(aligned_all)),
    }
    report = build_benchmark_report(
        benchmark=card,
        metrics=metrics,
        model={"models": []},
        protocol=protocol,
    )
    return GazeInWildLabellerAgreementRun(
        audit=audit,
        aligned=aligned_all,
        per_trial=per_trial,
        left_reference_events=left_reference_events,
        right_reference_events=right_reference_events,
        report=report,
    )
