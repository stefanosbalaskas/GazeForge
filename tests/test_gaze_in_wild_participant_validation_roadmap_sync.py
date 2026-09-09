from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_participant_validation_roadmap_sync import (
    COMPLETED_ISSUE_WORDING,
    EVIDENCE_FINGERPRINT,
    OPEN_TASK_ISSUE_WORDING,
    evidence_fingerprint,
    validate_gaze_in_wild_participant_validation_roadmap_sync,
)

EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-roadmap-evidence-sync-v3.json"
)


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def test_participant_validation_roadmap_sync_validates() -> None:
    result = validate_gaze_in_wild_participant_validation_roadmap_sync(EVIDENCE)
    assert result.fingerprint_sha256 == EVIDENCE_FINGERPRINT
    assert result.participant_validation_satisfied is True
    assert result.event_class_sensitivity_satisfied is True
    assert result.naturalistic_task_sensitivity_satisfied is False
    assert result.participant_count == 12
    assert result.recording_count == 18
    assert result.oof_row_count_per_model == 157850
    assert result.analysis_sampling_rate_hz == 60.0
    assert result.pursuit_analysis_support == 5696
    assert result.pursuit_reference_event_count == 327


def test_stored_fingerprint_tampering_fails() -> None:
    record = _load()
    record["evidence_fingerprint_sha256"] = "0" * 64
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_gaze_in_wild_participant_validation_roadmap_sync(record)


@pytest.mark.parametrize(
    ("section", "key"),
    [
        (
            "roadmap_completion",
            "authoritative_numeric_task_mapping_item_satisfied",
        ),
        ("roadmap_completion", "naturalistic_task_sensitivity_item_satisfied"),
        ("roadmap_completion", "task_stratified_validation_item_satisfied"),
        ("scientific_boundary", "acquisition_hardware_cadence_verified"),
        ("scientific_boundary", "cross_dataset_validation_created"),
        ("scientific_boundary", "gp3_validity_claim_created"),
        (
            "scientific_boundary",
            "historical_rit_archive_byte_equivalence_verified",
        ),
        ("scientific_boundary", "native_60hz_validity_claim_created"),
        ("scientific_boundary", "naturalistic_task_sensitivity_created"),
        ("scientific_boundary", "new_empirical_performance_claim_created"),
        ("scientific_boundary", "quarantine_exit_authorized"),
        ("scientific_boundary", "raw_dataset_bytes_retained"),
        ("scientific_boundary", "task_mapping_used"),
        ("scientific_boundary", "task_stratified_model_validation_created"),
    ],
)
def test_refingerprinted_forbidden_promotions_fail(
    section: str,
    key: str,
) -> None:
    record = copy.deepcopy(_load())
    record[section][key] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_participant_validation_roadmap_sync(record)


@pytest.mark.parametrize(
    ("section", "key"),
    [
        (
            "roadmap_completion",
            "task_agnostic_participant_disjoint_model_validation_item_satisfied",
        ),
        ("roadmap_completion", "event_class_sensitivity_item_satisfied"),
        (
            "roadmap_completion",
            "official_figshare_original_publication_copy_and_current_reuse_terms_"
            "scoped_item_satisfied",
        ),
        ("roadmap_completion", "processed_timestamp_grid_rate_item_satisfied"),
        ("roadmap_completion", "overlap_hha_item_satisfied"),
        ("scientific_boundary", "analysis_grid_is_derived_60hz"),
        ("scientific_boundary", "participant_disjoint_model_validation_created"),
        ("scientific_boundary", "event_class_sensitivity_created"),
        ("scientific_boundary", "pursuit_failure_case_must_remain_visible"),
    ],
)
def test_refingerprinted_required_completions_cannot_be_revoked(
    section: str,
    key: str,
) -> None:
    record = copy.deepcopy(_load())
    record[section][key] = False
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_participant_validation_roadmap_sync(record)


@pytest.mark.parametrize(
    ("key", "replacement"),
    [
        ("analysis_sampling_rate_hz", 120.0),
        ("participant_count", 13),
        ("recording_count", 19),
        ("oof_row_count_per_model", 157851),
        ("task_mapping_used", True),
        ("task_stratified_validation_created", True),
        ("task_fold_metrics_row_count", 1),
        ("task_summary_row_count", 1),
        ("pursuit_analysis_support", 5695),
        ("pursuit_reference_event_count", 326),
        (
            "cross_run_reproducibility_signature_sha256",
            "0" * 64,
        ),
        ("evidence_fingerprint_sha256", "0" * 64),
    ],
)
def test_refingerprinted_participant_reference_drift_fails(
    key: str,
    replacement: object,
) -> None:
    record = copy.deepcopy(_load())
    record["upstream_evidence"]["participant_disjoint_validation"][key] = replacement
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_participant_validation_roadmap_sync(record)


def test_issue_wording_splits_completed_and_open_components() -> None:
    record = _load()
    assert (
        record["issue_wording"]["completed_participant_validation"]
        == COMPLETED_ISSUE_WORDING
    )
    assert record["issue_wording"]["open_task_sensitivity"] == OPEN_TASK_ISSUE_WORDING


@pytest.mark.parametrize(
    ("key", "replacement"),
    [
        (
            "completed_participant_validation",
            "Run participant-disjoint GIW validation and report task sensitivity.",
        ),
        (
            "open_task_sensitivity",
            "Naturalistic-task sensitivity is complete.",
        ),
    ],
)
def test_refingerprinted_issue_wording_promotion_fails(
    key: str,
    replacement: str,
) -> None:
    record = copy.deepcopy(_load())
    record["issue_wording"][key] = replacement
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_participant_validation_roadmap_sync(record)


def test_claim_limit_cannot_hide_pursuit_failure() -> None:
    record = copy.deepcopy(_load())
    record["claim_limit"] = (
        "Participant-disjoint validation proves uniformly strong event recognition."
    )
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_participant_validation_roadmap_sync(record)


def test_v2_binding_cannot_drift() -> None:
    record = copy.deepcopy(_load())
    record["upstream_evidence"]["roadmap_sync_v2"][
        "evidence_fingerprint_sha256"
    ] = "0" * 64
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_participant_validation_roadmap_sync(record)
