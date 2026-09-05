"""Fail-closed validation for reviewed Gaze-in-the-Wild distribution evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "gaze-in-wild-distribution-availability-evidence-v1"
STATUS = "authoritative_historical_distribution_identified_current_exact_copy_unretrieved"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "2400c81a0897fb414285069c368a8a9d96de1d18eb185b1073cf15bb1c8bd1da"
)
PINNED_PROCESSING_COMMIT = "52262d44e366a53369e10ca73c5f41daf0e8f1e5"
HISTORICAL_DISTRIBUTION_URL = "http://www.cis.rit.edu/~rsk3900/gaze-in-wild/"


@dataclass(frozen=True, slots=True)
class GazeInWildDistributionAvailabilityEvidence:
    """Compact identity for reviewed GIW distribution-availability evidence."""

    path: Path | None
    fingerprint_sha256: str
    historical_distribution_identity_verified: bool
    current_exact_copy_obtained: bool
    dataset_file_rights_resolved: bool


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return canonical SHA-256 excluding the stored evidence fingerprint."""

    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(
    record_or_path: Mapping[str, Any] | str | Path,
) -> tuple[dict[str, Any], Path | None]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path), None
    path = Path(record_or_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load Gaze-in-the-Wild distribution evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild distribution evidence must contain one JSON object."
        )
    return payload, path


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild distribution field {key!r} is missing."
        )
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild distribution {label} drifted."
        )


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild distribution must preserve {label}."
        )


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild distribution must not promote {label}."
        )


def validate_gaze_in_wild_distribution_availability_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildDistributionAvailabilityEvidence:
    """Validate the reviewed evidence and its non-promotion boundaries."""

    record, path = _load(record_or_path)
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("checked_on"), "2026-09-05", "review date")
    _equal(
        record.get("dataset"),
        "Gaze-in-the-Wild naturalistic eye-head event benchmark",
        "dataset identity",
    )

    scope = _mapping(record, "scope")
    _equal(
        scope.get("authoritative_publication_doi"),
        "10.1038/s41598-020-59251-5",
        "DOI",
    )
    _equal(
        scope.get("authoritative_processing_repository"),
        "https://github.com/RSKothari/Gaze-in-Wild",
        "processing repository",
    )
    _equal(
        scope.get("pinned_processing_commit_sha1"),
        PINNED_PROCESSING_COMMIT,
        "pinned commit",
    )
    _equal(
        scope.get("historical_distribution_url"),
        HISTORICAL_DISTRIBUTION_URL,
        "historical distribution URL",
    )

    first_party = _mapping(record, "authoritative_first_party_evidence")
    for key in (
        "publication_states_compressed_data_and_code_publicly_available",
        "publication_distribution_url_matches_historical_url",
        "processing_repository_readme_directs_users_to_same_historical_url_for_all_data_files",
        "processing_repository_readme_states_raw_data_over_14tb_not_provided_online",
        "processing_repository_readme_states_contact_authors_for_raw_data",
    ):
        _true(first_party.get(key), key)
    _false(
        first_party.get("current_exact_compressed_copy_obtained"),
        "a current exact compressed copy",
    )

    retrieval = _mapping(record, "current_retrieval_observation")
    _equal(
        retrieval.get("https_historical_url_observed_http_status"),
        502,
        "dated retrieval status",
    )
    _false(retrieval.get("retrieval_succeeded"), "successful retrieval")
    _false(
        retrieval.get("observation_is_global_unavailability_proof"),
        "global unavailability proof",
    )
    _false(
        retrieval.get("observation_is_exact_copy_identity_evidence"),
        "exact-copy evidence",
    )

    replacement = _mapping(record, "replacement_source_search")
    _false(
        replacement.get("authoritative_replacement_dataset_doi_found"),
        "an authoritative replacement DOI",
    )
    _false(
        replacement.get("authoritative_replacement_repository_found"),
        "an authoritative replacement repository",
    )
    _false(
        replacement.get("current_rit_lab_listing_is_direct_archive"),
        "the current RIT listing as a direct archive",
    )

    leads = record.get("secondary_recovery_leads")
    if not isinstance(leads, list) or len(leads) != 2:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild distribution evidence must preserve exactly two "
            "reviewed secondary recovery leads."
        )
    for lead in leads:
        if not isinstance(lead, Mapping):
            raise BenchmarkIntegrityError(
                "GIW secondary recovery leads must be mappings."
            )
    mirror, labeller = leads
    _equal(
        mirror.get("repository"),
        "https://github.com/Morris88826/awesome-eye-data",
        "secondary mirror repository",
    )
    for key in (
        "authoritative_first_party_copy_verified",
        "exact_processdata_labeldata_copy_verified",
        "dataset_file_rights_verified",
        "empirical_analysis_eligible",
    ):
        _false(mirror.get(key), f"secondary mirror {key}")
    _equal(
        labeller.get("repository"),
        "https://github.com/George614/edit_distance_gpu",
        "labeller recovery lead repository",
    )
    _true(
        labeller.get("separately_named_labeller_files_are_provenance_lead_only"),
        "labeller filenames as provenance-only evidence",
    )
    for key in (
        "authoritative_source_verified",
        "shared_gaze_identity_verified",
        "independent_stream_recoverability_verified",
        "human_human_agreement_eligible",
    ):
        _false(labeller.get(key), f"labeller lead {key}")

    rights = _mapping(record, "rights_boundary")
    _equal(rights.get("article_license"), "CC BY 4.0", "article license")
    _false(
        rights.get("article_license_is_external_dataset_file_license"),
        "article license as dataset-file license",
    )
    _equal(
        rights.get("processing_repository_license"),
        "MIT",
        "processing repository license",
    )
    _equal(
        rights.get("processing_repository_license_scope"),
        "software and associated documentation files",
        "processing repository license scope",
    )
    _false(
        rights.get("processing_repository_mit_is_external_dataset_file_license"),
        "MIT as external dataset-file license",
    )
    _equal(
        rights.get("dataset_file_analysis_use_terms_status"),
        "unresolved",
        "analysis-use terms",
    )
    _equal(
        rights.get("dataset_file_redistribution_terms_status"),
        "unresolved",
        "redistribution terms",
    )
    _false(rights.get("license_inference_permitted"), "license inference")

    boundary = _mapping(record, "scientific_boundary")
    _true(
        boundary.get("authoritative_historical_distribution_identity_verified"),
        "historical distribution identity",
    )
    for key in (
        "current_exact_authoritative_copy_obtained",
        "exact_distributed_participant_identity_mapping_verified",
        "complete_trial_to_task_mapping_verified",
        "distributed_file_sampling_cadence_verified",
        "separately_recoverable_independent_labeller_streams_verified",
        "human_human_agreement_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_performance_created",
        "gp3_validity_created",
        "frozen_evidence_performance_claim_created",
    ):
        _false(boundary.get(key), key)

    stored = record.get("evidence_fingerprint_sha256")
    _equal(
        stored,
        EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        "stored evidence fingerprint",
    )
    _equal(
        evidence_fingerprint(record),
        EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        "recomputed evidence fingerprint",
    )

    return GazeInWildDistributionAvailabilityEvidence(
        path=path,
        fingerprint_sha256=EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        historical_distribution_identity_verified=True,
        current_exact_copy_obtained=False,
        dataset_file_rights_resolved=False,
    )
