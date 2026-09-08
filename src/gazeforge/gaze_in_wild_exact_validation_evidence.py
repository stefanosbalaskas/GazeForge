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
SCIENTIFIC_IDENTITY_TYPE = (
    "gaze-in-wild-exact-participant-disjoint-validation-scientific-identity-v1"
)
EXPECTED_EVIDENCE_FINGERPRINT = (
    "fa45366ea855a0bad662514c42187ffe3d24e5ce8e191a351c8c9b478325df6f"
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
    "0623353dda03ab6f5988c671cbc6dd5e82af8fb30b84a18bd9364c3aae5e4513"
)
EXPECTED_BENCHMARK_FINGERPRINT = (
    "170fab6ef5cf8bf109ad1f134b4d2b0a13f442e7d2b174f43e020441a3693c1f"
)
EXPECTED_PAIR_MANIFEST = (
    "1c129f4c2c18f78dbc41892eff476374f5ccdaaf6ee90d22d1a5808d6fdc2407"
)
EXPECTED_SCIENTIFIC_IDENTITY = (
    "772d632d8671e058407d0fe9fdfcd291c0371a45682ec9dfd145861a924eaf46"
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
        "balanced_accuracy_mean": 0.5285607220412606,
        "macro_f1_mean": 0.5192210487515447,
        "event_f1_mean": 0.4395648140542133,
    },
}
EXPECTED_SECTION_FINGERPRINTS = {
    "analysis_label_counts": (
        "e159cc1962a14693bfbfffcc723df60254cfab1e34866ec59c4c1946b0b942d1"
    ),
    "event_class_performance": (
        "47f323d75affba71190bebc2193468f59e7ed957fd664e4b152f19137e57ef57"
    ),
    "fold_metrics": (
        "0e1350e49240c76ffd9e5381fed3c689f48cd6dc3052b4df59a0d54aa935401d"
    ),
    "paired_model_difference_summary": (
        "ba632f6acb79104a97b5310038f3912cf44c2b5806759d099f18da0d1c6bb1ee"
    ),
    "paired_model_fold_deltas": (
        "ff8935ee8b06a3dca1a71f2b1c9540229a4d4594e7617ffc1e81d2ecc98da25c"
    ),
    "sample_event_class_performance": (
        "dee5f5a08f351e364c2224d43c761a7c537ca9a1800b44c5048b5cda7a8e33e0"
    ),
    "summary": (
        "651958828cd8eef539e30abe990c32c490f8c933916e689ab08bca469add5662"
    ),
    "task_fold_metrics": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
    ),
    "task_summary": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
    ),
}
EXPECTED_SECTION_ROW_COUNTS = {
    "analysis_label_counts": 5,
    "event_class_performance": 16,
    "fold_metrics": 15,
    "paired_model_difference_summary": 36,
    "paired_model_fold_deltas": 160,
    "sample_event_class_performance": 15,
    "summary": 3,
    "task_fold_metrics": 0,
    "task_summary": 0,
}
EXPECTED_PURSUIT = {
    "analysis_support": 5696,
    "reference_event_count": 327,
    "models": {
        "I-VT": {
            "sample_f1": 0.0,
            "sample_precision": 0.0,
            "sample_recall": 0.0,
            "event_f1": 0.0,
            "event_precision": 1.0,
            "event_recall": 0.0,
            "matched_reference_events": 0,
            "predicted_events": 0,
        },
        "RandomForest": {
            "sample_f1": 0.07687120701281187,
            "sample_precision": 0.16579406631762653,
            "sample_recall": 0.05003511235955056,
            "event_f1": 0.008583690987124463,
            "event_precision": 0.0056022408963585435,
            "event_recall": 0.01834862385321101,
            "matched_reference_events": 6,
            "predicted_events": 1071,
        },
        "ContextMLP": {
            "sample_f1": 0.0547112462006079,
            "sample_precision": 0.3081081081081081,
            "sample_recall": 0.030021067415730338,
            "event_f1": 0.0029585798816568047,
            "event_precision": 0.0028653295128939827,
            "event_recall": 0.0030581039755351682,
            "matched_reference_events": 1,
            "predicted_events": 349,
        },
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
        raise BenchmarkIntegrityError(
            f"GIW reviewed validation {label} must be an object."
        )
    return value


def _require(value: Any, expected: Any, label: str) -> None:
    if value != expected:
        raise BenchmarkIntegrityError(f"GIW reviewed validation {label} drifted.")


def load_reviewed_gaze_in_wild_validation_evidence(
    path: str | Path,
) -> dict[str, Any]:
    """Load one reviewed evidence JSON object."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BenchmarkIntegrityError(
            "GIW reviewed validation evidence must be an object."
        )
    return value


def _validate_split(split: Mapping[str, Any]) -> None:
    _require(split.get("participant_disjoint"), True, "participant-disjoint flag")
    _require(
        split.get("all_models_share_identical_oof_rows"), True, "OOF row identity"
    )
    _require(split.get("participant_count"), 12, "participant count")
    _require(split.get("fold_count"), 5, "fold count")
    _require(split.get("oof_row_count_per_model"), 157850, "OOF row count")
    _require(split.get("group_col"), "participant_id", "group column")
    assignments = split.get("fold_participant_assignments")
    if not isinstance(assignments, list) or len(assignments) != 12:
        raise BenchmarkIntegrityError(
            "GIW reviewed validation requires 12 fold assignments."
        )
    participants = [
        str(row.get("participant_id"))
        for row in assignments
        if isinstance(row, Mapping)
    ]
    folds = [
        row.get("validation_fold")
        for row in assignments
        if isinstance(row, Mapping)
    ]
    if len(participants) != 12 or len(set(participants)) != 12:
        raise BenchmarkIntegrityError(
            "GIW reviewed validation participant assignments overlap."
        )
    if set(folds) != {1, 2, 3, 4, 5}:
        raise BenchmarkIntegrityError(
            "GIW reviewed validation fold coverage drifted."
        )


def _summary_core(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or len(rows) != 3:
        raise BenchmarkIntegrityError(
            "GIW reviewed validation requires three model summaries."
        )
    result: list[dict[str, Any]] = []
    for row_value in rows:
        row = _mapping(row_value, "model summary row")
        result.append(
            {
                "model": row.get("model"),
                "n_folds": row.get("n_folds"),
                "balanced_accuracy_mean": row.get("balanced_accuracy_mean"),
                "macro_f1_mean": row.get("macro_f1_mean"),
                "event_f1_mean": row.get("event_f1_mean"),
            }
        )
    return result


def _validate_model_summary(rows: Any) -> None:
    core = _summary_core(rows)
    by_model = {str(row["model"]): row for row in core}
    _require(set(by_model), set(EXPECTED_MODEL_SUMMARY), "model summary names")
    for model, expected in EXPECTED_MODEL_SUMMARY.items():
        _require(by_model[model].get("n_folds"), 5, f"{model} fold count")
        for metric, value in expected.items():
            _require(by_model[model].get(metric), value, f"{model} {metric}")


def _extract_pursuit(metrics: Mapping[str, Any]) -> dict[str, Any]:
    sample_rows = metrics.get("sample_event_class_performance")
    event_rows = metrics.get("event_class_performance")
    if not isinstance(sample_rows, list) or not isinstance(event_rows, list):
        raise BenchmarkIntegrityError(
            "GIW fresh validation pursuit evidence sections are missing."
        )
    sample = {
        str(row.get("model")): row
        for row in sample_rows
        if isinstance(row, Mapping) and row.get("event_label") == "pursuit"
    }
    event = {
        str(row.get("model")): row
        for row in event_rows
        if isinstance(row, Mapping) and row.get("event_label") == "pursuit"
    }
    if set(sample) != set(EXPECTED_MODEL_SUMMARY) or set(event) != set(
        EXPECTED_MODEL_SUMMARY
    ):
        raise BenchmarkIntegrityError(
            "GIW fresh validation pursuit model coverage drifted."
        )
    reference_counts = {row.get("n_reference_events") for row in event.values()}
    if len(reference_counts) != 1:
        raise BenchmarkIntegrityError(
            "GIW fresh validation pursuit reference-event counts disagree."
        )
    result: dict[str, Any] = {
        "analysis_support": sample["ContextMLP"].get("support"),
        "reference_event_count": next(iter(reference_counts)),
        "models": {},
    }
    for model in ("I-VT", "RandomForest", "ContextMLP"):
        result["models"][model] = {
            "sample_f1": sample[model].get("f1"),
            "sample_precision": sample[model].get("precision"),
            "sample_recall": sample[model].get("recall"),
            "event_f1": event[model].get("f1"),
            "event_precision": event[model].get("precision"),
            "event_recall": event[model].get("recall"),
            "matched_reference_events": event[model].get("true_positive"),
            "predicted_events": event[model].get("n_predicted_events"),
        }
    return result


def _validate_metric_bindings(metrics: Mapping[str, Any]) -> None:
    _require(
        metrics.get("full_benchmark_report_fingerprint_sha256"),
        EXPECTED_BENCHMARK_FINGERPRINT,
        "full benchmark binding",
    )
    _require(
        metrics.get("section_fingerprints_sha256"),
        EXPECTED_SECTION_FINGERPRINTS,
        "metric section fingerprints",
    )
    _require(
        metrics.get("section_row_counts"),
        EXPECTED_SECTION_ROW_COUNTS,
        "metric section row counts",
    )
    _validate_model_summary(metrics.get("summary_core"))
    _require(
        metrics.get("pursuit_failure_case"),
        EXPECTED_PURSUIT,
        "pursuit failure case",
    )


def validate_reviewed_gaze_in_wild_validation_evidence(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the immutable reviewed exact-distribution GIW performance record."""
    record = dict(payload)
    _require(record.get("record_type"), RECORD_TYPE, "record type")
    _require(
        record.get("evidence_fingerprint_sha256"),
        EXPECTED_EVIDENCE_FINGERPRINT,
        "fingerprint",
    )
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    _require(_sha(body), EXPECTED_EVIDENCE_FINGERPRINT, "record body fingerprint")

    source = _mapping(record.get("source_binding"), "source binding")
    expected_source = {
        "reviewed_reference_preflight_evidence_fingerprint_sha256": (
            EXPECTED_REFERENCE_PREFLIGHT
        ),
        "reference_manifest_fingerprint_sha256": EXPECTED_REFERENCE_MANIFEST,
        "preparation_protocol_v1_fingerprint_sha256": EXPECTED_PREPARATION_PROTOCOL,
        "execution_protocol_v2_fingerprint_sha256": EXPECTED_EXECUTION_PROTOCOL_V2,
        "reviewed_exact_byte_evidence_fingerprint_sha256": EXPECTED_EXACT_BYTES,
        "reviewed_processdata_structure_evidence_fingerprint_sha256": (
            EXPECTED_PROCESS_STRUCTURE
        ),
        "reviewed_por_semantics_evidence_fingerprint_sha256": EXPECTED_POR_SEMANTICS,
        "discovery_fingerprint_sha256": EXPECTED_DISCOVERY_FINGERPRINT,
        "benchmark_report_fingerprint_sha256": EXPECTED_BENCHMARK_FINGERPRINT,
        "stable_verified_pair_manifest_sha256": EXPECTED_PAIR_MANIFEST,
        "stable_scientific_identity_sha256": EXPECTED_SCIENTIFIC_IDENTITY,
        "discovery_workflow_run_id": 34273647914,
        "discovery_workflow_job_id": 102221217862,
        "discovery_workflow_head_sha": (
            "9d2c5cd9c274527615e4e30b2feb53da2e20e523"
        ),
        "discovery_artifact_id": 10075402142,
        "discovery_artifact_zip_sha256": (
            "3406abd4eddc080b9b72687e3b164d863fe0d925782c746d4b369c48dfcbdf87"
        ),
    }
    for key, value in expected_source.items():
        _require(source.get(key), value, key)

    scope = _mapping(record.get("validation_scope"), "validation scope")
    expected_scope = {
        "dataset": "Gaze-in-the-Wild",
        "distribution": "official original Figshare ProcessData + LabelData",
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
    _require(
        scope.get("label_counts_analysis"), EXPECTED_ANALYSIS_COUNTS, "analysis labels"
    )
    _validate_split(_mapping(record.get("split_integrity"), "split integrity"))

    convergence = _mapping(record.get("convergence_review"), "convergence review")
    expected_convergence = {
        "initial_200_iteration_discovery_rejected_for_review": True,
        "performance_metrics_used_to_choose_amendment": False,
        "only_parameter_changed": "temporal_max_iter",
        "from": 200,
        "to": 1000,
        "accept_metrics_regardless_of_direction": True,
        "v2_contextmlp_convergence_warning_count": 0,
        "v2_convergence_requirement_satisfied": True,
    }
    for key, value in expected_convergence.items():
        _require(convergence.get(key), value, key)

    _validate_metric_bindings(_mapping(record.get("metrics"), "metrics"))

    boundary = _mapping(record.get("scientific_boundary"), "scientific boundary")
    for key in (
        "performance_evidence_reviewed",
        "participant_disjoint_model_validation_created",
        "event_class_sensitivity_created",
    ):
        _require(boundary.get(key), True, key)
    for key in (
        "new_empirical_performance_claim_created",
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
        raise BenchmarkIntegrityError(
            "GIW fresh validation requires 18 verified source pairs."
        )
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


def _validate_fresh_metric_sections(metrics: Mapping[str, Any]) -> None:
    for section, expected_hash in EXPECTED_SECTION_FINGERPRINTS.items():
        value = metrics.get(section)
        _require(_sha(value), expected_hash, f"fresh {section} fingerprint")
        if not isinstance(value, (list, Mapping)):
            raise BenchmarkIntegrityError(
                f"GIW fresh validation {section} must be a collection."
            )
        _require(
            len(value),
            EXPECTED_SECTION_ROW_COUNTS[section],
            f"fresh {section} rows",
        )
    _validate_model_summary(metrics.get("summary"))
    _require(_extract_pursuit(metrics), EXPECTED_PURSUIT, "fresh pursuit failure case")


def validate_fresh_gaze_in_wild_validation_discovery(
    discovery: Mapping[str, Any],
    reviewed: Mapping[str, Any],
) -> str:
    """Require a fresh v2 run to reproduce the reviewed scientific identity."""
    validate_reviewed_gaze_in_wild_validation_evidence(reviewed)
    fresh = dict(discovery)
    _require(fresh.get("record_type"), DISCOVERY_TYPE, "fresh record type")
    _require(
        fresh.get("discovery_fingerprint_sha256"),
        EXPECTED_DISCOVERY_FINGERPRINT,
        "fresh discovery fingerprint",
    )
    body = dict(fresh)
    body.pop("discovery_fingerprint_sha256", None)
    _require(_sha(body), EXPECTED_DISCOVERY_FINGERPRINT, "fresh discovery body")

    source = _mapping(fresh.get("source_binding"), "fresh source binding")
    for key, value in {
        "reference_manifest_fingerprint_sha256": EXPECTED_REFERENCE_MANIFEST,
        "preparation_protocol_v1_fingerprint_sha256": EXPECTED_PREPARATION_PROTOCOL,
        "execution_protocol_v2_fingerprint_sha256": EXPECTED_EXECUTION_PROTOCOL_V2,
    }.items():
        _require(source.get(key), value, f"fresh {key}")

    execution = _mapping(fresh.get("execution"), "fresh execution")
    _require(
        _stable_pair_manifest(execution.get("downloads")),
        EXPECTED_PAIR_MANIFEST,
        "fresh pair manifest",
    )
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

    preparation = _mapping(fresh.get("preparation"), "fresh preparation")
    for key, value in {
        "analysis_rows": 157850,
        "excluded_rows": 160295,
        "analysis_sampling_rate_hz": 60.0,
    }.items():
        _require(preparation.get(key), value, f"fresh {key}")

    _validate_split(_mapping(fresh.get("split_integrity"), "fresh split integrity"))
    report = _mapping(fresh.get("benchmark_report"), "fresh benchmark report")
    _require(
        report.get("report_fingerprint_sha256"),
        EXPECTED_BENCHMARK_FINGERPRINT,
        "fresh benchmark fingerprint",
    )
    _validate_fresh_metric_sections(
        _mapping(report.get("metrics"), "fresh metrics")
    )

    boundary = _mapping(fresh.get("scientific_boundary"), "fresh scientific boundary")
    _require(boundary.get("empirical_metrics_computed"), True, "fresh metrics flag")
    _require(
        boundary.get("participant_disjoint_model_validation_executed"),
        True,
        "fresh execution flag",
    )
    _require(
        boundary.get("contextmlp_convergence_requirement_satisfied"),
        True,
        "fresh convergence flag",
    )
    _require(
        boundary.get("performance_evidence_reviewed"),
        False,
        "fresh reviewed flag",
    )
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
        "record_type": SCIENTIFIC_IDENTITY_TYPE,
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
