"""Unified validation for benchmark source-resolution checkpoints."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .visus_source_resolution import validate_visus_source_resolution_record

_RECORD_TYPE = "source-resolution-status-v1"
_BUNDLE_TYPE = "source-resolution-validation-bundle-v1"
_RIGHTS_STATES = {"unresolved", "verified", "not_permitted"}
_HEX = set("0123456789abcdef")

_VISUS_DATASET = "VISUS dynamic-video eye-tracking benchmark"
_HOLLYWOOD2_DATASET = "Hollywood2EM eye-movement event benchmark"
_GAZE_IN_WILD_DATASET = "Gaze-in-the-Wild naturalistic eye-head event benchmark"

_DATASET_KEYS = {
    _VISUS_DATASET: "visus",
    _HOLLYWOOD2_DATASET: "hollywood2em",
    _GAZE_IN_WILD_DATASET: "gaze-in-the-wild",
}

_EXPECTED_STATUS = {
    "visus": "current_authoritative_distribution_unresolved",
    "hollywood2em": (
        "canonical_repository_and_ground_truth_recovered_terms_and_participant_"
        "mapping_unresolved"
    ),
    "gaze-in-the-wild": (
        "published_distribution_identifier_established_current_direct_copy_unverified"
    ),
}
_EXPECTED_EMPIRICAL_STATE = {
    "visus": False,
    "hollywood2em": True,
    "gaze-in-the-wild": False,
}
_EXPECTED_AUDIT_READY_STATE = {
    "visus": False,
    "hollywood2em": False,
    "gaze-in-the-wild": False,
}
_HOLLYWOOD2_TOKENS = (
    "001",
    "002",
    "003",
    "004",
    "005",
    "006",
    "008",
    "010",
    "011",
    "012",
    "013",
    "014",
    "015",
    "017",
    "018",
    "019",
)
_HOLLYWOOD2_LABEL_COUNTS = {
    "FIX": 2_414_211,
    "SACCADE": 353_208,
    "SP": 936_913,
    "NOISE": 167_248,
}
_HOLLYWOOD2_COMMIT = "870fa6d6209c9085260918d61433a0a2c70fd497"
_HOLLYWOOD2_LEDGER = "51dd0883cf5b7966a4caea94fb9ac97e43bee6cf716423f26f268810041d3030"
_HOLLYWOOD2_SCHEMA = "31a6db306fded47592ad4c1647da8df3413df970a2b8abcba91e23d6261881c0"
_HOLLYWOOD2_EVIDENCE = "d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea"
_HOLLYWOOD2_PROBE = "b3137d6bc4ff049802e6cdc62f6e9d3b8e490fe42384d501f789ba3bacb691dd"


def _fingerprint(payload: Mapping[str, Any]) -> str:
    canonical = dict(payload)
    canonical.pop("record_fingerprint_sha256", None)
    encoded = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bundle_fingerprint(records: Sequence[Mapping[str, Any]]) -> str:
    identity = [
        {
            "dataset_key": record["dataset_key"],
            "status": record["status"],
            "record_fingerprint_sha256": record["record_fingerprint_sha256"],
        }
        for record in records
    ]
    encoded = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_payload(path: str | Path) -> tuple[Path, Mapping[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise BenchmarkIntegrityError("Source-resolution checkpoint must be a JSON object.")
    return source, payload


def _require_bool(payload: Mapping[str, Any], key: str, *, dataset_key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise BenchmarkIntegrityError(
            f"{dataset_key} source-resolution field {key!r} must be boolean."
        )
    return value


def _require_mapping(
    payload: Mapping[str, Any],
    key: str,
    *,
    dataset_key: str,
) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(
            f"{dataset_key} source-resolution field {key!r} must be an object."
        )
    return value


def _require_nonempty_string_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    dataset_key: str,
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise BenchmarkIntegrityError(
            f"{dataset_key} source-resolution field {key!r} must contain non-empty strings."
        )
    return list(value)


def _validate_checked_on(payload: Mapping[str, Any], *, dataset_key: str) -> str:
    checked_on = str(payload.get("checked_on", "")).strip()
    try:
        date.fromisoformat(checked_on)
    except ValueError as exc:
        raise BenchmarkIntegrityError(
            f"{dataset_key} source-resolution checked_on must be an ISO calendar date."
        ) from exc
    return checked_on


def _validate_rights(
    payload: Mapping[str, Any],
    *,
    dataset_key: str,
) -> tuple[Mapping[str, Any], str, str]:
    rights = _require_mapping(payload, "rights", dataset_key=dataset_key)
    analysis = str(rights.get("analysis_use_terms_status", "")).strip()
    redistribution = str(rights.get("raw_data_redistribution_terms_status", "")).strip()
    if analysis not in _RIGHTS_STATES or redistribution not in _RIGHTS_STATES:
        raise BenchmarkIntegrityError(
            f"{dataset_key} source-resolution rights must use unresolved, verified, "
            "or not_permitted states."
        )
    if rights.get("license_inference_permitted") is not False:
        raise BenchmarkIntegrityError(
            f"{dataset_key} source-resolution checkpoints cannot infer a dataset license."
        )
    return rights, analysis, redistribution


def _validate_common(
    payload: Mapping[str, Any],
    *,
    dataset: str,
    dataset_key: str,
) -> tuple[str, str, bool, bool, Mapping[str, Any], str, str, list[str]]:
    if payload.get("record_type") != _RECORD_TYPE:
        raise BenchmarkIntegrityError(
            f"{dataset_key} source-resolution record_type must be {_RECORD_TYPE!r}."
        )
    if payload.get("dataset") != dataset:
        raise BenchmarkIntegrityError(
            f"{dataset_key} source-resolution dataset must be {dataset!r}."
        )

    checked_on = _validate_checked_on(payload, dataset_key=dataset_key)
    status = str(payload.get("status", "")).strip()
    if status != _EXPECTED_STATUS[dataset_key]:
        raise BenchmarkIntegrityError(
            f"{dataset_key} source-resolution status is not supported by this v1 checkpoint "
            "validator. Create a reviewed schema transition before changing evidence state."
        )

    empirical = _require_bool(payload, "empirical_evidence_created", dataset_key=dataset_key)
    expected_empirical = _EXPECTED_EMPIRICAL_STATE[dataset_key]
    if empirical is not expected_empirical:
        raise BenchmarkIntegrityError(
            f"{dataset_key} empirical_evidence_created does not match the reviewed checkpoint "
            "state."
        )

    audit_ready = _require_bool(payload, "source_audit_ready", dataset_key=dataset_key)
    expected_audit_ready = _EXPECTED_AUDIT_READY_STATE[dataset_key]
    if audit_ready is not expected_audit_ready:
        raise BenchmarkIntegrityError(
            f"{dataset_key} source_audit_ready does not match the reviewed checkpoint state."
        )

    rights, analysis, redistribution = _validate_rights(payload, dataset_key=dataset_key)
    claim_limits = _require_nonempty_string_list(
        payload,
        "claim_limits",
        dataset_key=dataset_key,
    )
    _require_nonempty_string_list(
        payload,
        "next_required_actions",
        dataset_key=dataset_key,
    )
    if analysis != "unresolved" or redistribution != "unresolved":
        raise BenchmarkIntegrityError(
            f"{dataset_key} current checkpoint must keep analysis and redistribution rights "
            "separately unresolved."
        )

    return (
        checked_on,
        status,
        audit_ready,
        empirical,
        rights,
        analysis,
        redistribution,
        claim_limits,
    )


def _verify_optional_fingerprint(payload: Mapping[str, Any], fingerprint: str) -> None:
    stored = payload.get("record_fingerprint_sha256")
    if stored is None:
        return
    stored_text = str(stored).strip().lower()
    if len(stored_text) != 64 or any(character not in _HEX for character in stored_text):
        raise BenchmarkIntegrityError(
            "Source-resolution record fingerprint must contain 64 hexadecimal digits."
        )
    if stored_text != fingerprint:
        raise BenchmarkIntegrityError(
            "Source-resolution record fingerprint does not match its content."
        )


def _require_hollywood2_rights(rights: Mapping[str, Any]) -> None:
    for key, label in (
        ("article_cc_by_is_dataset_license", "article license as dataset license"),
        ("repository_license_file_recovered", "repository license recovery"),
        ("dataset_specific_license_verified", "dataset-license verification"),
        (
            "open_source_description_is_exact_license_text",
            "open-source description as exact license text",
        ),
    ):
        if rights.get(key) is not False:
            raise BenchmarkIntegrityError(f"Hollywood2EM must not promote {label}.")


def validate_hollywood2_source_resolution_record(path: str | Path) -> dict[str, Any]:
    """Validate the reviewed Hollywood2EM recovered-source checkpoint."""

    _, payload = _load_payload(path)
    dataset_key = "hollywood2em"
    (
        checked_on,
        status,
        audit_ready,
        empirical,
        rights,
        analysis,
        redistribution,
        claim_limits,
    ) = _validate_common(payload, dataset=_HOLLYWOOD2_DATASET, dataset_key=dataset_key)

    canonical_found = _require_bool(
        payload,
        "canonical_distribution_identifier_found",
        dataset_key=dataset_key,
    )
    current_copy = _require_bool(
        payload,
        "current_retrievable_copy_verified",
        dataset_key=dataset_key,
    )
    if canonical_found is not True or current_copy is not True:
        raise BenchmarkIntegrityError(
            "Hollywood2EM reviewed state requires the canonical repository and exact current "
            "ground-truth copy to remain verified."
        )

    expected_history = (
        "validation/history/source-resolution/"
        "hollywood2-source-resolution-2026-09-04.json"
    )
    if payload.get("supersedes") != expected_history:
        raise BenchmarkIntegrityError(
            "Hollywood2EM checkpoint must preserve its reviewed historical predecessor path."
        )

    repository = _require_mapping(
        payload,
        "authoritative_repository",
        dataset_key=dataset_key,
    )
    expected_repository = {
        "url": "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git",
        "default_ref": "refs/heads/master",
        "commit_sha1": _HOLLYWOOD2_COMMIT,
        "commit_author_date": "2020-02-19T16:56:44+01:00",
        "readme_git_blob_sha1": "c8b7d126295e5f52a7748533952f044228423bf8",
        "readme_sha256": (
            "97f839bda127674b5de1eb5d8c3b1d2c82d65e7c6c1708c2e9f9711170ada383"
        ),
        "repository_license_file_recovered": False,
    }
    if dict(repository) != expected_repository:
        raise BenchmarkIntegrityError(
            "Hollywood2EM authoritative repository identity drifted from the reviewed state."
        )

    ground = _require_mapping(
        payload,
        "authoritative_ground_truth",
        dataset_key=dataset_key,
    )
    expected_counts = {
        "file_count": 697,
        "total_bytes": 137_328_178,
        "sample_count": 3_871_580,
        "test_file_count": 642,
        "train_file_count": 55,
        "clip_count": 56,
        "file_subject_token_count": 16,
    }
    for key, expected in expected_counts.items():
        if ground.get(key) != expected:
            raise BenchmarkIntegrityError(
                f"Hollywood2EM authoritative ground-truth {key} drifted."
            )
    if ground.get("source_identity_ledger_fingerprint_sha256") != _HOLLYWOOD2_LEDGER:
        raise BenchmarkIntegrityError("Hollywood2EM source-ledger fingerprint drifted.")
    if ground.get("schema_signature_sha256") != _HOLLYWOOD2_SCHEMA:
        raise BenchmarkIntegrityError("Hollywood2EM schema fingerprint drifted.")
    if ground.get("schema_uniform_across_all_files") is not True:
        raise BenchmarkIntegrityError(
            "Hollywood2EM schema must remain uniform across all recovered ground-truth files."
        )
    if ground.get("final_label_counts") != _HOLLYWOOD2_LABEL_COUNTS:
        raise BenchmarkIntegrityError("Hollywood2EM final-label counts drifted.")

    sensitivity = ground.get("student_vs_expert_corrected")
    if not isinstance(sensitivity, Mapping):
        raise BenchmarkIntegrityError(
            "Hollywood2EM student-to-expert annotation sensitivity is missing."
        )
    if sensitivity.get("sample_count") != 3_871_580:
        raise BenchmarkIntegrityError("Hollywood2EM sensitivity sample count drifted.")
    if sensitivity.get("changed_sample_count") != 291_315:
        raise BenchmarkIntegrityError("Hollywood2EM sensitivity changed-sample count drifted.")
    agreement = float(sensitivity.get("raw_agreement_fraction", math.nan))
    if not math.isclose(agreement, 0.9247555261676111, rel_tol=0.0, abs_tol=1e-15):
        raise BenchmarkIntegrityError("Hollywood2EM sensitivity raw agreement drifted.")
    interpretation = str(sensitivity.get("interpretation", "")).lower()
    if "sensitivity" not in interpretation or "not independent human-human" not in interpretation:
        raise BenchmarkIntegrityError(
            "Hollywood2EM student/expert comparison must remain annotation sensitivity, "
            "not independent human-human reliability."
        )

    semantics = _require_mapping(payload, "format_and_units", dataset_key=dataset_key)
    if semantics.get("arff_relation") != "gaze_labels":
        raise BenchmarkIntegrityError("Hollywood2EM ARFF relation drifted.")
    expected_attributes = [
        "time",
        "x",
        "y",
        "confidence",
        "handlabeller_1",
        "handlabeller_final",
    ]
    if semantics.get("attributes") != expected_attributes:
        raise BenchmarkIntegrityError("Hollywood2EM ARFF attribute schema drifted.")
    for key, expected in (
        ("time_unit", "microseconds"),
        ("coordinate_unit", "pixels"),
        ("native_sampling_rate_hz", 500.0),
        ("observed_median_file_rate_hz", 500.0),
    ):
        if semantics.get(key) != expected:
            raise BenchmarkIntegrityError(f"Hollywood2EM {key} drifted.")
    if semantics.get("coordinate_unit_verified") is not True:
        raise BenchmarkIntegrityError("Hollywood2EM coordinate-unit verification was lost.")
    if semantics.get("time_unit_verified") is not True:
        raise BenchmarkIntegrityError("Hollywood2EM time-unit verification was lost.")

    mapping = _require_mapping(payload, "mapping", dataset_key=dataset_key)
    for key in (
        "trial_clip_identity_file_bound",
        "trial_identity_mapping_verified",
        "file_subject_tokens_recovered",
    ):
        if mapping.get(key) is not True:
            raise BenchmarkIntegrityError(f"Hollywood2EM {key} must remain verified.")
    if tuple(mapping.get("file_subject_tokens", [])) != _HOLLYWOOD2_TOKENS:
        raise BenchmarkIntegrityError("Hollywood2EM file subject-token set drifted.")
    if mapping.get("participant_identity_mapping_verified") is not False:
        raise BenchmarkIntegrityError(
            "Hollywood2EM participant identity mapping must remain unresolved."
        )

    _require_hollywood2_rights(rights)

    evidence = _require_mapping(payload, "evidence", dataset_key=dataset_key)
    expected_evidence = {
        "record": (
            "validation/evidence/hollywood2/"
            "hollywood2-authoritative-ground-truth-evidence-v1.json"
        ),
        "evidence_fingerprint_sha256": _HOLLYWOOD2_EVIDENCE,
        "live_probe_record_type": "hollywood2-gin-live-probe-v2",
        "live_probe_fingerprint_sha256": _HOLLYWOOD2_PROBE,
    }
    if dict(evidence) != expected_evidence:
        raise BenchmarkIntegrityError(
            "Hollywood2EM evidence binding drifted from the reviewed recovered-source state."
        )

    fingerprint = _fingerprint(payload)
    _verify_optional_fingerprint(payload, fingerprint)
    return {
        "record_type": _RECORD_TYPE,
        "dataset": _HOLLYWOOD2_DATASET,
        "dataset_key": dataset_key,
        "checked_on": checked_on,
        "status": status,
        "record_fingerprint_sha256": fingerprint,
        "source_audit_ready": audit_ready,
        "empirical_evidence_created": empirical,
        "rights": {
            "analysis_use_terms_status": analysis,
            "raw_data_redistribution_terms_status": redistribution,
        },
        "source_state": {
            "canonical_distribution_identifier_found": canonical_found,
            "current_retrievable_copy_verified": current_copy,
            "authoritative_ground_truth_file_count": 697,
        },
        "annotation_independence": {
            "independent_annotation_streams_verified": False,
            "comparison_role": "annotation_sensitivity",
        },
        "claim_limits": claim_limits,
    }


def validate_gaze_in_wild_source_resolution_record(path: str | Path) -> dict[str, Any]:
    """Validate the conservative Gaze-in-the-Wild source-resolution checkpoint."""

    _, payload = _load_payload(path)
    dataset_key = "gaze-in-the-wild"
    (
        checked_on,
        status,
        audit_ready,
        empirical,
        rights,
        analysis,
        redistribution,
        claim_limits,
    ) = _validate_common(payload, dataset=_GAZE_IN_WILD_DATASET, dataset_key=dataset_key)

    published_identifier = _require_bool(
        payload,
        "published_distribution_identifier_found",
        dataset_key=dataset_key,
    )
    institutional_listing = _require_bool(
        payload,
        "current_institutional_dataset_listing_found",
        dataset_key=dataset_key,
    )
    direct_endpoint = _require_bool(
        payload,
        "current_direct_data_endpoint_verified",
        dataset_key=dataset_key,
    )
    if not published_identifier or not institutional_listing or direct_endpoint:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild v1 resolution must preserve the published distribution identity "
            "and current institutional listing while keeping direct exact-copy retrieval "
            "unverified."
        )

    publication = _require_mapping(payload, "authoritative_publication", dataset_key=dataset_key)
    if publication.get("doi") != "10.1038/s41598-020-59251-5":
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild source-resolution publication DOI is unexpected."
        )
    if publication.get("article_license_is_dataset_license") is not False:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild article licensing cannot be promoted into dataset-file licensing."
        )
    if rights.get("article_cc_by_is_dataset_license") is not False:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild CC BY article licensing cannot be treated as the dataset license."
        )
    if (
        rights.get("publication_public_availability_is_unrestricted_redistribution_permission")
        is not False
    ):
        raise BenchmarkIntegrityError(
            "Published Gaze-in-the-Wild availability cannot imply unrestricted redistribution."
        )

    annotation = _require_mapping(payload, "annotation_provenance", dataset_key=dataset_key)
    if annotation.get("published_trained_annotator_count") != 5:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild source-resolution must preserve the published five-annotator count."
        )
    if annotation.get("publication_states_annotators_decided_independently") is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild source-resolution must preserve published annotator independence."
        )
    if annotation.get("publication_independence_evidence_present") is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild published annotation-independence evidence cannot be discarded."
        )
    streams_verified = annotation.get("separately_recoverable_streams_verified_from_exact_copy")
    agreement_ready = annotation.get("human_human_agreement_execution_ready")
    if streams_verified is not False or agreement_ready is not False:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild human-human agreement must remain blocked until independently "
            "recoverable streams are verified from the exact copy."
        )

    sampling = _require_mapping(payload, "sampling_rate_provenance", dataset_key=dataset_key)
    if sampling.get("published_acquisition_hardware_rate_hz") != 120:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild primary publication hardware provenance must remain 120 Hz."
        )
    if sampling.get("secondary_evaluation_catalog_rate_hz") != 300:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild secondary catalog rate must remain separately identified as 300 Hz."
        )
    if sampling.get("rates_reconciled") is not False:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild 120 Hz and 300 Hz provenance cannot be silently reconciled."
        )
    if sampling.get("distributed_file_analysis_cadence_verified") is not False:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild distributed-file cadence must remain unverified at resolution stage."
        )
    method = str(sampling.get("required_resolution_method", "")).lower()
    if "timestamp" not in method:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild empirical cadence must be resolved from audited timestamps."
        )

    mapping = _require_mapping(payload, "mapping_and_coordinates", dataset_key=dataset_key)
    for key in (
        "participant_task_mapping_verified_from_exact_copy",
        "point_of_regard_coordinate_unit_verified_from_exact_copy",
    ):
        if mapping.get(key) is not False:
            raise BenchmarkIntegrityError(
                f"Gaze-in-the-Wild {key} must remain unverified until the exact copy is audited."
            )
    if mapping.get("verification_requires_exact_obtained_copy") is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild mapping/coordinate verification must require an exact obtained copy."
        )

    fingerprint = _fingerprint(payload)
    _verify_optional_fingerprint(payload, fingerprint)
    return {
        "record_type": _RECORD_TYPE,
        "dataset": _GAZE_IN_WILD_DATASET,
        "dataset_key": dataset_key,
        "checked_on": checked_on,
        "status": status,
        "record_fingerprint_sha256": fingerprint,
        "source_audit_ready": audit_ready,
        "empirical_evidence_created": empirical,
        "rights": {
            "analysis_use_terms_status": analysis,
            "raw_data_redistribution_terms_status": redistribution,
        },
        "source_state": {
            "published_distribution_identifier_found": published_identifier,
            "current_institutional_dataset_listing_found": institutional_listing,
            "current_direct_data_endpoint_verified": direct_endpoint,
        },
        "annotation_independence": {
            "published_independence": True,
            "separately_recoverable_streams_verified": False,
            "human_human_agreement_ready": False,
        },
        "sampling_rate_provenance": {
            "published_acquisition_hardware_rate_hz": 120,
            "secondary_evaluation_catalog_rate_hz": 300,
            "distributed_file_analysis_cadence_verified": False,
        },
        "claim_limits": claim_limits,
    }


def validate_source_resolution_record(path: str | Path) -> dict[str, Any]:
    """Validate a known v1 source-resolution checkpoint and auto-dispatch by dataset."""

    source, payload = _load_payload(path)
    if payload.get("record_type") != _RECORD_TYPE:
        raise BenchmarkIntegrityError(
            f"Source-resolution record_type must be {_RECORD_TYPE!r}."
        )

    dataset = str(payload.get("dataset", "")).strip()
    dataset_key = _DATASET_KEYS.get(dataset)
    if dataset_key is None:
        raise BenchmarkIntegrityError(
            "Unsupported source-resolution dataset. A reviewed validator is required before a new "
            "benchmark checkpoint can join the unified contract."
        )

    if dataset_key == "visus":
        summary = dict(validate_visus_source_resolution_record(source))
        if summary.get("status") != _EXPECTED_STATUS[dataset_key]:
            raise BenchmarkIntegrityError(
                "VISUS source-resolution status is not supported by the unified v1 contract."
            )
        summary["dataset_key"] = dataset_key
        return summary
    if dataset_key == "hollywood2em":
        return validate_hollywood2_source_resolution_record(source)
    return validate_gaze_in_wild_source_resolution_record(source)


def validate_source_resolution_records(paths: Sequence[str | Path]) -> dict[str, Any]:
    """Validate source-resolution checkpoints and fingerprint the reviewed bundle."""

    if not paths:
        raise ValueError("At least one source-resolution checkpoint path is required.")

    records = [validate_source_resolution_record(path) for path in paths]
    records.sort(key=lambda record: str(record["dataset_key"]))
    dataset_keys = [str(record["dataset_key"]) for record in records]
    if len(dataset_keys) != len(set(dataset_keys)):
        raise BenchmarkIntegrityError(
            "A source-resolution validation bundle cannot contain duplicate dataset checkpoints."
        )

    return {
        "bundle_type": _BUNDLE_TYPE,
        "record_count": len(records),
        "records": records,
        "bundle_fingerprint_sha256": _bundle_fingerprint(records),
    }


@dataclass(frozen=True, slots=True)
class SourceResolutionRecord:
    """Compact common identity for one validated benchmark source-resolution checkpoint."""

    path: Path
    dataset_key: str
    dataset: str
    checked_on: str
    status: str
    record_fingerprint_sha256: str
    source_audit_ready: bool
    empirical_evidence_created: bool
    analysis_use_terms_status: str
    raw_data_redistribution_terms_status: str


def load_source_resolution_record(path: str | Path) -> SourceResolutionRecord:
    """Return a typed common view after dataset-specific source-resolution validation."""

    source = Path(path)
    summary = validate_source_resolution_record(source)
    return SourceResolutionRecord(
        path=source,
        dataset_key=str(summary["dataset_key"]),
        dataset=str(summary["dataset"]),
        checked_on=str(summary["checked_on"]),
        status=str(summary["status"]),
        record_fingerprint_sha256=str(summary["record_fingerprint_sha256"]),
        source_audit_ready=bool(summary["source_audit_ready"]),
        empirical_evidence_created=bool(summary["empirical_evidence_created"]),
        analysis_use_terms_status=str(summary["rights"]["analysis_use_terms_status"]),
        raw_data_redistribution_terms_status=str(
            summary["rights"]["raw_data_redistribution_terms_status"]
        ),
    )
