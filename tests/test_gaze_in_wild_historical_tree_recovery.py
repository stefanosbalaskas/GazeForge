from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.gaze_in_wild_historical_tree_recovery import (
    HistoricalTreeRecoveryEvidenceError,
    evidence_fingerprint,
    load_evidence,
    validate_evidence,
)

EVIDENCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "validation"
    / "evidence"
    / "gaze-in-wild"
    / "gaze-in-wild-historical-tree-recovery-evidence-v1.json"
)


@pytest.fixture
def evidence() -> dict:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def test_frozen_historical_tree_recovery_evidence_is_valid() -> None:
    record = load_evidence(EVIDENCE_PATH)
    assert record["embedded_processdata"]["identity"]["PrIdx"] == 2
    assert record["embedded_processdata"]["identity"]["TrIdx"] == 2
    assert record["scientific_boundary"]["empirical_evidence_eligible"] is False


@pytest.mark.parametrize(
    "key",
    [
        "full_distribution_recovered",
        "original_distribution_equivalence_verified",
        "dataset_file_rights_resolved",
        "analysis_use_permitted",
        "redistribution_authorized",
        "quarantine_exit_authorized",
        "source_audit_ready",
        "empirical_evidence_eligible",
    ],
)
def test_scientific_boundary_cannot_be_promoted(evidence: dict, key: str) -> None:
    mutated = copy.deepcopy(evidence)
    mutated["scientific_boundary"][key] = True
    _refingerprint(mutated)
    with pytest.raises(HistoricalTreeRecoveryEvidenceError):
        validate_evidence(mutated)


def test_embedded_sample_cannot_be_promoted_to_distribution(evidence: dict) -> None:
    mutated = copy.deepcopy(evidence)
    mutated["embedded_processdata"]["exact_distribution_file_equivalence_verified"] = True
    _refingerprint(mutated)
    with pytest.raises(HistoricalTreeRecoveryEvidenceError):
        validate_evidence(mutated)


def test_embedded_labels_do_not_create_labeldata_recovery(evidence: dict) -> None:
    mutated = copy.deepcopy(evidence)
    mutated["embedded_processdata"]["separate_labeldata_recovered"] = True
    _refingerprint(mutated)
    with pytest.raises(HistoricalTreeRecoveryEvidenceError):
        validate_evidence(mutated)


def test_raw_path2data_is_rejected(evidence: dict) -> None:
    mutated = copy.deepcopy(evidence)
    mutated["embedded_processdata"]["identity"]["Path2Data"] = "/private/source/path"
    _refingerprint(mutated)
    with pytest.raises(HistoricalTreeRecoveryEvidenceError):
        validate_evidence(mutated)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("PrIdx", 3),
        ("TrIdx", 3),
        ("SR", 120),
        ("timestamp_count", 106_224),
        ("ETG.POR_shape", [106_224, 2]),
    ],
)
def test_embedded_sample_identity_is_pinned(evidence: dict, key: str, value: object) -> None:
    mutated = copy.deepcopy(evidence)
    mutated["embedded_processdata"]["identity"][key] = value
    _refingerprint(mutated)
    with pytest.raises(HistoricalTreeRecoveryEvidenceError):
        validate_evidence(mutated)


def test_repo_mit_cannot_be_added_as_dataset_rights(evidence: dict) -> None:
    mutated = copy.deepcopy(evidence)
    mutated["scientific_boundary"]["dataset_file_rights_resolved"] = True
    mutated["claim_limits"].append("Repository MIT applies to the dataset files.")
    _refingerprint(mutated)
    with pytest.raises(HistoricalTreeRecoveryEvidenceError):
        validate_evidence(mutated)


def test_fingerprint_tampering_is_rejected(evidence: dict) -> None:
    mutated = copy.deepcopy(evidence)
    mutated["evidence_fingerprint_sha256"] = "0" * 64
    with pytest.raises(HistoricalTreeRecoveryEvidenceError):
        validate_evidence(mutated)
