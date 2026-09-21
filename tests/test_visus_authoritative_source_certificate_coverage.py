from __future__ import annotations

import copy
from typing import Any

import pytest
from test_visus_authoritative_source_intake import (
    _candidate,
    _refingerprint_certificate,
    _refingerprint_review,
    _review,
    _write_review,
)

import gazeforge.visus_authoritative_source_certificate as certificate
from gazeforge.exceptions import BenchmarkIntegrityError


@pytest.fixture(scope="module")
def valid_certificate(tmp_path_factory):
    root = tmp_path_factory.mktemp("visus-authoritative-certificate-coverage")

    inputs, candidate_record = _candidate(root)

    review_path = _write_review(
        root,
        _review(candidate_record),
    )

    reviewed = certificate.require_reviewed_visus_source_authority(
        *inputs,
        candidate_record,
        review_path,
    )

    return reviewed.certificate


def _mutated(
    valid_certificate,
) -> dict[str, Any]:
    return copy.deepcopy(valid_certificate)


def _refingerprint(
    value: dict[str, Any],
) -> dict[str, Any]:
    return _refingerprint_certificate(value)


def test_review_timestamp_invalid_iso_guard() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="ISO-8601 timestamp",
    ):
        certificate._validate_review_timestamp("definitely-not-a-timestamp")


def test_review_timestamp_success() -> None:
    assert (
        certificate._validate_review_timestamp("2026-09-10T12:30:00+03:00")
        == "2026-09-10T12:30:00+03:00"
    )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "record_type",
            "wrong",
            "certificate type drifted",
        ),
        (
            "status",
            "wrong",
            "certificate status drifted",
        ),
        (
            "authoritative_source_recheck_fingerprint_sha256",
            "0" * 64,
            "source-recheck binding drifted",
        ),
    ],
)
def test_certificate_top_level_identity_guards(
    valid_certificate,
    field: str,
    value: Any,
    match: str,
) -> None:
    record = _mutated(valid_certificate)

    record[field] = value

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        certificate.validate_certificate_record(record)


@pytest.mark.parametrize(
    "field",
    [
        "candidate_fingerprint_sha256",
        "review_fingerprint_sha256",
        "certificate_fingerprint_sha256",
    ],
)
def test_certificate_top_level_sha_guards(
    valid_certificate,
    field: str,
) -> None:
    record = _mutated(valid_certificate)

    record[field] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        certificate.validate_certificate_record(record)


@pytest.mark.parametrize(
    "section",
    [
        "source",
        "rights",
        "inventory",
        "authority_boundary",
        "scientific_boundary",
    ],
)
def test_certificate_section_mapping_guards(
    valid_certificate,
    section: str,
) -> None:
    record = _mutated(valid_certificate)

    record[section] = None

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sections are missing",
    ):
        certificate.validate_certificate_record(record)


@pytest.mark.parametrize(
    "section",
    [
        "source",
        "rights",
        "inventory",
        "authority_boundary",
        "scientific_boundary",
    ],
)
def test_certificate_nested_closed_schema_guards(
    valid_certificate,
    section: str,
) -> None:
    record = _mutated(valid_certificate)

    record[section]["unexpected"] = False

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="schema drifted",
    ):
        certificate.validate_certificate_record(record)


def test_certificate_source_artifact_sha_guard(
    valid_certificate,
) -> None:
    record = _mutated(valid_certificate)

    record["source"]["artifact_sha256"] = "bad"

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        certificate.validate_certificate_record(record)


@pytest.mark.parametrize(
    "field",
    [
        "source_reference",
        "source_revision",
    ],
)
def test_certificate_source_resolved_text_guards(
    valid_certificate,
    field: str,
) -> None:
    record = _mutated(valid_certificate)

    record["source"][field] = "REVIEW_REQUIRED"

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=field,
    ):
        certificate.validate_certificate_record(record)


def test_certificate_source_authority_class_guard(
    valid_certificate,
) -> None:
    record = _mutated(valid_certificate)

    record["source"]["source_authority_claim"] = "unsupported-third-party-copy"

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source authority class drifted",
    ):
        certificate.validate_certificate_record(record)


def test_certificate_rights_evidence_sha_guard(
    valid_certificate,
) -> None:
    record = _mutated(valid_certificate)

    record["rights"]["evidence_sha256"] = "bad"

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        certificate.validate_certificate_record(record)


@pytest.mark.parametrize(
    "field",
    [
        "evidence_reference",
        "license_or_terms_identifier",
    ],
)
def test_certificate_rights_resolved_text_guards(
    valid_certificate,
    field: str,
) -> None:
    record = _mutated(valid_certificate)

    record["rights"][field] = "REVIEW_REQUIRED"

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        certificate.validate_certificate_record(record)


def test_certificate_inventory_sha_guard(
    valid_certificate,
) -> None:
    record = _mutated(valid_certificate)

    record["inventory"]["fingerprint_sha256"] = "bad"

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        certificate.validate_certificate_record(record)


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        "2",
        None,
    ],
)
def test_certificate_inventory_file_count_guard(
    valid_certificate,
    value: Any,
) -> None:
    record = _mutated(valid_certificate)

    record["inventory"]["file_count"] = value

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file count is invalid",
    ):
        certificate.validate_certificate_record(record)


def test_certificate_participant_count_guard(
    valid_certificate,
) -> None:
    record = _mutated(valid_certificate)

    record["inventory"]["published_participant_count"] = 24

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="participant count drifted",
    ):
        certificate.validate_certificate_record(record)


def test_certificate_stimulus_count_guard(
    valid_certificate,
) -> None:
    record = _mutated(valid_certificate)

    record["inventory"]["published_stimulus_count"] = 10

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="stimulus count drifted",
    ):
        certificate.validate_certificate_record(record)


def test_certificate_requires_analysis_permission(
    valid_certificate,
) -> None:
    record = _mutated(valid_certificate)

    record["rights"]["analysis_use_permitted"] = False

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires analysis permission",
    ):
        certificate.validate_certificate_record(record)


def test_certificate_redistribution_status_guard(
    valid_certificate,
) -> None:
    record = _mutated(valid_certificate)

    record["rights"]["redistribution_status"] = "assumed"

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="redistribution status drifted",
    ):
        certificate.validate_certificate_record(record)


def test_certificate_rights_scope_guard(
    valid_certificate,
) -> None:
    record = _mutated(valid_certificate)

    record["rights"]["rights_scope_verified"] = False

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="rights scope is not verified",
    ):
        certificate.validate_certificate_record(record)


def test_certificate_raw_redistribution_action_guard(
    valid_certificate,
) -> None:
    record = _mutated(valid_certificate)

    record["rights"]["raw_source_redistribution_action_authorized"] = True

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot itself authorize redistribution",
    ):
        certificate.validate_certificate_record(record)


def test_certificate_raw_rights_text_guard(
    valid_certificate,
) -> None:
    record = _mutated(valid_certificate)

    record["rights"]["raw_rights_text_copied_to_certificate"] = True

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="leaked raw rights text",
    ):
        certificate.validate_certificate_record(record)


@pytest.mark.parametrize(
    "field",
    [
        "source_authority_verified",
        "current_authoritative_distribution_identity_verified",
        "source_artifact_matches_authoritative_distribution_verified",
        "extracted_tree_matches_source_artifact_verified",
        "source_audit_stage_authorized",
    ],
)
def test_certificate_authority_boundary_true_guards(
    valid_certificate,
    field: str,
) -> None:
    record = _mutated(valid_certificate)

    record["authority_boundary"][field] = False

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=f"{field}=true",
    ):
        certificate.validate_certificate_record(record)


@pytest.mark.parametrize(
    "field",
    [
        "dataset_status_empirical_created",
        "participant_mapping_verified",
        "stimulus_mapping_verified",
        "coordinate_basis_verified",
        "timestamp_basis_verified",
        "independent_annotation_streams_verified",
        "human_human_agreement_created",
        "model_human_validation_created",
        "frozen_evidence_created",
        "raw_source_redistribution_action_authorized",
    ],
)
def test_certificate_scientific_boundary_false_guards(
    valid_certificate,
    field: str,
) -> None:
    record = _mutated(valid_certificate)

    record["scientific_boundary"][field] = True

    _refingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        certificate.validate_certificate_record(record)


def test_certificate_fingerprint_guard(
    valid_certificate,
) -> None:
    record = _mutated(valid_certificate)

    record["certificate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint drifted",
    ):
        certificate.validate_certificate_record(record)


def test_certificate_validator_success(
    valid_certificate,
) -> None:
    observed = certificate.validate_certificate_record(valid_certificate)

    assert observed == valid_certificate


def test_review_invalid_timestamp_format(
    tmp_path,
) -> None:
    inputs, candidate_record = _candidate(tmp_path)

    review = _review(candidate_record)

    review["reviewed_at"] = "definitely-not-iso"

    _refingerprint_review(review)

    review_path = _write_review(
        tmp_path,
        review,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="ISO-8601 timestamp",
    ):
        certificate.require_reviewed_visus_source_authority(
            *inputs,
            candidate_record,
            review_path,
        )


def test_review_fingerprint_guard(
    tmp_path,
) -> None:
    inputs, candidate_record = _candidate(tmp_path)

    review = _review(candidate_record)

    review["review_fingerprint_sha256"] = "0" * 64

    review_path = _write_review(
        tmp_path,
        review,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="review fingerprint drifted",
    ):
        certificate.require_reviewed_visus_source_authority(
            *inputs,
            candidate_record,
            review_path,
        )


def test_candidate_replay_identity_guard(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, candidate_record = _candidate(tmp_path)

    review_path = _write_review(
        tmp_path,
        _review(candidate_record),
    )

    replayed = copy.deepcopy(candidate_record)

    replayed["candidate_fingerprint_sha256"] = "0" * 64

    monkeypatch.setattr(
        certificate,
        "inspect_visus_authoritative_source_candidate",
        lambda *args, **kwargs: replayed,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="no longer matches the exact local inputs",
    ):
        certificate.require_reviewed_visus_source_authority(
            *inputs,
            candidate_record,
            review_path,
        )


def test_review_type_guard(
    tmp_path,
) -> None:
    inputs, candidate_record = _candidate(tmp_path)

    review = _review(candidate_record)

    review["record_type"] = "wrong"

    _refingerprint_review(review)

    review_path = _write_review(
        tmp_path,
        review,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="review type drifted",
    ):
        certificate.require_reviewed_visus_source_authority(
            *inputs,
            candidate_record,
            review_path,
        )
