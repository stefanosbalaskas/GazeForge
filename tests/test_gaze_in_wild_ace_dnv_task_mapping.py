from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_ace_dnv_task_mapping import (
    EXPECTED_COMMIT,
    EXPECTED_EVIDENCE_FINGERPRINT,
    EXPECTED_FILES,
    EXPECTED_MAPPINGS,
    EXPECTED_TREE,
    load_gaze_in_wild_ace_dnv_task_mapping_evidence,
    validate_gaze_in_wild_ace_dnv_task_mapping_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "validation"
    / "evidence"
    / "gaze-in-wild"
    / "gaze-in-wild-ace-dnv-task-mapping-corroboration-evidence-v1.json"
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


def test_frozen_ace_dnv_task_mapping_corroboration_is_self_consistent() -> None:
    record = load_gaze_in_wild_ace_dnv_task_mapping_evidence(EVIDENCE)
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT
    assert record["source"]["pinned_commit_sha1"] == EXPECTED_COMMIT
    assert record["source"]["pinned_tree_sha1"] == EXPECTED_TREE
    assert record["source"]["files"] == EXPECTED_FILES


def test_only_trials_one_to_three_are_secondarily_corroborated() -> None:
    record = validate_gaze_in_wild_ace_dnv_task_mapping_evidence(_load())
    assert record["secondary_corroboration"]["trial_mappings"] == EXPECTED_MAPPINGS
    assert [
        (row["trial_index"], row["secondary_task_label"])
        for row in record["secondary_corroboration"]["trial_mappings"]
    ] == [
        (1, "Indoor_Walk"),
        (2, "Ball_Catch"),
        (3, "Visual_Search"),
    ]


def test_trial_four_remains_unresolved_and_is_not_inferred() -> None:
    record = validate_gaze_in_wild_ace_dnv_task_mapping_evidence(_load())
    trial4 = record["secondary_corroboration"]["trial_index_4"]
    assert trial4["status"] == "unresolved"
    assert trial4["explicit_secondary_task_label_found_in_reviewed_ace_dnv_files"] is False
    assert trial4["tea_making_inferred_by_elimination"] is False
    assert record["secondary_corroboration"]["complete_mapping_recorded"] is False


def test_all_scientific_promotion_gates_remain_false() -> None:
    record = validate_gaze_in_wild_ace_dnv_task_mapping_evidence(_load())
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
        validate_gaze_in_wild_ace_dnv_task_mapping_evidence(record)


def test_refingerprinted_trial_four_tea_inference_is_rejected() -> None:
    record = copy.deepcopy(_load())
    trial4 = record["secondary_corroboration"]["trial_index_4"]
    trial4["status"] = "inferred"
    trial4["tea_making_inferred_by_elimination"] = True
    record["secondary_corroboration"]["complete_mapping_recorded"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_ace_dnv_task_mapping_evidence(record)


def test_refingerprinted_partial_mapping_drift_is_rejected() -> None:
    record = copy.deepcopy(_load())
    record["secondary_corroboration"]["trial_mappings"][0][
        "secondary_task_label"
    ] = "Tea_Making"
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_ace_dnv_task_mapping_evidence(record)


def test_refingerprinted_source_blob_drift_is_rejected() -> None:
    record = copy.deepcopy(_load())
    record["source"]["files"]["GiW/files_task1_lblr5.txt"][
        "git_blob_sha1"
    ] = "0" * 40
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_ace_dnv_task_mapping_evidence(record)


def test_review_status_cannot_be_promoted_to_empirical() -> None:
    record = copy.deepcopy(_load())
    record["review_status"] = "empirical"
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_ace_dnv_task_mapping_evidence(record)
