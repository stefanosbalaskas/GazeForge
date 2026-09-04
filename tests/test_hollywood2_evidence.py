from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    evidence_fingerprint,
    load_hollywood2_authoritative_evidence,
    validate_hollywood2_authoritative_evidence,
)

EVIDENCE = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-authoritative-ground-truth-evidence-v1.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def test_committed_hollywood2_authoritative_evidence_validates() -> None:
    record = validate_hollywood2_authoritative_evidence(EVIDENCE)
    assert record["upstream"]["commit_sha1"] == "870fa6d6209c9085260918d61433a0a2c70fd497"
    assert record["coverage"]["ground_truth_file_count"] == 697
    assert record["coverage"]["ground_truth_total_samples"] == 3_871_580


def test_compact_hollywood2_evidence_loader() -> None:
    loaded = load_hollywood2_authoritative_evidence(EVIDENCE)
    assert loaded.fingerprint_sha256 == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert loaded.ground_truth_file_count == 697
    assert loaded.sample_count == 3_871_580
    assert loaded.clip_count == 56
    assert loaded.file_subject_token_count == 16
    assert loaded.student_final_raw_agreement == pytest.approx(0.9247555261676111)


def test_hollywood2_evidence_self_fingerprint_tamper_fails() -> None:
    record = _record()
    record["coverage"]["ground_truth_total_samples"] += 1
    with pytest.raises(BenchmarkIntegrityError, match="sample count"):
        validate_hollywood2_authoritative_evidence(record)


def test_hollywood2_evidence_upstream_commit_drift_fails() -> None:
    record = _record()
    record["upstream"]["commit_sha1"] = "0" * 40
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="upstream commit"):
        validate_hollywood2_authoritative_evidence(record)


def test_hollywood2_source_ledger_fingerprint_drift_fails() -> None:
    record = _record()
    record["source_ledger"]["entries_fingerprint_sha256"] = "0" * 64
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="source-ledger fingerprint"):
        validate_hollywood2_authoritative_evidence(record)


def test_hollywood2_final_label_drift_fails() -> None:
    record = _record()
    record["final_labels"]["counts"]["FIX"] -= 1
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="final-label counts"):
        validate_hollywood2_authoritative_evidence(record)


def test_hollywood2_student_final_sensitivity_drift_fails() -> None:
    record = _record()
    record["student_vs_expert_corrected_sensitivity"]["changed_sample_count"] += 1
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="changed sample count"):
        validate_hollywood2_authoritative_evidence(record)


@pytest.mark.parametrize(
    ("section", "key", "value", "message"),
    [
        ("rights", "dataset_specific_license_verified", True, "dataset-license verification"),
        (
            "rights",
            "source_bytes_redistributed_by_gazeforge",
            True,
            "source-byte redistribution",
        ),
        (
            "scientific_boundary",
            "participant_identity_mapping_verified",
            True,
            "participant identity mapping",
        ),
        (
            "scientific_boundary",
            "independent_human_human_agreement_created",
            True,
            "independent human-human agreement",
        ),
        (
            "scientific_boundary",
            "model_validation_created",
            True,
            "model validation",
        ),
        (
            "scientific_boundary",
            "cross_dataset_validation_created",
            True,
            "cross-dataset validation",
        ),
        (
            "scientific_boundary",
            "full_original_hollywood2_video_dataset_recovered",
            True,
            "full video dataset recovery",
        ),
        (
            "scientific_boundary",
            "frozen_evidence_created",
            True,
            "canonical Frozen Evidence",
        ),
    ],
)
def test_hollywood2_claim_promotion_fails(
    section: str,
    key: str,
    value: object,
    message: str,
) -> None:
    record = copy.deepcopy(_record())
    record[section][key] = value
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match=message):
        validate_hollywood2_authoritative_evidence(record)


def test_hollywood2_immutable_v1_fingerprint_is_frozen() -> None:
    record = _record()
    assert evidence_fingerprint(record) == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
