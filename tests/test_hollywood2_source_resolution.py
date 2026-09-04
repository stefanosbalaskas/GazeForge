import json
from pathlib import Path

_RECORD = Path("validation/protocols/hollywood2-source-resolution-2026-09-04.json")


def _load_record():
    return json.loads(_RECORD.read_text(encoding="utf-8"))


def test_hollywood2_source_resolution_stays_non_empirical():
    record = _load_record()

    assert record["record_type"] == "source-resolution-status-v1"
    assert record["dataset"] == "Hollywood2EM eye-movement event benchmark"
    assert record["status"] == (
        "canonical_distribution_identifier_established_current_copy_unverified"
    )
    assert record["canonical_distribution_identifier_found"] is True
    assert record["current_retrievable_copy_verified"] is False
    assert record["source_audit_ready"] is False
    assert record["empirical_evidence_created"] is False


def test_hollywood2_resolution_preserves_canonical_distribution_identifier():
    record = _load_record()
    publication = record["authoritative_publication"]

    assert publication["doi"] == "10.16910/jemr.13.4.5"
    assert publication["published_distribution_url"] == (
        "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em"
    )
    assert publication["publication_states_dataset_available_at_distribution_url"] is True

    independent = record["independent_distribution_evidence"]
    assert any(
        item.get("reported_distribution_url") == publication["published_distribution_url"]
        for item in independent
    )


def test_hollywood2_resolution_does_not_infer_dataset_license_from_article():
    record = _load_record()
    publication = record["authoritative_publication"]
    rights = record["rights"]

    assert publication["article_license"] == "CC BY 4.0"
    assert publication["article_license_is_dataset_license"] is False
    assert rights["article_cc_by_is_dataset_license"] is False
    assert rights["open_source_description_is_exact_license_text"] is False
    assert rights["license_inference_permitted"] is False
    assert rights["analysis_use_terms_status"] == "unresolved"
    assert rights["raw_data_redistribution_terms_status"] == "unresolved"


def test_hollywood2_student_expert_labels_are_sensitivity_not_independent_reliability():
    provenance = _load_record()["annotation_provenance"]

    assert provenance["student_labels_reported_available"] is True
    assert provenance["expert_labels_are_corrections_of_student_work"] is True
    assert provenance["independent_human_annotation_streams_verified"] is False
    assert provenance["student_expert_comparison_interpretation"] == (
        "annotation sensitivity, not independent human-human reliability"
    )


def test_hollywood2_mapping_and_units_remain_blocked_until_exact_copy():
    mapping = _load_record()["mapping_and_units"]

    assert mapping["participant_identity_mapping_verified"] is False
    assert mapping["trial_identity_mapping_verified"] is False
    assert mapping["coordinate_unit_verified"] is False
    assert mapping["verification_requires_exact_obtained_copy"] is True
