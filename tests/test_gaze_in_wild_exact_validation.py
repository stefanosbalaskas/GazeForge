from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_exact_validation import (
    _split_integrity,
    validate_exact_execution_protocol,
    validate_exact_reference_manifest,
)

ROOT = Path(__file__).parents[1]
EVIDENCE_ROOT = ROOT / "validation" / "evidence" / "gaze-in-wild"
REFERENCE_PATH = EVIDENCE_ROOT / "gaze-in-wild-exact-model-reference-manifest-v1.json"
PROTOCOL_PATH = EVIDENCE_ROOT / "gaze-in-wild-exact-model-execution-protocol-evidence-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _predictions() -> pd.DataFrame:
    rows = []
    assignments = [(1, "PrIdx_1", [0, 1]), (2, "PrIdx_2", [2, 3])]
    for model in ("I-VT", "RandomForest", "ContextMLP"):
        for fold, participant, positions in assignments:
            for position in positions:
                rows.append(
                    {
                        "comparison_model": model,
                        "validation_fold": fold,
                        "participant_id": participant,
                        "comparison_row_position": position,
                    }
                )
    return pd.DataFrame(rows)


def test_committed_reference_manifest_validates() -> None:
    record = validate_exact_reference_manifest(_load(REFERENCE_PATH))
    selected = record["selected_reference"]
    assert selected["labeller_id"] == 5
    assert selected["participant_count"] == 12
    assert selected["recording_count"] == 18
    assert selected["total_samples"] == 1_590_659


def test_committed_execution_protocol_validates() -> None:
    record = validate_exact_execution_protocol(_load(PROTOCOL_PATH))
    protocol = record["execution_protocol"]
    assert protocol["source_confidence_threshold"] == 0.3
    assert protocol["analysis_sampling_rate_hz"] == 60.0
    assert protocol["task_mapping_used"] is False
    assert protocol["label_process_timestamp_vector_alignment_required"] == (
        "exact_numeric_vector_equality"
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("labeller_id", 6),
        ("participant_count", 11),
        ("recording_count", 17),
        ("total_samples", 1_590_658),
    ],
)
def test_reference_manifest_tampering_fails(field: str, replacement: int) -> None:
    record = deepcopy(_load(REFERENCE_PATH))
    record["selected_reference"][field] = replacement
    with pytest.raises(BenchmarkIntegrityError):
        validate_exact_reference_manifest(record)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("source_confidence_threshold", 0.0),
        ("task_mapping_used", True),
        ("task_stratified_validation_authorized", True),
        ("analysis_sampling_rate_hz", 120.0),
        ("n_splits", 4),
        ("raw_mat_retention_authorized", True),
        ("label_process_timestamp_vector_alignment_required", "approximately_equal"),
    ],
)
def test_execution_protocol_relaxation_fails(field: str, replacement: object) -> None:
    record = deepcopy(_load(PROTOCOL_PATH))
    record["execution_protocol"][field] = replacement
    with pytest.raises(BenchmarkIntegrityError):
        validate_exact_execution_protocol(record)


@pytest.mark.parametrize(
    "field",
    [
        "participant_disjoint_model_validation_created",
        "task_stratified_model_validation_created",
        "complete_file_to_publication_task_mapping_verified",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "quarantine_exit_authorized",
        "new_empirical_performance_claim_created",
    ],
)
def test_preperformance_boundary_promotion_fails(field: str) -> None:
    record = deepcopy(_load(PROTOCOL_PATH))
    record["scientific_boundary"][field] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_exact_execution_protocol(record)


def test_split_integrity_accepts_one_fold_per_participant_and_identical_oof_rows() -> None:
    result = _split_integrity(_predictions())
    assert result["participant_disjoint"] is True
    assert result["all_models_share_identical_oof_rows"] is True
    assert result["participant_count"] == 2
    assert result["fold_count"] == 2
    assert result["oof_row_count_per_model"] == 4


def test_split_integrity_rejects_participant_in_multiple_test_folds() -> None:
    frame = _predictions()
    mask = (frame["comparison_model"] == "I-VT") & (frame["comparison_row_position"] == 2)
    frame.loc[mask, "participant_id"] = "PrIdx_1"
    with pytest.raises(BenchmarkIntegrityError, match="multiple held-out folds"):
        _split_integrity(frame)


def test_split_integrity_rejects_model_oof_coverage_drift() -> None:
    frame = _predictions()
    frame = frame.loc[
        ~(
            (frame["comparison_model"] == "RandomForest")
            & (frame["comparison_row_position"] == 3)
        )
    ].copy()
    with pytest.raises(BenchmarkIntegrityError, match="identical OOF row coverage"):
        _split_integrity(frame)
