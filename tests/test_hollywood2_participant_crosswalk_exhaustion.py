from __future__ import annotations

import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_participant_crosswalk_exhaustion import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    evidence_fingerprint,
    validate_hollywood2_participant_crosswalk_exhaustion,
)

EVIDENCE_PATH = (
    Path(__file__).parents[1]
    / "validation"
    / "evidence"
    / "hollywood2"
    / "hollywood2-participant-crosswalk-exhaustion-evidence-v1.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def test_committed_crosswalk_exhaustion_evidence_validates() -> None:
    record = validate_hollywood2_participant_crosswalk_exhaustion(EVIDENCE_PATH)
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT_SHA256


def test_fingerprint_is_stable() -> None:
    record = _record()
    assert evidence_fingerprint(record) == EXPECTED_EVIDENCE_FINGERPRINT_SHA256


def test_count_match_remains_non_mapping_evidence() -> None:
    record = _record()
    token_context = record["gin_filename_token_context"]
    assert token_context["token_count"] == 16
    assert token_context["token_count_matches_earlier_public_subject_count"] is True
    assert token_context["token_count_match_is_crosswalk_evidence"] is False
    assert record["crosswalk_boundary"]["gin_tokens_are_original_participant_ids"] is False


@pytest.mark.parametrize(
    ("section", "key"),
    [
        ("crosswalk_boundary", "gin_tokens_are_original_participant_ids"),
        ("crosswalk_boundary", "gin_token_to_original_subject_id_verified"),
        ("crosswalk_boundary", "gin_token_to_task_group_verified"),
        ("crosswalk_boundary", "participant_identity_mapping_verified"),
        ("crosswalk_boundary", "missing_numeric_tokens_identify_additional_subjects"),
        ("crosswalk_boundary", "missing_numeric_tokens_define_task_group"),
        ("crosswalk_boundary", "ordinal_free_view_labels_map_to_gin_tokens"),
        ("crosswalk_boundary", "earlier_16_subject_count_defines_gin_token_identity"),
        ("crosswalk_boundary", "final_19_subject_count_defines_gin_token_identity"),
        ("crosswalk_boundary", "secondary_parser_is_authoritative_identity_evidence"),
        ("scientific_boundary", "participant_disjoint_model_validation_created"),
        ("scientific_boundary", "cross_dataset_validation_created"),
        ("scientific_boundary", "frozen_evidence_performance_claim_created"),
        ("scientific_boundary", "native_60hz_gp3_validity_created"),
        ("scientific_boundary", "rights_scope_promoted_by_crosswalk_audit"),
        ("scientific_boundary", "raw_gaze_redistributed"),
    ],
)
def test_refingerprinted_claim_promotions_are_rejected(section: str, key: str) -> None:
    record = _record()
    record[section][key] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_participant_crosswalk_exhaustion(record)


def test_numeric_holes_cannot_become_crosswalk_evidence() -> None:
    record = _record()
    token_context = record["gin_filename_token_context"]
    assert token_context["absent_numbers_within_001_to_019"] == [
        "007",
        "009",
        "016",
    ]
    assert token_context["numeric_hole_count_matches_16_to_19_publication_delta"] is True
    token_context["numeric_hole_match_is_crosswalk_evidence"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_participant_crosswalk_exhaustion(record)


def test_free_viewing_ordinals_do_not_resolve_gin_tokens() -> None:
    record = _record()
    record["reviewed_surface_findings"]["publication_lineage"][
        "free_viewing_ordinal_labels_resolve_gin_tokens"
    ] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_participant_crosswalk_exhaustion(record)


def test_secondary_parser_cannot_be_promoted_to_identity_authority() -> None:
    record = _record()
    record["reviewed_surface_findings"]["secondary_public_implementation"][
        "authoritative_for_original_participant_identity"
    ] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_participant_crosswalk_exhaustion(record)


def test_hollywood2em_article_observer_count_does_not_create_crosswalk() -> None:
    record = _record()
    article = record["reviewed_surface_findings"]["hollywood2em_article"]
    assert article["observer_count"] == 16
    article["explicit_filename_token_to_original_subject_id_crosswalk_recovered"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_participant_crosswalk_exhaustion(record)


def test_gin_history_absence_is_bound_to_existing_frozen_audit() -> None:
    record = _record()
    history = record["reviewed_surface_findings"]["canonical_gin_history"]
    assert history["reachable_commit_count"] == 7
    assert history["readme_unique_version_count"] == 3
    assert history["history_links_tokens_to_original_subject_ids"] is False
    record["source_binding"]["gin_history_evidence_fingerprint_sha256"] = "0" * 64
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_participant_crosswalk_exhaustion(record)


def test_remaining_routes_require_explicit_authoritative_mapping() -> None:
    record = _record()
    routes = record["remaining_authoritative_resolution_routes"]
    assert [item["route"] for item in routes] == [
        "authorized-original-archive-metadata",
        "author-or-institution-explicit-crosswalk",
        "author-supplied-reviewed-ledger",
    ]
    routes[0]["route"] = "count-based-inference"
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_participant_crosswalk_exhaustion(record)


def test_source_identifier_drift_is_rejected_even_when_refingerprinted() -> None:
    record = _record()
    record["source_binding"]["hollywood2em_article_doi"] = "10.0000/not-authoritative"
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_participant_crosswalk_exhaustion(record)
