"""Fail-closed validation for current first-party Gaze-in-the-Wild listing evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

EVIDENCE_RECORD_TYPE = "gaze-in-wild-current-first-party-listing-evidence-v1"
PROBE_RECORD_TYPE = "gaze-in-wild-current-first-party-listing-probe-v1"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "c2b9a19f43276e6bde08794f87212e4c2016a9e0ab3183dc4f8b69d310c02916"
)
EXPECTED_LISTING_STATE_FINGERPRINT_SHA256 = (
    "b7fcf78719cb23ce7133fe3fb51a757c561c5b25797f40de4a2e00b8e1c4f839"
)
REVIEWED_OBSERVATION_FINGERPRINT_SHA256 = (
    "a1660d1c70916b8af605f23c64518b4a50fdf59a649fd2fff460965474bae1e6"
)
PRIOR_DISTRIBUTION_EVIDENCE_FINGERPRINT_SHA256 = (
    "2400c81a0897fb414285069c368a8a9d96de1d18eb185b1073cf15bb1c8bd1da"
)
RIT_LAB_URL = "https://www.rit.edu/science/perception-movement-lab"
LISTING_TEXT = "The Gaze-In-Wild Dataset"
PUBLICATION_TARGET = "https://pubmed.ncbi.nlm.nih.gov/32054884/"
HISTORICAL_HTTPS_URL = "https://www.cis.rit.edu/~rsk3900/gaze-in-wild/"


@dataclass(frozen=True, slots=True)
class GazeInWildCurrentListingEvidence:
    """Compact identity for one reviewed current first-party listing state."""

    path: Path | None
    evidence_fingerprint_sha256: str
    listing_state_fingerprint_sha256: str
    listing_target: str
    current_exact_authoritative_copy_obtained: bool
    dataset_file_rights_resolved: bool


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return the canonical frozen-evidence fingerprint."""
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return _sha256(body)


def listing_state_fingerprint(record: Mapping[str, Any]) -> str:
    """Fingerprint only review-relevant live listing state, excluding transport diagnostics."""
    state = {
        "record_type": record.get("record_type"),
        "current_first_party_page": record.get("current_first_party_page"),
        "review_trigger": record.get("review_trigger"),
        "scientific_boundary": record.get("scientific_boundary"),
        "claim_limit": record.get("claim_limit"),
    }
    return _sha256(state)


def observation_fingerprint(record: Mapping[str, Any]) -> str:
    """Fingerprint one complete live observation, including non-gating transport diagnostics."""
    body = dict(record)
    body.pop("listing_state_fingerprint_sha256", None)
    body.pop("observation_fingerprint_sha256", None)
    return _sha256(body)


def _load(record_or_path: Mapping[str, Any] | str | Path) -> tuple[dict[str, Any], Path | None]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path), None
    path = Path(record_or_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load Gaze-in-the-Wild current-listing evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError("GIW current-listing evidence must contain one JSON object.")
    return payload, path


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"GIW current-listing field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"GIW current-listing {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"GIW current-listing must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"GIW current-listing must not promote {label}.")


def _validate_closed_scientific_boundary(boundary: Mapping[str, Any]) -> None:
    _true(boundary.get("current_first_party_listing_verified"), "first-party listing verification")
    for key in (
        "current_exact_authoritative_copy_obtained",
        "dataset_file_rights_resolved",
        "analysis_use_permitted",
        "redistribution_authorized",
        "participant_mapping_verified",
        "complete_trial_to_task_mapping_verified",
        "distributed_file_sampling_cadence_verified",
        "independent_labeller_recoverability_verified",
        "human_human_agreement_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_performance_created",
        "gp3_validity_created",
        "frozen_evidence_performance_claim_created",
    ):
        _false(boundary.get(key), key)
    if "original_distribution_equivalence_verified" in boundary:
        _false(
            boundary.get("original_distribution_equivalence_verified"),
            "original-distribution equivalence",
        )


def validate_gaze_in_wild_current_listing_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildCurrentListingEvidence:
    """Validate the dated frozen evidence and all non-promotion boundaries."""
    record, path = _load(record_or_path)
    _equal(record.get("record_type"), EVIDENCE_RECORD_TYPE, "evidence record type")
    _equal(record.get("reviewed_on"), "2026-09-06", "review date")
    _equal(
        record.get("dataset"),
        "Gaze-in-the-Wild naturalistic eye-head event benchmark",
        "dataset identity",
    )
    _equal(
        record.get("prior_distribution_evidence_fingerprint_sha256"),
        PRIOR_DISTRIBUTION_EVIDENCE_FINGERPRINT_SHA256,
        "prior distribution-evidence binding",
    )

    binding = _mapping(record, "live_probe_binding")
    _equal(binding.get("current_first_party_page_url"), RIT_LAB_URL, "first-party page URL")
    _equal(binding.get("listing_text"), LISTING_TEXT, "listing text")
    _equal(binding.get("listing_target"), PUBLICATION_TARGET, "listing target")
    _equal(binding.get("listing_target_class"), "publication_pubmed", "listing target class")
    _false(
        binding.get("listing_target_is_direct_dataset_archive_verified"),
        "direct-archive verification",
    )
    _equal(
        binding.get("listing_state_fingerprint_sha256"),
        EXPECTED_LISTING_STATE_FINGERPRINT_SHA256,
        "listing-state fingerprint",
    )
    _equal(
        binding.get("reviewed_observation_fingerprint_sha256"),
        REVIEWED_OBSERVATION_FINGERPRINT_SHA256,
        "reviewed observation fingerprint",
    )

    current = _mapping(record, "current_first_party_review")
    _true(current.get("current_first_party_listing_present"), "current first-party listing")
    _true(current.get("listing_points_to_publication_record"), "publication-target classification")
    for key in (
        "listing_points_to_direct_dataset_archive",
        "current_exact_authoritative_copy_obtained",
        "dataset_file_rights_terms_found_on_listing",
        "listing_page_copyright_is_dataset_file_license",
    ):
        _false(current.get(key), key)

    transport = _mapping(record, "historical_endpoint_transport_review")
    _equal(transport.get("url"), HISTORICAL_HTTPS_URL, "historical endpoint URL")
    _false(
        transport.get("github_actions_secure_tls_certificate_verified"),
        "GitHub Actions secure TLS verification",
    )
    _equal(
        transport.get("github_actions_secure_transport_failure_class"),
        "tls_certificate_verification_error",
        "GitHub Actions TLS failure class",
    )
    _equal(
        transport.get("github_actions_tls_unverified_fallback_http_status"),
        404,
        "reviewed GitHub Actions fallback status",
    )
    _equal(
        transport.get("interactive_web_fetch_observed_http_status"),
        502,
        "reviewed interactive-web status",
    )
    _true(
        transport.get("environment_specific_status_disagreement"),
        "environment-specific status disagreement",
    )
    for key in (
        "transport_status_is_source_identity_or_rights_evidence",
        "tls_unverified_fallback_is_source_authentication_evidence",
        "either_status_is_global_unavailability_proof",
        "either_status_is_exact_copy_identity_evidence",
    ):
        _false(transport.get(key), key)

    rights = _mapping(record, "rights_boundary")
    _equal(rights.get("article_license"), "CC BY 4.0", "article license")
    _equal(rights.get("processing_repository_license"), "MIT", "processing-repository license")
    _equal(rights.get("dataset_file_analysis_use_terms_status"), "unresolved", "analysis terms")
    _equal(
        rights.get("dataset_file_redistribution_terms_status"),
        "unresolved",
        "redistribution terms",
    )
    for key in (
        "article_license_is_external_dataset_file_license",
        "processing_repository_mit_is_external_dataset_file_license",
        "current_listing_provides_dataset_file_analysis_terms",
        "current_listing_provides_dataset_file_redistribution_terms",
        "analysis_use_permitted",
        "redistribution_authorized",
        "license_inference_permitted",
    ):
        _false(rights.get(key), key)

    exit_boundary = _mapping(record, "quarantine_exit_boundary")
    for key in (
        "current_listing_is_source_authority_for_an_exact_local_copy",
        "exact_copy_identity_verified",
        "dataset_file_rights_resolved",
        "reuse_terms_verified_for_dataset_files",
        "analysis_use_permitted",
        "redistribution_status_resolved",
        "quarantine_exit_authorizable_from_this_evidence",
    ):
        _false(exit_boundary.get(key), f"quarantine-exit {key}")

    _validate_closed_scientific_boundary(_mapping(record, "scientific_boundary"))
    _equal(
        record.get("evidence_fingerprint_sha256"),
        EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        "stored evidence fingerprint",
    )
    _equal(
        evidence_fingerprint(record),
        EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        "recomputed evidence fingerprint",
    )

    return GazeInWildCurrentListingEvidence(
        path=path,
        evidence_fingerprint_sha256=EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        listing_state_fingerprint_sha256=EXPECTED_LISTING_STATE_FINGERPRINT_SHA256,
        listing_target=PUBLICATION_TARGET,
        current_exact_authoritative_copy_obtained=False,
        dataset_file_rights_resolved=False,
    )


def validate_gaze_in_wild_current_listing_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildCurrentListingEvidence:
    """Bind a live probe to frozen listing state while treating transport as non-gating."""
    probe, _ = _load(probe_or_path)
    evidence = validate_gaze_in_wild_current_listing_evidence(evidence_or_path)
    _equal(probe.get("record_type"), PROBE_RECORD_TYPE, "live probe record type")

    page = _mapping(probe, "current_first_party_page")
    _equal(page.get("url"), RIT_LAB_URL, "live first-party page URL")
    _equal(page.get("observed_http_status"), 200, "live first-party page status")
    _equal(page.get("listing_text"), LISTING_TEXT, "live listing text")
    _true(page.get("listing_present_exactly_once"), "one live listing")
    _equal(page.get("listing_target"), PUBLICATION_TARGET, "live listing target")
    _equal(page.get("listing_target_class"), "publication_pubmed", "live target class")
    _true(page.get("listing_target_is_expected_publication"), "expected publication target")
    _false(page.get("listing_target_is_direct_dataset_archive_verified"), "live direct archive")
    _false(page.get("dataset_file_rights_terms_found_on_listing"), "live rights terms")

    review = _mapping(probe, "review_trigger")
    for key in (
        "listing_target_changed_from_expected_publication",
        "listing_target_is_first_party_rit_candidate",
        "requires_human_evidence_review",
        "automatic_source_or_rights_promotion_permitted",
        "historical_transport_observation_is_review_gate",
    ):
        _false(review.get(key), key)

    transport = _mapping(probe, "historical_endpoint_observation")
    _equal(transport.get("url"), HISTORICAL_HTTPS_URL, "live historical endpoint URL")
    status = transport.get("observed_http_status")
    if not isinstance(status, int) or isinstance(status, bool):
        raise BenchmarkIntegrityError(
            "GIW current-listing live transport status must be an integer."
        )
    for key in (
        "transport_status_is_source_identity_or_rights_evidence",
        "tls_unverified_fallback_is_source_authentication_evidence",
        "observation_is_global_unavailability_proof",
        "observation_is_exact_copy_identity_evidence",
    ):
        _false(transport.get(key), f"live transport {key}")

    _validate_closed_scientific_boundary(_mapping(probe, "scientific_boundary"))
    stored_listing = probe.get("listing_state_fingerprint_sha256")
    _equal(
        stored_listing,
        listing_state_fingerprint(probe),
        "live listing-state self-fingerprint",
    )
    _equal(
        stored_listing,
        evidence.listing_state_fingerprint_sha256,
        "frozen listing-state binding",
    )
    _equal(
        probe.get("observation_fingerprint_sha256"),
        observation_fingerprint(probe),
        "live observation self-fingerprint",
    )
    return evidence
