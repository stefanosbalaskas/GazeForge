"""Fail-closed validation for reviewed exact-distribution GIW model evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "gaze-in-wild-exact-participant-disjoint-model-validation-evidence-v1"
DISCOVERY_TYPE = "gaze-in-wild-exact-participant-disjoint-validation-discovery-v2"
EXPECTED_EVIDENCE_FINGERPRINT = (
    "7f802bfe02a47262700cfa8a0537974da796d8f3f4e9cd6463d838686224e3ff"
)
EXPECTED_REFERENCE_PREFLIGHT = (
    "aff7b7b1576b9a1eee6a774183ba4f8404052226cdcb984a4112120bbc5bea67"
)
EXPECTED_REFERENCE_MANIFEST = (
    "5688c283d5f1a199ef760994b4df655e42e4f27c4dd767cfb54760a4aa6816f9"
)
EXPECTED_PREPARATION_PROTOCOL = (
    "e07ad1c15b8964e6e012e05d37b6eb989f36380ffdf307590b36273b5f8485e5"
)
EXPECTED_EXECUTION_PROTOCOL_V2 = (
    "a81df34f66f9fd35a28195f768a959d55d57a8f449a916e671355c07de910e66"
)
EXPECTED_EXACT_BYTES = (
    "dbf277d698266fe53e337a15fc342e9af1835460d2bcc69c3992635de8fa0a00"
)
EXPECTED_PROCESS_STRUCTURE = (
    "cffcc8a10d176cc5eb8c15c080cf450e3e1b1404ced00ea8907cdd4ee3c3517f"
)
EXPECTED_POR_SEMANTICS = (
    "5eb245979385283571d6d9a5dda9a5d74dea6c00165bbe3a2587fcfa80e9adfb"
)
EXPECTED_DISCOVERY_FINGERPRINT = (
    "5d28bd2917fedf6071552d84d04f0eb3de08266d6c88e6c07144f2bd9351dee0"
)
EXPECTED_BENCHMARK_FINGERPRINT = (
    "a317075bcb2f9f2bb9d1475f136c2d6d0922373707d7dab50e3ce2378541e745"
)
EXPECTED_PAIR_MANIFEST = (
    "1c129f4c2c18f78dbc41892eff476374f5ccdaaf6ee90d22d1a5808d6fdc2407"
)
EXPECTED_SCIENTIFIC_IDENTITY = (
    "580b147f889ad7e4116ef2393444016829794ced0c387a48f0372768cc8d8ed8"
)
EXPECTED_ANALYSIS_COUNTS = {
    "blink": 13889,
    "fixation": 26341,
    "pursuit": 5696,
    "saccade": 20061,
    "vor": 91863,
}
EXPECTED_MODEL_SUMMARY = {
    "I-VT": {
        "balanced_accuracy_mean": 0.2830575956976663,
        "macro_f1_mean": 0.1165214397458667,
        "event_f1_mean": 0.1567955197251188,
    },
    "RandomForest": {
        "balanced_accuracy_mean": 0.497332257041737,
        "macro_f1_mean": 0.4752446106119213,
        "event_f1_mean": 0.3085443882700346,
    },
    "ContextMLP": {
        "balanced_accuracy_mean": 0.5243307497014328,
        "macro_f1_mean": 0.5115817997735749,
        "event_f1_mean": 0.4355330321669305,
    },
}


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"GIW reviewed validation {label} must be an object.")
    return value


def _require(value: Any, expected: Any, label: str) -> None:
    if value != expected:
        raise BenchmarkIntegrityError(f"GIW reviewed validation {label} drifted.")


def load_reviewed_gaze_in_wild_validation_evidence(path: str | Path) -> dict[str, Any]:
    """Load one reviewed evidence JSON object."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BenchmarkIntegrityError("GIW reviewed validation evidence must be an object.")
    return value


def _validate_split(split: Mapping[str, Any]) -> None:
    _require(split.get("participant_disjoint"), True, "participant-disjoint flag")
    _require(split.get("all_models_share_identical_oof_rows"), True, "OOF row identity")
    _require(split.get("participant_count"), 12, "participant count")
    _require(split.get("fold_count"), 5, "fold count")
    _require(split.get("oof_row_count_per_model"), 157850, "OOF row count")
    _require(split.get("group_col"), "participant_id", "group column")
    assignments = split.get("fold_participant_assignments")
    if not isinstance(assignments, list) or len(assignments) != 12:
        raise BenchmarkIntegrityError("GIW reviewed validation requires 12 fold assignments.")
    participants = [str(row.get("participant_id")) for row in assignments if isinstance(row, Mapping)]
    folds = [row.get("validation_fold") for row in assignments if isinstance(row, Mapping)]
    if len(participants) != 12 or len(set(participants)) != 12:
        raise BenchmarkIntegrityError("GIW reviewed validation participant assignments overlap.")
    if set(folds) != {1, 2, 3, 4, 5}:
        raise BenchmarkIntegrityError("GIW reviewed validation fold coverage drifted.")


def _summary_map(rows: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(rows, list) or len(rows) != 3:
        raise BenchmarkIntegrityError("GIW reviewed validation requires three model summaries.")
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        item = _mapping(row, "model summary row")
        model = str(item.get("model"))
        if model in result:
            raise BenchmarkIntegrityError("GIW reviewed validation model summary is duplicated.")
        result[model] = item
    return result


def _validate_model_summary(rows: Any) -> None:
    summary = _summary_map(rows)
    _require(set(summary), set(EXPECTED_MODEL_SUMMARY), "model summary names")
    for model, expected in EXPECTED_MODEL_SUMMARY.items():
        for metric, value in expected.items():
            _require(summary[model].get(metric), value, f"{model} {metric}")
        _require(summary[model].get("n_folds"), 5, f"{model} fold count")


def validate_reviewed_gaze_in_wild_validation_evidence(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the immutable reviewed exact-distribution GIW performance record."""
    record = dict(payload)
    _require(record.get("record_type"), RECORD_TYPE, "record type")
    _require(record.get("evidence_fingerprint_sha256"), EXPECTED_EVIDENCE_FINGERPRINT, "fingerprint")
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    _require(_sha(body), EXPECTED_EVIDENCE_FINGERPRINT, "record body fingerprint")

    source = _mapping(record.get("source_binding"), "source binding")
    expected_source = {
        "reviewed_reference_preflight_evidence_fingerprint_sha256": EXPECTED_REFERENCE_PREFLIGHT,
        "reference_manifest_fingerprint_sha256": EXPECTED_REFERENCE_MANIFEST,
        "preparation_protocol_v1_fingerprint_sha256": EXPECTED_PREPARATION_PROTOCOL,
        "execution_protocol_v2_fingerprint_sha256": EXPECTED_EXECUTION_PROTOCOL_V2,
        "reviewed_exact_byte_evidence_fingerprint_sha256": EXPECTED_EXACT_BYTES,
        "reviewed_processdata_structure_evidence_fingerprint_sha256": EXPECTED_PROCESS_STRUCTURE,
        "reviewed_por_semantics_evidence_fingerprint_sha256": EXPECTED_POR_SEMANTICS,
        "discovery_fingerprint_sha256": EXPECTED_DISCOVERY_FINGERPRINT,
        "benchmark_report_fingerprint_sha256": EXPECTED_BENCHMARK_FINGERPRINT,
        "stable_verified_pair_manifest_sha256": EXPECTED_PAIR_MANIFEST,
        "stable_scientific_identity_sha256": EXPECTED_SCIENTIFIC_IDENTITY,
        "discovery_workflow_run_id": 34216383450,
        "discovery_workflow_job_id": 102029002501,
        "discovery_workflow_head_sha": "3f47e1914f1db895c1cfa51676e8bd89cbf94991",
        "discovery_artifact_id": 10052349927,
        "discovery_artifact_zip_sha256": "c136407a2db519508503c0fb736fd051aff67ef1ee1cc3f392195a4f4503450a",
    }
    for key, value in expected_source.items():
        _require(source.get(key), value, key)

    scope = _mapping(record.get("validation_scope"), "validation scope")
    expected_scope = {
        "reference_labeller_id": 5,
        "participant_count": 12,
        "recording_count": 18,
        "source_sample_count": 1590659,
        "derived_60hz_rows_before_exclusions": 318145,
        "excluded_rows": 160295,
        "analysis_row_count": 157850,
        "analysis_sampling_rate_hz": 60.0,
        "source_confidence_threshold": 0.3,
        "task_mapping_used": False,
        "task_stratified_validation_created": False,
    }
    for key, value in expected_scope.items():
        _require(scope.get(key), value, key)
    _require(scope.get("label_counts_analysis"), EXPECTED_ANALYSIS_COUNTS, "analysis labels")
    _validate_split(_mapping(record.get("split_integrity"), "split integrity"))

    convergence = _mapping(record.get("convergence_review"), "convergence review")
    _require(convergence.get("initial_200_iteration_discovery_rejected_for_review"), True, "v1 rejection")
    _require(convergence.get("performance_metrics_used_to_choose_amendment"), False, "amendment selection")
    _require(convergence.get("only_parameter_changed"), "temporal_max_iter", "amended parameter")
    _require(convergence.get("from"), 200, "old max_iter")
    _require(convergence.get("to"), 1000, "new max_iter")
    _require(convergence.get("v2_contextmlp_convergence_warning_count"), 0, "v2 warnings")
    _require(convergence.get("v2_convergence_requirement_satisfied"), True, "v2 convergence")

    metrics = _mapping(record.get("metrics"), "metrics")
    _require(metrics.get("full_benchmark_report_fingerprint_sha256"), EXPECTED_BENCHMARK_FINGERPRINT, "full benchmark binding")
    _validate_model_summary(metrics.get("summary"))
    fold_rows = metrics.get("fold_core_metrics")
    if not isinstance(fold_rows, list) or len(fold_rows) != 15:
        raise BenchmarkIntegrityError("GIW reviewed validation requires 15 model-fold rows.")
    class_rows = metrics.get("sample_event_class_performance")
    if not isinstance(class_rows, list) or len(class_rows) != 15:
        raise BenchmarkIntegrityError("GIW reviewed validation requires 15 sample-class rows.")
    event_rows = metrics.get("event_class_performance")
    if not isinstance(event_rows, list) or len(event_rows) != 16:
        raise BenchmarkIntegrityError("GIW reviewed validation requires 16 event-class rows.")
    paired = metrics.get("paired_model_difference_summary_core")
    if not isinstance(paired, list) or len(paired) != 9:
        raise BenchmarkIntegrityError("GIW reviewed validation requires nine paired core comparisons.")

    boundary = _mapping(record.get("scientific_boundary"), "scientific boundary")
    for key in (
        "performance_evidence_reviewed",
        "participant_disjoint_model_validation_created",
        "new_empirical_performance_claim_created",
    ):
        _require(boundary.get(key), True, key)
    for key in (
        "task_stratified_model_validation_created",
        "complete_file_to_publication_task_mapping_verified",
        "cross_dataset_validation_created",
        "native_gp3_or_native_60hz_validity_created",
        "gp3_validity_claim_created",
        "quarantine_exit_authorized",
        "acquisition_hardware_cadence_verified_by_this_validation",
        "raw_dataset_bytes_retained",
    ):
        _require(boundary.get(key), False, key)
    return record


def _stable_pair_manifest(downloads: Any) -> str:
    if not isinstance(downloads, list) or len(downloads) != 18:
        raise BenchmarkIntegrityError("GIW fresh validation requires 18 verified source pairs.")
    stable_rows: list[dict[str, Any]] = []
    for item_value in downloads:
        item = _mapping(item_value, "fresh download row")
        stable: dict[str, Any] = {
            "recording_token": item.get("recording_token"),
            "raw_bytes_deleted_after_preparation": item.get(
                "raw_bytes_deleted_after_preparation"
            ),
        }
        for side in ("label", "process"):
            value = dict(_mapping(item.get(side), f"fresh {side} identity"))
            value.pop("download_attempt", None)
            stable[side] = value
        stable_rows.append(stable)
    return _sha(stable_rows)


def validate_fresh_gaze_in_wild_validation_discovery(
    discovery: Mapping[str, Any],
    reviewed: Mapping[str, Any],
) -> str:
    """Require a fresh v2 run to reproduce the reviewed scientific identity."""
    validate_reviewed_gaze_in_wild_validation_evidence(reviewed)
    fresh = dict(discovery)
    _require(fresh.get("record_type"), DISCOVERY_TYPE, "fresh record type")
    execution = _mapping(fresh.get("execution"), "fresh execution")
    _require(_stable_pair_manifest(execution.get("downloads")), EXPECTED_PAIR_MANIFEST, "fresh pair manifest")
    for key, value in {
        "selected_labeller_id": 5,
        "selected_participant_count": 12,
        "selected_recording_count": 18,
        "selected_source_sample_count": 1590659,
        "downloaded_pair_count": 18,
        "all_selected_label_and_process_bytes_reverified": True,
        "all_label_process_timestamp_vectors_exactly_equal": True,
        "all_raw_mat_bytes_deleted_after_preparation": True,
        "processdata_cleaned_downloaded": False,
        "contextmlp_convergence_warning_count": 0,
        "contextmlp_convergence_requirement_satisfied": True,
    }.items():
        _require(execution.get(key), value, f"fresh {key}")

    _validate_split(_mapping(fresh.get("split_integrity"), "fresh split integrity"))
    report = _mapping(fresh.get("benchmark_report"), "fresh benchmark report")
    _require(report.get("report_fingerprint_sha256"), EXPECTED_BENCHMARK_FINGERPRINT, "fresh benchmark fingerprint")
    _validate_model_summary(_mapping(report.get("metrics"), "fresh metrics").get("summary"))

    boundary = _mapping(fresh.get("scientific_boundary"), "fresh scientific boundary")
    _require(boundary.get("empirical_metrics_computed"), True, "fresh metrics-computed flag")
    _require(boundary.get("participant_disjoint_model_validation_executed"), True, "fresh execution flag")
    _require(boundary.get("contextmlp_convergence_requirement_satisfied"), True, "fresh convergence flag")
    _require(boundary.get("performance_evidence_reviewed"), False, "fresh reviewed flag")
    for key in (
        "participant_disjoint_model_validation_created",
        "task_stratified_model_validation_created",
        "complete_file_to_publication_task_mapping_verified",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "quarantine_exit_authorized",
        "new_empirical_performance_claim_created",
    ):
        _require(boundary.get(key), False, f"fresh {key}")
    _require(fresh.get("raw_dataset_bytes_retained"), False, "fresh raw retention")

    stable_execution = dict(execution)
    stable_execution.pop("downloads", None)
    stable_execution["stable_verified_pair_manifest_sha256"] = EXPECTED_PAIR_MANIFEST
    stable_payload = {
        "record_type": "gaze-in-wild-exact-participant-disjoint-validation-scientific-identity-v1",
        "source_binding": fresh.get("source_binding"),
        "execution": stable_execution,
        "preparation": fresh.get("preparation"),
        "split_integrity": fresh.get("split_integrity"),
        "benchmark_report": fresh.get("benchmark_report"),
        "raw_dataset_bytes_retained": fresh.get("raw_dataset_bytes_retained"),
    }
    identity = _sha(stable_payload)
    _require(identity, EXPECTED_SCIENTIFIC_IDENTITY, "fresh scientific identity")
    return identity
