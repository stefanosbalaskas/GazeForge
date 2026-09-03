"""Audited participant-held-out model validation for Gaze-in-the-Wild."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support

from .benchmarks import BenchmarkDatasetCard, benchmark_fingerprint, build_benchmark_report
from .comparison import EventModelComparison, compare_event_models_grouped
from .event_evaluation import evaluate_sample_event_predictions
from .exceptions import BenchmarkIntegrityError, SchemaError
from .gaze_in_wild_audit import GazeInWildAuditedFile, GazeInWildSourceAuditRun
from .paired import PairedModelDifferences, paired_model_metric_differences
from .resampling import resample_labeled_gaze
from .stratified import StratifiedEventPerformance, summarize_event_predictions_by_stratum

_DEFAULT_EXCLUDED_LABELS = ("ambiguous", "unlabelled", "undefined")
_TASK_COLUMNS = ("participant_id", "trial_id")


@dataclass(slots=True)
class GazeInWildPreparedBenchmark:
    """One audited labeller prepared at a common analysis cadence."""

    data: pd.DataFrame
    dataset_card: BenchmarkDatasetCard
    preparation_report: dict[str, Any]


@dataclass(slots=True)
class GazeInWildModelValidationRun:
    """Prepared data, participant-held-out comparisons, sensitivities, and report."""

    prepared: GazeInWildPreparedBenchmark
    comparison: EventModelComparison
    paired_model_differences: PairedModelDifferences
    sample_event_class_performance: pd.DataFrame
    event_class_performance: pd.DataFrame
    task_performance: StratifiedEventPerformance | None
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


def _json_safe_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    clean = frame.astype(object).where(pd.notna(frame), None)
    return clean.to_dict(orient="records")


def _selected_files(
    audit: GazeInWildSourceAuditRun,
    labeller_id: int,
) -> list[GazeInWildAuditedFile]:
    labeller = int(labeller_id)
    if labeller <= 0:
        raise ValueError("labeller_id must be a positive integer.")
    selected = [item for item in audit.files if item.record.labeller_id == labeller]
    if not selected:
        raise SchemaError(f"No audited Gaze-in-the-Wild files exist for labeller {labeller}.")
    selected.sort(
        key=lambda item: (
            item.record.participant_id,
            item.record.trial_id,
            item.record.path,
        )
    )
    identities = [(item.record.participant_id, item.record.trial_id) for item in selected]
    if len(identities) != len(set(identities)):
        raise BenchmarkIntegrityError(
            "Selected Gaze-in-the-Wild labeller contains duplicate participant/trial identities."
        )
    return selected


def _interpolate_adjacent(
    timestamps_ms: np.ndarray,
    values: np.ndarray,
    target_ms: np.ndarray,
    *,
    max_gap_ms: float,
) -> np.ndarray:
    """Interpolate only when the immediate bracketing source samples are finite."""
    source_t = np.asarray(timestamps_ms, dtype=float)
    source_v = np.asarray(values, dtype=float)
    target = np.asarray(target_ms, dtype=float)
    output = np.full(target.shape, np.nan, dtype=float)

    for index, time_ms in enumerate(target):
        right = int(np.searchsorted(source_t, time_ms, side="left"))
        if right < len(source_t) and np.isclose(
            source_t[right], time_ms, rtol=0.0, atol=1e-9
        ):
            if np.isfinite(source_v[right]):
                output[index] = source_v[right]
            continue
        left = right - 1
        if left < 0 or right >= len(source_t):
            continue
        gap = source_t[right] - source_t[left]
        if not np.isfinite(gap) or gap <= 0 or gap > max_gap_ms:
            continue
        if not np.isfinite(source_v[left]) or not np.isfinite(source_v[right]):
            continue
        weight = (time_ms - source_t[left]) / gap
        output[index] = source_v[left] + weight * (source_v[right] - source_v[left])
    return output


def _prepare_file(
    item: GazeInWildAuditedFile,
    *,
    target_sampling_rate_hz: float,
    min_label_purity: float,
    max_coordinate_gap_factor: float,
    confidence_threshold: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source = item.gaze.data.sort_values("timestamp_ms", kind="stable").reset_index(drop=True)
    source_rate = float(item.gaze.sampling_rate_hz)
    target_rate = float(target_sampling_rate_hz)
    if target_rate > source_rate and not np.isclose(
        target_rate, source_rate, rtol=1e-6, atol=1e-6
    ):
        raise SchemaError(
            "Gaze-in-the-Wild preparation refuses upsampling: "
            f"{item.record.path!r} is {source_rate:.9g} Hz but the requested common "
            f"analysis rate is {target_rate:.9g} Hz."
        )

    if np.isclose(target_rate, source_rate, rtol=1e-6, atol=1e-6):
        prepared = source.copy()
        prepared["benchmark_label_purity"] = 1.0
        prepared["benchmark_label_source_samples"] = 1
        prepared["benchmark_label_ambiguous"] = False
        resampling_report: dict[str, Any] | None = None
        sampling_origin = "native"
    else:
        resampled = resample_labeled_gaze(
            source,
            target_sampling_rate_hz=target_rate,
            continuous_cols=(),
            carry_cols=("annotator", "dataset_id", "source_file"),
            min_label_purity=float(min_label_purity),
            source_sampling_rate_hz=source_rate,
        )
        prepared = resampled.data
        source_t = pd.to_numeric(source["timestamp_ms"], errors="coerce").to_numpy(dtype=float)
        target_t = pd.to_numeric(
            prepared["timestamp_ms"], errors="coerce"
        ).to_numpy(dtype=float)
        source_period_ms = 1000.0 / source_rate
        gap_limit_ms = float(max_coordinate_gap_factor) * source_period_ms
        for column in ("x_px", "y_px", "confidence"):
            values = pd.to_numeric(source[column], errors="coerce").to_numpy(dtype=float)
            prepared[column] = _interpolate_adjacent(
                source_t,
                values,
                target_t,
                max_gap_ms=gap_limit_ms,
            )
        prepared["validity"] = (
            np.isfinite(prepared["x_px"].to_numpy(dtype=float))
            & np.isfinite(prepared["y_px"].to_numpy(dtype=float))
            & np.isfinite(prepared["confidence"].to_numpy(dtype=float))
            & (prepared["confidence"].to_numpy(dtype=float) >= float(confidence_threshold))
        )
        resampling_report = dict(resampled.report)
        resampling_report["coordinate_interpolation"] = (
            "linear_immediate_finite_brackets_only"
        )
        resampling_report["max_coordinate_gap_ms"] = gap_limit_ms
        resampling_report["invalid_source_samples_are_not_bridged"] = True
        sampling_origin = "resampled"

    prepared["human_labeller_id"] = int(item.record.labeller_id)
    prepared["source_label_path"] = item.record.path
    prepared["source_process_path"] = item.record.process_path
    prepared["source_file_sampling_rate_hz"] = source_rate
    prepared["analysis_sampling_rate_hz"] = target_rate
    prepared["source_audit_report_fingerprint_sha256"] = item.gaze.metadata[
        "source_audit_report_fingerprint_sha256"
    ]
    prepared["source_audit_spec_fingerprint_sha256"] = item.gaze.metadata[
        "source_audit_spec_fingerprint_sha256"
    ]

    return prepared, {
        "participant_id": item.record.participant_id,
        "trial_id": item.record.trial_id,
        "labeller_id": int(item.record.labeller_id),
        "label_path": item.record.path,
        "process_path": item.record.process_path,
        "source_sampling_rate_hz": source_rate,
        "analysis_sampling_rate_hz": target_rate,
        "sampling_origin": sampling_origin,
        "source_rows": int(len(source)),
        "prepared_rows": int(len(prepared)),
        "resampling": resampling_report,
    }


def _attach_task_mapping(
    data: pd.DataFrame,
    task_mapping: pd.DataFrame,
    *,
    task_col: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = [*_TASK_COLUMNS, task_col]
    missing = [column for column in required if column not in task_mapping.columns]
    if missing:
        raise SchemaError(f"Gaze-in-the-Wild task mapping requires columns: {missing}")
    mapping = task_mapping[required].copy()
    if mapping[required].isna().any().any():
        raise SchemaError("Gaze-in-the-Wild task mapping cannot contain missing values.")
    for column in required:
        mapping[column] = mapping[column].astype(str).str.strip()
        if mapping[column].eq("").any():
            raise SchemaError("Gaze-in-the-Wild task mapping cannot contain empty values.")
    if mapping.duplicated(list(_TASK_COLUMNS)).any():
        raise SchemaError(
            "Gaze-in-the-Wild task mapping must contain one row per participant/trial."
        )

    selected = {
        (str(participant), str(trial))
        for participant, trial in data[list(_TASK_COLUMNS)].drop_duplicates().itertuples(
            index=False, name=None
        )
    }
    mapped = {
        (str(participant), str(trial))
        for participant, trial in mapping[list(_TASK_COLUMNS)].itertuples(index=False, name=None)
    }
    missing_identities = sorted(selected - mapped)
    extra_identities = sorted(mapped - selected)
    if missing_identities or extra_identities:
        raise SchemaError(
            "Gaze-in-the-Wild task mapping must exactly cover the selected audited trials: "
            f"missing={missing_identities}, extra={extra_identities}."
        )
    attached = data.merge(
        mapping,
        on=list(_TASK_COLUMNS),
        how="left",
        validate="many_to_one",
    )
    records = (
        mapping.sort_values([*_TASK_COLUMNS, task_col], kind="stable")
        .reset_index(drop=True)
        .to_dict(orient="records")
    )
    return attached, {
        "task_col": task_col,
        "mapping_rows": len(records),
        "mapping_fingerprint_sha256": benchmark_fingerprint(records),
        "mapping": records,
        "task_labels": sorted(mapping[task_col].astype(str).unique()),
        "task_labels_inferred_from_filenames": False,
    }


def prepare_gaze_in_wild_benchmark(
    audit: GazeInWildSourceAuditRun,
    *,
    labeller_id: int,
    target_sampling_rate_hz: float = 60.0,
    min_label_purity: float = 0.75,
    excluded_labels: tuple[str, ...] = _DEFAULT_EXCLUDED_LABELS,
    max_coordinate_gap_factor: float = 1.5,
    task_mapping: pd.DataFrame | None = None,
    task_col: str = "task_label",
) -> GazeInWildPreparedBenchmark:
    """Prepare one audited human labeller for leakage-safe event-model validation."""
    _verify_audit_integrity(audit)
    coordinates = audit.report.get("coordinates", {})
    if (
        coordinates.get("verified") is not True
        or str(coordinates.get("unit", "")).strip().lower() != "pixels"
        or coordinates.get("pixel_kinematics_compatible") is not True
    ):
        raise SchemaError(
            "Gaze-in-the-Wild pixel-kinematics modelling requires an audited pixel coordinate "
            "basis with pixel_kinematics_compatible=true."
        )
    target_rate = float(target_sampling_rate_hz)
    if not np.isfinite(target_rate) or target_rate <= 0:
        raise ValueError("target_sampling_rate_hz must be finite and positive.")
    purity = float(min_label_purity)
    if not np.isfinite(purity) or not 0.0 < purity <= 1.0:
        raise ValueError("min_label_purity must be in (0, 1].")
    gap_factor = float(max_coordinate_gap_factor)
    if not np.isfinite(gap_factor) or gap_factor < 1.0:
        raise ValueError("max_coordinate_gap_factor must be finite and at least 1.0.")

    selected = _selected_files(audit, labeller_id)
    file_parts: list[pd.DataFrame] = []
    file_reports: list[dict[str, Any]] = []
    for item in selected:
        part, report = _prepare_file(
            item,
            target_sampling_rate_hz=target_rate,
            min_label_purity=purity,
            max_coordinate_gap_factor=gap_factor,
            confidence_threshold=audit.spec.confidence_threshold,
        )
        file_parts.append(part)
        file_reports.append(report)

    prepared = pd.concat(file_parts, ignore_index=True)
    unknown_labels = sorted(
        label
        for label in prepared["event_label"].astype(str).str.lower().unique()
        if label.startswith("unknown_")
    )
    if unknown_labels:
        raise SchemaError(
            "Gaze-in-the-Wild contains event codes outside the supported audited taxonomy: "
            f"{unknown_labels}."
        )

    task_report: dict[str, Any] | None = None
    if task_mapping is not None:
        prepared, task_report = _attach_task_mapping(
            prepared,
            task_mapping,
            task_col=task_col,
        )

    labels_before = prepared["event_label"].fillna("unlabelled").astype(str).str.lower()
    excluded = {str(label).strip().lower() for label in excluded_labels}
    retained_mask = ~labels_before.isin(excluded)
    analysis = prepared.loc[retained_mask].copy().reset_index(drop=True)
    if analysis.empty:
        raise SchemaError("Gaze-in-the-Wild preparation excluded every modelling row.")
    if analysis["event_label"].nunique() < 2:
        raise SchemaError("Gaze-in-the-Wild preparation retained fewer than two event classes.")
    participant_count = int(analysis["participant_id"].astype(str).nunique())
    if participant_count < 2:
        raise SchemaError(
            "Gaze-in-the-Wild participant-held-out validation requires at least two participants."
        )

    source_rates = sorted(
        {float(report["source_sampling_rate_hz"]) for report in file_reports}
    )
    origins = {str(report["sampling_origin"]) for report in file_reports}
    sampling_origin = (
        "native" if origins == {"native"} else "resampled" if origins == {"resampled"} else "mixed"
    )
    reference_strength = (
        "human-reference" if sampling_origin == "native" else "derived-human-reference"
    )
    audit_fingerprint = str(audit.report["report_fingerprint_sha256"])
    spec_fingerprint = str(audit.report["spec_fingerprint_sha256"])
    ambiguous_rows = int(prepared["benchmark_label_ambiguous"].astype(bool).sum())
    preparation_report: dict[str, Any] = {
        "dataset": audit.spec.dataset_name,
        "labeller_id": int(labeller_id),
        "source_audit_report_fingerprint_sha256": audit_fingerprint,
        "source_audit_spec_fingerprint_sha256": spec_fingerprint,
        "label_manifest_fingerprint_sha256": audit.report["label_inventory"][
            "manifest_fingerprint_sha256"
        ],
        "process_manifest_fingerprint_sha256": audit.report["process_inventory"][
            "manifest_fingerprint_sha256"
        ],
        "coordinate_unit": audit.spec.coordinate_unit,
        "pixel_kinematics_compatible": audit.spec.pixel_kinematics_compatible,
        "source_sampling_rates_hz": source_rates,
        "analysis_sampling_rate_hz": target_rate,
        "sampling_origin": sampling_origin,
        "min_label_purity": purity,
        "max_coordinate_gap_factor": gap_factor,
        "source_rows": int(sum(report["source_rows"] for report in file_reports)),
        "prepared_rows_before_exclusions": int(len(prepared)),
        "analysis_rows": int(len(analysis)),
        "excluded_rows": int((~retained_mask).sum()),
        "excluded_labels": sorted(excluded),
        "ambiguous_rows": ambiguous_rows,
        "ambiguous_fraction": float(ambiguous_rows / len(prepared)),
        "participant_count": participant_count,
        "participant_trial_count": int(
            analysis[list(_TASK_COLUMNS)].drop_duplicates().shape[0]
        ),
        "label_counts_before_exclusions": labels_before.value_counts().sort_index().to_dict(),
        "label_counts_analysis": (
            analysis["event_label"].astype(str).value_counts().sort_index().to_dict()
        ),
        "files": file_reports,
        "task_mapping": task_report,
        "claim_limits": [
            "The selected human labeller is an explicit reference stream, not ground truth.",
            "Files are never upsampled; any lower-rate preparation is explicitly derived.",
            "Published 120 Hz hardware provenance is not substituted for timestamp-inferred file rates.",
            "Task labels are used only when an explicit complete mapping is supplied.",
            "This validation is not Gazepoint GP3-specific evidence.",
        ],
    }
    card = BenchmarkDatasetCard(
        name=f"{audit.spec.dataset_name}-labeller-{int(labeller_id)}",
        version=audit.spec.dataset_version,
        source=audit.spec.source,
        license=audit.spec.license,
        task="participant-held-out naturalistic eye-event classification",
        sampling_rates_hz=[target_rate],
        participant_count=participant_count,
        stimulus_count=int(analysis[list(_TASK_COLUMNS)].drop_duplicates().shape[0]),
        split_unit="participant_id",
        validation_scope="audited-source-participant-held-out-model-validation",
        annotation_origin="human-manual",
        sampling_origin=sampling_origin,
        reference_strength=reference_strength,
        human_annotator_count=1,
        reference_description=(
            f"Human manual labels from audited Gaze-in-the-Wild labeller {int(labeller_id)}."
        ),
        notes=[
            "One audited labeller is selected explicitly before modelling.",
            "Participant identity is the protected cross-validation split unit.",
            "Pixel-space kinematics are allowed only after an explicit source-audit compatibility gate.",
            "Per-file cadence is preserved as provenance before any declared downsampling.",
        ],
    )
    return GazeInWildPreparedBenchmark(
        data=analysis,
        dataset_card=card,
        preparation_report=preparation_report,
    )


def _sample_class_sensitivity(predictions: pd.DataFrame, *, label_col: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for model, part in predictions.groupby("comparison_model", sort=True):
        truth = part[label_col].astype(str)
        predicted = part["predicted_event"].astype(str)
        labels = sorted(truth.unique())
        precision, recall, f1, support = precision_recall_fscore_support(
            truth,
            predicted,
            labels=labels,
            zero_division=0,
        )
        for label, p_value, r_value, f_value, n_value in zip(
            labels, precision, recall, f1, support, strict=True
        ):
            rows.append(
                {
                    "model": str(model),
                    "event_label": str(label),
                    "precision": float(p_value),
                    "recall": float(r_value),
                    "f1": float(f_value),
                    "support": int(n_value),
                }
            )
    return pd.DataFrame(rows)


def _event_class_sensitivity(
    predictions: pd.DataFrame,
    *,
    sampling_rate_hz: float,
    event_min_iou: float,
    event_excluded_labels: tuple[str, ...],
) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for model, part in predictions.groupby("comparison_model", sort=True):
        evaluation = evaluate_sample_event_predictions(
            part,
            true_label_col="event_label",
            predicted_label_col="predicted_event",
            group_cols=("participant_id", "trial_id"),
            sampling_rate_hz=float(sampling_rate_hz),
            excluded_labels=event_excluded_labels,
            min_iou=float(event_min_iou),
        )
        table = evaluation.per_class.copy()
        table.insert(0, "model", str(model))
        parts.append(table)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def run_gaze_in_wild_model_validation(
    audit: GazeInWildSourceAuditRun,
    *,
    labeller_id: int,
    target_sampling_rate_hz: float = 60.0,
    min_label_purity: float = 0.75,
    excluded_labels: tuple[str, ...] = _DEFAULT_EXCLUDED_LABELS,
    max_coordinate_gap_factor: float = 1.5,
    task_mapping: pd.DataFrame | None = None,
    task_col: str = "task_label",
    n_splits: int = 5,
    ivt_velocity_threshold_px_s: float = 1000.0,
    min_confidence: float = 0.0,
    random_state: int = 42,
    n_estimators: int = 200,
    context_radius_ms: float = 50.0,
    rolling_window_ms: float = 80.0,
    hidden_layer_sizes: tuple[int, ...] = (64, 32),
    temporal_solver: str = "adam",
    temporal_max_iter: int = 200,
    calibration_bins: int = 10,
    event_min_iou: float = 0.50,
) -> GazeInWildModelValidationRun:
    """Run participant-disjoint I-VT/RF/ContextMLP validation on audited Gaze-in-the-Wild."""
    prepared = prepare_gaze_in_wild_benchmark(
        audit,
        labeller_id=labeller_id,
        target_sampling_rate_hz=target_sampling_rate_hz,
        min_label_purity=min_label_purity,
        excluded_labels=excluded_labels,
        max_coordinate_gap_factor=max_coordinate_gap_factor,
        task_mapping=task_mapping,
        task_col=task_col,
    )
    participant_count = int(prepared.data["participant_id"].astype(str).nunique())
    folds = min(int(n_splits), participant_count)
    if folds < 2:
        raise SchemaError(
            "At least two participant-held-out folds are required for Gaze-in-the-Wild validation."
        )
    threshold = float(ivt_velocity_threshold_px_s)
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("ivt_velocity_threshold_px_s must be finite and positive.")

    event_excluded = tuple(sorted({str(value).strip().lower() for value in excluded_labels}))
    comparison = compare_event_models_grouped(
        prepared.data,
        label_col="event_label",
        group_col="participant_id",
        n_splits=folds,
        sampling_rate_hz=float(target_sampling_rate_hz),
        ivt_velocity_threshold_px_s=threshold,
        ivt_velocity_threshold_deg_s=None,
        min_confidence=float(min_confidence),
        random_state=int(random_state),
        n_estimators=int(n_estimators),
        context_radius_ms=float(context_radius_ms),
        rolling_window_ms=float(rolling_window_ms),
        hidden_layer_sizes=hidden_layer_sizes,
        temporal_solver=temporal_solver,
        temporal_max_iter=int(temporal_max_iter),
        calibration_bins=int(calibration_bins),
        include_event_level_metrics=True,
        event_group_cols=("participant_id", "trial_id"),
        event_min_iou=float(event_min_iou),
        event_excluded_labels=event_excluded,
    )
    paired = paired_model_metric_differences(comparison.fold_metrics)
    sample_class = _sample_class_sensitivity(comparison.predictions, label_col="event_label")
    event_class = _event_class_sensitivity(
        comparison.predictions,
        sampling_rate_hz=float(target_sampling_rate_hz),
        event_min_iou=float(event_min_iou),
        event_excluded_labels=event_excluded,
    )

    task_performance: StratifiedEventPerformance | None = None
    if task_mapping is not None:
        task_performance = summarize_event_predictions_by_stratum(
            comparison.predictions,
            stratify_col=task_col,
            sampling_rate_hz=float(target_sampling_rate_hz),
            calibration_bins=int(comparison.design["calibration_bins"]),
            include_event_level_metrics=True,
            event_group_cols=("participant_id", "trial_id"),
            event_min_iou=float(event_min_iou),
            event_excluded_labels=event_excluded,
        )

    metrics: dict[str, Any] = {
        "summary": _json_safe_records(comparison.summary),
        "fold_metrics": _json_safe_records(comparison.fold_metrics),
        "paired_model_difference_summary": _json_safe_records(paired.summary),
        "paired_model_fold_deltas": _json_safe_records(paired.deltas),
        "sample_event_class_performance": _json_safe_records(sample_class),
        "event_class_performance": _json_safe_records(event_class),
        "analysis_label_counts": prepared.preparation_report["label_counts_analysis"],
        "task_summary": (
            [] if task_performance is None else _json_safe_records(task_performance.summary)
        ),
        "task_fold_metrics": (
            [] if task_performance is None else _json_safe_records(task_performance.fold_metrics)
        ),
    }
    protocol: dict[str, Any] = {
        "preparation": prepared.preparation_report,
        "comparison_design": comparison.design,
        "paired_model_difference_design": paired.design,
        "event_class_sensitivity": {
            "source": "fixed_out_of_fold_predictions",
            "models_refit_by_event_class": False,
            "inferential_p_values": False,
        },
        "task_sensitivity_design": (
            None if task_performance is None else task_performance.design
        ),
    }
    report = build_benchmark_report(
        benchmark=prepared.dataset_card,
        metrics=metrics,
        model={"models": comparison.design["models"]},
        protocol=protocol,
    )
    return GazeInWildModelValidationRun(
        prepared=prepared,
        comparison=comparison,
        paired_model_differences=paired,
        sample_event_class_performance=sample_class,
        event_class_performance=event_class,
        task_performance=task_performance,
        report=report,
    )
