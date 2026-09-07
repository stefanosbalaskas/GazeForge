from __future__ import annotations

import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_token_portability_v3_evidence import (
    PORTABILITY_V3_EVIDENCE_FINGERPRINT,
    V3_CANONICAL_REPORT_FILE_SHA256,
    V3_CANONICAL_REPORT_FINGERPRINT,
    V3_DIAGNOSTIC_ARTIFACT_ID,
    V3_DIAGNOSTIC_ARTIFACT_ZIP_SHA256,
    V3_DIAGNOSTIC_CONTENT_FINGERPRINT,
    V3_DIAGNOSTIC_HEAD_SHA,
    V3_DIAGNOSTIC_JOB_ID,
    V3_DIAGNOSTIC_LIVE_RAW_REPORT_FILE_SHA256,
    V3_DIAGNOSTIC_LIVE_RAW_REPORT_FINGERPRINT,
    V3_DIAGNOSTIC_MAX_ABS_RAW_METRIC_DELTA,
    V3_DIAGNOSTIC_MAX_DELTA_PATH,
    V3_DIAGNOSTIC_REPORT_FILE_SHA256,
    V3_DIAGNOSTIC_RUN_ID,
    portability_v3_evidence_fingerprint,
    validate_hollywood2_source_token_portability_v3_evidence,
)

EVIDENCE = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-source-token-numeric-portability-evidence-v3.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = portability_v3_evidence_fingerprint(record)
    return record


def test_hollywood2_v3_portability_evidence_is_immutable() -> None:
    record = validate_hollywood2_source_token_portability_v3_evidence(EVIDENCE)
    assert record["evidence_fingerprint_sha256"] == PORTABILITY_V3_EVIDENCE_FINGERPRINT
    assert portability_v3_evidence_fingerprint(record) == PORTABILITY_V3_EVIDENCE_FINGERPRINT

    after = record["migration"]["to_contract"]
    assert after["metric_float_decimal_places"] == 13
    assert after["canonical_source_report_fingerprint_sha256"] == (
        V3_CANONICAL_REPORT_FINGERPRINT
    )
    assert after["canonical_source_report_file_sha256"] == V3_CANONICAL_REPORT_FILE_SHA256


def test_hollywood2_v3_diagnostic_lineage_is_exact() -> None:
    record = validate_hollywood2_source_token_portability_v3_evidence(EVIDENCE)
    diagnostic = record["portability_observations"]["full_report_diagnostic"]
    assert diagnostic["workflow_run_id"] == V3_DIAGNOSTIC_RUN_ID
    assert diagnostic["job_id"] == V3_DIAGNOSTIC_JOB_ID
    assert diagnostic["head_sha"] == V3_DIAGNOSTIC_HEAD_SHA
    assert diagnostic["artifact_id"] == V3_DIAGNOSTIC_ARTIFACT_ID
    assert diagnostic["artifact_zip_sha256"] == V3_DIAGNOSTIC_ARTIFACT_ZIP_SHA256
    assert diagnostic["diagnostic_report_file_sha256"] == V3_DIAGNOSTIC_REPORT_FILE_SHA256
    assert diagnostic["diagnostic_content_fingerprint_sha256"] == (
        V3_DIAGNOSTIC_CONTENT_FINGERPRINT
    )
    assert diagnostic["live_raw_report_file_sha256"] == (
        V3_DIAGNOSTIC_LIVE_RAW_REPORT_FILE_SHA256
    )
    assert diagnostic["live_raw_report_fingerprint_sha256"] == (
        V3_DIAGNOSTIC_LIVE_RAW_REPORT_FINGERPRINT
    )
    assert diagnostic["max_abs_raw_metric_delta"] == V3_DIAGNOSTIC_MAX_ABS_RAW_METRIC_DELTA
    assert diagnostic["max_abs_raw_metric_delta_path"] == V3_DIAGNOSTIC_MAX_DELTA_PATH
    assert diagnostic["highest_precision_with_exact_full_report_match"] == 13
    assert diagnostic["precision_14_exact_full_report_match"] is False
    assert diagnostic["precision_13_exact_full_report_match"] is True


def test_hollywood2_v3_rejects_precision_relaxation() -> None:
    record = _record()
    record["migration"]["to_contract"]["metric_float_decimal_places"] = 12
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_source_token_portability_v3_evidence(record)


def test_hollywood2_v3_rejects_diagnostic_lineage_drift() -> None:
    record = _record()
    record["portability_observations"]["full_report_diagnostic"]["artifact_id"] += 1
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_source_token_portability_v3_evidence(record)


def test_hollywood2_v3_rejects_false_high_precision_claim() -> None:
    record = _record()
    record["portability_observations"]["full_report_diagnostic"][
        "precision_14_exact_full_report_match"
    ] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_source_token_portability_v3_evidence(record)


def test_hollywood2_v3_rejects_reviewed_artifact_lineage_drift() -> None:
    record = _record()
    record["reviewed_source_verified_artifacts"]["exact_merge"]["artifact_id"] += 1
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_source_token_portability_v3_evidence(record)


@pytest.mark.parametrize(
    "flag",
    [
        "scientific_metrics_reestimated",
        "model_configuration_changed",
        "fold_assignment_changed",
        "source_rows_changed",
        "participant_identity_mapping_verified",
        "participant_disjoint_validation_created",
        "participant_generalization_claim",
        "cross_dataset_validation_created",
        "rights_status_changed",
        "raw_source_redistributed_by_gazeforge",
        "v1_evidence_rewritten",
        "v2_evidence_rewritten",
    ],
)
def test_hollywood2_v3_rejects_scientific_or_governance_promotions(flag: str) -> None:
    record = _record()
    record["scientific_boundary"][flag] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_source_token_portability_v3_evidence(record)
