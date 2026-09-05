from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_current_listing_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    EXPECTED_LISTING_STATE_FINGERPRINT_SHA256,
    PRIOR_DISTRIBUTION_EVIDENCE_FINGERPRINT_SHA256,
    REVIEWED_OBSERVATION_FINGERPRINT_SHA256,
    evidence_fingerprint,
    listing_state_fingerprint,
    observation_fingerprint,
    validate_gaze_in_wild_current_listing_evidence,
    validate_gaze_in_wild_current_listing_probe,
)

EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-current-first-party-listing-evidence-v1.json"
)
PRIOR = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-distribution-availability-evidence-v1.json"
)


def _evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _probe(*, historical_status: int = 404) -> dict:
    record = {
        "record_type": "gaze-in-wild-current-first-party-listing-probe-v1",
        "current_first_party_page": {
            "url": "https://www.rit.edu/science/perception-movement-lab",
            "observed_http_status": 200,
            "listing_text": "The Gaze-In-Wild Dataset",
            "listing_present_exactly_once": True,
            "listing_target": "https://pubmed.ncbi.nlm.nih.gov/32054884/",
            "listing_target_class": "publication_pubmed",
            "listing_target_is_expected_publication": True,
            "listing_target_is_direct_dataset_archive_verified": False,
            "dataset_file_rights_terms_found_on_listing": False,
        },
        "historical_endpoint_observation": {
            "url": "https://www.cis.rit.edu/~rsk3900/gaze-in-wild/",
            "secure_tls_certificate_verified": False,
            "secure_transport_failure_class": "tls_certificate_verification_error",
            "tls_unverified_fallback_used": True,
            "observed_http_status": historical_status,
            "retrieval_succeeded": historical_status == 200,
            "transport_status_is_source_identity_or_rights_evidence": False,
            "tls_unverified_fallback_is_source_authentication_evidence": False,
            "observation_is_global_unavailability_proof": False,
            "observation_is_exact_copy_identity_evidence": False,
        },
        "review_trigger": {
            "listing_target_changed_from_expected_publication": False,
            "listing_target_is_first_party_rit_candidate": False,
            "requires_human_evidence_review": False,
            "automatic_source_or_rights_promotion_permitted": False,
            "historical_transport_observation_is_review_gate": False,
        },
        "scientific_boundary": {
            "current_first_party_listing_verified": True,
            "current_exact_authoritative_copy_obtained": False,
            "dataset_file_rights_resolved": False,
            "analysis_use_permitted": False,
            "redistribution_authorized": False,
            "participant_mapping_verified": False,
            "complete_trial_to_task_mapping_verified": False,
            "distributed_file_sampling_cadence_verified": False,
            "independent_labeller_recoverability_verified": False,
            "human_human_agreement_created": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_performance_created": False,
            "gp3_validity_created": False,
            "frozen_evidence_performance_claim_created": False,
        },
        "claim_limit": (
            "The current first-party RIT listing is the review gate. The historical endpoint "
            "probe is a transport diagnostic only because HTTP/TLS outcomes can vary by network "
            "environment. A TLS-unverified fallback may observe HTTP status only and is not "
            "source-authentication evidence. Neither listing nor endpoint observations can "
            "automatically establish an exact dataset copy, dataset-file rights, participant/task "
            "mappings, labeller recoverability, agreement, model performance, cross-dataset "
            "validity, or Gazepoint GP3 validity."
        ),
    }
    record["listing_state_fingerprint_sha256"] = listing_state_fingerprint(record)
    record["observation_fingerprint_sha256"] = observation_fingerprint(record)
    return record


def test_frozen_current_listing_evidence_validates_and_extends_prior_record() -> None:
    evidence = validate_gaze_in_wild_current_listing_evidence(EVIDENCE)
    prior = json.loads(PRIOR.read_text(encoding="utf-8"))

    assert evidence.evidence_fingerprint_sha256 == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert evidence.listing_state_fingerprint_sha256 == EXPECTED_LISTING_STATE_FINGERPRINT_SHA256
    assert evidence.current_exact_authoritative_copy_obtained is False
    assert evidence.dataset_file_rights_resolved is False
    assert evidence_fingerprint(_evidence()) == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert (
        _evidence()["prior_distribution_evidence_fingerprint_sha256"]
        == PRIOR_DISTRIBUTION_EVIDENCE_FINGERPRINT_SHA256
        == prior["evidence_fingerprint_sha256"]
    )


def test_reviewed_live_probe_binds_exact_listing_state() -> None:
    probe = _probe()
    evidence = validate_gaze_in_wild_current_listing_probe(probe, EVIDENCE)

    assert probe["listing_state_fingerprint_sha256"] == EXPECTED_LISTING_STATE_FINGERPRINT_SHA256
    assert probe["observation_fingerprint_sha256"] == REVIEWED_OBSERVATION_FINGERPRINT_SHA256
    assert evidence.listing_target == "https://pubmed.ncbi.nlm.nih.gov/32054884/"


def test_historical_transport_status_can_vary_without_promoting_listing_state() -> None:
    probe = _probe(historical_status=502)
    assert probe["listing_state_fingerprint_sha256"] == EXPECTED_LISTING_STATE_FINGERPRINT_SHA256
    assert probe["observation_fingerprint_sha256"] != REVIEWED_OBSERVATION_FINGERPRINT_SHA256

    validate_gaze_in_wild_current_listing_probe(probe, EVIDENCE)


def test_listing_target_change_requires_new_reviewed_state() -> None:
    probe = _probe()
    probe["current_first_party_page"]["listing_target"] = (
        "https://www.rit.edu/example/gaze-in-wild.zip"
    )
    probe["current_first_party_page"]["listing_target_class"] = "first_party_rit_candidate"
    probe["current_first_party_page"]["listing_target_is_expected_publication"] = False
    probe["review_trigger"]["listing_target_changed_from_expected_publication"] = True
    probe["review_trigger"]["listing_target_is_first_party_rit_candidate"] = True
    probe["review_trigger"]["requires_human_evidence_review"] = True
    probe["listing_state_fingerprint_sha256"] = listing_state_fingerprint(probe)
    probe["observation_fingerprint_sha256"] = observation_fingerprint(probe)

    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_current_listing_probe(probe, EVIDENCE)


@pytest.mark.parametrize(
    ("section", "key"),
    [
        ("current_first_party_review", "listing_points_to_direct_dataset_archive"),
        ("current_first_party_review", "current_exact_authoritative_copy_obtained"),
        ("current_first_party_review", "dataset_file_rights_terms_found_on_listing"),
        ("rights_boundary", "article_license_is_external_dataset_file_license"),
        ("rights_boundary", "processing_repository_mit_is_external_dataset_file_license"),
        ("rights_boundary", "current_listing_provides_dataset_file_analysis_terms"),
        ("rights_boundary", "analysis_use_permitted"),
        ("rights_boundary", "redistribution_authorized"),
        ("quarantine_exit_boundary", "exact_copy_identity_verified"),
        ("quarantine_exit_boundary", "dataset_file_rights_resolved"),
        ("quarantine_exit_boundary", "quarantine_exit_authorizable_from_this_evidence"),
        ("scientific_boundary", "current_exact_authoritative_copy_obtained"),
        ("scientific_boundary", "original_distribution_equivalence_verified"),
        ("scientific_boundary", "human_human_agreement_created"),
        ("scientific_boundary", "participant_disjoint_model_validation_created"),
        ("scientific_boundary", "cross_dataset_performance_created"),
        ("scientific_boundary", "gp3_validity_created"),
        ("scientific_boundary", "frozen_evidence_performance_claim_created"),
    ],
)
def test_frozen_evidence_rejects_unsupported_promotion(section: str, key: str) -> None:
    record = copy.deepcopy(_evidence())
    record[section][key] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_current_listing_evidence(record)


def test_transport_status_cannot_be_promoted_to_global_unavailability() -> None:
    record = copy.deepcopy(_evidence())
    record["historical_endpoint_transport_review"][
        "either_status_is_global_unavailability_proof"
    ] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_current_listing_evidence(record)


def test_tls_unverified_fallback_cannot_be_promoted_to_source_authentication() -> None:
    probe = _probe()
    probe["historical_endpoint_observation"][
        "tls_unverified_fallback_is_source_authentication_evidence"
    ] = True
    probe["observation_fingerprint_sha256"] = observation_fingerprint(probe)
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_current_listing_probe(probe, EVIDENCE)


def test_frozen_evidence_fingerprint_rejects_unreviewed_metadata_change() -> None:
    record = copy.deepcopy(_evidence())
    record["reviewed_on"] = "2026-09-07"
    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_current_listing_evidence(record)
