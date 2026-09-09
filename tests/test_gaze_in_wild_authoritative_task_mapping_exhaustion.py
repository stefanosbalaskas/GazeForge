from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_authoritative_task_mapping_exhaustion import (
    EXPECTED_EVIDENCE_FINGERPRINT,
    EXPECTED_SECONDARY,
    EXPECTED_TASKS,
    EXPECTED_UPSTREAM_EVIDENCE,
    load_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence,
    validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "validation"
    / "evidence"
    / "gaze-in-wild"
    / "gaze-in-wild-authoritative-task-mapping-exhaustion-evidence-v1.json"
)


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _refingerprint(record: dict) -> None:
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    record["evidence_fingerprint_sha256"] = _canonical_sha256(body)


def test_frozen_authoritative_task_mapping_exhaustion_is_self_consistent() -> None:
    record = load_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(EVIDENCE)
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT
    assert record["upstream_evidence"] == EXPECTED_UPSTREAM_EVIDENCE
    assert record["scope_statement"] == {
        "enumerated_reviewed_scope_exhausted": True,
        "global_nonexistence_claimed": False,
    }


def test_original_first_party_history_remains_exhausted_without_mapping() -> None:
    record = validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(
        _load()
    )
    source = record["authoritative_search_scope"]["original_giw_repository"]
    assert source["reachable_commit_count"] == 56
    assert source["appdesigner_container_reviewed"] is True
    assert source["explicit_numeric_task_lookup_recovered"] is False
    assert source["publication_order_used_as_numeric_mapping"] is False


def test_perform_file_history_is_single_commit_and_still_no_lookup() -> None:
    record = validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(
        _load()
    )
    perform = record["authoritative_search_scope"][
        "perform_lab_institutional_repository"
    ]
    assert perform["file_history_commit_count"] == 1
    assert perform["file_history_commit_shas"] == [
        "ebec5d1db118e39de60a14160f09ee33cd7f3b5d"
    ]
    assert perform["task_directory_labels"] == EXPECTED_TASKS
    assert perform["processdata_fields_read"] == ["PrIdx", "TrIdx"]
    assert perform["separate_giw_mapping_manifest_found"] is False
    assert perform["explicit_numeric_task_lookup_recovered"] is False
    assert perform["task_directory_order_used_as_numeric_mapping"] is False


def test_ace_dnv_remains_secondary_and_trial_four_unresolved() -> None:
    record = validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(
        _load()
    )
    state = record["resolution_state"]
    assert state["secondary_corroboration"] == EXPECTED_SECONDARY
    assert state["secondary_mapping_promoted_to_authoritative"] is False
    assert state["complete_mapping_recorded"] is False
    assert state["trial_index_4"] == {
        "status": "unresolved",
        "explicit_authoritative_binding_found": False,
        "explicit_secondary_binding_found": False,
        "tea_making_inferred_by_elimination": False,
    }


def test_task_stratified_validation_remains_unauthorized() -> None:
    record = validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(
        _load()
    )
    assert record["resolution_state"]["task_stratified_validation_authorized"] is False
    assert record["scientific_boundary"]["task_stratified_validation_authorized"] is False
    assert record["scientific_boundary"]["task_stratified_validation_created"] is False


def test_all_scientific_promotion_gates_remain_false() -> None:
    record = validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(
        _load()
    )
    assert not any(record["scientific_boundary"].values())


@pytest.mark.parametrize(
    "boundary_key",
    [
        "authoritative_trial_task_mapping_verified",
        "complete_trial_task_mapping_verified",
        "tridx4_tea_making_verified",
        "task_stratified_validation_authorized",
        "task_stratified_validation_created",
        "new_empirical_performance_claim_created",
        "cross_dataset_validation_created",
        "native_60hz_validity_created",
        "gp3_validity_created",
        "acquisition_hardware_cadence_verified",
        "quarantine_exit_authorized",
        "raw_data_retention_claim_created",
    ],
)
def test_refingerprinted_scientific_promotions_are_rejected(
    boundary_key: str,
) -> None:
    record = copy.deepcopy(_load())
    record["scientific_boundary"][boundary_key] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(record)


@pytest.mark.parametrize(
    ("section", "key"),
    [
        ("resolution_state", "authoritative_numeric_mapping_recovered"),
        ("resolution_state", "complete_mapping_recorded"),
        ("resolution_state", "publication_order_used_as_numeric_mapping"),
        ("resolution_state", "task_directory_order_used_as_numeric_mapping"),
        ("resolution_state", "secondary_mapping_promoted_to_authoritative"),
        ("resolution_state", "task_stratified_validation_authorized"),
    ],
)
def test_refingerprinted_resolution_promotions_are_rejected(
    section: str,
    key: str,
) -> None:
    record = copy.deepcopy(_load())
    record[section][key] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(record)


def test_refingerprinted_trial_four_tea_inference_is_rejected() -> None:
    record = copy.deepcopy(_load())
    trial4 = record["resolution_state"]["trial_index_4"]
    trial4["status"] = "inferred"
    trial4["tea_making_inferred_by_elimination"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(record)


def test_refingerprinted_publication_order_mapping_is_rejected() -> None:
    record = copy.deepcopy(_load())
    published = record["authoritative_search_scope"][
        "published_supplement_and_distribution_metadata"
    ]
    published["task_column_order_used_as_numeric_mapping"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(record)


def test_refingerprinted_task_directory_order_mapping_is_rejected() -> None:
    record = copy.deepcopy(_load())
    perform = record["authoritative_search_scope"][
        "perform_lab_institutional_repository"
    ]
    perform["task_directory_order_used_as_numeric_mapping"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(record)


def test_refingerprinted_secondary_promotion_is_rejected() -> None:
    record = copy.deepcopy(_load())
    record["resolution_state"]["secondary_corroboration"][0]["status"] = "authoritative"
    record["resolution_state"]["secondary_mapping_promoted_to_authoritative"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(record)


def test_refingerprinted_upstream_binding_drift_is_rejected() -> None:
    record = copy.deepcopy(_load())
    record["upstream_evidence"][0]["fingerprint_sha256"] = "0" * 64
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(record)


def test_global_nonexistence_claim_is_rejected() -> None:
    record = copy.deepcopy(_load())
    record["scope_statement"]["global_nonexistence_claimed"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(record)


def test_review_status_cannot_be_promoted_to_resolved() -> None:
    record = copy.deepcopy(_load())
    record["review_status"] = "authoritative_mapping_resolved"
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_authoritative_task_mapping_exhaustion_evidence(record)
