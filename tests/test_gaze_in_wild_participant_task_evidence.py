from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_participant_task_evidence import (
    ARXIV_SHA256,
    ARXIV_TEXT_SHA256,
    EVIDENCE_FINGERPRINT,
    SPRINGER_SHA256,
    SPRINGER_TEXT_SHA256,
    evidence_fingerprint,
    validate_gaze_in_wild_participant_task_evidence,
    validate_live_publication_probe,
)

EVIDENCE_PATH = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-participant-task-metadata-evidence-v2.json"
)


def _record() -> dict[str, object]:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def _refingerprint(record: dict[str, object]) -> dict[str, object]:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def _valid_probe() -> dict[str, object]:
    return {
        "record_type": "gaze-in-wild-participant-task-live-probe-v2",
        "springer": {
            "sha256": SPRINGER_SHA256,
            "byte_size": 5_514_416,
            "page_count": 4,
            "text_sha256_whitespace_canonical": SPRINGER_TEXT_SHA256,
            "required_markers_present": True,
        },
        "arxiv": {
            "sha256": ARXIV_SHA256,
            "byte_size": 9_437_264,
            "page_count": 23,
            "text_sha256_whitespace_canonical": ARXIV_TEXT_SHA256,
            "required_markers_present": True,
        },
        "boundaries": {
            "exact_distribution_equivalence_verified": False,
            "universal_tridx_to_task_name_mapping_verified": False,
            "analysis_use_permitted": False,
            "redistribution_permission_verified": False,
            "new_empirical_performance_claim_created": False,
        },
    }


def test_committed_participant_task_evidence_is_valid() -> None:
    record = validate_gaze_in_wild_participant_task_evidence(EVIDENCE_PATH)
    assert record["evidence_fingerprint_sha256"] == EVIDENCE_FINGERPRINT
    assert record["publication_matrix"]["participant_count"] == 19
    assert record["publication_matrix"]["status_counts"] == {
        "multiple_labellers": 5,
        "single_labeller": 30,
        "not_labeled": 30,
        "discarded": 11,
    }


def test_participant_task_cell_drift_is_rejected_even_after_refingerprint() -> None:
    record = copy.deepcopy(_record())
    record["publication_matrix"]["participants"][1]["tasks"]["tea_making"] = (
        "not_labeled"
    )
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="task row drifted"):
        validate_gaze_in_wild_participant_task_evidence(record)


def test_missing_participant_is_rejected_even_after_refingerprint() -> None:
    record = copy.deepcopy(_record())
    record["publication_matrix"]["participants"].pop()
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="row count drifted"):
        validate_gaze_in_wild_participant_task_evidence(record)


def test_universal_trial_task_promotion_is_rejected() -> None:
    record = copy.deepcopy(_record())
    record["task_mapping_boundary"]["universal_tridx_to_task_name_mapping_verified"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="must remain false"):
        validate_gaze_in_wild_participant_task_evidence(record)


def test_exact_distribution_identity_promotion_is_rejected() -> None:
    record = copy.deepcopy(_record())
    record["processing_identity_convention"]["exact_distributed_file_identity_verified"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="must remain false"):
        validate_gaze_in_wild_participant_task_evidence(record)


def test_age_cannot_become_an_identity_join() -> None:
    record = copy.deepcopy(_record())
    record["processing_identity_convention"]["age_used_as_identity_join"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="age must not"):
        validate_gaze_in_wild_participant_task_evidence(record)


def test_participant_18_age_discrepancy_is_locked() -> None:
    record = copy.deepcopy(_record())
    record["processing_identity_convention"]["age_discrepancy_preserved"][
        "processing_metadata_age"
    ] = 34
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="age discrepancy drifted"):
        validate_gaze_in_wild_participant_task_evidence(record)


def test_rights_promotion_is_rejected() -> None:
    record = copy.deepcopy(_record())
    record["rights_boundary"]["analysis_use_permitted"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="must remain false"):
        validate_gaze_in_wild_participant_task_evidence(record)


def test_live_publication_probe_binds_to_exact_pdf_identities() -> None:
    validated = validate_live_publication_probe(_valid_probe(), EVIDENCE_PATH)
    assert validated["evidence_fingerprint_sha256"] == EVIDENCE_FINGERPRINT


def test_live_publication_probe_rejects_pdf_byte_drift() -> None:
    probe = _valid_probe()
    probe["springer"]["sha256"] = "0" * 64
    with pytest.raises(BenchmarkIntegrityError, match="Springer supplement binding drifted"):
        validate_live_publication_probe(probe, EVIDENCE_PATH)


def test_publication_matrix_does_not_create_file_level_task_mapping() -> None:
    record = validate_gaze_in_wild_participant_task_evidence(EVIDENCE_PATH)
    mapping = record["task_mapping_boundary"]
    assert mapping["publication_person_to_task_status_matrix_verified"] is True
    assert mapping["universal_tridx_to_task_name_mapping_verified"] is False
    assert mapping["exact_processdata_file_to_publication_task_mapping_verified"] is False
