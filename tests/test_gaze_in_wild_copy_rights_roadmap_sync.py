from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_copy_rights_roadmap_sync import (
    EVIDENCE_FINGERPRINT,
    EXPECTED_ISSUE_WORDING,
    VERIFIED_FILE_COUNT,
    VERIFIED_TOTAL_BYTES,
    evidence_fingerprint,
    validate_gaze_in_wild_copy_rights_roadmap_sync,
)

EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-roadmap-evidence-sync-v2.json"
)


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def test_copy_rights_roadmap_sync_validates() -> None:
    result = validate_gaze_in_wild_copy_rights_roadmap_sync(EVIDENCE)
    assert result.fingerprint_sha256 == EVIDENCE_FINGERPRINT
    assert result.official_figshare_item_satisfied is True
    assert result.license_name == "CC BY 4.0"
    assert result.verified_file_count == VERIFIED_FILE_COUNT == 118
    assert result.verified_total_size_bytes == VERIFIED_TOTAL_BYTES == 2_413_299_242
    assert result.raw_dataset_bytes_retained is False
    assert result.quarantine_exit_authorized is False


def test_stored_fingerprint_tampering_fails() -> None:
    record = _load()
    record["evidence_fingerprint_sha256"] = "0" * 64
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_gaze_in_wild_copy_rights_roadmap_sync(record)


@pytest.mark.parametrize(
    ("section", "key"),
    [
        ("roadmap_completion", "historical_rit_archive_byte_equivalence_verified"),
        ("roadmap_completion", "authoritative_numeric_task_mapping_item_satisfied"),
        ("roadmap_completion", "task_stratified_validation_item_satisfied"),
        ("scientific_boundary", "historical_rit_archive_byte_equivalence_verified"),
        ("scientific_boundary", "processdata_cleaned_promoted_to_original"),
        ("scientific_boundary", "raw_dataset_bytes_retained"),
        ("scientific_boundary", "quarantine_exit_authorized"),
        ("scientific_boundary", "task_mapping_verified"),
        ("scientific_boundary", "task_stratified_model_validation_created"),
        ("scientific_boundary", "cross_dataset_validation_created"),
        ("scientific_boundary", "native_60hz_validity_claim_created"),
        ("scientific_boundary", "gp3_validity_claim_created"),
        ("scientific_boundary", "acquisition_hardware_cadence_verified"),
        ("scientific_boundary", "new_empirical_performance_claim_created"),
    ],
)
def test_refingerprinted_forbidden_promotions_fail(section: str, key: str) -> None:
    record = copy.deepcopy(_load())
    record[section][key] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_copy_rights_roadmap_sync(record)


def test_scoped_completion_cannot_be_revoked_and_refingerprinted() -> None:
    record = copy.deepcopy(_load())
    record["roadmap_completion"][
        "official_figshare_original_publication_copy_and_current_reuse_terms_scoped_item_satisfied"
    ] = False
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_copy_rights_roadmap_sync(record)


@pytest.mark.parametrize(
    ("section", "key", "replacement"),
    [
        ("figshare_distribution_rights", "deposit_author_name", "Unknown Author"),
        ("figshare_distribution_rights", "verified_license_name", "CC0"),
        ("figshare_distribution_rights", "processdata_doi", "10.0000/drift"),
        ("figshare_distribution_rights", "labeldata_doi", "10.0000/drift"),
        ("figshare_exact_bytes", "verified_file_count", 119),
        ("figshare_exact_bytes", "verified_total_size_bytes", 2_413_299_243),
        ("figshare_exact_bytes", "stable_exact_byte_identity_fingerprint_sha256", "0" * 64),
        ("figshare_exact_bytes", "raw_dataset_bytes_retained", True),
        ("figshare_exact_bytes", "processdata_cleaned_downloaded", True),
    ],
)
def test_refingerprinted_upstream_summary_drift_fails(
    section: str,
    key: str,
    replacement: object,
) -> None:
    record = copy.deepcopy(_load())
    record["upstream_evidence"][section][key] = replacement
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_copy_rights_roadmap_sync(record)


def test_verified_article_labels_cannot_include_cleaned_data() -> None:
    record = copy.deepcopy(_load())
    record["upstream_evidence"]["figshare_exact_bytes"]["verified_article_labels"].append(
        "ProcessData_cleaned"
    )
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_copy_rights_roadmap_sync(record)


def test_issue_wording_is_exact_and_cannot_claim_historical_archive() -> None:
    record = copy.deepcopy(_load())
    assert record["issue_wording"]["official_copy_and_rights"] == EXPECTED_ISSUE_WORDING
    record["issue_wording"]["official_copy_and_rights"] = (
        "Obtain/audit the authoritative historical RIT archive and prove equivalence."
    )
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_copy_rights_roadmap_sync(record)


def test_claim_limit_cannot_be_widened() -> None:
    record = copy.deepcopy(_load())
    record["claim_limit"] = "All Gaze-in-the-Wild source and validation gates are complete."
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_copy_rights_roadmap_sync(record)
