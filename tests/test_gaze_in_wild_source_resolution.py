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
    assert record["official_processing_repository_verified"] is True
    assert record["current_direct_data_endpoint_verified"] is False
    assert record["source_audit_ready"] is False
    assert record["empirical_evidence_created"] is False


def test_gaze_in_wild_binds_first_author_repository_to_exact_revision():
    source = _load_record()["authoritative_processing_repository"]

    assert source["repository"] == "https://github.com/RSKothari/Gaze-in-Wild"
    assert source["owner_is_dataset_first_author"] is True
    assert source["pinned_commit_sha1"] == "52262d44e366a53369e10ca73c5f41daf0e8f1e5"
    assert source["root_tree_sha1"] == "c0fa1ae13c101a8d95b09370970a6012ea97a3d9"
    assert source["files"]["README.md"]["git_blob_sha1"] == (
        "5b8536d0166d8c58e33d908fccd9c3f9c2b59a12"
    )
    assert source["files"]["License.md"]["git_blob_sha1"] == (
        "b6f41e2ee0550feabd3938efc7d93ae24c491903"
    )
    assert source["files"]["DataExtraction/GetParticipantInfo.m"]["git_blob_sha1"] == (
        "6c21df7554891015a1ae09182867b5d707b6a505"
    )
    assert source["files"]["DataExtraction/ReadData_function.m"]["git_blob_sha1"] == (
        "36d81839fb9f9eadb1274b998d2a8652fb0840ca"
    )


def test_gaze_in_wild_stage_rates_are_resolved_without_imposing_file_cadence():
    provenance = _load_record()["sampling_rate_provenance"]

    assert provenance["published_acquisition_hardware_rate_hz"] == 120
    assert provenance["official_processing_target_rate_hz"] == 300
    assert provenance["secondary_evaluation_catalog_rate_hz"] == 300
    assert provenance["acquisition_processing_stage_relationship_verified"] is True
    assert provenance["rates_reconciled"] is False
    assert provenance["distributed_file_analysis_cadence_verified"] is False
    assert "timestamps" in provenance["required_resolution_method"]
    assert "120 Hz" in provenance["reconciliation"]
    assert "300 Hz" in provenance["reconciliation"]


def test_gaze_in_wild_published_independence_does_not_skip_file_verification():
    provenance = _load_record()["annotation_provenance"]

    assert provenance["published_trained_annotator_count"] == 5
    assert provenance["publication_states_annotators_decided_independently"] is True
    assert provenance["publication_independence_evidence_present"] is True
    assert provenance["official_repository_documents_multiple_labellers_possible"] is True
    assert provenance["separately_recoverable_streams_verified_from_exact_copy"] is False
    assert provenance["human_human_agreement_execution_ready"] is False


def test_gaze_in_wild_article_and_software_licenses_are_scoped_separately():
    record = _load_record()
    publication = record["authoritative_publication"]
    rights = record["rights"]

    assert publication["article_license"] == "CC BY 4.0"
    assert publication["article_license_is_dataset_license"] is False
    assert rights["article_cc_by_is_dataset_license"] is False
    assert rights["official_repository_license_identifier"] == "MIT"
    assert rights["official_repository_license_scope"] == (
        "software and associated documentation files"
    )
    assert rights["repository_mit_promoted_to_external_dataset_files"] is False
    assert rights["external_dataset_file_license_status"] == "unresolved"
    assert (
        rights["publication_public_availability_is_unrestricted_redistribution_permission"]
        is False
    )
    assert rights["license_inference_permitted"] is False
    assert rights["analysis_use_terms_status"] == "unresolved"
    assert rights["raw_data_redistribution_terms_status"] == "unresolved"


def test_gaze_in_wild_publication_set_does_not_infer_file_identity_or_task_mapping():
    mapping = _load_record()["mapping_and_coordinates"]

    assert mapping["official_participant_trial_index_scheme_verified"] is True
    assert mapping["official_processing_code_highest_participant_index"] == 23
    assert mapping["published_participant_count"] == 19
    assert mapping["published_included_participant_set_verified"] is True
    assert mapping["published_included_participant_ids"] == [
        1,
        2,
        3,
        6,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        22,
        23,
    ]
    assert mapping["processing_indices_absent_from_published_included_set"] == [4, 5, 7, 21]
    assert mapping[
        "published_person_number_to_exact_distributed_participant_identity_verified"
    ] is False
    assert mapping["trial_index_to_published_task_mapping_verified"] is False
    assert mapping["participant_task_mapping_verified_from_exact_copy"] is False


def test_gaze_in_wild_por_semantics_are_verified_without_claiming_file_audit():
    mapping = _load_record()["mapping_and_coordinates"]

    assert mapping["point_of_regard_coordinate_semantics_verified_from_official_processing_code"]
    assert mapping["point_of_regard_source_unit"] == "normalized Pupil scene-camera coordinates"
    assert mapping["point_of_regard_y_transform"] == "1 - norm_pos_y"
    assert mapping["scene_resolution_px"] == [1920, 1080]
    assert mapping["canonical_pixel_conversion_basis_verified"] is True
    assert mapping["exact_distributed_file_point_of_regard_audited"] is False
    assert mapping["point_of_regard_coordinate_unit_verified_from_exact_copy"] is False
    assert mapping["verification_requires_exact_obtained_copy"] is True
    assert mapping["verification_requires_exact_obtained_copy_for_empirical_source_audit"]


def test_gaze_in_wild_resolution_docs_keep_rate_rights_and_gp3_boundaries_explicit():
    text = Path("docs/gaze-in-wild-source-resolution.md").read_text(encoding="utf-8")
    homepage = Path("docs/index.md").read_text(encoding="utf-8")

    assert "not Gazepoint GP3" in text
    assert "120 Hz" in text
    assert "300 Hz" in text
    assert "MIT" in text
    assert "normalized" in text
    assert "1920" in text
    assert "actual analysis cadence from timestamps" in homepage
    assert "120 Hz acquisition" in homepage
    assert "300 Hz processed-stream" in homepage
