from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_layout_convergence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    EXPECTED_PROBE_FINGERPRINT_SHA256,
    evidence_fingerprint,
    probe_fingerprint,
    validate_gaze_in_wild_layout_convergence_evidence,
    validate_gaze_in_wild_layout_convergence_probe,
)

EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-layout-convergence-evidence-v1.json"
)


def _load_evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _probe() -> dict:
    record = {
        "record_type": "gaze-in-wild-layout-convergence-probe-v1",
        "first_party": {
            "repository": "https://github.com/RSKothari/Gaze-in-Wild",
            "pinned_commit_sha1": "52262d44e366a53369e10ca73c5f41daf0e8f1e5",
            "plot_labels_path": "PlotLabels.m",
            "plot_labels_git_blob_sha1": "511581250e04c62037c71d2da16271be4979d434",
            "gitignore_path": ".gitignore",
            "gitignore_git_blob_sha1": "85f9e994c92da6cbb5632ab241ae7473a83b35e5",
            "process_filename_pattern": "PrIdx_%d_TrIdx_%d.mat",
            "label_filename_pattern": "PrIdx_%d_TrIdx_%d_Lbr_%d.mat",
            "process_variable": "ProcessData",
            "label_variable": "LabelData",
            "mat_files_ignored_by_processing_repository": True,
            "repository_is_exact_dataset_copy": False,
        },
        "secondary_sources": [
            {
                "key": "dfki_open_gaze_lab",
                "repository": (
                    "https://github.com/DFKI-Interactive-Machine-Learning/open-gaze-lab"
                ),
                "pinned_commit_sha1": "2c87abb3ed5d3e21ed027252a8fcd4fcfd9bdeee",
                "path": "backend/src/preprocess_headmounted/giw.py",
                "git_blob_sha1": "eebf405662caa0657095012d9451b3a0576bb5dc",
                "classification": "independent_downstream_full_layout_match",
                "process_filename_grammar_matches_first_party": True,
                "label_filename_grammar_matches_first_party": True,
                "process_variable_matches_first_party": True,
                "label_variable_matches_first_party": True,
                "exact_copy_identity_verified": False,
                "dataset_file_rights_resolved": False,
            },
            {
                "key": "ace_dnv",
                "repository": "https://github.com/arnejad/ACE-DNV",
                "pinned_commit_sha1": "3142eb4457087743664d96994e952ed784741d1f",
                "path": "modules/GiW.py",
                "git_blob_sha1": "eb30815510c2e04d4239e06b7b22ffc74c10c595",
                "classification": "independent_downstream_full_layout_match",
                "process_filename_grammar_matches_first_party": True,
                "label_filename_grammar_matches_first_party": True,
                "process_variable_matches_first_party": True,
                "label_variable_matches_first_party": True,
                "exact_copy_identity_verified": False,
                "dataset_file_rights_resolved": False,
            },
            {
                "key": "leo_umcg_unsupervised",
                "repository": (
                    "https://github.com/LEO-UMCG/"
                    "Unsupervised-Gaze-Event-Discrimination"
                ),
                "pinned_commit_sha1": "12ff306d8690e483d5e721e18d447fbd0d887e54",
                "path": "preprocessing.py",
                "git_blob_sha1": "7489c5df1ef5f5d7125f14b6b609ab2e170c0d3e",
                "classification": (
                    "independent_downstream_label_schema_corroboration"
                ),
                "raw_giw_label_files_read": True,
                "label_variable_matches_first_party": True,
                "full_filename_grammar_independently_verified": False,
                "exact_copy_identity_verified": False,
                "dataset_file_rights_resolved": False,
            },
        ],
        "convergence": {
            "independent_downstream_source_count": 3,
            "full_layout_match_count": 2,
            "label_schema_corroboration_count": 3,
            "candidate_layout_screening_signal_only": True,
            "filename_or_schema_match_proves_exact_copy": False,
            "filename_or_schema_match_proves_source_authority": False,
            "filename_or_schema_match_proves_dataset_file_rights": False,
            "filename_or_schema_match_authorizes_empirical_use": False,
        },
        "scientific_boundary": {
            "authoritative_original_or_canonical_dataset_copy_obtained": False,
            "original_distribution_equivalence_verified": False,
            "dataset_file_rights_resolved": False,
            "analysis_use_permitted": False,
            "redistribution_authorized": False,
            "quarantine_exit_authorized": False,
            "source_audit_ready": False,
            "empirical_evidence_eligible": False,
            "human_human_agreement_created": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_validation_created": False,
            "gp3_validity_claim_created": False,
            "frozen_evidence_performance_claim_created": False,
        },
    }
    record["probe_fingerprint_sha256"] = probe_fingerprint(record)
    return record


def _refingerprint_evidence(record: dict) -> None:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)


def _refingerprint_probe(record: dict) -> None:
    record["probe_fingerprint_sha256"] = probe_fingerprint(record)


def test_frozen_layout_convergence_evidence_validates() -> None:
    record = validate_gaze_in_wild_layout_convergence_evidence(EVIDENCE)
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert record["downstream_convergence"]["full_layout_match_count"] == 2
    assert record["downstream_convergence"]["label_schema_corroboration_count"] == 3


def test_reviewed_probe_binds_exactly() -> None:
    probe = _probe()
    assert probe["probe_fingerprint_sha256"] == EXPECTED_PROBE_FINGERPRINT_SHA256
    summary = validate_gaze_in_wild_layout_convergence_probe(probe, EVIDENCE)
    assert summary.candidate_layout_screening_signal_only is True
    assert summary.exact_copy_identity_verified is False


@pytest.mark.parametrize(
    ("section", "key"),
    [
        ("downstream_convergence", "convergence_is_exact_copy_identity_evidence"),
        ("downstream_convergence", "convergence_is_dataset_file_rights_evidence"),
        ("downstream_convergence", "convergence_is_empirical_authorization"),
        ("scientific_boundary", "analysis_use_permitted"),
        ("scientific_boundary", "redistribution_authorized"),
        ("scientific_boundary", "quarantine_exit_authorized"),
        ("scientific_boundary", "empirical_evidence_eligible"),
    ],
)
def test_frozen_evidence_rejects_unsupported_promotions(section: str, key: str) -> None:
    record = _load_evidence()
    record[section][key] = True
    _refingerprint_evidence(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_layout_convergence_evidence(record)


def test_frozen_evidence_rejects_first_party_repository_as_dataset_copy() -> None:
    record = _load_evidence()
    record["first_party_schema"]["repository_is_exact_dataset_copy"] = True
    _refingerprint_evidence(record)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_layout_convergence_evidence(record)


def test_probe_rejects_secondary_full_layout_match_as_exact_copy() -> None:
    probe = _probe()
    probe["secondary_sources"][0]["exact_copy_identity_verified"] = True
    _refingerprint_probe(probe)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_layout_convergence_probe(probe, EVIDENCE)


def test_probe_rejects_layout_match_as_rights_evidence() -> None:
    probe = _probe()
    probe["convergence"]["filename_or_schema_match_proves_dataset_file_rights"] = True
    _refingerprint_probe(probe)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_layout_convergence_probe(probe, EVIDENCE)


def test_probe_rejects_layout_match_as_empirical_authorization() -> None:
    probe = _probe()
    probe["convergence"]["filename_or_schema_match_authorizes_empirical_use"] = True
    _refingerprint_probe(probe)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_layout_convergence_probe(probe, EVIDENCE)


def test_probe_rejects_changed_source_identity() -> None:
    probe = _probe()
    probe["secondary_sources"][1]["pinned_commit_sha1"] = "0" * 40
    _refingerprint_probe(probe)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_layout_convergence_probe(probe, EVIDENCE)


def test_probe_rejects_scientific_gate_promotion() -> None:
    probe = _probe()
    probe["scientific_boundary"]["source_audit_ready"] = True
    _refingerprint_probe(probe)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_layout_convergence_probe(probe, EVIDENCE)


def test_evidence_tampering_without_refingerprint_is_rejected() -> None:
    record = copy.deepcopy(_load_evidence())
    record["first_party_schema"]["process_variable"] = "OtherData"
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_layout_convergence_evidence(record)
