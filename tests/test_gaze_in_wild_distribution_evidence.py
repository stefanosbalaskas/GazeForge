from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_distribution_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    evidence_fingerprint,
    validate_gaze_in_wild_distribution_availability_evidence,
)

EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-distribution-availability-evidence-v1.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_reviewed_distribution_availability_evidence_validates() -> None:
    evidence = validate_gaze_in_wild_distribution_availability_evidence(EVIDENCE)
    assert evidence.fingerprint_sha256 == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert evidence.historical_distribution_identity_verified is True
    assert evidence.current_exact_copy_obtained is False
    assert evidence.dataset_file_rights_resolved is False
    assert evidence_fingerprint(_record()) == EXPECTED_EVIDENCE_FINGERPRINT_SHA256


@pytest.mark.parametrize(
    ("section", "key"),
    [
        ("scientific_boundary", "current_exact_authoritative_copy_obtained"),
        ("scientific_boundary", "exact_distributed_participant_identity_mapping_verified"),
        ("scientific_boundary", "complete_trial_to_task_mapping_verified"),
        ("scientific_boundary", "distributed_file_sampling_cadence_verified"),
        ("scientific_boundary", "separately_recoverable_independent_labeller_streams_verified"),
        ("scientific_boundary", "human_human_agreement_created"),
        ("scientific_boundary", "participant_disjoint_model_validation_created"),
        ("scientific_boundary", "cross_dataset_performance_created"),
        ("scientific_boundary", "gp3_validity_created"),
        ("scientific_boundary", "frozen_evidence_performance_claim_created"),
        ("rights_boundary", "article_license_is_external_dataset_file_license"),
        ("rights_boundary", "processing_repository_mit_is_external_dataset_file_license"),
        ("rights_boundary", "license_inference_permitted"),
    ],
)
def test_evidence_rejects_unsupported_promotion(section: str, key: str) -> None:
    record = copy.deepcopy(_record())
    record[section][key] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_distribution_availability_evidence(record)


def test_failed_endpoint_probe_cannot_be_promoted_to_global_unavailability() -> None:
    record = copy.deepcopy(_record())
    record["current_retrieval_observation"]["observation_is_global_unavailability_proof"] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_distribution_availability_evidence(record)


def test_secondary_processed_mirror_cannot_be_promoted_to_authoritative_copy() -> None:
    record = copy.deepcopy(_record())
    record["secondary_recovery_leads"][0]["authoritative_first_party_copy_verified"] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_distribution_availability_evidence(record)


def test_secondary_labeller_filename_lead_cannot_create_agreement_eligibility() -> None:
    record = copy.deepcopy(_record())
    record["secondary_recovery_leads"][1]["human_human_agreement_eligible"] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_distribution_availability_evidence(record)


def test_fingerprint_rejects_any_unreviewed_content_change() -> None:
    record = copy.deepcopy(_record())
    record["replacement_source_search"]["authoritative_replacement_repository_found"] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_distribution_availability_evidence(record)
