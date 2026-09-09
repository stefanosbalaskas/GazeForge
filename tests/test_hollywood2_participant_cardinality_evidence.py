from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_participant_cardinality_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    evidence_fingerprint,
    validate_hollywood2_participant_cardinality_evidence,
)

EVIDENCE = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-participant-cardinality-evidence-v1.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def test_frozen_participant_cardinality_evidence_validates() -> None:
    record = validate_hollywood2_participant_cardinality_evidence(EVIDENCE)
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert record["cardinality_assessment"]["observed_subject_count_delta"] == 3
    assert record["mapping_boundary"]["participant_identity_mapping_verified"] is False


def test_unfingerprinted_edit_is_rejected() -> None:
    record = _record()
    record["cardinality_assessment"]["observed_subject_count_delta"] = 2
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_participant_cardinality_evidence(record)


def test_refingerprinted_16_token_count_mapping_promotion_is_rejected() -> None:
    record = _record()
    record["gin_token_context"]["token_count_match_is_mapping_evidence"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_hollywood2_participant_cardinality_evidence(record)


def test_refingerprinted_numeric_hole_mapping_promotion_is_rejected() -> None:
    record = _record()
    record["gin_token_context"]["numeric_hole_count_is_mapping_or_group_evidence"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_hollywood2_participant_cardinality_evidence(record)


def test_refingerprinted_missing_tokens_as_added_subjects_is_rejected() -> None:
    record = _record()
    record["forbidden_inferences"][
        "infer_absent_007_009_016_are_the_three_additional_final_article_subjects"
    ] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_hollywood2_participant_cardinality_evidence(record)


def test_refingerprinted_task_group_from_missing_tokens_is_rejected() -> None:
    record = _record()
    record["forbidden_inferences"]["infer_absent_007_009_016_define_a_task_group"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_hollywood2_participant_cardinality_evidence(record)


def test_refingerprinted_automatic_reconciliation_is_rejected() -> None:
    record = _record()
    record["cardinality_assessment"]["automatic_cardinality_reconciliation_permitted"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_hollywood2_participant_cardinality_evidence(record)


def test_refingerprinted_participant_mapping_is_rejected() -> None:
    record = _record()
    record["mapping_boundary"]["participant_identity_mapping_verified"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_hollywood2_participant_cardinality_evidence(record)


def test_refingerprinted_participant_disjoint_validation_is_rejected() -> None:
    record = _record()
    record["mapping_boundary"]["participant_disjoint_model_validation_created"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_hollywood2_participant_cardinality_evidence(record)


def test_refingerprinted_rights_promotion_is_rejected() -> None:
    record = _record()
    record["rights_boundary"]["analysis_use_authorized_by_this_evidence"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_hollywood2_participant_cardinality_evidence(record)


def test_refingerprinted_final_cardinality_drift_is_rejected() -> None:
    record = copy.deepcopy(_record())
    record["reviewed_cardinality_surfaces"]["final_pami_article_abstract"][
        "reported_subject_count"
    ] = 16
    record["cardinality_assessment"]["final_article_surface_subject_count"] = 16
    record["cardinality_assessment"]["observed_subject_count_delta"] = 0
    record["cardinality_assessment"]["publication_lineage_cardinality_drift_observed"] = False
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_participant_cardinality_evidence(record)
