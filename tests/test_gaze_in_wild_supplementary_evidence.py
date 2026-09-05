import copy
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_supplementary_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    PUBLISHED_PERSON_NUMBERS,
    PUBLISHED_TASK_COLUMNS,
    load_gaze_in_wild_supplementary_identity_evidence,
    validate_gaze_in_wild_supplementary_identity_evidence,
)

_RECORD = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-supplementary-identity-evidence-v1.json"
)


def _record():
    import json

    return json.loads(_RECORD.read_text(encoding="utf-8"))


def test_committed_gaze_in_wild_supplementary_identity_evidence_validates():
    validated = validate_gaze_in_wild_supplementary_identity_evidence(_RECORD)

    assert validated["evidence_fingerprint_sha256"] == (
        EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    )
    assert tuple(validated["supplementary_table_1"]["person_numbers"]) == (
        PUBLISHED_PERSON_NUMBERS
    )
    assert tuple(validated["supplementary_table_1"]["task_columns"]) == (
        PUBLISHED_TASK_COLUMNS
    )


def test_typed_loader_preserves_publication_level_scope_only():
    evidence = load_gaze_in_wild_supplementary_identity_evidence(_RECORD)

    assert evidence.fingerprint_sha256 == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert evidence.published_person_numbers == PUBLISHED_PERSON_NUMBERS
    assert evidence.published_task_columns == PUBLISHED_TASK_COLUMNS
    assert evidence.exact_distributed_identity_mapping_verified is False
    assert evidence.complete_tridx_to_task_mapping_verified is False


def test_person_set_drift_is_rejected():
    payload = _record()
    payload["supplementary_table_1"]["person_numbers"][-1] = 21

    with pytest.raises(BenchmarkIntegrityError, match="person-number set"):
        validate_gaze_in_wild_supplementary_identity_evidence(payload)


def test_complete_trial_task_mapping_cannot_be_promoted():
    payload = _record()
    payload["cross_source_processing_context"][
        "complete_tridx_to_task_mapping_verified"
    ] = True

    with pytest.raises(BenchmarkIntegrityError, match="TrIdx-to-task"):
        validate_gaze_in_wild_supplementary_identity_evidence(payload)


def test_exact_distributed_identity_mapping_cannot_be_promoted():
    payload = _record()
    payload["cross_source_processing_context"][
        "published_person_number_to_exact_distributed_participant_identity_verified"
    ] = True

    with pytest.raises(BenchmarkIntegrityError, match="distributed-file identity"):
        validate_gaze_in_wild_supplementary_identity_evidence(payload)


def test_supplement_byte_fingerprint_cannot_be_invented():
    payload = _record()
    payload["publication"]["supplementary_information_bytes_fingerprinted"] = True

    with pytest.raises(BenchmarkIntegrityError, match="supplementary-PDF"):
        validate_gaze_in_wild_supplementary_identity_evidence(payload)


def test_age_discrepancy_cannot_be_repaired_or_used_as_identity_join():
    payload = _record()
    payload["metadata_discrepancy"]["processing_metadata_value"] = 34

    with pytest.raises(BenchmarkIntegrityError, match="processing age"):
        validate_gaze_in_wild_supplementary_identity_evidence(payload)

    payload = _record()
    payload["metadata_discrepancy"]["identity_mapping_can_be_inferred_from_age"] = True
    with pytest.raises(BenchmarkIntegrityError, match="identity mapping from age"):
        validate_gaze_in_wild_supplementary_identity_evidence(payload)


def test_scientific_boundary_cannot_be_promoted_to_empirical_validation():
    for key in (
        "authoritative_supplement_bytes_fingerprinted",
        "exact_dataset_copy_obtained",
        "dataset_file_rights_resolved",
        "source_audit_ready",
        "human_human_agreement_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
    ):
        payload = _record()
        payload["scientific_boundary"][key] = True
        with pytest.raises(BenchmarkIntegrityError):
            validate_gaze_in_wild_supplementary_identity_evidence(payload)


def test_self_fingerprint_rejects_other_unreviewed_content_changes():
    payload = copy.deepcopy(_record())
    payload["claim_limits"][0] += " Unreviewed change."

    with pytest.raises(BenchmarkIntegrityError, match="self-fingerprint"):
        validate_gaze_in_wild_supplementary_identity_evidence(payload)
