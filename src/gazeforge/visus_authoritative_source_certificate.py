"""Manual authority/rights review and certificate for a VISUS source candidate."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .visus_authoritative_source_common import (
    CERTIFICATE_RECORD_TYPE,
    CERTIFICATE_STATUS,
    EXPECTED_PARTICIPANT_COUNT,
    EXPECTED_STIMULUS_COUNT,
    MAX_MANIFEST_BYTES,
    REVIEW_RECORD_TYPE,
    SOURCE_RECHECK_FINGERPRINT,
    _ALLOWED_AUTHORITY_CLAIMS,
    _ALLOWED_REDISTRIBUTION_STATUS,
    _CERTIFICATE_AUTHORITY_KEYS,
    _CERTIFICATE_INVENTORY_KEYS,
    _CERTIFICATE_KEYS,
    _CERTIFICATE_RIGHTS_KEYS,
    _CERTIFICATE_SOURCE_KEYS,
    _REVIEW_KEYS,
    _SCIENTIFIC_KEYS,
    _read_json,
    _require_exact_keys,
    _resolved_text,
    _sha256_value,
    certificate_fingerprint,
    review_fingerprint,
)
from .visus_authoritative_source_intake import (
    inspect_visus_authoritative_source_candidate,
    validate_candidate_record,
)


@dataclass(frozen=True, slots=True)
class ReviewedVisusSourceAuthority:
    """Reviewed source-authority certificate; no empirical VISUS audit is created."""

    certificate: dict[str, Any]


def _validate_review_timestamp(value: Any) -> str:
    text = _resolved_text(value, label="reviewed_at")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BenchmarkIntegrityError(
            "VISUS source-authority reviewed_at must be an ISO-8601 timestamp."
        ) from exc
    if parsed.tzinfo is None:
        raise BenchmarkIntegrityError(
            "VISUS source-authority reviewed_at must include a timezone offset."
        )
    return text


def validate_certificate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a reviewed source/rights certificate without creating empirical validity."""
    value = dict(record)
    _require_exact_keys(value, _CERTIFICATE_KEYS, label="certificate")
    if value.get("record_type") != CERTIFICATE_RECORD_TYPE:
        raise BenchmarkIntegrityError("VISUS source-authority certificate type drifted.")
    if value.get("status") != CERTIFICATE_STATUS:
        raise BenchmarkIntegrityError("VISUS source-authority certificate status drifted.")
    if value.get("authoritative_source_recheck_fingerprint_sha256") != SOURCE_RECHECK_FINGERPRINT:
        raise BenchmarkIntegrityError("VISUS certificate source-recheck binding drifted.")
    for field in (
        "candidate_fingerprint_sha256",
        "review_fingerprint_sha256",
        "certificate_fingerprint_sha256",
    ):
        _sha256_value(value.get(field), label=field)

    source = value.get("source")
    rights = value.get("rights")
    inventory = value.get("inventory")
    authority = value.get("authority_boundary")
    scientific = value.get("scientific_boundary")
    if not all(
        isinstance(item, Mapping)
        for item in (source, rights, inventory, authority, scientific)
    ):
        raise BenchmarkIntegrityError("VISUS source-authority certificate sections are missing.")
    assert isinstance(source, Mapping)
    assert isinstance(rights, Mapping)
    assert isinstance(inventory, Mapping)
    assert isinstance(authority, Mapping)
    assert isinstance(scientific, Mapping)
    _require_exact_keys(source, _CERTIFICATE_SOURCE_KEYS, label="certificate source")
    _require_exact_keys(rights, _CERTIFICATE_RIGHTS_KEYS, label="certificate rights")
    _require_exact_keys(inventory, _CERTIFICATE_INVENTORY_KEYS, label="certificate inventory")
    _require_exact_keys(
        authority,
        _CERTIFICATE_AUTHORITY_KEYS,
        label="certificate authority boundary",
    )
    _require_exact_keys(scientific, _SCIENTIFIC_KEYS, label="certificate scientific boundary")

    _sha256_value(source.get("artifact_sha256"), label="certificate source SHA-256")
    _resolved_text(source.get("source_reference"), label="certificate source_reference")
    _resolved_text(source.get("source_revision"), label="certificate source_revision")
    if source.get("source_authority_claim") not in _ALLOWED_AUTHORITY_CLAIMS:
        raise BenchmarkIntegrityError("VISUS certificate source authority class drifted.")
    _sha256_value(rights.get("evidence_sha256"), label="certificate rights evidence SHA-256")
    _resolved_text(rights.get("evidence_reference"), label="certificate rights evidence reference")
    _resolved_text(
        rights.get("license_or_terms_identifier"),
        label="certificate license_or_terms_identifier",
    )
    _sha256_value(inventory.get("fingerprint_sha256"), label="certificate inventory SHA-256")
    if not isinstance(inventory.get("file_count"), int) or inventory["file_count"] <= 0:
        raise BenchmarkIntegrityError("VISUS certificate inventory file count is invalid.")
    if inventory.get("published_participant_count") != EXPECTED_PARTICIPANT_COUNT:
        raise BenchmarkIntegrityError("VISUS certificate published participant count drifted.")
    if inventory.get("published_stimulus_count") != EXPECTED_STIMULUS_COUNT:
        raise BenchmarkIntegrityError("VISUS certificate published stimulus count drifted.")
    if rights.get("analysis_use_permitted") is not True:
        raise BenchmarkIntegrityError("VISUS source certificate requires analysis permission.")
    if rights.get("redistribution_status") not in _ALLOWED_REDISTRIBUTION_STATUS:
        raise BenchmarkIntegrityError("VISUS source certificate redistribution status drifted.")
    if rights.get("rights_scope_verified") is not True:
        raise BenchmarkIntegrityError("VISUS source certificate rights scope is not verified.")
    if rights.get("raw_source_redistribution_action_authorized") is not False:
        raise BenchmarkIntegrityError(
            "VISUS source certificate cannot itself authorize redistribution action."
        )
    if rights.get("raw_rights_text_copied_to_certificate") is not False:
        raise BenchmarkIntegrityError("VISUS source certificate leaked raw rights text.")
    for key in (
        "source_authority_verified",
        "current_authoritative_distribution_identity_verified",
        "source_artifact_matches_authoritative_distribution_verified",
        "extracted_tree_matches_source_artifact_verified",
        "source_audit_stage_authorized",
    ):
        if authority.get(key) is not True:
            raise BenchmarkIntegrityError(f"VISUS source certificate requires {key}=true.")
    for key, observed in scientific.items():
        if observed is not False:
            raise BenchmarkIntegrityError(f"VISUS source certificate must not promote {key}.")
    if value.get("certificate_fingerprint_sha256") != certificate_fingerprint(value):
        raise BenchmarkIntegrityError("VISUS source-authority certificate fingerprint drifted.")
    return value


def require_reviewed_visus_source_authority(
    root: str | Path,
    source_artifact_path: str | Path,
    rights_evidence_path: str | Path,
    manifest_path: str | Path,
    candidate_record: Mapping[str, Any],
    review_path: str | Path,
) -> ReviewedVisusSourceAuthority:
    """Promote only source authority/rights after exact replay and manual review."""
    candidate = validate_candidate_record(candidate_record)
    replayed = inspect_visus_authoritative_source_candidate(
        root,
        source_artifact_path,
        rights_evidence_path,
        manifest_path,
    )
    if replayed["candidate_fingerprint_sha256"] != candidate["candidate_fingerprint_sha256"]:
        raise BenchmarkIntegrityError(
            "VISUS source-authority candidate no longer matches the exact local inputs."
        )

    review = _read_json(
        Path(review_path),
        label="source-authority review",
        max_bytes=MAX_MANIFEST_BYTES,
    )
    _require_exact_keys(review, _REVIEW_KEYS, label="source-authority review")
    if review.get("record_type") != REVIEW_RECORD_TYPE:
        raise BenchmarkIntegrityError("VISUS source-authority review type drifted.")
    if review.get("decision") != "approved":
        raise BenchmarkIntegrityError("VISUS source authority requires decision='approved'.")
    if review.get("candidate_fingerprint_sha256") != candidate[
        "candidate_fingerprint_sha256"
    ]:
        raise BenchmarkIntegrityError(
            "VISUS source-authority review is not bound to this candidate."
        )
    _resolved_text(review.get("reviewer"), label="reviewer")
    _validate_review_timestamp(review.get("reviewed_at"))

    evidence_fields = (
        "source_authority_evidence",
        "current_distribution_identity_evidence",
        "source_artifact_match_evidence",
        "extracted_tree_match_evidence",
        "rights_evidence_authority_evidence",
        "analysis_use_evidence",
        "redistribution_evidence",
        "license_or_terms_identifier",
    )
    for field in evidence_fields:
        _resolved_text(review.get(field), label=field)
    for field in (
        "source_authority_verified",
        "current_authoritative_distribution_identity_verified",
        "source_artifact_matches_authoritative_distribution_verified",
        "extracted_tree_matches_source_artifact_verified",
        "rights_evidence_authoritative_verified",
        "analysis_use_permitted_verified",
        "rights_scope_limited_to_reviewed_source",
    ):
        if review.get(field) is not True:
            raise BenchmarkIntegrityError(f"VISUS approved source review requires {field}=true.")
    redistribution = str(review.get("redistribution_status_verified", "")).strip().lower()
    if redistribution not in _ALLOWED_REDISTRIBUTION_STATUS:
        raise BenchmarkIntegrityError(
            "VISUS approved source review requires a supported redistribution status."
        )
    for field in (
        "participant_mapping_verified",
        "stimulus_mapping_verified",
        "coordinate_basis_verified",
        "timestamp_basis_verified",
        "independent_annotation_streams_verified",
        "empirical_validation_created",
        "raw_source_redistributed",
    ):
        if review.get(field) is not False:
            raise BenchmarkIntegrityError(f"VISUS source review cannot promote {field}.")
    stored_review_fp = str(review.get("review_fingerprint_sha256", ""))
    if stored_review_fp != review_fingerprint(review):
        raise BenchmarkIntegrityError("VISUS source-authority review fingerprint drifted.")

    source = candidate["source"]
    rights_evidence = candidate["rights_evidence"]
    inventory = candidate["inventory"]
    assert isinstance(source, Mapping)
    assert isinstance(rights_evidence, Mapping)
    assert isinstance(inventory, Mapping)

    certificate: dict[str, Any] = {
        "record_type": CERTIFICATE_RECORD_TYPE,
        "status": CERTIFICATE_STATUS,
        "authoritative_source_recheck_fingerprint_sha256": SOURCE_RECHECK_FINGERPRINT,
        "candidate_fingerprint_sha256": candidate["candidate_fingerprint_sha256"],
        "review_fingerprint_sha256": stored_review_fp,
        "source": {
            "artifact_sha256": source["artifact_sha256"],
            "source_reference": source["source_reference"],
            "source_revision": source["source_revision"],
            "source_authority_claim": source["source_authority_claim"],
        },
        "rights": {
            "evidence_sha256": rights_evidence["sha256"],
            "evidence_reference": rights_evidence["reference"],
            "license_or_terms_identifier": str(review["license_or_terms_identifier"]).strip(),
            "analysis_use_permitted": True,
            "redistribution_status": redistribution,
            "rights_scope_verified": True,
            "raw_source_redistribution_action_authorized": False,
            "raw_rights_text_copied_to_certificate": False,
        },
        "inventory": {
            "file_count": inventory["file_count"],
            "fingerprint_sha256": inventory["fingerprint_sha256"],
            "published_participant_count": EXPECTED_PARTICIPANT_COUNT,
            "published_stimulus_count": EXPECTED_STIMULUS_COUNT,
        },
        "authority_boundary": {
            "source_authority_verified": True,
            "current_authoritative_distribution_identity_verified": True,
            "source_artifact_matches_authoritative_distribution_verified": True,
            "extracted_tree_matches_source_artifact_verified": True,
            "source_audit_stage_authorized": True,
        },
        "scientific_boundary": {
            "dataset_status_empirical_created": False,
            "participant_mapping_verified": False,
            "stimulus_mapping_verified": False,
            "coordinate_basis_verified": False,
            "timestamp_basis_verified": False,
            "independent_annotation_streams_verified": False,
            "human_human_agreement_created": False,
            "model_human_validation_created": False,
            "frozen_evidence_created": False,
            "raw_source_redistribution_action_authorized": False,
        },
    }
    certificate["certificate_fingerprint_sha256"] = certificate_fingerprint(certificate)
    validate_certificate_record(certificate)
    return ReviewedVisusSourceAuthority(certificate=certificate)
