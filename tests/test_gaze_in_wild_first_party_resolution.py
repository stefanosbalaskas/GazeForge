from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_first_party_resolution import (
    EXPECTED_REQUEST_FINGERPRINT_SHA256,
    build_gaze_in_wild_first_party_resolution_request,
    build_gaze_in_wild_first_party_resolution_response_scaffold,
    request_fingerprint,
    response_fingerprint,
    validate_gaze_in_wild_first_party_resolution_request,
    validate_gaze_in_wild_first_party_resolution_response,
)

_ROOT = Path(__file__).resolve().parents[1]
_DISTRIBUTION = (
    _ROOT
    / "validation/evidence/gaze-in-wild/gaze-in-wild-distribution-availability-evidence-v1.json"
)
_CURRENT = (
    _ROOT
    / "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-current-first-party-listing-evidence-v1.json"
)
_REQUEST = (
    _ROOT
    / "validation/requests/gaze-in-wild/gaze-in-wild-first-party-resolution-request-v1.json"
)


def _request():
    return validate_gaze_in_wild_first_party_resolution_request(
        _REQUEST,
        _DISTRIBUTION,
        _CURRENT,
    )


def _message(tmp_path: Path, text: str = "First-party reply placeholder") -> Path:
    path = tmp_path / "reply.eml"
    path.write_text(text, encoding="utf-8")
    return path


def _scaffold(tmp_path: Path) -> tuple[dict[str, object], Path]:
    message = _message(tmp_path)
    record = build_gaze_in_wild_first_party_resolution_response_scaffold(message, _request())
    return record, message


def _refresh_response(record: dict[str, object]) -> None:
    record["response_fingerprint_sha256"] = response_fingerprint(record)


def _reviewed(record: dict[str, object]) -> None:
    record["received_on"] = "2026-09-06"
    record["channel"] = "email"
    sender = record["sender"]
    assert isinstance(sender, dict)
    sender.update(
        {
            "name": "First Party",
            "email_or_identifier": "first.party@rit.edu",
            "claimed_role": "dataset steward",
        }
    )
    review = record["review"]
    assert isinstance(review, dict)
    review.update(
        {
            "status": "reviewed",
            "reviewer": "Stefanos Balaskas",
            "reviewed_on": "2026-09-06",
        }
    )


def _verify_authority(record: dict[str, object]) -> None:
    authority = record["authority_review"]
    assert isinstance(authority, dict)
    authority.update(
        {
            "status": "verified",
            "authority_scope": "Gaze-in-the-Wild dataset-file reuse terms",
            "evidence_basis": "Reviewed first-party role/authority statement.",
        }
    )


def test_committed_request_is_exact_and_bound_to_both_parent_evidence() -> None:
    request = _request()
    assert request.request_fingerprint_sha256 == EXPECTED_REQUEST_FINGERPRINT_SHA256
    assert request.current_listing_state_fingerprint_sha256.startswith("b7fcf787")

    generated = build_gaze_in_wild_first_party_resolution_request(_DISTRIBUTION, _CURRENT)
    committed = json.loads(_REQUEST.read_text(encoding="utf-8"))
    assert generated == committed
    assert request_fingerprint(committed) == EXPECTED_REQUEST_FINGERPRINT_SHA256


def test_request_rejects_public_availability_or_license_promotion() -> None:
    record = json.loads(_REQUEST.read_text(encoding="utf-8"))
    record["request_boundary"]["public_availability_statement_is_dataset_file_license"] = True
    record["request_fingerprint_sha256"] = request_fingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_first_party_resolution_request(
            record,
            _DISTRIBUTION,
            _CURRENT,
        )


def test_pending_response_is_digest_bound_and_contains_no_message_body(tmp_path: Path) -> None:
    record, message = _scaffold(tmp_path)
    response = validate_gaze_in_wild_first_party_resolution_response(record, message, _request())
    assert response.review_status == "pending_review"
    assert response.analysis_use_status == "unresolved"
    assert response.redistribution_status == "unresolved"
    serialized = json.dumps(record)
    assert "First-party reply placeholder" not in serialized
    assert record["privacy_boundary"]["raw_correspondence_serialized"] is False


def test_response_rejects_correspondence_digest_drift(tmp_path: Path) -> None:
    record, message = _scaffold(tmp_path)
    message.write_text("changed reply", encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="digest binding"):
        validate_gaze_in_wild_first_party_resolution_response(record, message, _request())


def test_response_rejects_serialized_raw_correspondence(tmp_path: Path) -> None:
    record, message = _scaffold(tmp_path)
    record["message_body"] = "do not commit this"
    _refresh_response(record)
    with pytest.raises(BenchmarkIntegrityError, match="must not serialize raw correspondence"):
        validate_gaze_in_wild_first_party_resolution_response(record, message, _request())


def test_rit_email_domain_does_not_verify_authority(tmp_path: Path) -> None:
    record, message = _scaffold(tmp_path)
    _reviewed(record)
    sender = record["sender"]
    assert isinstance(sender, dict)
    sender["email_or_identifier"] = "gabriel.diaz@rit.edu"
    _refresh_response(record)
    response = validate_gaze_in_wild_first_party_resolution_response(record, message, _request())
    assert response.authority_status == "unresolved"


def test_public_availability_is_not_an_allowed_resolved_rights_basis(tmp_path: Path) -> None:
    record, message = _scaffold(tmp_path)
    _reviewed(record)
    _verify_authority(record)
    rights = record["rights_review"]
    assert isinstance(rights, dict)
    rights.update(
        {
            "dataset_files_explicitly_in_scope": True,
            "analysis_use_status": "permitted",
            "rights_basis_kind": "publication_public_availability_statement",
            "reuse_terms_source": "Scientific Reports data-availability statement",
            "evidence_basis": "The publication says the compressed data were publicly available.",
        }
    )
    _refresh_response(record)
    with pytest.raises(BenchmarkIntegrityError, match="rights_basis_kind"):
        validate_gaze_in_wild_first_party_resolution_response(record, message, _request())


def test_resolved_rights_require_verified_authority(tmp_path: Path) -> None:
    record, message = _scaffold(tmp_path)
    _reviewed(record)
    rights = record["rights_review"]
    assert isinstance(rights, dict)
    rights.update(
        {
            "dataset_files_explicitly_in_scope": True,
            "analysis_use_status": "permitted",
            "rights_basis_kind": "explicit_first_party_statement",
            "reuse_terms_source": "Reviewed correspondence",
            "evidence_basis": "Explicit dataset-file analysis statement.",
        }
    )
    _refresh_response(record)
    with pytest.raises(BenchmarkIntegrityError, match="verified authority"):
        validate_gaze_in_wild_first_party_resolution_response(record, message, _request())


def test_resolved_rights_require_explicit_dataset_file_scope(tmp_path: Path) -> None:
    record, message = _scaffold(tmp_path)
    _reviewed(record)
    _verify_authority(record)
    rights = record["rights_review"]
    assert isinstance(rights, dict)
    rights.update(
        {
            "analysis_use_status": "permitted",
            "rights_basis_kind": "explicit_first_party_statement",
            "reuse_terms_source": "Reviewed correspondence",
            "evidence_basis": "Statement does not explicitly identify the dataset files.",
        }
    )
    _refresh_response(record)
    with pytest.raises(BenchmarkIntegrityError, match="explicit dataset-file scope"):
        validate_gaze_in_wild_first_party_resolution_response(record, message, _request())


def test_reviewed_explicit_dataset_file_rights_can_be_recorded_without_authorizing_audit(
    tmp_path: Path,
) -> None:
    record, message = _scaffold(tmp_path)
    _reviewed(record)
    _verify_authority(record)
    rights = record["rights_review"]
    assert isinstance(rights, dict)
    rights.update(
        {
            "dataset_files_explicitly_in_scope": True,
            "analysis_use_status": "permitted",
            "redistribution_status": "restricted",
            "derived_outputs_status": "permitted",
            "rights_basis_kind": "explicit_first_party_statement",
            "reuse_terms_source": "Reviewed correspondence digest",
            "evidence_basis": "Explicit dataset-file terms reviewed against the local message.",
        }
    )
    _refresh_response(record)
    response = validate_gaze_in_wild_first_party_resolution_response(record, message, _request())
    assert response.analysis_use_status == "permitted"
    assert response.redistribution_status == "restricted"
    assert record["scientific_boundary"]["response_is_source_audit_authorization"] is False
    assert record["scientific_boundary"]["response_is_quarantine_exit_authorization"] is False
    assert record["scientific_boundary"]["empirical_evidence_created"] is False


def test_archive_location_does_not_verify_exact_copy_identity(tmp_path: Path) -> None:
    record, message = _scaffold(tmp_path)
    _reviewed(record)
    archive = record["archive_review"]
    assert isinstance(archive, dict)
    archive.update(
        {
            "authoritative_archive_location_status": "provided",
            "archive_location": "https://example.invalid/gaze-in-wild.zip",
            "source_authority_statement_present": True,
            "evidence_basis": "Reviewed reply supplied a candidate location.",
        }
    )
    _refresh_response(record)
    response = validate_gaze_in_wild_first_party_resolution_response(record, message, _request())
    assert response.authoritative_archive_location_status == "provided"
    assert archive["exact_copy_identity_verified"] is False

    promoted = copy.deepcopy(record)
    promoted["archive_review"]["exact_copy_identity_verified"] = True
    _refresh_response(promoted)
    with pytest.raises(BenchmarkIntegrityError, match="exact-copy identity"):
        validate_gaze_in_wild_first_party_resolution_response(promoted, message, _request())


def test_response_self_fingerprint_tampering_is_rejected(tmp_path: Path) -> None:
    record, message = _scaffold(tmp_path)
    record["response_fingerprint_sha256"] = "0" * 64
    with pytest.raises(BenchmarkIntegrityError, match="self-fingerprint"):
        validate_gaze_in_wild_first_party_resolution_response(record, message, _request())
