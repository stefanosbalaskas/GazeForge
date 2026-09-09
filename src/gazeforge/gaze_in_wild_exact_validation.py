"""Exact-distribution participant-disjoint validation for Gaze-in-the-Wild."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.io import loadmat

from .benchmarks import BenchmarkDatasetCard, benchmark_fingerprint, build_benchmark_report
from .comparison import EventModelComparison, compare_event_models_grouped
from .exceptions import BenchmarkIntegrityError, SchemaError
from .gaze_in_wild import _field, load_gaze_in_wild_mat
from .gaze_in_wild_processdata_preflight import preflight_gaze_in_wild_processdata
from .gaze_in_wild_validation import (
    _event_class_sensitivity,
    _interpolate_adjacent,
    _json_safe_records,
    _sample_class_sensitivity,
)
from .paired import PairedModelDifferences, paired_model_metric_differences
from .resampling import resample_labeled_gaze

REFERENCE_MANIFEST_TYPE = "gaze-in-wild-exact-model-reference-manifest-v1"
EXECUTION_PROTOCOL_TYPE = "gaze-in-wild-exact-model-execution-protocol-evidence-v1"
REFERENCE_MANIFEST_FINGERPRINT = (
    "5688c283d5f1a199ef760994b4df655e42e4f27c4dd767cfb54760a4aa6816f9"
)
EXECUTION_PROTOCOL_FINGERPRINT = (
    "e07ad1c15b8964e6e012e05d37b6eb989f36380ffdf307590b36273b5f8485e5"
)
EXPECTED_PROCESS_STRUCTURE_EVIDENCE = (
    "cffcc8a10d176cc5eb8c15c080cf450e3e1b1404ced00ea8907cdd4ee3c3517f"
)
EXPECTED_POR_SEMANTICS_EVIDENCE = (
    "5eb245979385283571d6d9a5dda9a5d74dea6c00165bbe3a2587fcfa80e9adfb"
)
EXPECTED_REFERENCE_PREFLIGHT_EVIDENCE = (
    "aff7b7b1576b9a1eee6a774183ba4f8404052226cdcb984a4112120bbc5bea67"
)
_EXPECTED_SCENE = (1920, 1080)
_EXPECTED_LABELLER = 5
_EXPECTED_PARTICIPANTS = 12
_EXPECTED_RECORDINGS = 18
_EXPECTED_SOURCE_SAMPLES = 1_590_659


@dataclass(slots=True)
class GazeInWildExactPreparedBenchmark:
    """Derived 60-Hz benchmark assembled from exact original-distribution pairs."""

    data: pd.DataFrame
    dataset_card: BenchmarkDatasetCard
    preparation_report: dict[str, Any]


@dataclass(slots=True)
class GazeInWildExactValidationRun:
    """Participant-disjoint model comparison and fixed-OOF sensitivity outputs."""

    prepared: GazeInWildExactPreparedBenchmark
    comparison: EventModelComparison
    paired_model_differences: PairedModelDifferences
    sample_event_class_performance: pd.DataFrame
    event_class_performance: pd.DataFrame
    report: dict[str, Any]
    split_integrity: dict[str, Any]


def _validated_evidence(
    payload: Mapping[str, Any],
    *,
    record_type: str,
    fingerprint: str,
) -> dict[str, Any]:
    record = dict(payload)
    if record.get("record_type") != record_type:
        raise BenchmarkIntegrityError(f"Unexpected GIW exact evidence type: {record_type}.")
    stored = str(record.pop("evidence_fingerprint_sha256", ""))
    if stored != fingerprint or benchmark_fingerprint(record) != fingerprint:
        raise BenchmarkIntegrityError(f"GIW exact evidence fingerprint drifted: {record_type}.")
    record["evidence_fingerprint_sha256"] = stored
    return record


def validate_exact_reference_manifest(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the frozen pre-performance selected-reference manifest."""
    record = _validated_evidence(
        payload,
        record_type=REFERENCE_MANIFEST_TYPE,
        fingerprint=REFERENCE_MANIFEST_FINGERPRINT,
    )
    selected = record.get("selected_reference")
    if not isinstance(selected, Mapping):
        raise BenchmarkIntegrityError("GIW exact reference manifest lacks selected_reference.")
    expected = {
        "labeller_id": _EXPECTED_LABELLER,
        "participant_count": _EXPECTED_PARTICIPANTS,
        "recording_count": _EXPECTED_RECORDINGS,
        "file_count": _EXPECTED_RECORDINGS,
        "total_samples": _EXPECTED_SOURCE_SAMPLES,
    }
    for key, value in expected.items():
        if selected.get(key) != value:
            raise BenchmarkIntegrityError(f"GIW exact reference manifest {key} drifted.")
    if selected.get("observed_label_codes") != [0, 1, 2, 3, 4, 5]:
        raise BenchmarkIntegrityError("GIW exact reference label-code support drifted.")
    files = selected.get("files")
    if not isinstance(files, list) or len(files) != _EXPECTED_RECORDINGS:
        raise BenchmarkIntegrityError("GIW exact reference requires exactly 18 file rows.")
    participants = {str(row.get("participant_token")) for row in files if isinstance(row, Mapping)}
    recordings = {str(row.get("recording_token")) for row in files if isinstance(row, Mapping)}
    if len(participants) != _EXPECTED_PARTICIPANTS or len(recordings) != _EXPECTED_RECORDINGS:
        raise BenchmarkIntegrityError("GIW exact reference participant/recording coverage drifted.")
    if any(
        not isinstance(row, Mapping)
        or row.get("labeller_id") != _EXPECTED_LABELLER
        or row.get("raw_bytes_retained") is not False
        for row in files
    ):
        raise BenchmarkIntegrityError("GIW exact reference file-row boundary drifted.")
    boundary = record.get("scientific_boundary")
    if not isinstance(boundary, Mapping) or boundary.get("reference_manifest_frozen") is not True:
        raise BenchmarkIntegrityError("GIW exact reference manifest is not frozen.")
    for key in (
        "participant_disjoint_model_validation_created",
        "task_stratified_model_validation_created",
        "complete_file_to_publication_task_mapping_verified",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "quarantine_exit_authorized",
        "new_empirical_performance_claim_created",
    ):
        if boundary.get(key) is not False:
            raise BenchmarkIntegrityError(f"GIW reference manifest must keep {key}=false.")
    return record


def validate_exact_execution_protocol(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the final pre-fit exact-distribution execution protocol."""
    record = _validated_evidence(
        payload,
        record_type=EXECUTION_PROTOCOL_TYPE,
        fingerprint=EXECUTION_PROTOCOL_FINGERPRINT,
    )
    parent = record.get("parent_evidence")
    if not isinstance(parent, Mapping):
        raise BenchmarkIntegrityError("GIW exact execution protocol lacks parent evidence.")
    expected_parent = {
        "model_reference_preflight_evidence_fingerprint_sha256": (
            EXPECTED_REFERENCE_PREFLIGHT_EVIDENCE
        ),
        "exact_processdata_structure_evidence_fingerprint_sha256": (
            EXPECTED_PROCESS_STRUCTURE_EVIDENCE
        ),
        "por_coordinate_semantics_evidence_fingerprint_sha256": (
            EXPECTED_POR_SEMANTICS_EVIDENCE
        ),
    }
    for key, value in expected_parent.items():
        if parent.get(key) != value:
            raise BenchmarkIntegrityError(f"GIW exact execution parent {key} drifted.")
    protocol = record.get("execution_protocol")
    if not isinstance(protocol, Mapping):
        raise BenchmarkIntegrityError("GIW exact execution protocol is missing.")
    exact_values = {
        "selected_labeller_id": 5,
        "selected_participant_count": 12,
        "selected_recording_count": 18,
        "task_mapping_used": False,
        "task_stratified_validation_authorized": False,
        "source_confidence_threshold": 0.3,
        "analysis_sampling_rate_hz": 60.0,
        "min_label_purity": 0.75,
        "max_coordinate_gap_factor": 1.5,
        "n_splits": 5,
        "group_splitter": "GroupKFold",
        "ivt_velocity_threshold_px_s": 1000.0,
        "model_min_confidence": 0.0,
        "random_state": 42,
        "random_forest_n_estimators": 200,
        "context_radius_ms": 50.0,
        "rolling_window_ms": 80.0,
        "temporal_solver": "adam",
        "temporal_max_iter": 200,
        "calibration_bins": 10,
        "event_min_iou": 0.5,
        "models_refit_by_event_class": False,
        "raw_mat_retention_authorized": False,
    }
    for key, value in exact_values.items():
        if protocol.get(key) != value:
            raise BenchmarkIntegrityError(f"GIW exact execution protocol {key} drifted.")
    if protocol.get("models") != ["I-VT", "RandomForest", "ContextMLP"]:
        raise BenchmarkIntegrityError("GIW exact execution model family drifted.")
    if protocol.get("hidden_layer_sizes") != [64, 32]:
        raise BenchmarkIntegrityError("GIW exact execution MLP topology drifted.")
    if protocol.get("scene_resolution_px") != [1920, 1080]:
        raise BenchmarkIntegrityError("GIW exact execution scene resolution drifted.")
    if protocol.get("label_process_timestamp_vector_alignment_required") != (
        "exact_numeric_vector_equality"
    ):
        raise BenchmarkIntegrityError("GIW exact timestamp-alignment requirement drifted.")
    boundary = record.get("scientific_boundary")
    if not isinstance(boundary, Mapping):
        raise BenchmarkIntegrityError("GIW exact execution scientific boundary is missing.")
    if boundary.get("exact_distribution_model_execution_authorized") is not True:
        raise BenchmarkIntegrityError("GIW exact model execution is not authorized.")
    for key in (
        "participant_disjoint_model_validation_created",
        "task_stratified_model_validation_created",
        "complete_file_to_publication_task_mapping_verified",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "quarantine_exit_authorized",
        "new_empirical_performance_claim_created",
    ):
        if boundary.get(key) is not False:
            raise BenchmarkIntegrityError(f"GIW execution protocol must keep {key}=false.")
    return record


def _numeric_vector(value: Any, *, name: str) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=float).reshape(-1)
    except (TypeError, ValueError) as exc:
        raise SchemaError(f"GIW exact field {name!r} must be numeric.") from exc
    if array.size < 2 or np.any(~np.isfinite(array)):
        raise SchemaError(f"GIW exact field {name!r} must contain finite timestamps.")
    return array


def _mat_timestamp_vector(path: Path, variable: str) -> np.ndarray:
    raw = loadmat(path, squeeze_me=True, struct_as_record=False)
    if variable not in raw:
        raise SchemaError(f"{path.name} lacks MATLAB variable {variable!r}.")
    return _numeric_vector(_field(raw[variable], "T"), name=f"{variable}.T")


def _float64_sha(values: np.ndarray) -> str:
    stable = np.asarray(values, dtype="<f8")
    return benchmark_fingerprint(stable.tobytes(order="C").hex())


def _raw_float64_sha(values: np.ndarray) -> str:
    import hashlib

    stable = np.asarray(values, dtype="<f8")
    return hashlib.sha256(stable.tobytes(order="C")).hexdigest()


def prepare_exact_gaze_in_wild_recording(
    label_path: str | Path,
    process_path: str | Path,
    manifest_row: Mapping[str, Any],
    protocol_evidence: Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Verify one exact selected pair and derive its pre-registered 60-Hz view."""
    protocol_record = validate_exact_execution_protocol(protocol_evidence)
    protocol = protocol_record["execution_protocol"]
    label_file = Path(label_path)
    process_file = Path(process_path)
    if not label_file.is_file() or not process_file.is_file():
        raise FileNotFoundError(label_file if not label_file.is_file() else process_file)

    label_times = _mat_timestamp_vector(label_file, "LabelData")
    process_times = _mat_timestamp_vector(process_file, "ProcessData")
    if not np.array_equal(label_times, process_times):
        raise BenchmarkIntegrityError(
            f"GIW exact LabelData/ProcessData timestamps differ for {label_file.name}."
        )
    expected_timestamp_sha = str(manifest_row.get("timestamp_sha256_float64_le", ""))
    observed_timestamp_sha = _raw_float64_sha(label_times)
    if observed_timestamp_sha != expected_timestamp_sha:
        raise BenchmarkIntegrityError(
            f"GIW exact selected LabelData timestamp digest drifted for {label_file.name}."
        )

    participant = str(manifest_row.get("participant_token"))
    trial = str(manifest_row.get("trial_token"))
    process_name = str(manifest_row.get("process_filename"))
    if label_file.name != str(manifest_row.get("name")) or process_file.name != process_name:
        raise BenchmarkIntegrityError("GIW exact local filename/manifest binding drifted.")

    preflight = preflight_gaze_in_wild_processdata(process_file)
    if preflight.scene_resolution_px != _EXPECTED_SCENE:
        raise BenchmarkIntegrityError("GIW exact ProcessData scene resolution drifted.")
    expected_participant = int(participant.removeprefix("PrIdx_"))
    expected_trial = int(trial.removeprefix("TrIdx_"))
    if (
        preflight.participant_index != expected_participant
        or preflight.trial_index != expected_trial
    ):
        raise BenchmarkIntegrityError("GIW exact ProcessData internal identity drifted.")

    source_confidence = float(protocol["source_confidence_threshold"])
    gaze = load_gaze_in_wild_mat(
        label_file,
        process_path=process_file,
        participant_id=participant,
        trial_id=trial,
        confidence_threshold=source_confidence,
    )
    source = gaze.data.sort_values("timestamp_ms", kind="stable").reset_index(drop=True)
    source_rate = float(gaze.sampling_rate_hz)
    expected_rate = float(manifest_row.get("inferred_sampling_rate_hz"))
    if not np.isclose(source_rate, expected_rate, rtol=1e-12, atol=1e-12):
        raise BenchmarkIntegrityError("GIW exact selected LabelData inferred rate drifted.")

    target_rate = float(protocol["analysis_sampling_rate_hz"])
    resampled = resample_labeled_gaze(
        source,
        target_sampling_rate_hz=target_rate,
        continuous_cols=(),
        carry_cols=("annotator", "dataset_id", "source_file"),
        min_label_purity=float(protocol["min_label_purity"]),
        source_sampling_rate_hz=source_rate,
    )
    prepared = resampled.data
    source_t = source["timestamp_ms"].to_numpy(dtype=float)
    target_t = prepared["timestamp_ms"].to_numpy(dtype=float)
    gap_limit_ms = float(protocol["max_coordinate_gap_factor"]) * (1000.0 / source_rate)
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
        & (prepared["confidence"].to_numpy(dtype=float) >= source_confidence)
    )
    prepared["human_labeller_id"] = _EXPECTED_LABELLER
    prepared["source_label_path"] = label_file.name
    prepared["source_process_path"] = process_file.name
    prepared["source_file_sampling_rate_hz"] = source_rate
    prepared["analysis_sampling_rate_hz"] = target_rate
    prepared["reference_manifest_fingerprint_sha256"] = REFERENCE_MANIFEST_FINGERPRINT
    prepared["execution_protocol_fingerprint_sha256"] = EXECUTION_PROTOCOL_FINGERPRINT

    return prepared, {
        "participant_id": participant,
        "trial_id": trial,
        "labeller_id": _EXPECTED_LABELLER,
        "label_file": label_file.name,
        "process_file": process_file.name,
        "source_rows": int(len(source)),
        "prepared_rows": int(len(prepared)),
        "source_sampling_rate_hz": source_rate,
        "analysis_sampling_rate_hz": target_rate,
        "source_confidence_threshold": source_confidence,
        "label_process_timestamp_vector_exactly_equal": True,
        "timestamp_sha256_float64_le": observed_timestamp_sha,
        "scene_resolution_px": list(_EXPECTED_SCENE),
        "coordinate_conversion": "normalized_scene_por_to_pixels",
        "resampling": resampled.report,
        "max_coordinate_gap_ms": gap_limit_ms,
        "invalid_source_samples_are_not_bridged": True,
        "raw_bytes_retained_by_preparation": False,
    }


def assemble_exact_gaze_in_wild_benchmark(
    parts: Sequence[pd.DataFrame],
    file_reports: Sequence[Mapping[str, Any]],
    reference_manifest: Mapping[str, Any],
    protocol_evidence: Mapping[str, Any],
) -> GazeInWildExactPreparedBenchmark:
    """Assemble selected recording views and apply the pre-registered exclusions."""
    manifest_record = validate_exact_reference_manifest(reference_manifest)
    protocol_record = validate_exact_execution_protocol(protocol_evidence)
    if len(parts) != _EXPECTED_RECORDINGS or len(file_reports) != _EXPECTED_RECORDINGS:
        raise BenchmarkIntegrityError("GIW exact preparation requires all 18 selected recordings.")
    prepared = pd.concat(list(parts), ignore_index=True)
    labels_before = prepared["event_label"].fillna("unlabelled").astype(str).str.lower()
    unknown = sorted(label for label in labels_before.unique() if label.startswith("unknown_"))
    if unknown:
        raise SchemaError(f"GIW exact preparation found unsupported label codes: {unknown}.")
    excluded = {
        str(value).strip().lower()
        for value in protocol_record["execution_protocol"]["excluded_event_labels"]
    }
    retained = ~labels_before.isin(excluded)
    analysis = prepared.loc[retained].copy().reset_index(drop=True)
    if analysis.empty or analysis["event_label"].nunique() < 2:
        raise SchemaError("GIW exact preparation retained insufficient event classes.")
    participant_count = int(analysis["participant_id"].astype(str).nunique())
    recording_count = int(
        analysis[["participant_id", "trial_id"]].drop_duplicates().shape[0]
    )
    if participant_count != _EXPECTED_PARTICIPANTS or recording_count != _EXPECTED_RECORDINGS:
        raise BenchmarkIntegrityError("GIW exact prepared participant/recording coverage drifted.")
    if not all(
        bool(report.get("label_process_timestamp_vector_exactly_equal")) for report in file_reports
    ):
        raise BenchmarkIntegrityError("GIW exact timestamp pairing is incomplete.")

    target_rate = float(protocol_record["execution_protocol"]["analysis_sampling_rate_hz"])
    preparation_report: dict[str, Any] = {
        "dataset": "Gaze-in-the-Wild",
        "distribution": "official original Figshare ProcessData + LabelData",
        "selected_labeller_id": _EXPECTED_LABELLER,
        "reference_manifest_fingerprint_sha256": REFERENCE_MANIFEST_FINGERPRINT,
        "execution_protocol_fingerprint_sha256": EXECUTION_PROTOCOL_FINGERPRINT,
        "source_process_structure_evidence_fingerprint_sha256": (
            EXPECTED_PROCESS_STRUCTURE_EVIDENCE
        ),
        "por_coordinate_semantics_evidence_fingerprint_sha256": (
            EXPECTED_POR_SEMANTICS_EVIDENCE
        ),
        "analysis_sampling_rate_hz": target_rate,
        "sampling_origin": "resampled",
        "reference_strength": "derived-human-reference",
        "source_confidence_threshold": float(
            protocol_record["execution_protocol"]["source_confidence_threshold"]
        ),
        "min_label_purity": float(protocol_record["execution_protocol"]["min_label_purity"]),
        "participant_count": participant_count,
        "participant_trial_count": recording_count,
        "source_rows": int(sum(int(report["source_rows"]) for report in file_reports)),
        "prepared_rows_before_exclusions": int(len(prepared)),
        "analysis_rows": int(len(analysis)),
        "excluded_rows": int((~retained).sum()),
        "excluded_labels": sorted(excluded),
        "label_counts_before_exclusions": labels_before.value_counts().sort_index().to_dict(),
        "label_counts_analysis": (
            analysis["event_label"].astype(str).value_counts().sort_index().to_dict()
        ),
        "all_label_process_timestamp_vectors_exactly_equal": True,
        "task_mapping": None,
        "task_mapping_used": False,
        "files": [dict(report) for report in file_reports],
        "claim_limits": [
            "Labeller 5 is a pre-registered human reference stream, not ground truth.",
            "The 60-Hz benchmark is derived from exact processed timestamp grids.",
            "PrIdx and TrIdx are distribution-native identity tokens; task names are not inferred.",
            "The result is not Gazepoint GP3-specific validation.",
        ],
    }
    card = BenchmarkDatasetCard(
        name="Gaze-in-the-Wild-exact-labeller-5",
        version="Figshare original publication distribution v1",
        source="10.6084/m9.figshare.11673645.v1 + 10.6084/m9.figshare.11673696.v1",
        license="CC BY 4.0",
        task="participant-held-out naturalistic eye-event classification",
        sampling_rates_hz=[target_rate],
        participant_count=participant_count,
        stimulus_count=recording_count,
        split_unit="participant_id",
        validation_scope="exact-distribution-task-agnostic-participant-held-out-model-validation",
        annotation_origin="human-manual",
        sampling_origin="resampled",
        reference_strength="derived-human-reference",
        human_annotator_count=1,
        reference_description="Pre-registered distributed human labeller 5 reference stream.",
        notes=[
            "Reference labeller selected before model execution by participant/recording coverage.",
            "Every selected LabelData/ProcessData timestamp vector must match exactly.",
            "Participant identity is the protected cross-validation split unit.",
            "No publication task-name mapping is used or inferred.",
        ],
    )
    source = manifest_record["selected_reference"]
    if int(source["total_samples"]) != _EXPECTED_SOURCE_SAMPLES:
        raise BenchmarkIntegrityError("GIW exact frozen selected-source sample count drifted.")
    return GazeInWildExactPreparedBenchmark(
        data=analysis,
        dataset_card=card,
        preparation_report=preparation_report,
    )


def _split_integrity(predictions: pd.DataFrame) -> dict[str, Any]:
    reference = predictions.loc[
        predictions["comparison_model"].eq("I-VT"),
        ["validation_fold", "participant_id", "comparison_row_position"],
    ].copy()
    if reference["comparison_row_position"].duplicated().any():
        raise BenchmarkIntegrityError("GIW exact OOF rows repeat within the reference model.")
    participant_folds = reference.groupby("participant_id")["validation_fold"].nunique()
    if not participant_folds.eq(1).all():
        raise BenchmarkIntegrityError("GIW exact participant appears in multiple held-out folds.")
    model_counts = predictions.groupby("comparison_model")["comparison_row_position"].nunique()
    if model_counts.nunique() != 1 or int(model_counts.iloc[0]) != len(reference):
        raise BenchmarkIntegrityError("GIW exact models do not share identical OOF row coverage.")
    assignments = (
        reference[["validation_fold", "participant_id"]]
        .drop_duplicates()
        .sort_values(["validation_fold", "participant_id"], kind="stable")
    )
    return {
        "group_col": "participant_id",
        "participant_disjoint": True,
        "all_models_share_identical_oof_rows": True,
        "oof_row_count_per_model": int(len(reference)),
        "participant_count": int(reference["participant_id"].nunique()),
        "fold_count": int(reference["validation_fold"].nunique()),
        "fold_participant_assignments": _json_safe_records(assignments),
    }


def run_exact_gaze_in_wild_model_validation(
    prepared: GazeInWildExactPreparedBenchmark,
    protocol_evidence: Mapping[str, Any],
) -> GazeInWildExactValidationRun:
    """Run the locked task-agnostic participant-disjoint validation protocol."""
    protocol_record = validate_exact_execution_protocol(protocol_evidence)
    protocol = protocol_record["execution_protocol"]
    comparison = compare_event_models_grouped(
        prepared.data,
        label_col="event_label",
        group_col="participant_id",
        n_splits=int(protocol["n_splits"]),
        sampling_rate_hz=float(protocol["analysis_sampling_rate_hz"]),
        ivt_velocity_threshold_px_s=float(protocol["ivt_velocity_threshold_px_s"]),
        ivt_velocity_threshold_deg_s=None,
        min_confidence=float(protocol["model_min_confidence"]),
        random_state=int(protocol["random_state"]),
        n_estimators=int(protocol["random_forest_n_estimators"]),
        context_radius_ms=float(protocol["context_radius_ms"]),
        rolling_window_ms=float(protocol["rolling_window_ms"]),
        hidden_layer_sizes=tuple(int(value) for value in protocol["hidden_layer_sizes"]),
        temporal_solver=str(protocol["temporal_solver"]),
        temporal_max_iter=int(protocol["temporal_max_iter"]),
        calibration_bins=int(protocol["calibration_bins"]),
        include_event_level_metrics=True,
        event_group_cols=("participant_id", "trial_id"),
        event_min_iou=float(protocol["event_min_iou"]),
        event_excluded_labels=tuple(str(value) for value in protocol["excluded_event_labels"]),
    )
    split_integrity = _split_integrity(comparison.predictions)
    paired = paired_model_metric_differences(comparison.fold_metrics)
    sample_class = _sample_class_sensitivity(comparison.predictions, label_col="event_label")
    event_class = _event_class_sensitivity(
        comparison.predictions,
        sampling_rate_hz=float(protocol["analysis_sampling_rate_hz"]),
        event_min_iou=float(protocol["event_min_iou"]),
        event_excluded_labels=tuple(str(value) for value in protocol["excluded_event_labels"]),
    )
    metrics: dict[str, Any] = {
        "summary": _json_safe_records(comparison.summary),
        "fold_metrics": _json_safe_records(comparison.fold_metrics),
        "paired_model_difference_summary": _json_safe_records(paired.summary),
        "paired_model_fold_deltas": _json_safe_records(paired.deltas),
        "sample_event_class_performance": _json_safe_records(sample_class),
        "event_class_performance": _json_safe_records(event_class),
        "analysis_label_counts": prepared.preparation_report["label_counts_analysis"],
        "task_summary": [],
        "task_fold_metrics": [],
    }
    report = build_benchmark_report(
        benchmark=prepared.dataset_card,
        metrics=metrics,
        model={"models": list(protocol["models"])},
        protocol={
            "preparation": prepared.preparation_report,
            "comparison_design": comparison.design,
            "paired_model_difference_design": paired.design,
            "event_class_sensitivity": {
                "source": "fixed_out_of_fold_predictions",
                "models_refit_by_event_class": False,
                "inferential_p_values": False,
            },
            "task_sensitivity_design": None,
            "split_integrity": split_integrity,
            "execution_protocol_fingerprint_sha256": EXECUTION_PROTOCOL_FINGERPRINT,
        },
    )
    return GazeInWildExactValidationRun(
        prepared=prepared,
        comparison=comparison,
        paired_model_differences=paired,
        sample_event_class_performance=sample_class,
        event_class_performance=event_class,
        report=report,
        split_integrity=split_integrity,
    )
