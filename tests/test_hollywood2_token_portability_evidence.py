from __future__ import annotations

import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_token_portability_evidence import (
    HOLLYWOOD2_SOURCE_TOKEN_V1_V2_MAX_ABS_METRIC_DELTA,
    PORTABILITY_EVIDENCE_FINGERPRINT,
    V1_CANONICAL_REPORT_FILE_SHA256,
    V1_CANONICAL_REPORT_FINGERPRINT,
    V1_FROZEN_SUMMARY_FINGERPRINT,
    V2_CANONICAL_REPORT_FILE_SHA256,
    V2_CANONICAL_REPORT_FINGERPRINT,
    portability_evidence_fingerprint,
    validate_hollywood2_source_token_portability_evidence,
    validate_hollywood2_v1_v2_metric_equivalence,
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
    assert (
        before["frozen_summary_report_fingerprint_sha256"]
        == V1_FROZEN_SUMMARY_FINGERPRINT
    )
    assert (
        before["canonical_source_report_fingerprint_sha256"]
        == V1_CANONICAL_REPORT_FINGERPRINT
    )
    assert (
        before["canonical_source_report_file_sha256"]
        == V1_CANONICAL_REPORT_FILE_SHA256
    )
    assert (
        after["canonical_source_report_fingerprint_sha256"]
        == V2_CANONICAL_REPORT_FINGERPRINT
    )
    assert (
        after["canonical_source_report_file_sha256"]
        == V2_CANONICAL_REPORT_FILE_SHA256
    )


def test_hollywood2_v1_v2_metric_equivalence_accepts_only_serialization_delta() -> None:
    v1 = {
        "accuracy": 0.817326596815109,
        "rows": [{"fold": 1, "score": 0.263223085435483}],
        "label": "ContextMLP",
        "enabled": False,
        "missing": None,
    }
    v2 = {
        "accuracy": 0.81732659681511,
        "rows": [{"fold": 1, "score": 0.26322308543548}],
        "label": "ContextMLP",
        "enabled": False,
        "missing": None,
    }
    observed = validate_hollywood2_v1_v2_metric_equivalence(v1, v2)
    assert observed <= HOLLYWOOD2_SOURCE_TOKEN_V1_V2_MAX_ABS_METRIC_DELTA


def test_hollywood2_v1_v2_metric_equivalence_rejects_larger_numeric_drift() -> None:
    with pytest.raises(BenchmarkIntegrityError, match="exceeded portability bound"):
        validate_hollywood2_v1_v2_metric_equivalence(
            {"metric": 0.5},
            {"metric": 0.50000000000002},
        )


def test_hollywood2_v1_v2_metric_equivalence_rejects_structure_drift() -> None:
    with pytest.raises(BenchmarkIntegrityError, match="structure drifted"):
        validate_hollywood2_v1_v2_metric_equivalence(
            {"metric": [0.5]},
            {"other": [0.5]},
        )


def test_hollywood2_v1_v2_metric_equivalence_rejects_nonfloat_drift() -> None:
    with pytest.raises(BenchmarkIntegrityError, match="non-float metric value drifted"):
        validate_hollywood2_v1_v2_metric_equivalence(
            {"fold": 1},
            {"fold": 2},
        )


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
