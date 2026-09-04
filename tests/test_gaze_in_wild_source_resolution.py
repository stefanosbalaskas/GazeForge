import json
from pathlib import Path

_RECORD = Path("validation/protocols/gaze-in-wild-source-resolution-2026-09-04.json")


def _load_record():
    return json.loads(_RECORD.read_text(encoding="utf-8"))


def test_gaze_in_wild_source_resolution_stays_non_empirical():
    record = _load_record()

    assert record["record_type"] == "source-resolution-status-v1"
    assert record["dataset"] == "Gaze-in-the-Wild naturalistic eye-head event benchmark"
    assert record["status"] == (
        "published_distribution_identifier_established_current_direct_copy_unverified"
    )
    assert record["published_distribution_identifier_found"] is True
    assert record["current_institutional_dataset_listing_found"] is True
    assert record["current_direct_data_endpoint_verified"] is False
    assert record["source_audit_ready"] is False
    assert record["empirical_evidence_created"] is False


def test_gaze_in_wild_preserves_hardware_rate_separately_from_secondary_catalog():
    provenance = _load_record()["sampling_rate_provenance"]

    assert provenance["published_acquisition_hardware_rate_hz"] == 120
    assert provenance["secondary_evaluation_catalog_rate_hz"] == 300
    assert provenance["rates_reconciled"] is False
    assert provenance["distributed_file_analysis_cadence_verified"] is False
    assert "timestamps" in provenance["required_resolution_method"]


def test_gaze_in_wild_published_independence_does_not_skip_file_verification():
    provenance = _load_record()["annotation_provenance"]

    assert provenance["published_trained_annotator_count"] == 5
    assert provenance["publication_states_annotators_decided_independently"] is True
    assert provenance["publication_independence_evidence_present"] is True
    assert provenance["separately_recoverable_streams_verified_from_exact_copy"] is False
    assert provenance["human_human_agreement_execution_ready"] is False


def test_gaze_in_wild_article_license_is_not_promoted_to_dataset_license():
    record = _load_record()
    publication = record["authoritative_publication"]
    rights = record["rights"]

    assert publication["article_license"] == "CC BY 4.0"
    assert publication["article_license_is_dataset_license"] is False
    assert rights["article_cc_by_is_dataset_license"] is False
    assert (
        rights["publication_public_availability_is_unrestricted_redistribution_permission"]
        is False
    )
    assert rights["license_inference_permitted"] is False
    assert rights["analysis_use_terms_status"] == "unresolved"
    assert rights["raw_data_redistribution_terms_status"] == "unresolved"


def test_gaze_in_wild_mapping_and_coordinates_wait_for_exact_copy():
    mapping = _load_record()["mapping_and_coordinates"]

    assert mapping["participant_task_mapping_verified_from_exact_copy"] is False
    assert mapping["point_of_regard_coordinate_unit_verified_from_exact_copy"] is False
    assert mapping["verification_requires_exact_obtained_copy"] is True


def test_gaze_in_wild_resolution_docs_keep_rate_and_gp3_boundaries_explicit():
    text = Path("docs/gaze-in-wild-source-resolution.md").read_text(encoding="utf-8")
    homepage = Path("docs/index.md").read_text(encoding="utf-8")

    assert "not Gazepoint GP3" in text
    assert "120 Hz" in text
    assert "300 Hz" in text
    assert "actual analysis cadence from timestamps" in text
    assert "published 120 Hz acquisition" in homepage
    assert "published 120 Hz hardware provenance is kept separate" in homepage
