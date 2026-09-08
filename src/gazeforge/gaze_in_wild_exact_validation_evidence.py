"""Fail-closed validation for reviewed exact-distribution GIW model evidence."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "gaze-in-wild-exact-participant-disjoint-model-validation-evidence-v1"
DISCOVERY_TYPE = "gaze-in-wild-exact-participant-disjoint-validation-discovery-v2"
REPRODUCIBILITY_TYPE = (
    "gaze-in-wild-exact-participant-disjoint-validation-reproducibility-signature-v1"
)
EXPECTED_EVIDENCE_FINGERPRINT = (
    "b2fe85ec7e5d5cd425c0cd2593742bab835686c3f560d8a6c06e9c6d67dc547a"
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
EXPECTED_PROCESS_IDENTITY_LEDGER = (
    "85f131389315a1185e3a8973629c8e5ee3417bb73704de8054366e508af0a2e2"
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
REPRODUCIBILITY_FLOAT_DECIMALS = 8
EXPECTED_BENCHMARK_ENVELOPE_FINGERPRINT = (
    "8f1f4e37848d966957ea8ffb771fa418d43ee6254f9762590e02a1840285dc36"
)
EXPECTED_REPRODUCIBILITY_SIGNATURE = (
    "f8c8d27ddbb1fe065a15df18d53c9fa84544315ef57cf2783554b236839ff286"
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
EXPECTED_REPRODUCIBILITY_SECTION_FINGERPRINTS = {
    "analysis_label_counts": (
        "e159cc1962a14693bfbfffcc723df60254cfab1e34866ec59c4c1946b0b942d1"
    ),
    "event_class_performance": (
        "755a09be6e5cc5e3e2962de0b3bbb193d79a01e09a50bb5cbc2f3df39e94caaf"
    ),
    "fold_metrics": (
        "c1cf30a41cfa8c1981de5927f58d46a02e49da261041b2aa0624ba7f67231a47"
    ),
    "paired_model_difference_summary": (
        "a1f00d1c934fa46879f8097de0c3ba93f5ae78edc3ca6baaad17aa03d890aafd"
    ),
    "paired_model_fold_deltas": (
        "9956990388304906121205b355cda3354a07fefeb2dfcc1bfcd1cb0f02450097"
    ),
    "sample_event_class_performance": (
        "f5d7aeb4c0173daec12288d28f5b5bade1d711e0ccc5617ee82027d4c2682a43"
    ),
    "summary": (
        "9cfca876e1fe733f8bcc3648e3b6bb060a197cbaefe16c85a1c0c712404042ca"
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
REPRODUCIBILITY_POLICY = (
    "Cross-run certification preserves exact source, split, count, class, convergence, "
    "and scientific-boundary identities while comparing floating benchmark outputs "
    "after canonical rounding to 8 decimal places. Original whole-report/discovery "
    "hashes remain immutable provenance for the reviewed source run and are not "
    "required to repeat across different hosted-runner numerical backends."
)


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


def _canonicalize(value: Any, decimals: int = REPRODUCIBILITY_FLOAT_DECIMALS) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(item, decimals) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonicalize(item, decimals) for item in value]
    if isinstance(value, tuple):
        return [_canonicalize(item, decimals) for item in value]
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        rounded = round(value, decimals)
        return 0.0 if rounded == 0.0 else rounded
    return value


def _canonical_sha(value: Any) -> str:
    return _sha(_canonicalize(value))


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


def _validate_model_summary(rows: Any, *, canonical: bool = False) -> None:
    core = _summary_core(rows)
    by_model = {str(row["model"]): row for row in core}
    _require(set(by_model), set(EXPECTED_MODEL_SUMMARY), "model summary names")
    for model, expected in EXPECTED_MODEL_SUMMARY.items():
        _require(by_model[model].get("n_folds"), 5, f"{model} fold count")
        for metric, expected_value in expected.items():
            actual = by_model[model].get(metric)
            if canonical:
                actual = _canonicalize(actual)
                expected_value = _canonicalize(expected_value)
            _require(actual, expected_value, f"{model} {metric}")


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


def _validate_reproducibility_record(value: Any) -> None:
    record = _mapping(value, "reproducibility record")
    _require(
        record.get("float_decimal_places"),
        REPRODUCIBILITY_FLOAT_DECIMALS,
        "reproducibility float precision",
    )
    _require(
        record.get("benchmark_envelope_fingerprint_sha256"),
        EXPECTED_BENCHMARK_ENVELOPE_FINGERPRINT,
        "reproducibility benchmark envelope",
    )
    _require(
        record.get("metric_section_fingerprints_sha256"),
        EXPECTED_REPRODUCIBILITY_SECTION_FINGERPRINTS,
        "reproducibility metric sections",
    )
    _require(
        record.get("metric_section_row_counts"),
        EXPECTED_SECTION_ROW_COUNTS,
        "reproducibility metric row counts",
    )
    _require(
        record.get("cross_run_reproducibility_signature_sha256"),
        EXPECTED_REPRODUCIBILITY_SIGNATURE,
        "cross-run reproducibility signature",
    )
    _require(record.get("policy"), REPRODUCIBILITY_POLICY, "reproducibility policy")


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
    for key, expected in expected_source.items():
        _require(source.get(key), expected, key)

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
    for key, expected in expected_scope.items():
        _require(scope.get(key), expected, key)
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
    for key, expected in expected_convergence.items():
        _require(convergence.get(key), expected, key)

    _validate_metric_bindings(_mapping(record.get("metrics"), "metrics"))
    _validate_reproducibility_record(record.get("reproducibility"))

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
            identity = dict(_mapping(item.get(side), f"fresh {side} identity"))
            identity.pop("download_attempt", None)
            stable[side] = identity
        stable_rows.append(stable)
    return _sha(stable_rows)


def _section_count(value: Any, section: str) -> int:
    if not isinstance(value, (list, Mapping)):
        raise BenchmarkIntegrityError(
            f"GIW fresh validation {section} must be a collection."
        )
    return len(value)


def _fresh_metric_signatures(metrics: Mapping[str, Any]) -> dict[str, str]:
    signatures: dict[str, str] = {}
    for section, expected_count in EXPECTED_SECTION_ROW_COUNTS.items():
        value = metrics.get(section)
        _require(_section_count(value, section), expected_count, f"fresh {section} rows")
        signature = _canonical_sha(value)
        _require(
            signature,
            EXPECTED_REPRODUCIBILITY_SECTION_FINGERPRINTS[section],
            f"fresh {section} canonical fingerprint",
        )
        signatures[section] = signature
    _validate_model_summary(metrics.get("summary"), canonical=True)
    _require(
        _canonicalize(_extract_pursuit(metrics)),
        _canonicalize(EXPECTED_PURSUIT),
        "fresh pursuit failure case",
    )
    return signatures


def _validate_internal_fingerprint(
    value: Mapping[str, Any],
    fingerprint_key: str,
    label: str,
) -> None:
    body = dict(value)
    stored = body.pop(fingerprint_key, None)
    if not isinstance(stored, str) or len(stored) != 64:
        raise BenchmarkIntegrityError(
            f"GIW fresh validation {label} fingerprint is malformed."
        )
    _require(_sha(body), stored, f"{label} body fingerprint")


def _fresh_reproducibility_signature(
    fresh: Mapping[str, Any],
    metric_signatures: Mapping[str, str],
) -> str:
    execution = dict(_mapping(fresh.get("execution"), "fresh execution"))
    execution.pop("downloads", None)
    execution["stable_verified_pair_manifest_sha256"] = EXPECTED_PAIR_MANIFEST
    report = _mapping(fresh.get("benchmark_report"), "fresh benchmark report")
    envelope = {
        "benchmark": report.get("benchmark"),
        "model": report.get("model"),
        "protocol": report.get("protocol"),
    }
    envelope_fingerprint = _canonical_sha(envelope)
    _require(
        envelope_fingerprint,
        EXPECTED_BENCHMARK_ENVELOPE_FINGERPRINT,
        "fresh benchmark envelope",
    )
    payload = {
        "record_type": REPRODUCIBILITY_TYPE,
        "float_decimal_places": REPRODUCIBILITY_FLOAT_DECIMALS,
        "source_binding": fresh.get("source_binding"),
        "execution": execution,
        "preparation": fresh.get("preparation"),
        "split_integrity": fresh.get("split_integrity"),
        "benchmark_envelope_fingerprint_sha256": envelope_fingerprint,
        "metric_section_fingerprints_sha256": dict(metric_signatures),
        "metric_section_row_counts": dict(EXPECTED_SECTION_ROW_COUNTS),
        "scientific_boundary": fresh.get("scientific_boundary"),
        "raw_dataset_bytes_retained": fresh.get("raw_dataset_bytes_retained"),
    }
    return _canonical_sha(payload)


def validate_fresh_gaze_in_wild_validation_discovery(
    discovery: Mapping[str, Any],
    reviewed: Mapping[str, Any],
) -> str:
    """Require a fresh v2 run to reproduce the reviewed scientific result."""
    validate_reviewed_gaze_in_wild_validation_evidence(reviewed)
    fresh = dict(discovery)
    _require(fresh.get("record_type"), DISCOVERY_TYPE, "fresh record type")
    _validate_internal_fingerprint(
        fresh, "discovery_fingerprint_sha256", "fresh discovery"
    )

    source = _mapping(fresh.get("source_binding"), "fresh source binding")
    expected_fresh_source = {
        "reference_manifest_fingerprint_sha256": EXPECTED_REFERENCE_MANIFEST,
        "preparation_protocol_v1_fingerprint_sha256": EXPECTED_PREPARATION_PROTOCOL,
        "execution_protocol_v2_fingerprint_sha256": EXPECTED_EXECUTION_PROTOCOL_V2,
        "processdata_exact_identity_ledger_fingerprint_sha256": (
            EXPECTED_PROCESS_IDENTITY_LEDGER
        ),
        "frozen_figshare_metadata_source_probe_fingerprint_sha256": None,
        "figshare_project_id": 74580,
        "processdata_article_id": 11673645,
        "labeldata_article_id": 11673696,
    }
    for key, expected in expected_fresh_source.items():
        _require(source.get(key), expected, f"fresh {key}")

    execution = _mapping(fresh.get("execution"), "fresh execution")
    _require(
        _stable_pair_manifest(execution.get("downloads")),
        EXPECTED_PAIR_MANIFEST,
        "fresh pair manifest",
    )
    for key, expected in {
        "selected_labeller_id": 5,
        "selected_participant_count": 12,
        "selected_recording_count": 18,
        "selected_source_sample_count": 1590659,
        "downloaded_pair_count": 18,
        "all_selected_label_and_process_bytes_reverified": True,
        "all_label_process_timestamp_vectors_exactly_equal": True,
        "all_raw_mat_bytes_deleted_after_preparation": True,
        "processdata_cleaned_downloaded": False,
        "processdata_cleaned_article_id": 11673717,
        "contextmlp_convergence_warning_count": 0,
        "contextmlp_convergence_requirement_satisfied": True,
    }.items():
        _require(execution.get(key), expected, f"fresh {key}")

    preparation = _mapping(fresh.get("preparation"), "fresh preparation")
    for key, expected in {
        "dataset": "Gaze-in-the-Wild",
        "distribution": "official original Figshare ProcessData + LabelData",
        "analysis_rows": 157850,
        "excluded_rows": 160295,
        "prepared_rows_before_exclusions": 318145,
        "analysis_sampling_rate_hz": 60.0,
        "source_rows": 1590659,
        "participant_count": 12,
        "participant_trial_count": 18,
        "selected_labeller_id": 5,
        "source_confidence_threshold": 0.3,
        "task_mapping_used": False,
        "sampling_origin": "resampled",
        "reference_strength": "derived-human-reference",
        "all_label_process_timestamp_vectors_exactly_equal": True,
    }.items():
        _require(preparation.get(key), expected, f"fresh preparation {key}")
    _require(
        preparation.get("label_counts_analysis"),
        EXPECTED_ANALYSIS_COUNTS,
        "fresh preparation analysis labels",
    )
    _require(
        preparation.get("task_mapping"),
        None,
        "fresh preparation task mapping",
    )

    _validate_split(_mapping(fresh.get("split_integrity"), "fresh split integrity"))

    report = _mapping(fresh.get("benchmark_report"), "fresh benchmark report")
    _validate_internal_fingerprint(
        report, "report_fingerprint_sha256", "fresh benchmark report"
    )
    metric_signatures = _fresh_metric_signatures(
        _mapping(report.get("metrics"), "fresh metrics")
    )

    boundary = _mapping(fresh.get("scientific_boundary"), "fresh scientific boundary")
    for key in (
        "empirical_metrics_computed",
        "participant_disjoint_model_validation_executed",
        "contextmlp_convergence_requirement_satisfied",
    ):
        _require(boundary.get(key), True, f"fresh {key}")
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

    signature = _fresh_reproducibility_signature(fresh, metric_signatures)
    _require(
        signature,
        EXPECTED_REPRODUCIBILITY_SIGNATURE,
        "fresh cross-run reproducibility signature",
    )
    return signature
