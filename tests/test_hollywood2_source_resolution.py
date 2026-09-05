import json
from pathlib import Path

_RECORD = Path("validation/protocols/hollywood2-source-resolution-2026-09-05.json")
_HISTORY = Path(
    "validation/history/source-resolution/hollywood2-source-resolution-2026-09-04.json"
)


def _load_record():
    return json.loads(_RECORD.read_text(encoding="utf-8"))


def test_hollywood2_source_resolution_records_recovered_empirical_source_state():
    record = _load_record()

    assert record["record_type"] == "source-resolution-status-v1"
    assert record["dataset"] == "Hollywood2EM eye-movement event benchmark"
    assert record["status"] == (
        "canonical_repository_and_ground_truth_recovered_terms_and_participant_mapping_unresolved"
    )
    assert record["canonical_distribution_identifier_found"] is True
    assert record["current_retrievable_copy_verified"] is True
    assert record["source_audit_ready"] is False
    assert record["empirical_evidence_created"] is True
    assert record["supersedes"] == str(_HISTORY).replace("\\", "/")


def test_hollywood2_resolution_preserves_exact_canonical_repository_identity():
    record = _load_record()
    repository = record["authoritative_repository"]

    assert repository["url"] == (
        "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git"
    )
    assert repository["default_ref"] == "refs/heads/master"
    assert repository["commit_sha1"] == (
        "870fa6d6209c9085260918d61433a0a2c70fd497"
    )
    assert repository["repository_license_file_recovered"] is False


def test_hollywood2_resolution_does_not_infer_dataset_license_from_article():
    rights = _load_record()["rights"]

    assert rights["article_cc_by_is_dataset_license"] is False
    assert rights["repository_license_file_recovered"] is False
    assert rights["dataset_specific_license_verified"] is False
    assert rights["open_source_description_is_exact_license_text"] is False
    assert rights["license_inference_permitted"] is False
    assert rights["analysis_use_terms_status"] == "unresolved"
    assert rights["raw_data_redistribution_terms_status"] == "unresolved"


def test_hollywood2_student_expert_labels_are_sensitivity_not_independent_reliability():
    sensitivity = _load_record()["authoritative_ground_truth"][
        "student_vs_expert_corrected"
    ]

    assert sensitivity["sample_count"] == 3871580
    assert sensitivity["changed_sample_count"] == 291315
    assert sensitivity["raw_agreement_fraction"] == 0.9247555261676111
    assert "annotation sensitivity" in sensitivity["interpretation"]
    assert "not independent human-human reliability" in sensitivity["interpretation"]


def test_hollywood2_mapping_and_units_split_verified_and_unresolved_fields():
    record = _load_record()
    mapping = record["mapping"]
    semantics = record["format_and_units"]

    assert mapping["trial_clip_identity_file_bound"] is True
    assert mapping["trial_identity_mapping_verified"] is True
    assert mapping["file_subject_tokens_recovered"] is True
    assert mapping["participant_identity_mapping_verified"] is False
    assert len(mapping["file_subject_tokens"]) == 16

    assert semantics["time_unit"] == "microseconds"
    assert semantics["coordinate_unit"] == "pixels"
    assert semantics["time_unit_verified"] is True
    assert semantics["coordinate_unit_verified"] is True
    assert semantics["native_sampling_rate_hz"] == 500.0
    assert semantics["observed_median_file_rate_hz"] == 500.0


def test_hollywood2_source_evidence_binding_is_explicit():
    evidence = _load_record()["evidence"]

    assert evidence["record"] == (
        "validation/evidence/hollywood2/"
        "hollywood2-authoritative-ground-truth-evidence-v1.json"
    )
    assert evidence["evidence_fingerprint_sha256"] == (
        "d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea"
    )
    assert evidence["live_probe_fingerprint_sha256"] == (
        "b3137d6bc4ff049802e6cdc62f6e9d3b8e490fe42384d501f789ba3bacb691dd"
    )
