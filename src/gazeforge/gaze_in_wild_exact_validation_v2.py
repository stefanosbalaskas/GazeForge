"""Convergence-qualified GIW exact participant-disjoint model validation."""

from __future__ import annotations

import warnings
from collections.abc import Mapping
from typing import Any

from sklearn.exceptions import ConvergenceWarning

from .benchmarks import benchmark_fingerprint, build_benchmark_report
from .comparison import compare_event_models_grouped
from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_exact_validation import (
    EXECUTION_PROTOCOL_FINGERPRINT,
    GazeInWildExactPreparedBenchmark,
    GazeInWildExactValidationRun,
    _split_integrity,
)
from .gaze_in_wild_validation import (
    _event_class_sensitivity,
    _json_safe_records,
    _sample_class_sensitivity,
)
from .paired import paired_model_metric_differences

EXECUTION_PROTOCOL_V2_TYPE = "gaze-in-wild-exact-model-execution-protocol-evidence-v2"
EXECUTION_PROTOCOL_V2_FINGERPRINT = (
    "a81df34f66f9fd35a28195f768a959d55d57a8f449a916e671355c07de910e66"
)
DISCOVERY_V1_FINGERPRINT = (
    "75834affeee6ab18da640256bea7b010d6fe45cc71178bc8f12a61f65f42772c"
)
DISCOVERY_V1_REPORT_FINGERPRINT = (
    "b642ce8707b9ebb5ec453fc81e666160b31e7dc3d5f388cdcb3d5bf936d5ca2e"
)


def validate_exact_execution_protocol_v2(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the convergence-only post-discovery protocol amendment."""
    record = dict(payload)
    stored = str(record.pop("evidence_fingerprint_sha256", ""))
    if record.get("record_type") != EXECUTION_PROTOCOL_V2_TYPE:
        raise BenchmarkIntegrityError("Unexpected GIW exact execution protocol v2 type.")
    if stored != EXECUTION_PROTOCOL_V2_FINGERPRINT:
        raise BenchmarkIntegrityError("GIW exact execution protocol v2 fingerprint drifted.")
    if benchmark_fingerprint(record) != EXECUTION_PROTOCOL_V2_FINGERPRINT:
        raise BenchmarkIntegrityError("GIW exact execution protocol v2 body drifted.")
    record["evidence_fingerprint_sha256"] = stored

    amendment = record.get("amendment")
    if not isinstance(amendment, Mapping):
        raise BenchmarkIntegrityError("GIW exact convergence amendment is missing.")
    expected_amendment = {
        "acceptance_rule": (
            "accept_rerun_metrics_irrespective_of_direction_only_if_zero_"
            "contextmlp_convergence_warnings"
        ),
        "performance_metrics_used_to_choose_amendment": False,
        "reason": (
            "all_five_contextmlp_folds_hit_the_preregistered_200_iteration_"
            "optimization_ceiling"
        ),
        "unchanged_protocol_fields_required": True,
    }
    for key, expected in expected_amendment.items():
        if amendment.get(key) != expected:
            raise BenchmarkIntegrityError(f"GIW exact convergence amendment {key} drifted.")
    if amendment.get("changed_fields") != {"temporal_max_iter": {"from": 200, "to": 1000}}:
        raise BenchmarkIntegrityError("GIW exact convergence amendment changed extra fields.")

    parent = record.get("parent_evidence")
    if not isinstance(parent, Mapping):
        raise BenchmarkIntegrityError("GIW exact protocol v2 parent evidence is missing.")
    parent_expected = {
        "model_execution_protocol_v1_fingerprint_sha256": EXECUTION_PROTOCOL_FINGERPRINT,
        "discovery_fingerprint_sha256": DISCOVERY_V1_FINGERPRINT,
        "discovery_benchmark_report_fingerprint_sha256": DISCOVERY_V1_REPORT_FINGERPRINT,
        "discovery_workflow_run_id": 34214673871,
        "discovery_workflow_job_id": 102023517588,
        "discovery_workflow_head_sha": "b0b6feb3382290fb4f53a9d120f5555147ed8a14",
        "discovery_artifact_id": 10051567756,
        "discovery_artifact_zip_sha256": (
            "22292e9f011d2546fc89349f0ea5bcb40dfa6d6550d7e2d008d10b18d5a683ef"
        ),
        "observed_contextmlp_convergence_warning_count": 5,
    }
    for key, expected in parent_expected.items():
        if parent.get(key) != expected:
            raise BenchmarkIntegrityError(f"GIW exact protocol v2 parent {key} drifted.")

    protocol = record.get("execution_protocol")
    if not isinstance(protocol, Mapping):
        raise BenchmarkIntegrityError("GIW exact execution protocol v2 payload is missing.")
    expected_values = {
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
        "temporal_max_iter": 1000,
        "calibration_bins": 10,
        "event_min_iou": 0.5,
        "models_refit_by_event_class": False,
        "raw_mat_retention_authorized": False,
        "context_mlp_convergence_warning_policy": "error",
    }
    for key, expected in expected_values.items():
        if protocol.get(key) != expected:
            raise BenchmarkIntegrityError(f"GIW exact execution protocol v2 {key} drifted.")
    if protocol.get("models") != ["I-VT", "RandomForest", "ContextMLP"]:
        raise BenchmarkIntegrityError("GIW exact execution protocol v2 model family drifted.")
    if protocol.get("hidden_layer_sizes") != [64, 32]:
        raise BenchmarkIntegrityError("GIW exact execution protocol v2 topology drifted.")
    if protocol.get("scene_resolution_px") != [1920, 1080]:
        raise BenchmarkIntegrityError("GIW exact execution protocol v2 scene resolution drifted.")
    if protocol.get("excluded_event_labels") != ["ambiguous", "unlabelled", "undefined"]:
        raise BenchmarkIntegrityError("GIW exact execution protocol v2 exclusions drifted.")
    if protocol.get("label_process_timestamp_vector_alignment_required") != (
        "exact_numeric_vector_equality"
    ):
        raise BenchmarkIntegrityError("GIW exact execution protocol v2 timestamp rule drifted.")

    boundary = record.get("scientific_boundary")
    if not isinstance(boundary, Mapping):
        raise BenchmarkIntegrityError("GIW exact execution protocol v2 boundary is missing.")
    if boundary.get("exact_distribution_model_execution_authorized") is not True:
        raise BenchmarkIntegrityError("GIW exact execution protocol v2 is not authorized.")
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
            raise BenchmarkIntegrityError(f"GIW exact protocol v2 must keep {key}=false.")
    return record


def run_exact_gaze_in_wild_model_validation_v2(
    prepared: GazeInWildExactPreparedBenchmark,
    protocol_evidence_v2: Mapping[str, Any],
) -> GazeInWildExactValidationRun:
    """Run the convergence-qualified task-agnostic participant-disjoint protocol."""
    protocol_record = validate_exact_execution_protocol_v2(protocol_evidence_v2)
    protocol = protocol_record["execution_protocol"]
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
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
            event_excluded_labels=tuple(
                str(value) for value in protocol["excluded_event_labels"]
            ),
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
            "execution_protocol_v1_fingerprint_sha256": EXECUTION_PROTOCOL_FINGERPRINT,
            "execution_protocol_v2_fingerprint_sha256": EXECUTION_PROTOCOL_V2_FINGERPRINT,
            "contextmlp_convergence_warning_count": 0,
            "contextmlp_convergence_requirement_satisfied": True,
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
