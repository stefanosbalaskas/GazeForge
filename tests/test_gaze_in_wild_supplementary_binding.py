import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_supplementary_binding import (
    validate_gaze_in_wild_supplementary_binding,
)
from gazeforge.gaze_in_wild_supplementary_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    PUBLISHED_PERSON_NUMBERS,
    PUBLISHED_TASK_COLUMNS,
)

_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-supplementary-identity-evidence-v1.json"
)
_PROTOCOL = Path("validation/protocols/gaze-in-wild-source-resolution-2026-09-04.json")


def _checkpoint() -> dict:
    return json.loads(_PROTOCOL.read_text(encoding="utf-8"))


def _write_checkpoint(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "gaze-in-wild-source-resolution.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_source_resolution_checkpoint_is_bound_to_reviewed_supplementary_identity():
    binding = validate_gaze_in_wild_supplementary_binding(_PROTOCOL, _EVIDENCE)

    assert binding.evidence_fingerprint_sha256 == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert binding.published_person_numbers == PUBLISHED_PERSON_NUMBERS
    assert binding.published_task_columns == PUBLISHED_TASK_COLUMNS
    assert binding.source_record_fingerprint_sha256 == (
        "22bbdef6e6f2823d10c84fd099596700d9db19c54aecfb76484c7625fd9ebb08"
    )
    assert binding.exact_distributed_identity_mapping_verified is False
    assert binding.complete_tridx_to_task_mapping_verified is False


def test_binding_rejects_file_level_identity_promotion(tmp_path):
    payload = _checkpoint()
    payload["mapping_and_coordinates"][
        "published_person_number_to_exact_distributed_participant_identity_verified"
    ] = True

    altered = _write_checkpoint(tmp_path, payload)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_gaze_in_wild_supplementary_binding(altered, _EVIDENCE)


def test_binding_rejects_complete_trial_task_promotion(tmp_path):
    payload = _checkpoint()
    payload["supplementary_identity_evidence"][
        "complete_tridx_to_task_mapping_verified"
    ] = True

    altered = _write_checkpoint(tmp_path, payload)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_gaze_in_wild_supplementary_binding(altered, _EVIDENCE)


def test_binding_rejects_supplementary_fingerprint_drift(tmp_path):
    payload = _checkpoint()
    payload["supplementary_identity_evidence"]["evidence_fingerprint_sha256"] = "0" * 64

    altered = _write_checkpoint(tmp_path, payload)
    with pytest.raises(BenchmarkIntegrityError, match="reviewed supplementary evidence"):
        validate_gaze_in_wild_supplementary_binding(altered, _EVIDENCE)


def test_binding_preserves_age_discrepancy_as_non_identity_evidence(tmp_path):
    payload = _checkpoint()
    payload["mapping_and_coordinates"]["participant_18_age_metadata_discrepancy"][
        "processing_metadata_age"
    ] = 34

    altered = _write_checkpoint(tmp_path, payload)
    with pytest.raises(BenchmarkIntegrityError, match="age discrepancy"):
        validate_gaze_in_wild_supplementary_binding(altered, _EVIDENCE)
