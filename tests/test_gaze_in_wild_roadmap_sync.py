from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_roadmap_sync import (
    RATE_LEDGER_FINGERPRINT,
    SYNC_FINGERPRINT,
    evidence_fingerprint,
    validate_gaze_in_wild_processed_rate_ledger,
    validate_gaze_in_wild_roadmap_sync,
)

SYNC_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-roadmap-evidence-sync-v1.json"
)
RATE_LEDGER = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-processdata-processed-rate-ledger-v1.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _refingerprint(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def test_processed_rate_ledger_passes_with_scoped_semantics() -> None:
    result = validate_gaze_in_wild_processed_rate_ledger(RATE_LEDGER)
    assert result.fingerprint_sha256 == RATE_LEDGER_FINGERPRINT
    assert result.file_count == 68
    assert 299.98 < result.min_inferred_rate_hz < 300.01
    assert 299.98 < result.max_inferred_rate_hz < 300.01


def test_scoped_roadmap_sync_passes() -> None:
    result = validate_gaze_in_wild_roadmap_sync(SYNC_EVIDENCE)
    assert result.fingerprint_sha256 == SYNC_FINGERPRINT
    assert result.processed_rate_file_count == 68
    assert result.overlap_hha_recording_count == 5
    assert result.overlap_hha_pair_count == 6


def test_sync_tampered_stored_fingerprint_fails() -> None:
    record = _load(SYNC_EVIDENCE)
    record["evidence_fingerprint_sha256"] = "0" * 64
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_gaze_in_wild_roadmap_sync(record)


def test_sync_upstream_drift_fails_even_if_refingerprinted() -> None:
    record = _load(SYNC_EVIDENCE)
    record["upstream_evidence"]["processed_rate_ledger"]["file_count"] = 69
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_gaze_in_wild_roadmap_sync(record)


@pytest.mark.parametrize(
    "boundary_key",
    [
        "acquisition_hardware_cadence_verified",
        "full_distributed_labeldata_hha_created",
        "task_mapping_verified",
        "task_stratified_hha_created",
        "task_stratified_model_validation_created",
        "native_60hz_validity_claim_created",
        "gp3_validity_claim_created",
        "cross_dataset_validation_created",
        "quarantine_exit_authorized",
        "new_model_performance_claim_created",
    ],
)
def test_sync_forbidden_boundary_promotion_fails_even_if_refingerprinted(
    boundary_key: str,
) -> None:
    record = _load(SYNC_EVIDENCE)
    record["scientific_boundary"][boundary_key] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_gaze_in_wild_roadmap_sync(record)


def test_sync_cannot_mark_task_mapping_or_stratified_validation_complete() -> None:
    for key in (
        "authoritative_numeric_task_mapping_item_satisfied",
        "task_stratified_validation_item_satisfied",
    ):
        record = _load(SYNC_EVIDENCE)
        record["roadmap_completion"][key] = True
        _refingerprint(record)
        with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
            validate_gaze_in_wild_roadmap_sync(record)


def test_rate_ledger_boundary_promotion_fails_even_if_refingerprinted() -> None:
    record = _load(RATE_LEDGER)
    record["scientific_boundary"]["acquisition_hardware_cadence_verified"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_gaze_in_wild_processed_rate_ledger(record)


def test_rate_ledger_semantics_drift_fails_if_reviewed_hash_is_spoofed() -> None:
    record = copy.deepcopy(_load(RATE_LEDGER))
    record["stored_rate_semantics"] = "acquisition hardware rate"
    record["evidence_fingerprint_sha256"] = RATE_LEDGER_FINGERPRINT
    with pytest.raises(BenchmarkIntegrityError, match="recomputed rate-ledger fingerprint"):
        validate_gaze_in_wild_processed_rate_ledger(record)


def test_sync_issue_wording_cannot_be_widened() -> None:
    record = _load(SYNC_EVIDENCE)
    record["issue_wording"]["human_human_agreement"] = (
        "Freeze full-distribution Gaze-in-the-Wild human agreement."
    )
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_gaze_in_wild_roadmap_sync(record)
