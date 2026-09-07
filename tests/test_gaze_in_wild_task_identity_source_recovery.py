from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.gaze_in_wild_task_identity_source_recovery import (
    TaskIdentitySourceRecoveryEvidenceError,
    evidence_fingerprint,
    load_evidence,
    validate_evidence,
)

EVIDENCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "validation"
    / "evidence"
    / "gaze-in-wild"
    / "gaze-in-wild-task-identity-source-recovery-evidence-v1.json"
)


@pytest.fixture
def evidence() -> dict:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> None:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)


def test_frozen_negative_source_recovery_evidence_is_valid() -> None:
    record = load_evidence(EVIDENCE_PATH)
    assert record["source_scope"]["reachable_commit_count"] == 56
    assert record["source_scope"]["unique_text_blob_count"] == 302
    assert record["mlapp_audit"]["task_context_count"] == 0
    assert (
        record["reachable_history_observation"]
        ["identity_plus_tridx_candidate_context_count"]
        == 0
    )
    assert record["scientific_boundary"]["universal_tridx_to_task_mapping_verified"] is False


@pytest.mark.parametrize(
    "key",
    [
        "universal_tridx_to_task_mapping_verified",
        "complete_per_file_task_mapping_verified",
        "participant_disjoint_model_validation_created",
        "human_human_agreement_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "quarantine_exit_authorized",
        "new_empirical_performance_claim_created",
    ],
)
def test_negative_evidence_cannot_promote_scientific_boundary(
    evidence: dict, key: str
) -> None:
    mutated = copy.deepcopy(evidence)
    mutated["scientific_boundary"][key] = True
    _refingerprint(mutated)
    with pytest.raises(TaskIdentitySourceRecoveryEvidenceError):
        validate_evidence(mutated)


def test_indoor_walk_context_cannot_be_promoted_to_global_t1_mapping(evidence: dict) -> None:
    mutated = copy.deepcopy(evidence)
    mutated["reachable_history_observation"]["nearby_tridx_assignments"] = [1]
    mutated["reachable_history_observation"]["explicit_task_to_trial_mapping_recovered"] = True
    _refingerprint(mutated)
    with pytest.raises(TaskIdentitySourceRecoveryEvidenceError):
        validate_evidence(mutated)


def test_mlapp_cannot_gain_unreviewed_task_context(evidence: dict) -> None:
    mutated = copy.deepcopy(evidence)
    mutated["mlapp_audit"]["task_context_count"] = 1
    _refingerprint(mutated)
    with pytest.raises(TaskIdentitySourceRecoveryEvidenceError):
        validate_evidence(mutated)


def test_source_inventory_is_pinned(evidence: dict) -> None:
    mutated = copy.deepcopy(evidence)
    mutated["source_scope"]["unique_text_blob_count"] = 301
    _refingerprint(mutated)
    with pytest.raises(TaskIdentitySourceRecoveryEvidenceError):
        validate_evidence(mutated)


def test_probe_artifact_binding_is_pinned(evidence: dict) -> None:
    mutated = copy.deepcopy(evidence)
    mutated["probe_binding"]["probe_fingerprint_sha256"] = "0" * 64
    _refingerprint(mutated)
    with pytest.raises(TaskIdentitySourceRecoveryEvidenceError):
        validate_evidence(mutated)


def test_fingerprint_tampering_is_rejected(evidence: dict) -> None:
    mutated = copy.deepcopy(evidence)
    mutated["evidence_fingerprint_sha256"] = "0" * 64
    with pytest.raises(TaskIdentitySourceRecoveryEvidenceError):
        validate_evidence(mutated)
