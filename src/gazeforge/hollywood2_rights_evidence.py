"""Validation for authoritative Hollywood2 underlying-source rights evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "hollywood2-underlying-source-rights-evidence-v1"
STATUS = "verified-authoritative-underlying-rights-context"
LIVE_RECORD_TYPE = "hollywood2-underlying-source-live-probe-v1"
LIVE_STATUS = "verified_institutional_underlying_gaze_source_probe"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "6227045c3cc831b3669b34ca74b955847df4b26fafbf825c9a1b5473e25bc943"
)
EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256 = (
    "1face6d676270165134f34a7956bf848d6422b69dbbfc2e2ecfdb9ac64688707"
)
DESCRIPTION_SHA256 = "305c5f6d7f977d419d40e60509f5b1ce7cdf58d57f91e8710313cb178493d6fe"
DESCRIPTION_TEXT_SHA256 = (
    "bc324312fa64119633a14a7bdd52283560bc25009beade4b4bd16fd18a7e7c06"
)
LICENCE_SHA256 = "a50bc0cc3f422f6220798acac9991d3c18cbec0533d5d9cfe88554690abfdc2f"
LICENCE_TEXT_SHA256 = "0824a62438326029f4337822279bb7ea7c5517d0bb32795cba5068dbde269557"
GIN_COMMIT = "870fa6d6209c9085260918d61433a0a2c70fd497"
GIN_TOKENS = (
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


@dataclass(frozen=True, slots=True)
class Hollywood2RightsEvidence:
    """Compact identity for the validated underlying-source rights record."""

    path: Path | None
    fingerprint_sha256: str
    live_probe_fingerprint_sha256: str
    participant_count: int
    analysis_use_terms_status: str
    raw_archive_redistribution_status: str


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _probe_fingerprint(record: Mapping[str, Any]) -> str:
    body = dict(record)
    body.pop("probe_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(record_or_path: Mapping[str, Any] | str | Path) -> tuple[dict[str, Any], Path | None]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path), None
    path = Path(record_or_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"Could not load Hollywood2 rights evidence: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError("Hollywood2 rights evidence must be a JSON object.")
    return payload, path


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"Hollywood2 rights evidence field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"Hollywood2 rights evidence {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"Hollywood2 rights evidence must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"Hollywood2 rights evidence must not promote {label}.")


def _validate_pages(record: Mapping[str, Any]) -> None:
    source = _mapping(record, "institutional_source")
    description = _mapping(source, "description_page")
    licence = _mapping(source, "licence_page")
    download = _mapping(source, "download_endpoint")

    _equal(
        description.get("requested_url"),
        "https://vision.imar.ro/eyetracking/description.php",
        "description URL",
    )
    _equal(description.get("final_url"), "http://vision.imar.ro/eyetracking/description.php", "description redirect")
    _equal(description.get("http_status"), 200, "description status")
    _equal(description.get("bytes"), 18184, "description bytes")
    _equal(description.get("sha256"), DESCRIPTION_SHA256, "description SHA-256")
    _equal(
        description.get("normalised_text_sha256"),
        DESCRIPTION_TEXT_SHA256,
        "description text SHA-256",
    )

    _equal(
        licence.get("requested_url"),
        "https://vision.imar.ro/eyetracking/license.php",
        "licence URL",
    )
    _equal(licence.get("final_url"), "https://vision.imar.ro/eyetracking/license.php", "licence redirect")
    _equal(licence.get("http_status"), 200, "licence status")
    _equal(licence.get("bytes"), 5503, "licence bytes")
    _equal(licence.get("sha256"), LICENCE_SHA256, "licence SHA-256")
    _equal(
        licence.get("normalised_text_sha256"),
        LICENCE_TEXT_SHA256,
        "licence text SHA-256",
    )

    _equal(
        download.get("requested_url"),
        "http://vision.imar.ro/eyetracking/getdata.php?filepath=data&filename=gaze_hollywood2.zip",
        "published archive endpoint",
    )
    _equal(download.get("published_archive_name"), "gaze_hollywood2.zip", "archive name")
    _equal(download.get("published_link_scheme"), "http", "published archive scheme")
    _equal(
        download.get("final_url"),
        "https://vision.imar.ro/eyetracking/main_login.php",
        "archive access redirect",
    )
    _equal(download.get("final_scheme"), "https", "archive final scheme")
    _equal(download.get("http_status"), 200, "archive access status")
    _equal(download.get("access_state"), "redirects_to_login_page", "archive access state")
    _false(download.get("anonymous_direct_archive_access_verified"), "anonymous archive access")
    _false(download.get("authenticated_archive_access_tested"), "authenticated archive access")
    _false(download.get("full_corpus_downloaded"), "corpus-byte acquisition")


def validate_hollywood2_rights_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the frozen institutional source-and-rights context."""

    record, _ = _load(record_or_path)
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("checked_on"), "2026-09-05", "review date")
    _validate_pages(record)

    context = _mapping(record, "recording_context")
    _equal(context.get("participant_count"), 16, "participant count")
    _equal(context.get("active_participant_count"), 12, "active participant count")
    _equal(context.get("free_viewing_participant_count"), 4, "free-viewing participant count")
    _equal(context.get("sampling_rate_hz"), 500.0, "sampling rate")
    _equal(context.get("eye_tracker"), "SMI iView X HiSpeed 1250", "eye tracker")
    _equal(context.get("display_resolution_pixels"), [1280, 1024], "display resolution")
    _equal(context.get("display_size_cm"), [47.5, 29.5], "display size")
    _equal(context.get("viewing_distance_cm"), 60.0, "viewing distance")

    rights = _mapping(record, "underlying_rights")
    _true(rights.get("academic_use_only"), "academic-use-only scope")
    _true(
        rights.get("limited_nonexclusive_nonassignable_nontransferable"),
        "limited non-transferable grant",
    )
    _false(rights.get("standard_grant_allows_dataset_transfer"), "dataset transfer")
    _true(rights.get("citation_of_mathe_sminchisescu_papers_required"), "citation requirement")
    _true(
        rights.get("commercial_or_other_unpermitted_use_requires_prior_permission"),
        "permission requirement for other uses",
    )
    _equal(rights.get("analysis_use_terms_status"), "verified_academic_use_only", "analysis-use status")
    _equal(
        rights.get("raw_archive_redistribution_status"),
        "not_permitted_under_standard_grant",
        "raw-archive redistribution status",
    )
    _equal(rights.get("license_scope"), "underlying_hollywood2_gaze_distribution", "licence scope")
    _false(rights.get("article_cc_by_is_dataset_license"), "article licence as dataset licence")

    annotation = _mapping(record, "annotation_repository_rights")
    _equal(annotation.get("commit_sha1"), GIN_COMMIT, "GIN commit")
    _false(annotation.get("repository_license_file_recovered"), "GIN licence-file recovery")
    _equal(annotation.get("analysis_use_terms_status"), "unresolved", "GIN analysis-use status")
    _equal(
        annotation.get("raw_data_redistribution_terms_status"),
        "unresolved",
        "GIN redistribution status",
    )
    _false(annotation.get("dataset_specific_license_verified"), "GIN dataset licence verification")
    _false(
        annotation.get("underlying_license_automatically_applies_to_annotation_repository"),
        "automatic licence inheritance",
    )
    _false(annotation.get("article_cc_by_is_dataset_license"), "article licence as GIN dataset licence")
    _false(annotation.get("license_inference_permitted"), "licence inference")

    mapping = _mapping(record, "participant_mapping")
    _equal(mapping.get("published_participant_count"), 16, "mapping participant count")
    _equal(mapping.get("published_active_count"), 12, "mapping active count")
    _equal(mapping.get("published_free_viewing_count"), 4, "mapping free-viewing count")
    _equal(tuple(mapping.get("gin_file_subject_tokens", [])), GIN_TOKENS, "GIN subject tokens")
    _equal(mapping.get("gin_file_subject_token_count"), 16, "GIN token count")
    _true(mapping.get("token_count_matches_published_participant_count"), "token-count cross-check")
    _false(mapping.get("file_subject_token_to_participant_mapping_verified"), "token mapping")
    _false(mapping.get("participant_group_membership_by_file_token_verified"), "token group mapping")
    _false(mapping.get("mapping_inference_permitted"), "participant mapping inference")

    boundary = _mapping(record, "scientific_boundary")
    for key, label in (
        ("underlying_hollywood2_gaze_source_identified", "underlying source identification"),
        ("underlying_hollywood2_current_description_verified", "current description verification"),
        ("underlying_hollywood2_current_licence_verified", "current licence verification"),
        ("underlying_hollywood2_download_endpoint_resolved", "download endpoint resolution"),
        ("underlying_hollywood2_current_rights_context_frozen", "rights-context freeze"),
        (
            "underlying_hollywood2_standard_academic_analysis_use_verified",
            "academic analysis-use verification",
        ),
        (
            "underlying_hollywood2_standard_raw_archive_redistribution_not_permitted",
            "standard raw-archive redistribution restriction",
        ),
    ):
        _true(boundary.get(key), label)
    for key, label in (
        ("underlying_hollywood2_corpus_bytes_downloaded", "corpus-byte acquisition"),
        ("underlying_hollywood2_archive_manifest_verified", "archive-manifest verification"),
        ("gin_annotation_repository_license_verified", "GIN licence verification"),
        ("gin_annotation_repository_redistribution_verified", "GIN redistribution verification"),
        ("annotation_repository_rights_resolved", "GIN rights resolution"),
        ("file_subject_token_to_participant_mapping_verified", "participant token mapping"),
        ("participant_group_membership_by_file_token_verified", "participant group mapping"),
        ("participant_identity_mapping_verified", "participant identity mapping"),
        ("model_validation_created", "model validation"),
        ("participant_disjoint_model_validation_created", "participant-disjoint validation"),
        ("cross_dataset_validation_created", "cross-dataset validation"),
        ("frozen_evidence_performance_claim_created", "performance evidence"),
    ):
        _false(boundary.get(key), label)

    execution = _mapping(record, "execution")
    _equal(execution.get("live_probe_record_type"), LIVE_RECORD_TYPE, "live probe type")
    _equal(
        execution.get("live_probe_fingerprint_sha256"),
        EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256,
        "live probe fingerprint",
    )

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    calculated = evidence_fingerprint(record)
    if stored != calculated:
        raise BenchmarkIntegrityError("Hollywood2 rights evidence self-fingerprint is invalid.")
    if stored != EXPECTED_EVIDENCE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError("Hollywood2 rights evidence immutable v1 fingerprint drifted.")
    return record


def validate_hollywood2_underlying_source_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Bind a fresh institutional probe to the frozen rights-context evidence."""

    evidence = validate_hollywood2_rights_evidence(evidence_or_path)
    probe, _ = _load(probe_or_path)
    _equal(probe.get("record_type"), LIVE_RECORD_TYPE, "live record type")
    _equal(probe.get("status"), LIVE_STATUS, "live status")
    stored = str(probe.get("probe_fingerprint_sha256", ""))
    if stored != _probe_fingerprint(probe):
        raise BenchmarkIntegrityError("Hollywood2 underlying-source live probe self-fingerprint is invalid.")
    if stored != EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError("Hollywood2 institutional source or rights page drifted.")

    expected = evidence["institutional_source"]
    for section in ("description_page", "licence_page"):
        live_section = _mapping(probe, section)
        frozen_section = _mapping(expected, section)
        for key in (
            "requested_url",
            "final_url",
            "http_status",
            "content_type",
            "bytes",
            "sha256",
            "normalised_text_sha256",
        ):
            _equal(live_section.get(key), frozen_section.get(key), f"live {section} {key}")

    live_download = _mapping(probe, "download_endpoint")
    frozen_download = _mapping(expected, "download_endpoint")
    for key in (
        "requested_url",
        "published_link_scheme",
        "final_url",
        "final_scheme",
        "transport_encrypted",
        "probe_method",
        "http_status",
        "content_type",
        "content_length",
        "content_range",
        "content_disposition",
        "accept_ranges",
        "sampled_bytes",
        "full_corpus_downloaded",
    ):
        _equal(live_download.get(key), frozen_download.get(key), f"live download {key}")

    _equal(probe.get("verified_recording_context"), evidence["recording_context"], "live recording context")
    live_rights = _mapping(probe, "verified_underlying_rights")
    frozen_rights = evidence["underlying_rights"]
    for key in (
        "academic_use_only",
        "limited_nonexclusive_nonassignable_nontransferable",
        "standard_grant_allows_dataset_transfer",
        "citation_of_mathe_sminchisescu_papers_required",
        "commercial_or_other_unpermitted_use_requires_prior_permission",
    ):
        _equal(live_rights.get(key), frozen_rights.get(key), f"live rights {key}")
    return evidence


def load_hollywood2_rights_evidence(path: str | Path) -> Hollywood2RightsEvidence:
    """Load the frozen rights context into a compact typed identity."""

    record, record_path = _load(path)
    record = validate_hollywood2_rights_evidence(record)
    rights = record["underlying_rights"]
    return Hollywood2RightsEvidence(
        path=record_path,
        fingerprint_sha256=str(record["evidence_fingerprint_sha256"]),
        live_probe_fingerprint_sha256=str(record["execution"]["live_probe_fingerprint_sha256"]),
        participant_count=int(record["recording_context"]["participant_count"]),
        analysis_use_terms_status=str(rights["analysis_use_terms_status"]),
        raw_archive_redistribution_status=str(rights["raw_archive_redistribution_status"]),
    )
