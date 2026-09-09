from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_copy_rights_roadmap_sync import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    evidence_fingerprint,
    validate_hollywood2_copy_rights_roadmap_sync,
    validate_hollywood2_copy_rights_roadmap_sync_with_upstreams,
)

EVIDENCE_DIR = Path("validation/evidence/hollywood2")
EVIDENCE = EVIDENCE_DIR / "hollywood2-copy-rights-roadmap-sync-evidence-v1.json"
AUTHORITATIVE = EVIDENCE_DIR / "hollywood2-authoritative-ground-truth-evidence-v1.json"
HISTORY = EVIDENCE_DIR / "hollywood2-gin-history-evidence-v1.json"
AUTHOR_LICENSE = EVIDENCE_DIR / "hollywood2-author-license-statement-evidence-v1.json"
ORIGINAL_SUBJECT = EVIDENCE_DIR / "hollywood2-original-subject-metadata-evidence-v1.json"


def _record() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def test_committed_hollywood2_copy_rights_roadmap_sync_validates() -> None:
    record = validate_hollywood2_copy_rights_roadmap_sync(EVIDENCE)
    assert record["roadmap"]["authoritative_copy_source_identity_component_satisfied"] is True
    assert record["roadmap"]["current_reuse_terms_component_satisfied"] is False
    assert record["identity_boundary"]["participant_identity_mapping_verified"] is False


def test_sync_revalidates_all_four_upstream_evidence_records() -> None:
    record = validate_hollywood2_copy_rights_roadmap_sync_with_upstreams(
        EVIDENCE,
        authoritative_evidence_path=AUTHORITATIVE,
        history_evidence_path=HISTORY,
        author_license_evidence_path=AUTHOR_LICENSE,
        original_subject_evidence_path=ORIGINAL_SUBJECT,
    )
    assert record["canonical_copy_identity"]["ground_truth_file_count"] == 697
    assert record["canonical_copy_identity"]["ground_truth_total_samples"] == 3871580


def test_hollywood2_copy_rights_roadmap_fingerprint_is_frozen() -> None:
    record = _record()
    assert evidence_fingerprint(record) == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT_SHA256


@pytest.mark.parametrize(
    ("key", "match"),
    [
        ("exact_annotation_repository_license_identifier_verified", "exact licence identifier"),
        ("exact_annotation_repository_license_text_verified", "exact licence text"),
        ("analysis_use_terms_resolved", "analysis-use terms"),
        ("raw_annotation_redistribution_terms_resolved", "redistribution terms"),
        ("article_cc_by_promoted_to_dataset_license", "article CC BY as dataset licence"),
        ("original_hollywood2_terms_promoted_to_gin_terms", "original-source rights inheritance"),
    ],
)
def test_refingerprinting_cannot_promote_unresolved_rights(key: str, match: str) -> None:
    record = copy.deepcopy(_record())
    record["rights_boundary"][key] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match=match):
        validate_hollywood2_copy_rights_roadmap_sync(record)


@pytest.mark.parametrize(
    ("key", "match"),
    [
        ("participant_identity_mapping_verified", "participant identity mapping"),
        ("participant_group_mapping_verified", "participant group mapping"),
    ],
)
def test_refingerprinting_cannot_promote_participant_mapping(key: str, match: str) -> None:
    record = copy.deepcopy(_record())
    record["identity_boundary"][key] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match=match):
        validate_hollywood2_copy_rights_roadmap_sync(record)


@pytest.mark.parametrize(
    ("key", "match"),
    [
        ("current_reuse_terms_component_satisfied", "current reuse-terms component"),
        ("participant_identity_mapping_component_satisfied", "participant mapping component"),
        ("lund_hollywood2_cross_dataset_component_satisfied", "cross-dataset component"),
    ],
)
def test_refingerprinting_cannot_close_open_roadmap_components(key: str, match: str) -> None:
    record = copy.deepcopy(_record())
    record["roadmap"][key] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match=match):
        validate_hollywood2_copy_rights_roadmap_sync(record)


@pytest.mark.parametrize(
    ("key", "match"),
    [
        ("new_empirical_performance_claim_created", "new empirical performance"),
        ("participant_disjoint_hollywood2_validation_created", "participant-disjoint validation"),
        ("cross_dataset_validation_created", "cross-dataset validation"),
        ("redistribution_authorized", "redistribution authorization"),
    ],
)
def test_refingerprinting_cannot_promote_scientific_boundaries(key: str, match: str) -> None:
    record = copy.deepcopy(_record())
    record["scientific_boundary"][key] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match=match):
        validate_hollywood2_copy_rights_roadmap_sync(record)


def test_refingerprinting_cannot_claim_gazeforge_redistributes_source_bytes() -> None:
    record = copy.deepcopy(_record())
    record["canonical_copy_identity"]["source_bytes_redistributed_by_gazeforge"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="source-byte redistribution"):
        validate_hollywood2_copy_rights_roadmap_sync(record)


@pytest.mark.parametrize(
    ("key", "value", "match"),
    [
        ("repository", "https://example.invalid/hollywood2_em.git", "canonical repository"),
        ("pinned_commit_sha1", "0" * 40, "canonical commit"),
        ("ground_truth_file_count", 696, "ground-truth file count"),
        ("ground_truth_total_samples", 3871579, "ground-truth sample count"),
        ("source_identity_ledger_fingerprint_sha256", "0" * 64, "source-identity ledger"),
    ],
)
def test_copy_identity_drift_is_rejected(key: str, value: object, match: str) -> None:
    record = copy.deepcopy(_record())
    record["canonical_copy_identity"][key] = value
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match=match):
        validate_hollywood2_copy_rights_roadmap_sync(record)


@pytest.mark.parametrize(
    "key",
    [
        "authoritative_ground_truth_evidence_fingerprint_sha256",
        "gin_history_evidence_fingerprint_sha256",
        "author_license_statement_evidence_fingerprint_sha256",
        "original_subject_metadata_evidence_fingerprint_sha256",
    ],
)
def test_upstream_evidence_fingerprint_drift_is_rejected(key: str) -> None:
    record = copy.deepcopy(_record())
    record["upstream_evidence"][key] = "0" * 64
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="upstream evidence"):
        validate_hollywood2_copy_rights_roadmap_sync(record)


def test_copy_identity_component_cannot_be_reopened_by_refingerprinting() -> None:
    record = copy.deepcopy(_record())
    record["roadmap"]["authoritative_copy_source_identity_component_satisfied"] = False
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="authoritative copy/source-identity"):
        validate_hollywood2_copy_rights_roadmap_sync(record)
