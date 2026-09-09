from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_exact_validation_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT,
    EXPECTED_REPRODUCIBILITY_SIGNATURE,
    EXPECTED_SCIENTIFIC_IDENTITY,
    REPRODUCIBILITY_FLOAT_DECIMALS,
    _canonicalize,
    load_reviewed_gaze_in_wild_validation_evidence,
    validate_reviewed_gaze_in_wild_validation_evidence,
)

EVIDENCE_PATH = (
    Path(__file__).parents[1]
    / "validation"
    / "evidence"
    / "gaze-in-wild"
    / "gaze-in-wild-exact-participant-disjoint-model-validation-evidence-v1.json"
)


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _reviewed() -> dict[str, Any]:
    return load_reviewed_gaze_in_wild_validation_evidence(EVIDENCE_PATH)


def _resign(payload: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(payload)
    value.pop("evidence_fingerprint_sha256", None)
    value["evidence_fingerprint_sha256"] = _sha(value)
    return value


def test_committed_reviewed_evidence_is_exactly_frozen() -> None:
    record = validate_reviewed_gaze_in_wild_validation_evidence(_reviewed())
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT
    assert (
        record["source_binding"]["stable_scientific_identity_sha256"]
        == EXPECTED_SCIENTIFIC_IDENTITY
    )
    assert (
        record["reproducibility"]["cross_run_reproducibility_signature_sha256"]
        == EXPECTED_REPRODUCIBILITY_SIGNATURE
    )
    assert (
        record["reproducibility"]["float_decimal_places"]
        == REPRODUCIBILITY_FLOAT_DECIMALS
    )
    assert (
        record["scientific_boundary"]["new_empirical_performance_claim_created"]
        is False
    )


def test_cross_run_float_canonicalization_is_strict_and_deterministic() -> None:
    assert _canonicalize(0.1234567891) == 0.12345679
    assert _canonicalize(-0.0) == 0.0
    assert _canonicalize({"x": [0.1234567891]}) == {"x": [0.12345679]}


def test_reviewed_evidence_rejects_newer_source_binding_even_when_resigned() -> None:
    record = _reviewed()
    record["source_binding"]["discovery_workflow_run_id"] += 1
    with pytest.raises(BenchmarkIntegrityError):
        validate_reviewed_gaze_in_wild_validation_evidence(_resign(record))


def test_reviewed_evidence_rejects_metric_summary_drift_even_when_resigned() -> None:
    record = _reviewed()
    record["metrics"]["summary_core"][2]["macro_f1_mean"] += 0.001
    with pytest.raises(BenchmarkIntegrityError):
        validate_reviewed_gaze_in_wild_validation_evidence(_resign(record))


def test_reviewed_evidence_rejects_metric_section_hash_drift_when_resigned() -> None:
    record = _reviewed()
    record["metrics"]["section_fingerprints_sha256"]["fold_metrics"] = "0" * 64
    with pytest.raises(BenchmarkIntegrityError):
        validate_reviewed_gaze_in_wild_validation_evidence(_resign(record))


def test_reviewed_evidence_rejects_reproducibility_hash_drift_when_resigned() -> None:
    record = _reviewed()
    record["reproducibility"]["metric_section_fingerprints_sha256"][
        "fold_metrics"
    ] = "0" * 64
    with pytest.raises(BenchmarkIntegrityError):
        validate_reviewed_gaze_in_wild_validation_evidence(_resign(record))


def test_reviewed_evidence_rejects_reproducibility_precision_drift_when_resigned() -> None:
    record = _reviewed()
    record["reproducibility"]["float_decimal_places"] = 7
    with pytest.raises(BenchmarkIntegrityError):
        validate_reviewed_gaze_in_wild_validation_evidence(_resign(record))


def test_reviewed_evidence_rejects_metric_row_count_drift_when_resigned() -> None:
    record = _reviewed()
    record["metrics"]["section_row_counts"]["paired_model_fold_deltas"] = 159
    with pytest.raises(BenchmarkIntegrityError):
        validate_reviewed_gaze_in_wild_validation_evidence(_resign(record))


def test_reviewed_evidence_rejects_erased_pursuit_failure_when_resigned() -> None:
    record = _reviewed()
    record["metrics"]["pursuit_failure_case"]["models"]["ContextMLP"]["event_f1"] = 0.4
    with pytest.raises(BenchmarkIntegrityError):
        validate_reviewed_gaze_in_wild_validation_evidence(_resign(record))


def test_reviewed_evidence_rejects_performance_claim_promotion_when_resigned() -> None:
    record = _reviewed()
    record["scientific_boundary"]["new_empirical_performance_claim_created"] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_reviewed_gaze_in_wild_validation_evidence(_resign(record))


def test_reviewed_evidence_rejects_task_mapping_promotion_when_resigned() -> None:
    record = _reviewed()
    record["scientific_boundary"][
        "complete_file_to_publication_task_mapping_verified"
    ] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_reviewed_gaze_in_wild_validation_evidence(_resign(record))


def test_reviewed_evidence_rejects_fold_overlap_when_resigned() -> None:
    record = _reviewed()
    assignments = record["split_integrity"]["fold_participant_assignments"]
    assignments[1]["participant_id"] = assignments[0]["participant_id"]
    with pytest.raises(BenchmarkIntegrityError):
        validate_reviewed_gaze_in_wild_validation_evidence(_resign(record))


def test_reviewed_evidence_rejects_convergence_regression_when_resigned() -> None:
    record = _reviewed()
    record["convergence_review"]["v2_contextmlp_convergence_warning_count"] = 1
    with pytest.raises(BenchmarkIntegrityError):
        validate_reviewed_gaze_in_wild_validation_evidence(_resign(record))


def test_reviewed_evidence_rejects_raw_retention_when_resigned() -> None:
    record = _reviewed()
    record["scientific_boundary"]["raw_dataset_bytes_retained"] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_reviewed_gaze_in_wild_validation_evidence(_resign(record))
