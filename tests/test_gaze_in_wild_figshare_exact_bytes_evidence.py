from __future__ import annotations

import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_figshare_exact_bytes_evidence import (
    evidence_fingerprint,
    validate_gaze_in_wild_figshare_exact_bytes_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "validation/evidence/gaze-in-wild"
EVIDENCE = BASE / "gaze-in-wild-figshare-exact-bytes-evidence-v1.json"
RAW = BASE / "gaze-in-wild-figshare-public-metadata-raw-v1.json"
RIGHTS = BASE / "gaze-in-wild-figshare-distribution-rights-evidence-v1.json"
SUMMARY = BASE / "gaze-in-wild-figshare-public-metadata-summary-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _refresh(record: dict) -> dict:
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def _validate(record=EVIDENCE):
    return validate_gaze_in_wild_figshare_exact_bytes_evidence(
        record,
        RAW,
        RIGHTS,
        SUMMARY,
    )


def test_reviewed_exact_byte_evidence_validates() -> None:
    result = _validate()
    assert result.exact_original_distribution_bytes_verified is True
    assert result.verified_file_count == 118
    assert result.verified_total_size_bytes == 2_413_299_242
    assert result.raw_dataset_bytes_retained is False
    assert result.quarantine_exit_authorized is False


def test_cleaned_data_cannot_be_promoted_even_with_rehashed_record() -> None:
    record = _load(EVIDENCE)
    record["excluded_distribution"]["downloaded"] = True
    _refresh(record)
    with pytest.raises(BenchmarkIntegrityError):
        _validate(record)


def test_task_mapping_cannot_be_promoted_even_with_rehashed_record() -> None:
    record = _load(EVIDENCE)
    record["scientific_boundary"]["universal_tridx_to_task_mapping_verified"] = True
    _refresh(record)
    with pytest.raises(BenchmarkIntegrityError):
        _validate(record)


def test_complete_file_task_mapping_cannot_be_promoted() -> None:
    record = _load(EVIDENCE)
    record["scientific_boundary"]["complete_file_to_task_mapping_verified"] = True
    _refresh(record)
    with pytest.raises(BenchmarkIntegrityError):
        _validate(record)


def test_human_agreement_cannot_be_created_by_exact_bytes() -> None:
    record = _load(EVIDENCE)
    record["scientific_boundary"]["human_human_agreement_created"] = True
    _refresh(record)
    with pytest.raises(BenchmarkIntegrityError):
        _validate(record)


def test_model_validation_cannot_be_created_by_exact_bytes() -> None:
    record = _load(EVIDENCE)
    record["scientific_boundary"]["participant_disjoint_model_validation_created"] = True
    _refresh(record)
    with pytest.raises(BenchmarkIntegrityError):
        _validate(record)


def test_gp3_validity_cannot_be_created_by_exact_bytes() -> None:
    record = _load(EVIDENCE)
    record["scientific_boundary"]["gp3_validity_claim_created"] = True
    _refresh(record)
    with pytest.raises(BenchmarkIntegrityError):
        _validate(record)


def test_quarantine_exit_cannot_be_created_by_exact_bytes() -> None:
    record = _load(EVIDENCE)
    record["scientific_boundary"]["quarantine_exit_authorized"] = True
    _refresh(record)
    with pytest.raises(BenchmarkIntegrityError):
        _validate(record)


def test_stable_identity_fingerprint_cannot_drift() -> None:
    record = _load(EVIDENCE)
    record["verified_distribution"]["stable_exact_byte_identity_fingerprint_sha256"] = "0" * 64
    _refresh(record)
    with pytest.raises(BenchmarkIntegrityError):
        _validate(record)


def test_discovery_artifact_binding_cannot_drift() -> None:
    record = _load(EVIDENCE)
    record["source_binding"]["artifact_zip_sha256"] = "0" * 64
    _refresh(record)
    with pytest.raises(BenchmarkIntegrityError):
        _validate(record)
