from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_exact_validation_v2 import validate_exact_execution_protocol_v2

ROOT = Path(__file__).parents[1]
EVIDENCE_ROOT = ROOT / "validation" / "evidence" / "gaze-in-wild"
PROTOCOL_V2_PATH = (
    EVIDENCE_ROOT / "gaze-in-wild-exact-model-execution-protocol-evidence-v2.json"
)


def _load() -> dict:
    return json.loads(PROTOCOL_V2_PATH.read_text(encoding="utf-8"))


def test_committed_execution_protocol_v2_validates() -> None:
    record = validate_exact_execution_protocol_v2(_load())
    protocol = record["execution_protocol"]
    amendment = record["amendment"]
    assert protocol["temporal_max_iter"] == 1000
    assert protocol["context_mlp_convergence_warning_policy"] == "error"
    assert amendment["changed_fields"] == {"temporal_max_iter": {"from": 200, "to": 1000}}
    assert amendment["performance_metrics_used_to_choose_amendment"] is False


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("temporal_max_iter", 999),
        ("context_mlp_convergence_warning_policy", "warn"),
        ("source_confidence_threshold", 0.0),
        ("task_mapping_used", True),
        ("task_stratified_validation_authorized", True),
        ("n_splits", 4),
        ("random_forest_n_estimators", 300),
        ("raw_mat_retention_authorized", True),
    ],
)
def test_v2_execution_protocol_relaxation_fails(field: str, replacement: object) -> None:
    record = deepcopy(_load())
    record["execution_protocol"][field] = replacement
    with pytest.raises(BenchmarkIntegrityError):
        validate_exact_execution_protocol_v2(record)


def test_v2_amendment_cannot_change_extra_field() -> None:
    record = deepcopy(_load())
    record["amendment"]["changed_fields"]["random_forest_n_estimators"] = {
        "from": 200,
        "to": 300,
    }
    with pytest.raises(BenchmarkIntegrityError):
        validate_exact_execution_protocol_v2(record)


def test_v2_amendment_cannot_be_declared_performance_selected() -> None:
    record = deepcopy(_load())
    record["amendment"]["performance_metrics_used_to_choose_amendment"] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_exact_execution_protocol_v2(record)


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
def test_v2_preperformance_boundary_promotion_fails(field: str) -> None:
    record = deepcopy(_load())
    record["scientific_boundary"][field] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_exact_execution_protocol_v2(record)
