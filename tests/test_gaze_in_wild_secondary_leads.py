from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_secondary_leads import (
    EXPECTED_EVIDENCE_FINGERPRINT,
    EXPECTED_PROBE_FINGERPRINT,
    validate_gaze_in_wild_secondary_lead_evidence,
    validate_gaze_in_wild_secondary_lead_probe,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "validation"
    / "evidence"
    / "gaze-in-wild"
    / "gaze-in-wild-secondary-recovery-lead-evidence-v1.json"
)


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _probe_from_frozen() -> dict:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    probe = {
        "record_type": "gaze-in-wild-secondary-recovery-lead-provenance-probe-v1",
        "dataset": evidence["dataset"],
        "sources": evidence["sources"],
        "scientific_boundary": evidence["scientific_boundary"],
        "claim_limit": evidence["claim_limit"],
    }
    probe["probe_fingerprint_sha256"] = _canonical_sha256(probe)
    return probe


def _refingerprint_probe(probe: dict) -> None:
    body = dict(probe)
    body.pop("probe_fingerprint_sha256", None)
    probe["probe_fingerprint_sha256"] = _canonical_sha256(body)


def _refingerprint_evidence(evidence: dict) -> None:
    body = dict(evidence)
    body.pop("evidence_fingerprint_sha256", None)
    evidence["evidence_fingerprint_sha256"] = _canonical_sha256(body)


def test_frozen_secondary_lead_evidence_is_self_consistent() -> None:
    probe = _probe_from_frozen()
    assert probe["probe_fingerprint_sha256"] == EXPECTED_PROBE_FINGERPRINT
    validated = validate_gaze_in_wild_secondary_lead_evidence(probe, EVIDENCE)
    assert validated.probe_fingerprint_sha256 == EXPECTED_PROBE_FINGERPRINT
    assert validated.evidence_fingerprint_sha256 == EXPECTED_EVIDENCE_FINGERPRINT


def test_secondary_leads_remain_distinct_non_empirical_classes() -> None:
    probe = validate_gaze_in_wild_secondary_lead_probe(_probe_from_frozen())
    transformed = probe["sources"]["transformed_collection_lead"]
    labeller = probe["sources"]["labeller_filename_lead"]
    assert (
        transformed["classification"]
        == "external_transformed_collection_advertisement"
    )
    assert (
        transformed["advertised_annotation_representation"]
        == "CSV files (one per chunk)"
    )
    assert transformed["tracked_official_process_or_label_paths"] == []
    assert labeller["classification"] == "local_path_reference_only"
    assert labeller["reference_code_paths"] == [
        "levenGPU_demo.py",
        "levenSequential.py",
    ]
    assert labeller["referenced_labeller_files_repository_resident"] is False
    assert labeller["independent_annotation_streams_recovered"] is False
    assert not any(probe["scientific_boundary"].values())


@pytest.mark.parametrize(
    "boundary_key",
    [
        "authoritative_original_dataset_copy_obtained",
        "dataset_file_rights_resolved",
        "independent_labeller_recoverability_verified",
        "empirical_evidence_eligible",
        "human_human_agreement_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_performance_created",
        "gp3_validity_created",
        "frozen_evidence_performance_claim_created",
    ],
)
def test_refingerprinted_scientific_promotions_are_rejected(boundary_key: str) -> None:
    probe = copy.deepcopy(_probe_from_frozen())
    probe["scientific_boundary"][boundary_key] = True
    _refingerprint_probe(probe)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_secondary_lead_probe(probe)


def test_refingerprinted_labeller_file_promotion_is_rejected() -> None:
    probe = copy.deepcopy(_probe_from_frozen())
    lead = probe["sources"]["labeller_filename_lead"]
    lead["referenced_labeller_files_repository_resident"] = True
    lead["independent_annotation_streams_recovered"] = True
    lead["human_human_agreement_eligible"] = True
    _refingerprint_probe(probe)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_secondary_lead_probe(probe)


def test_refingerprinted_transformed_collection_promotion_is_rejected() -> None:
    probe = copy.deepcopy(_probe_from_frozen())
    lead = probe["sources"]["transformed_collection_lead"]
    lead["external_collection_contents_obtained_by_this_probe"] = True
    lead["authoritative_original_distribution_equivalence_verified"] = True
    _refingerprint_probe(probe)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_secondary_lead_probe(probe)


def test_frozen_evidence_tampering_is_rejected() -> None:
    probe = _probe_from_frozen()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    evidence["review_status"] = "empirical"
    with pytest.raises(BenchmarkIntegrityError, match="must remain quarantined"):
        validate_gaze_in_wild_secondary_lead_evidence(probe, evidence)


def test_refingerprinted_frozen_evidence_tampering_is_rejected() -> None:
    probe = _probe_from_frozen()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    evidence["review_status"] = "empirical"
    _refingerprint_evidence(evidence)
    with pytest.raises(BenchmarkIntegrityError, match="must remain quarantined"):
        validate_gaze_in_wild_secondary_lead_evidence(probe, evidence)


def test_refingerprinted_extra_evidence_metadata_is_rejected() -> None:
    probe = _probe_from_frozen()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    evidence["empirical_status"] = "approved"
    _refingerprint_evidence(evidence)
    with pytest.raises(BenchmarkIntegrityError, match="reviewed evidence contract drifted"):
        validate_gaze_in_wild_secondary_lead_evidence(probe, evidence)
