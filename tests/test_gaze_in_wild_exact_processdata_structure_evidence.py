from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_exact_processdata_structure_evidence import (
    evidence_fingerprint,
    validate_gaze_in_wild_exact_processdata_structure_evidence,
)

BASE = Path("validation/evidence/gaze-in-wild")
STRUCTURE = BASE / "gaze-in-wild-exact-processdata-structure-evidence-v1.json"
IDENTITIES = BASE / "gaze-in-wild-processdata-exact-file-identities-v1.json"
RATES = BASE / "gaze-in-wild-processdata-processed-rate-ledger-v1.json"
POR = BASE / "gaze-in-wild-por-coordinate-semantics-evidence-v1.json"
EXACT = BASE / "gaze-in-wild-figshare-exact-bytes-evidence-v1.json"
RAW = BASE / "gaze-in-wild-figshare-public-metadata-raw-v1.json"
RIGHTS = BASE / "gaze-in-wild-figshare-distribution-rights-evidence-v1.json"
SUMMARY = BASE / "gaze-in-wild-figshare-public-metadata-summary-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(record: dict | Path = STRUCTURE):
    return validate_gaze_in_wild_exact_processdata_structure_evidence(
        record,
        IDENTITIES,
        RATES,
        POR,
        EXACT,
        RAW,
        RIGHTS,
        SUMMARY,
    )


def _mutated_structure(path: tuple[str, ...], value) -> dict:
    record = copy.deepcopy(_load(STRUCTURE))
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)
    return record


def test_reviewed_exact_processdata_structure_evidence_validates() -> None:
    result = _validate()
    assert result.fingerprint_sha256 == (
        "cffcc8a10d176cc5eb8c15c080cf450e3e1b1404ced00ea8907cdd4ee3c3517f"
    )
    assert result.processdata_file_count == 68
    assert result.processdata_participant_count == 20
    assert result.labelled_recording_count == 37
    assert result.labelled_participant_count == 16
    assert result.normalized_por_semantics_bound is True
    assert result.participant_disjoint_partitioning_available is True
    assert result.participant_disjoint_model_validation_created is False
    assert result.quarantine_exit_authorized is False


def test_partial_exact_byte_parent_chain_is_rejected() -> None:
    with pytest.raises(BenchmarkIntegrityError, match="requires all four inputs"):
        validate_gaze_in_wild_exact_processdata_structure_evidence(
            STRUCTURE,
            IDENTITIES,
            RATES,
            POR,
            EXACT,
        )


def test_reviewed_evidence_fingerprint_drift_is_rejected() -> None:
    record = _load(STRUCTURE)
    record["status"] = "drifted"
    with pytest.raises(BenchmarkIntegrityError, match="status drifted"):
        _validate(record)


def test_identity_ledger_drift_is_rejected() -> None:
    identities = _load(IDENTITIES)
    identities["files"][0]["sha256"] = "0" * 64
    identities["evidence_fingerprint_sha256"] = evidence_fingerprint(identities)
    with pytest.raises(BenchmarkIntegrityError, match="identity-ledger stored fingerprint"):
        validate_gaze_in_wild_exact_processdata_structure_evidence(
            STRUCTURE,
            identities,
            RATES,
            POR,
        )


def test_processed_rate_ledger_drift_is_rejected() -> None:
    rates = _load(RATES)
    rates["rows"][0][5] = 120.0
    rates["evidence_fingerprint_sha256"] = evidence_fingerprint(rates)
    with pytest.raises(BenchmarkIntegrityError, match="rate-ledger stored fingerprint"):
        validate_gaze_in_wild_exact_processdata_structure_evidence(
            STRUCTURE,
            IDENTITIES,
            rates,
            POR,
        )


@pytest.mark.parametrize(
    "key",
    [
        "acquisition_hardware_cadence_verified",
        "complete_file_to_publication_task_mapping_verified",
        "task_stratified_model_validation_feasible",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "quarantine_exit_authorized",
        "new_model_performance_claim_created",
    ],
)
def test_downstream_scientific_boundary_cannot_be_promoted(key: str) -> None:
    record = _mutated_structure(("scientific_boundary", key), True)
    with pytest.raises(BenchmarkIntegrityError):
        _validate(record)


def test_corpus_wide_por_value_range_claim_cannot_be_promoted() -> None:
    record = _mutated_structure(
        ("scientific_boundary", "corpus_wide_por_value_ranges_empirically_verified"),
        True,
    )
    with pytest.raises(BenchmarkIntegrityError):
        _validate(record)


def test_raw_dataset_retention_cannot_be_promoted() -> None:
    record = _mutated_structure(("raw_dataset_bytes_retained",), True)
    with pytest.raises(BenchmarkIntegrityError):
        _validate(record)


def test_normalized_por_binding_cannot_be_removed() -> None:
    record = _mutated_structure(
        ("scientific_boundary", "normalized_por_semantics_bound_to_exact_distribution"),
        False,
    )
    with pytest.raises(BenchmarkIntegrityError):
        _validate(record)
