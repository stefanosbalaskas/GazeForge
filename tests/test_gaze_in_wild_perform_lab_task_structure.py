from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_perform_lab_task_structure import (
    EXPECTED_COMMIT,
    EXPECTED_EVIDENCE_FINGERPRINT,
    EXPECTED_FILE_BLOB,
    EXPECTED_FILE_PATH,
    EXPECTED_OBSERVED_CONTRACT,
    EXPECTED_TASKS,
    EXPECTED_TREE,
    load_gaze_in_wild_perform_lab_task_structure_evidence,
    validate_gaze_in_wild_perform_lab_task_structure_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "validation"
    / "evidence"
    / "gaze-in-wild"
    / "gaze-in-wild-perform-lab-task-structure-corroboration-evidence-v1.json"
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


def test_frozen_perform_lab_task_structure_is_self_consistent() -> None:
    record = load_gaze_in_wild_perform_lab_task_structure_evidence(EVIDENCE)
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT
    assert record["source"]["pinned_commit_sha1"] == EXPECTED_COMMIT
    assert record["source"]["pinned_tree_sha1"] == EXPECTED_TREE
    assert record["source"]["file"]["path"] == EXPECTED_FILE_PATH
    assert record["source"]["file"]["git_blob_sha1"] == EXPECTED_FILE_BLOB


def test_first_party_task_directory_set_is_frozen() -> None:
    record = validate_gaze_in_wild_perform_lab_task_structure_evidence(_load())
    section = record["first_party_structural_corroboration"]
    assert section["task_directory_labels"] == EXPECTED_TASKS
    assert record["source"]["file"]["observed_contract"] == EXPECTED_OBSERVED_CONTRACT


def test_processdata_and_raw_recording_linkage_is_preserved() -> None:
    record = validate_gaze_in_wild_perform_lab_task_structure_evidence(_load())
    section = record["first_party_structural_corroboration"]
    assert section["task_directory_processdata_linkage_observed"] is True
    assert section["processdata_fields_read"] == ["PrIdx", "TrIdx"]
    assert section["raw_recording_address_uses_pridx_tridx"] is True


def test_numeric_trial_task_mapping_remains_unresolved() -> None:
    record = validate_gaze_in_wild_perform_lab_task_structure_evidence(_load())
    section = record["first_party_structural_corroboration"]
    assert section["direct_numeric_trial_task_bindings"] == []
    assert section["complete_numeric_mapping_recorded"] is False
    assert section["trial_index_4"] == {
        "status": "unresolved",
        "explicit_first_party_numeric_binding_found": False,
        "tea_making_inferred_by_elimination": False,
    }


def test_all_scientific_promotion_gates_remain_false() -> None:
    record = validate_gaze_in_wild_perform_lab_task_structure_evidence(_load())
    assert not any(record["scientific_boundary"].values())


@pytest.mark.parametrize(
    "boundary_key",
    [
        "authoritative_trial_task_mapping_verified",
        "complete_trial_task_mapping_verified",
        "task_stratified_validation_authorized",
        "task_stratified_validation_created",
        "new_empirical_performance_claim_created",
        "cross_dataset_validation_created",
        "native_60hz_validity_created",
        "gp3_validity_created",
        "acquisition_hardware_cadence_verified",
        "quarantine_exit_authorized",
    ],
)
def test_refingerprinted_scientific_promotions_are_rejected(
    boundary_key: str,
) -> None:
    record = copy.deepcopy(_load())
    record["scientific_boundary"][boundary_key] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_perform_lab_task_structure_evidence(record)


def test_refingerprinted_numeric_mapping_promotion_is_rejected() -> None:
    record = copy.deepcopy(_load())
    section = record["first_party_structural_corroboration"]
    section["direct_numeric_trial_task_bindings"] = [
        {"trial_index": 4, "task": "Tea_Making"}
    ]
    section["complete_numeric_mapping_recorded"] = True
    section["trial_index_4"] = {
        "status": "inferred",
        "explicit_first_party_numeric_binding_found": False,
        "tea_making_inferred_by_elimination": True,
    }
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_perform_lab_task_structure_evidence(record)


def test_refingerprinted_task_directory_drift_is_rejected() -> None:
    record = copy.deepcopy(_load())
    record["first_party_structural_corroboration"]["task_directory_labels"][3] = (
        "Tea"
    )
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_perform_lab_task_structure_evidence(record)


def test_refingerprinted_source_blob_drift_is_rejected() -> None:
    record = copy.deepcopy(_load())
    record["source"]["file"]["git_blob_sha1"] = "0" * 40
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_perform_lab_task_structure_evidence(record)


def test_review_status_cannot_be_promoted_to_authoritative() -> None:
    record = copy.deepcopy(_load())
    record["review_status"] = "authoritative_mapping_verified"
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_perform_lab_task_structure_evidence(record)
