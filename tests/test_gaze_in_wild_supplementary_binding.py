import json
from pathlib import Path

from gazeforge.gaze_in_wild_supplementary_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    PUBLISHED_PERSON_NUMBERS,
    PUBLISHED_TASK_COLUMNS,
    validate_gaze_in_wild_supplementary_identity_evidence,
)
from gazeforge.source_resolution import validate_source_resolution_record

_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-supplementary-identity-evidence-v1.json"
)
_PROTOCOL = Path("validation/protocols/gaze-in-wild-source-resolution-2026-09-04.json")


def test_source_resolution_checkpoint_is_bound_to_reviewed_supplementary_identity():
    evidence = validate_gaze_in_wild_supplementary_identity_evidence(_EVIDENCE)
    source_summary = validate_source_resolution_record(_PROTOCOL)
    checkpoint = json.loads(_PROTOCOL.read_text(encoding="utf-8"))

    binding = checkpoint["supplementary_identity_evidence"]
    mapping = checkpoint["mapping_and_coordinates"]

    assert source_summary["dataset_key"] == "gaze-in-the-wild"
    assert binding["record_type"] == "gaze-in-wild-supplementary-identity-evidence-v1"
    assert binding["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert binding["evidence_fingerprint_sha256"] == evidence["evidence_fingerprint_sha256"]
    assert tuple(binding["published_person_numbers"]) == PUBLISHED_PERSON_NUMBERS
    assert tuple(mapping["published_included_participant_ids"]) == PUBLISHED_PERSON_NUMBERS
    assert tuple(binding["published_task_columns"]) == PUBLISHED_TASK_COLUMNS
    assert tuple(mapping["published_task_columns"]) == PUBLISHED_TASK_COLUMNS
    assert mapping["processing_indices_absent_from_published_included_set"] == [4, 5, 7, 21]
    assert mapping["published_included_participant_set_verified"] is True
    assert binding["published_included_participant_set_verified"] is True

    # Publication-level person numbers are not silently upgraded to file-level identities.
    assert binding[
        "published_person_number_to_exact_distributed_participant_identity_verified"
    ] is False
    assert mapping[
        "published_person_number_to_exact_distributed_participant_identity_verified"
    ] is False
    assert binding["complete_tridx_to_task_mapping_verified"] is False
    assert mapping["trial_index_to_published_task_mapping_verified"] is False
    assert mapping["participant_task_mapping_verified_from_exact_copy"] is False


def test_source_resolution_preserves_age_discrepancy_as_non_identity_evidence():
    checkpoint = json.loads(_PROTOCOL.read_text(encoding="utf-8"))
    discrepancy = checkpoint["mapping_and_coordinates"][
        "participant_18_age_metadata_discrepancy"
    ]

    assert discrepancy == {
        "supplementary_table_age": 34,
        "processing_metadata_age": 45,
        "identity_mapping_from_age_permitted": False,
    }
