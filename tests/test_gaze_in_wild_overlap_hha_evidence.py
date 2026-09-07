from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_overlap_hha_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    evidence_fingerprint,
    validate_gaze_in_wild_overlap_hha_evidence,
)

EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-distributed-overlap-human-human-agreement-evidence-v1.json"
)


def _record() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def test_reviewed_overlap_hha_evidence_passes() -> None:
    result = validate_gaze_in_wild_overlap_hha_evidence(EVIDENCE)
    assert result.fingerprint_sha256 == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert result.pair_count == 6
    assert result.recording_count == 5
    assert result.selected_label_file_count == 18
    assert result.overlap_hha_verified is True
    assert result.quarantine_exit_authorized is False


def test_tampered_stored_fingerprint_fails() -> None:
    record = _record()
    record["evidence_fingerprint_sha256"] = "0" * 64
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_gaze_in_wild_overlap_hha_evidence(record)


def test_metric_change_with_recomputed_fingerprint_still_fails() -> None:
    record = _record()
    record["pair_results"][0]["sample_all_labels"]["exact_agreement"] += 0.001
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_gaze_in_wild_overlap_hha_evidence(record)


@pytest.mark.parametrize(
    "boundary_key",
    [
        "full_distributed_labeldata_hha_created",
        "task_stratified_hha_created",
        "gaze_coordinate_validation_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "complete_file_to_publication_task_mapping_verified",
        "quarantine_exit_authorized",
        "new_model_performance_claim_created",
    ],
)
def test_forbidden_boundary_promotion_fails_even_if_refingerprinted(boundary_key: str) -> None:
    record = _record()
    record["scientific_boundary"][boundary_key] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_gaze_in_wild_overlap_hha_evidence(record)


def test_widened_recording_scope_fails_even_if_refingerprinted() -> None:
    record = _record()
    record["verified_inputs"]["recording_tokens"].append("PrIdx_7_TrIdx_1")
    record["verified_inputs"]["selected_recording_count"] = 6
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_gaze_in_wild_overlap_hha_evidence(record)


def test_task_name_substitution_fails_even_if_refingerprinted() -> None:
    record = _record()
    record["verified_inputs"]["recording_tokens"][0] = "indoor_navigation"
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_gaze_in_wild_overlap_hha_evidence(record)


def test_source_run_or_artifact_drift_fails_even_if_refingerprinted() -> None:
    for key, replacement in (("workflow_run_id", 1), ("artifact_id", 2)):
        record = _record()
        record["source_binding"][key] = replacement
        _refingerprint(record)
        with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
            validate_gaze_in_wild_overlap_hha_evidence(record)


def test_pair_symmetry_tampering_fails_even_if_reviewed_hash_is_spoofed() -> None:
    record = copy.deepcopy(_record())
    record["pair_results"][0]["event_agreement"]["right_as_reference"]["recall"] = 0.5
    record["evidence_fingerprint_sha256"] = EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    with pytest.raises(BenchmarkIntegrityError, match="recomputed evidence fingerprint"):
        validate_gaze_in_wild_overlap_hha_evidence(record)
