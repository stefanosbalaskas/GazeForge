from __future__ import annotations

import copy
from typing import Any

import pytest
from test_visus_authoritative_source_intake import (
    _candidate,
    _refingerprint_candidate,
)

import gazeforge.visus_authoritative_source_intake as intake
from gazeforge.exceptions import BenchmarkIntegrityError


@pytest.fixture(scope="module")
def candidate_fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp("visus-authoritative-intake-coverage")

    inputs, candidate = _candidate(root)

    return {
        "inputs": inputs,
        "candidate": candidate,
    }


def _record(candidate_fixture):
    return copy.deepcopy(candidate_fixture["candidate"])


def _resign(record):
    return _refingerprint_candidate(record)


def test_inspect_requires_three_distinct_evidence_files(
    candidate_fixture,
) -> None:
    root, source, rights, manifest = candidate_fixture["inputs"]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be distinct files",
    ):
        intake.inspect_visus_authoritative_source_candidate(
            root,
            source,
            source,
            manifest,
        )


def test_inspect_candidate_success(
    candidate_fixture,
) -> None:
    root, source, rights, manifest = candidate_fixture["inputs"]

    observed = intake.inspect_visus_authoritative_source_candidate(
        root,
        source,
        rights,
        manifest,
    )

    assert observed["record_type"] == intake.CANDIDATE_RECORD_TYPE

    assert observed["status"] == intake.CANDIDATE_STATUS

    assert observed["source"]["authorized_channel_affirmed"] is True

    assert observed["review_boundary"]["manual_review_required"] is True


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "record_type",
            "wrong",
            "candidate type drifted",
        ),
        (
            "status",
            "wrong",
            "candidate status drifted",
        ),
        (
            "authoritative_source_recheck_fingerprint_sha256",
            "0" * 64,
            "recheck binding drifted",
        ),
    ],
)
def test_candidate_top_level_identity_guards(
    candidate_fixture,
    field: str,
    value: Any,
    match: str,
) -> None:
    record = _record(candidate_fixture)

    record[field] = value
    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        intake.validate_candidate_record(record)


def test_candidate_fingerprint_guard(
    candidate_fixture,
) -> None:
    record = _record(candidate_fixture)

    record["candidate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="candidate fingerprint drifted",
    ):
        intake.validate_candidate_record(record)


@pytest.mark.parametrize(
    "section",
    [
        "source",
        "rights_evidence",
        "manifest",
        "inventory",
        "review_boundary",
        "scientific_boundary",
    ],
)
def test_candidate_sections_require_mappings(
    candidate_fixture,
    section: str,
) -> None:
    record = _record(candidate_fixture)

    record[section] = None
    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="candidate sections are missing",
    ):
        intake.validate_candidate_record(record)


@pytest.mark.parametrize(
    "section",
    [
        "source",
        "rights_evidence",
        "manifest",
        "inventory",
        "review_boundary",
        "scientific_boundary",
    ],
)
def test_candidate_nested_closed_schema(
    candidate_fixture,
    section: str,
) -> None:
    record = _record(candidate_fixture)

    record[section]["unexpected_contract_field"] = False

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="schema drifted",
    ):
        intake.validate_candidate_record(record)


def test_candidate_authority_class_guard(
    candidate_fixture,
) -> None:
    record = _record(candidate_fixture)

    record["source"]["source_authority_claim"] = "third_party_repack"

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="authority class drifted",
    ):
        intake.validate_candidate_record(record)


@pytest.mark.parametrize(
    "field",
    [
        "source_reference",
        "source_revision",
    ],
)
def test_candidate_source_text_must_be_resolved(
    candidate_fixture,
    field: str,
) -> None:
    record = _record(candidate_fixture)

    record["source"][field] = "REVIEW_REQUIRED"

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        intake.validate_candidate_record(record)


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        "12",
        None,
        True,
    ],
)
def test_candidate_source_size_guard(
    candidate_fixture,
    value: Any,
) -> None:
    record = _record(candidate_fixture)

    record["source"]["artifact_size_bytes"] = value

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source artifact size is invalid",
    ):
        intake.validate_candidate_record(record)


def test_candidate_authorized_channel_guard(
    candidate_fixture,
) -> None:
    record = _record(candidate_fixture)

    record["source"]["authorized_channel_affirmed"] = False

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="authorization drifted",
    ):
        intake.validate_candidate_record(record)


@pytest.mark.parametrize(
    ("section", "field"),
    [
        (
            "source",
            "artifact_sha256",
        ),
        (
            "rights_evidence",
            "sha256",
        ),
        (
            "manifest",
            "sha256",
        ),
        (
            "inventory",
            "fingerprint_sha256",
        ),
    ],
)
def test_candidate_sha_guards(
    candidate_fixture,
    section: str,
    field: str,
) -> None:
    record = _record(candidate_fixture)

    record[section][field] = "BAD"

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="SHA-256",
    ):
        intake.validate_candidate_record(record)


def test_candidate_rights_reference_must_be_resolved(
    candidate_fixture,
) -> None:
    record = _record(candidate_fixture)

    record["rights_evidence"]["reference"] = "TODO"

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        intake.validate_candidate_record(record)


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        "12",
        None,
        True,
    ],
)
def test_candidate_rights_size_guard(
    candidate_fixture,
    value: Any,
) -> None:
    record = _record(candidate_fixture)

    record["rights_evidence"]["size_bytes"] = value

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="rights-evidence size is invalid",
    ):
        intake.validate_candidate_record(record)


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        "12",
        None,
        True,
    ],
)
def test_candidate_manifest_size_guard(
    candidate_fixture,
    value: Any,
) -> None:
    record = _record(candidate_fixture)

    record["manifest"]["size_bytes"] = value

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="manifest size is invalid",
    ):
        intake.validate_candidate_record(record)


def test_candidate_must_not_copy_raw_rights_text(
    candidate_fixture,
) -> None:
    record = _record(candidate_fixture)

    record["rights_evidence"]["raw_rights_text_copied_to_candidate"] = True

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="leaked raw rights text",
    ):
        intake.validate_candidate_record(record)


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        "2",
        None,
        True,
    ],
)
def test_candidate_inventory_count_guard(
    candidate_fixture,
    value: Any,
) -> None:
    record = _record(candidate_fixture)

    record["inventory"]["file_count"] = value

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="inventory file count is invalid",
    ):
        intake.validate_candidate_record(record)


def test_candidate_participant_count_guard(
    candidate_fixture,
) -> None:
    record = _record(candidate_fixture)

    record["inventory"]["published_participant_count"] = 24

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="participant count drifted",
    ):
        intake.validate_candidate_record(record)


def test_candidate_stimulus_count_guard(
    candidate_fixture,
) -> None:
    record = _record(candidate_fixture)

    record["inventory"]["published_stimulus_count"] = 10

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="stimulus count drifted",
    ):
        intake.validate_candidate_record(record)


@pytest.mark.parametrize(
    "field",
    [
        "file_roles_inferred",
        "participant_ids_inferred",
        "stimulus_ids_inferred",
    ],
)
def test_candidate_inventory_must_not_infer(
    candidate_fixture,
    field: str,
) -> None:
    record = _record(candidate_fixture)

    record["inventory"][field] = True

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not infer",
    ):
        intake.validate_candidate_record(record)


@pytest.mark.parametrize(
    "field",
    [
        "source_authority_verified",
        "current_authoritative_distribution_identity_verified",
        "source_artifact_matches_authoritative_distribution_verified",
        "extracted_tree_matches_source_artifact_verified",
        "rights_evidence_authoritative_verified",
        "analysis_use_permitted_verified",
        "redistribution_status_verified",
        "source_audit_stage_authorized",
    ],
)
def test_candidate_review_boundary_must_not_promote(
    candidate_fixture,
    field: str,
) -> None:
    record = _record(candidate_fixture)

    record["review_boundary"][field] = True

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        intake.validate_candidate_record(record)


def test_candidate_manual_review_gate_required(
    candidate_fixture,
) -> None:
    record = _record(candidate_fixture)

    record["review_boundary"]["manual_review_required"] = False

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="manual-review gate was relaxed",
    ):
        intake.validate_candidate_record(record)


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
def test_candidate_scientific_boundary_must_not_promote(
    candidate_fixture,
    field: str,
) -> None:
    record = _record(candidate_fixture)

    record["scientific_boundary"][field] = True

    _resign(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        intake.validate_candidate_record(record)


def test_candidate_validator_success(
    candidate_fixture,
) -> None:
    record = _record(candidate_fixture)

    observed = intake.validate_candidate_record(record)

    assert observed == record
