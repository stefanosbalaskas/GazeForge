from __future__ import annotations

import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_token_portability_evidence import (
    PORTABILITY_EVIDENCE_FINGERPRINT,
    V1_CANONICAL_REPORT_FILE_SHA256,
    V1_CANONICAL_REPORT_FINGERPRINT,
    V1_FROZEN_SUMMARY_FINGERPRINT,
    V2_CANONICAL_REPORT_FILE_SHA256,
    V2_CANONICAL_REPORT_FINGERPRINT,
    portability_evidence_fingerprint,
    validate_hollywood2_source_token_portability_evidence,
)

EVIDENCE = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-source-token-numeric-portability-evidence-v2.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = portability_evidence_fingerprint(record)
    return record


def test_hollywood2_numeric_portability_evidence_is_immutable() -> None:
    record = validate_hollywood2_source_token_portability_evidence(EVIDENCE)
    assert record["evidence_fingerprint_sha256"] == PORTABILITY_EVIDENCE_FINGERPRINT
    assert portability_evidence_fingerprint(record) == PORTABILITY_EVIDENCE_FINGERPRINT

    before = record["migration"]["from_contract"]
    after = record["migration"]["to_contract"]
    assert before["frozen_summary_report_fingerprint_sha256"] == V1_FROZEN_SUMMARY_FINGERPRINT
    assert before["canonical_source_report_fingerprint_sha256"] == V1_CANONICAL_REPORT_FINGERPRINT
    assert before["canonical_source_report_file_sha256"] == V1_CANONICAL_REPORT_FILE_SHA256
    assert after["canonical_source_report_fingerprint_sha256"] == V2_CANONICAL_REPORT_FINGERPRINT
    assert after["canonical_source_report_file_sha256"] == V2_CANONICAL_REPORT_FILE_SHA256


def test_hollywood2_numeric_portability_evidence_rejects_precision_relaxation() -> None:
    record = _record()
    record["migration"]["to_contract"]["metric_float_decimal_places"] = 13
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_source_token_portability_evidence(record)


def test_hollywood2_numeric_portability_evidence_rejects_lineage_drift() -> None:
    record = _record()
    record["reviewed_source_verified_artifacts"]["exact_merge"]["artifact_id"] += 1
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_source_token_portability_evidence(record)


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
    ],
)
def test_hollywood2_numeric_portability_evidence_rejects_promotions(flag: str) -> None:
    record = _record()
    record["scientific_boundary"][flag] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_source_token_portability_evidence(record)
