"""First-party Gaze-in-the-Wild archive/rights resolution request and response intake.

This module deliberately separates a public request for clarification from any later
correspondence, exact-copy verification, source-audit authorization, or empirical work.
Raw correspondence is hashed locally and is not serialized into the structured response
record by default.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_current_listing_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256 as CURRENT_LISTING_EVIDENCE_FINGERPRINT,
)
from .gaze_in_wild_current_listing_evidence import (
    EXPECTED_LISTING_STATE_FINGERPRINT_SHA256,
    GazeInWildCurrentListingEvidence,
    validate_gaze_in_wild_current_listing_evidence,
)
from .gaze_in_wild_distribution_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256 as DISTRIBUTION_EVIDENCE_FINGERPRINT,
)
from .gaze_in_wild_distribution_evidence import (
    GazeInWildDistributionAvailabilityEvidence,
    validate_gaze_in_wild_distribution_availability_evidence,
)

REQUEST_RECORD_TYPE = "gaze-in-wild-first-party-resolution-request-v1"
RESPONSE_RECORD_TYPE = "gaze-in-wild-first-party-resolution-response-v1"
EXPECTED_REQUEST_FINGERPRINT_SHA256 = (
    "39ae27429a6a23c2fc07125e8f500b9d8d2ceb133c59e52d7379225007a7d6db"
)
DATASET = "Gaze-in-the-Wild naturalistic eye-head event benchmark"
PREPARED_ON = "2026-09-06"
HISTORICAL_DISTRIBUTION_URL = "http://www.cis.rit.edu/~rsk3900/gaze-in-wild/"
CURRENT_LISTING_URL = "https://www.rit.edu/science/perception-movement-lab"
CURRENT_LISTING_TARGET = "https://pubmed.ncbi.nlm.nih.gov/32054884/"

_ALLOWED_REVIEW_STATUS = {"pending_review", "reviewed"}
_ALLOWED_AUTHORITY_STATUS = {"unresolved", "verified", "not_verified"}
_ALLOWED_RIGHTS_STATUS = {"unresolved", "permitted", "restricted", "prohibited"}
_ALLOWED_LOCATION_STATUS = {"unresolved", "provided", "not_available"}
_ALLOWED_METADATA_STATUS = {"unresolved", "provided", "not_available", "not_confirmed"}
_ALLOWED_RIGHTS_BASIS = {"none", "explicit_first_party_statement", "formal_dataset_terms"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UNRESOLVED_TEXT = {"", "review_required", "__unresolved__", "unknown", "none", "nan"}
_FORBIDDEN_CORRESPONDENCE_KEYS = {
    "body",
    "message_body",
    "raw_body",
    "raw_correspondence",
    "correspondence_text",
    "transcript",
}


@dataclass(frozen=True, slots=True)
class GazeInWildFirstPartyResolutionRequest:
    """Validated identity of the public first-party clarification request."""

    path: Path | None
    request_fingerprint_sha256: str
    distribution_evidence_fingerprint_sha256: str
    current_listing_evidence_fingerprint_sha256: str
    current_listing_state_fingerprint_sha256: str


@dataclass(frozen=True, slots=True)
class GazeInWildFirstPartyResolutionResponse:
    """Privacy-safe structured findings bound to one local correspondence file."""

    path: Path | None
    response_fingerprint_sha256: str
    request_fingerprint_sha256: str
    correspondence_sha256: str
    review_status: str
    authority_status: str
    analysis_use_status: str
    redistribution_status: str
    authoritative_archive_location_status: str


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _fingerprint(record: Mapping[str, Any], stored_field: str) -> str:
    body = dict(record)
    body.pop(stored_field, None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def request_fingerprint(record: Mapping[str, Any]) -> str:
    """Return canonical request SHA-256 excluding its stored fingerprint."""

    return _fingerprint(record, "request_fingerprint_sha256")


def response_fingerprint(record: Mapping[str, Any]) -> str:
    """Return canonical response-evidence SHA-256 excluding its stored fingerprint."""

    return _fingerprint(record, "response_fingerprint_sha256")


def correspondence_sha256(path: str | Path) -> str:
    """Hash a local correspondence file without serializing its contents."""

    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(file_path)
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json_object(
    value: Mapping[str, Any] | str | Path,
    *,
    label: str,
) -> tuple[dict[str, Any], Path | None]:
    if isinstance(value, Mapping):
        return dict(value), None
    path = Path(value)
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"{label} must be valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"{label} must contain one JSON object.")
    return payload, path


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"GIW first-party resolution field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"GIW first-party resolution {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"GIW first-party resolution must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"GIW first-party resolution must not promote {label}.")


def _resolved_text(value: Any, label: str) -> str:
    text = "" if value is None else str(value).strip()
    if text.lower() in _UNRESOLVED_TEXT:
        raise BenchmarkIntegrityError(f"GIW first-party resolution requires reviewed {label}.")
    return text


def _sha256(value: Any, label: str) -> str:
    digest = str(value).strip().lower()
    if _SHA256_RE.fullmatch(digest) is None:
        raise BenchmarkIntegrityError(f"GIW first-party resolution {label} must be SHA-256.")
    return digest


def _validate_parent_evidence(
    distribution_evidence: Mapping[str, Any] | str | Path,
    current_listing_evidence: Mapping[str, Any] | str | Path,
) -> tuple[GazeInWildDistributionAvailabilityEvidence, GazeInWildCurrentListingEvidence]:
    distribution = validate_gaze_in_wild_distribution_availability_evidence(
        distribution_evidence
    )
    current = validate_gaze_in_wild_current_listing_evidence(current_listing_evidence)
    _equal(
        distribution.fingerprint_sha256,
        DISTRIBUTION_EVIDENCE_FINGERPRINT,
        "distribution-evidence parent fingerprint",
    )
    _equal(
        current.evidence_fingerprint_sha256,
        CURRENT_LISTING_EVIDENCE_FINGERPRINT,
        "current-listing parent fingerprint",
    )
    return distribution, current


def _expected_request_body() -> dict[str, Any]:
    return {
        "record_type": REQUEST_RECORD_TYPE,
        "dataset": DATASET,
        "prepared_on": PREPARED_ON,
        "purpose": (
            "Request first-party clarification of the current authoritative compressed "
            "distribution and dataset-file reuse terms without inferring rights from "
            "public-availability statements."
        ),
        "evidence_binding": {
            "historical_distribution_evidence_fingerprint_sha256": (
                DISTRIBUTION_EVIDENCE_FINGERPRINT
            ),
            "current_listing_evidence_fingerprint_sha256": (
                CURRENT_LISTING_EVIDENCE_FINGERPRINT
            ),
            "current_listing_state_fingerprint_sha256": (
                EXPECTED_LISTING_STATE_FINGERPRINT_SHA256
            ),
            "historical_distribution_url": HISTORICAL_DISTRIBUTION_URL,
            "current_first_party_listing_url": CURRENT_LISTING_URL,
            "current_listing_target": CURRENT_LISTING_TARGET,
        },
        "first_party_contact_candidates": [
            {
                "name": "Gabriel J. Diaz",
                "email": "gabriel.diaz@rit.edu",
                "role_basis": "current Director, RIT Perception for Movement Lab",
                "contact_status": "current_institutional_contact",
                "source": "https://www.rit.edu/science/directory/gjdgis-gabriel-diaz",
            },
            {
                "name": "Rakshit Kothari",
                "email": "rsk3900@rit.edu",
                "role_basis": (
                    "historical corresponding-author contact in the Gaze-in-the-Wild publication"
                ),
                "contact_status": "historical_published_contact_current_delivery_not_verified",
                "source": "https://pubmed.ncbi.nlm.nih.gov/32054884/",
            },
        ],
        "questions": [
            {
                "id": "Q1",
                "topic": "current_authoritative_distribution",
                "text": (
                    "What is the current authoritative location or access route for the compressed "
                    "Gaze-in-the-Wild distribution used with the published processing code, "
                    "including ProcessData and LabelData?"
                ),
            },
            {
                "id": "Q2",
                "topic": "archive_identity",
                "text": (
                    "If a current archive or replacement copy is available, is it the original "
                    "compressed public distribution or a canonical replacement, and how can "
                    "exact-copy identity be verified?"
                ),
            },
            {
                "id": "Q3",
                "topic": "analysis_use_terms",
                "text": (
                    "What terms explicitly govern analysis/research use of the dataset files "
                    "themselves, separate from the article licence and processing-code licence?"
                ),
            },
            {
                "id": "Q4",
                "topic": "redistribution_terms",
                "text": (
                    "May the dataset files themselves be redistributed, mirrored, or bundled with "
                    "research software, and under what exact terms or restrictions?"
                ),
            },
            {
                "id": "Q5",
                "topic": "derived_outputs",
                "text": (
                    "May derived metrics, trained-model outputs, validation reports, and "
                    "non-reconstructive aggregate results be published if dataset-file "
                    "redistribution is restricted?"
                ),
            },
            {
                "id": "Q6",
                "topic": "authority",
                "text": (
                    "Who currently has authority to confirm or grant these dataset-file reuse and "
                    "redistribution terms?"
                ),
            },
            {
                "id": "Q7",
                "topic": "participant_trial_metadata",
                "text": (
                    "If available, what authoritative metadata defines participant identities and "
                    "the complete TrIdx-to-task mapping in the compressed distribution?"
                ),
            },
            {
                "id": "Q8",
                "topic": "signal_metadata",
                "text": (
                    "If available, what authoritative metadata defines distributed-file coordinate "
                    "units/semantics and sampling cadence?"
                ),
            },
            {
                "id": "Q9",
                "topic": "labeller_streams",
                "text": (
                    "If available, are independently created labeller streams separately "
                    "recoverable for the same gaze samples, and how are those streams identified "
                    "in the authoritative distribution?"
                ),
            },
        ],
        "request_boundary": {
            "request_itself_grants_analysis_permission": False,
            "request_itself_grants_redistribution_permission": False,
            "public_availability_statement_is_dataset_file_license": False,
            "article_cc_by_is_dataset_file_license": False,
            "processing_repository_mit_is_dataset_file_license": False,
            "contact_email_domain_alone_proves_rights_authority": False,
            "response_alone_verifies_exact_copy_identity": False,
            "empirical_evidence_created": False,
        },
        "privacy_boundary": {
            "request_contains_private_correspondence": False,
            "response_workflow_commits_raw_correspondence_by_default": False,
        },
    }


def build_gaze_in_wild_first_party_resolution_request(
    distribution_evidence: Mapping[str, Any] | str | Path,
    current_listing_evidence: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Build the deterministic public request after validating both parent evidence records."""

    _validate_parent_evidence(distribution_evidence, current_listing_evidence)
    record = _expected_request_body()
    record["request_fingerprint_sha256"] = request_fingerprint(record)
    _equal(
        record["request_fingerprint_sha256"],
        EXPECTED_REQUEST_FINGERPRINT_SHA256,
        "generated request fingerprint",
    )
    return record


def validate_gaze_in_wild_first_party_resolution_request(
    request_or_path: Mapping[str, Any] | str | Path,
    distribution_evidence: Mapping[str, Any] | str | Path,
    current_listing_evidence: Mapping[str, Any] | str | Path,
) -> GazeInWildFirstPartyResolutionRequest:
    """Validate the exact public request and its immutable evidence lineage."""

    _validate_parent_evidence(distribution_evidence, current_listing_evidence)
    record, path = _load_json_object(
        request_or_path,
        label="Gaze-in-the-Wild first-party resolution request",
    )
    expected = _expected_request_body()
    for key, value in expected.items():
        _equal(record.get(key), value, f"request field {key}")
    _equal(set(record), set(expected) | {"request_fingerprint_sha256"}, "request schema")
    _equal(
        record.get("request_fingerprint_sha256"),
        EXPECTED_REQUEST_FINGERPRINT_SHA256,
        "stored request fingerprint",
    )
    _equal(
        request_fingerprint(record),
        EXPECTED_REQUEST_FINGERPRINT_SHA256,
        "recomputed request fingerprint",
    )
    return GazeInWildFirstPartyResolutionRequest(
        path=path,
        request_fingerprint_sha256=EXPECTED_REQUEST_FINGERPRINT_SHA256,
        distribution_evidence_fingerprint_sha256=DISTRIBUTION_EVIDENCE_FINGERPRINT,
        current_listing_evidence_fingerprint_sha256=CURRENT_LISTING_EVIDENCE_FINGERPRINT,
        current_listing_state_fingerprint_sha256=EXPECTED_LISTING_STATE_FINGERPRINT_SHA256,
    )


def build_gaze_in_wild_first_party_resolution_response_scaffold(
    correspondence_path: str | Path,
    request: GazeInWildFirstPartyResolutionRequest,
) -> dict[str, Any]:
    """Create a pending privacy-safe response scaffold bound only to a local message digest."""

    if not isinstance(request, GazeInWildFirstPartyResolutionRequest):
        raise TypeError("request must be a validated GazeInWildFirstPartyResolutionRequest.")
    record: dict[str, Any] = {
        "record_type": RESPONSE_RECORD_TYPE,
        "dataset": DATASET,
        "request_fingerprint_sha256": request.request_fingerprint_sha256,
        "correspondence_sha256": correspondence_sha256(correspondence_path),
        "received_on": "REVIEW_REQUIRED",
        "channel": "REVIEW_REQUIRED",
        "sender": {
            "name": "REVIEW_REQUIRED",
            "email_or_identifier": "REVIEW_REQUIRED",
            "claimed_role": "REVIEW_REQUIRED",
        },
        "review": {
            "status": "pending_review",
            "reviewer": "REVIEW_REQUIRED",
            "reviewed_on": "REVIEW_REQUIRED",
            "notes": [],
        },
        "authority_review": {
            "status": "unresolved",
            "authority_scope": "REVIEW_REQUIRED",
            "evidence_basis": "REVIEW_REQUIRED",
        },
        "archive_review": {
            "authoritative_archive_location_status": "unresolved",
            "archive_location": "REVIEW_REQUIRED",
            "source_authority_statement_present": False,
            "original_distribution_equivalence_claimed": False,
            "exact_copy_identity_verified": False,
            "evidence_basis": "REVIEW_REQUIRED",
        },
        "rights_review": {
            "dataset_files_explicitly_in_scope": False,
            "analysis_use_status": "unresolved",
            "redistribution_status": "unresolved",
            "derived_outputs_status": "unresolved",
            "rights_basis_kind": "none",
            "reuse_terms_source": "REVIEW_REQUIRED",
            "evidence_basis": "REVIEW_REQUIRED",
        },
        "metadata_review": {
            "participant_task_mapping_status": "unresolved",
            "coordinate_semantics_status": "unresolved",
            "sampling_cadence_status": "unresolved",
            "independent_labeller_streams_status": "unresolved",
            "evidence_basis": "REVIEW_REQUIRED",
        },
        "privacy_boundary": {
            "raw_correspondence_serialized": False,
            "correspondence_content_committed_by_this_record": False,
            "local_correspondence_required_for_digest_validation": True,
        },
        "scientific_boundary": {
            "correspondence_review_only": True,
            "response_is_source_audit_authorization": False,
            "response_is_quarantine_exit_authorization": False,
            "response_alone_verifies_exact_copy_identity": False,
            "source_audit_executed": False,
            "human_human_agreement_created": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_performance_created": False,
            "gp3_validity_created": False,
            "frozen_evidence_performance_claim_created": False,
            "empirical_evidence_created": False,
        },
    }
    record["response_fingerprint_sha256"] = response_fingerprint(record)
    return record


def _reject_raw_correspondence(record: Mapping[str, Any]) -> None:
    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key).strip().lower() in _FORBIDDEN_CORRESPONDENCE_KEYS:
                    raise BenchmarkIntegrityError(
                        "GIW first-party response records must not serialize raw correspondence."
                    )
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(record)


def _validate_status(value: Any, allowed: set[str], label: str) -> str:
    status = str(value).strip().lower()
    if status not in allowed:
        raise BenchmarkIntegrityError(
            f"GIW first-party resolution {label} must be one of {sorted(allowed)}."
        )
    return status


def validate_gaze_in_wild_first_party_resolution_response(
    response_or_path: Mapping[str, Any] | str | Path,
    correspondence_path: str | Path,
    request: GazeInWildFirstPartyResolutionRequest,
) -> GazeInWildFirstPartyResolutionResponse:
    """Validate structured findings against the exact request and local correspondence digest.

    A reviewed response may record explicit first-party rights statements, but this validator
    deliberately does not convert them into source-audit or quarantine-exit authorization.
    """

    if not isinstance(request, GazeInWildFirstPartyResolutionRequest):
        raise TypeError("request must be a validated GazeInWildFirstPartyResolutionRequest.")
    record, path = _load_json_object(
        response_or_path,
        label="Gaze-in-the-Wild first-party resolution response",
    )
    _reject_raw_correspondence(record)
    _equal(record.get("record_type"), RESPONSE_RECORD_TYPE, "response record type")
    _equal(record.get("dataset"), DATASET, "response dataset")
    _equal(
        record.get("request_fingerprint_sha256"),
        request.request_fingerprint_sha256,
        "response request binding",
    )
    stored_correspondence = _sha256(
        record.get("correspondence_sha256"),
        "correspondence fingerprint",
    )
    _equal(
        stored_correspondence,
        correspondence_sha256(correspondence_path),
        "local correspondence digest binding",
    )

    review = _mapping(record, "review")
    review_status = _validate_status(review.get("status"), _ALLOWED_REVIEW_STATUS, "review status")
    if review_status == "reviewed":
        _resolved_text(record.get("received_on"), "response receipt date")
        _resolved_text(record.get("channel"), "response channel")
        sender = _mapping(record, "sender")
        for key in ("name", "email_or_identifier", "claimed_role"):
            _resolved_text(sender.get(key), f"sender {key}")
        _resolved_text(review.get("reviewer"), "response reviewer")
        _resolved_text(review.get("reviewed_on"), "response review date")

    authority = _mapping(record, "authority_review")
    authority_status = _validate_status(
        authority.get("status"),
        _ALLOWED_AUTHORITY_STATUS,
        "authority status",
    )
    if authority_status == "verified":
        if review_status != "reviewed":
            raise BenchmarkIntegrityError(
                "Verified first-party authority requires a completed human response review."
            )
        _resolved_text(authority.get("authority_scope"), "authority scope")
        _resolved_text(authority.get("evidence_basis"), "authority evidence")

    archive = _mapping(record, "archive_review")
    archive_status = _validate_status(
        archive.get("authoritative_archive_location_status"),
        _ALLOWED_LOCATION_STATUS,
        "archive-location status",
    )
    if archive_status == "provided":
        if review_status != "reviewed":
            raise BenchmarkIntegrityError(
                "A provided authoritative archive location requires completed human review."
            )
        _resolved_text(archive.get("archive_location"), "archive location")
        _resolved_text(archive.get("evidence_basis"), "archive evidence")
    _false(
        archive.get("exact_copy_identity_verified"),
        "exact-copy identity from correspondence alone",
    )

    rights = _mapping(record, "rights_review")
    analysis_status = _validate_status(
        rights.get("analysis_use_status"),
        _ALLOWED_RIGHTS_STATUS,
        "analysis-use status",
    )
    redistribution_status = _validate_status(
        rights.get("redistribution_status"),
        _ALLOWED_RIGHTS_STATUS,
        "redistribution status",
    )
    _validate_status(
        rights.get("derived_outputs_status"),
        _ALLOWED_RIGHTS_STATUS,
        "derived-output status",
    )
    rights_basis_kind = str(rights.get("rights_basis_kind")).strip().lower()
    if rights_basis_kind not in _ALLOWED_RIGHTS_BASIS:
        raise BenchmarkIntegrityError(
            "GIW first-party resolution rights_basis_kind must be an explicit reviewed basis."
        )
    resolved_rights = any(
        status != "unresolved"
        for status in (
            analysis_status,
            redistribution_status,
            str(rights.get("derived_outputs_status")).strip().lower(),
        )
    )
    if resolved_rights:
        if review_status != "reviewed":
            raise BenchmarkIntegrityError(
                "Resolved GIW dataset-file rights require a completed human response review."
            )
        if authority_status != "verified":
            raise BenchmarkIntegrityError(
                "Resolved GIW dataset-file rights require independently verified authority."
            )
        _true(
            rights.get("dataset_files_explicitly_in_scope"),
            "explicit dataset-file scope for resolved rights",
        )
        if rights_basis_kind == "none":
            raise BenchmarkIntegrityError(
                "Resolved GIW dataset-file rights require explicit first-party or formal terms."
            )
        _resolved_text(rights.get("reuse_terms_source"), "reuse-terms source")
        _resolved_text(rights.get("evidence_basis"), "rights evidence")
    elif rights_basis_kind != "none":
        _resolved_text(rights.get("evidence_basis"), "unresolved rights evidence")

    metadata = _mapping(record, "metadata_review")
    for key in (
        "participant_task_mapping_status",
        "coordinate_semantics_status",
        "sampling_cadence_status",
        "independent_labeller_streams_status",
    ):
        _validate_status(metadata.get(key), _ALLOWED_METADATA_STATUS, key)

    privacy = _mapping(record, "privacy_boundary")
    _false(privacy.get("raw_correspondence_serialized"), "raw correspondence serialization")
    _false(
        privacy.get("correspondence_content_committed_by_this_record"),
        "correspondence-content commit",
    )
    _true(
        privacy.get("local_correspondence_required_for_digest_validation"),
        "local correspondence digest validation",
    )

    boundary = _mapping(record, "scientific_boundary")
    _true(boundary.get("correspondence_review_only"), "correspondence-review-only status")
    for key in (
        "response_is_source_audit_authorization",
        "response_is_quarantine_exit_authorization",
        "response_alone_verifies_exact_copy_identity",
        "source_audit_executed",
        "human_human_agreement_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_performance_created",
        "gp3_validity_created",
        "frozen_evidence_performance_claim_created",
        "empirical_evidence_created",
    ):
        _false(boundary.get(key), key)

    stored_response = _sha256(
        record.get("response_fingerprint_sha256"),
        "response fingerprint",
    )
    _equal(
        stored_response,
        response_fingerprint(record),
        "response self-fingerprint",
    )
    return GazeInWildFirstPartyResolutionResponse(
        path=path,
        response_fingerprint_sha256=stored_response,
        request_fingerprint_sha256=request.request_fingerprint_sha256,
        correspondence_sha256=stored_correspondence,
        review_status=review_status,
        authority_status=authority_status,
        analysis_use_status=analysis_status,
        redistribution_status=redistribution_status,
        authoritative_archive_location_status=archive_status,
    )


def _write_json(record: Mapping[str, Any], output: str | Path, *, overwrite: bool) -> Path:
    path = Path(output)
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path


def write_gaze_in_wild_first_party_resolution_request(
    record: Mapping[str, Any],
    output: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write one already built public request record."""

    return _write_json(record, output, overwrite=overwrite)


def write_gaze_in_wild_first_party_resolution_response(
    record: Mapping[str, Any],
    output: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write one privacy-safe structured response record."""

    _reject_raw_correspondence(record)
    return _write_json(record, output, overwrite=overwrite)
