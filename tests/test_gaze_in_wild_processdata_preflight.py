from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.io import savemat

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError
from gazeforge.gaze_in_wild_processdata_preflight import (
    build_gaze_in_wild_processdata_preflight_record,
    preflight_gaze_in_wild_processdata,
    validate_gaze_in_wild_processdata_preflight_record,
)

FROZEN = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-processdata-preflight-evidence-v1.json"
)


def _write_processdata(
    path: Path,
    *,
    n: int = 6,
    include_labels: bool = True,
    top_level_labeldata: bool = False,
    process_updates: dict[str, object] | None = None,
    etg_updates: dict[str, object] | None = None,
) -> None:
    times = np.arange(n, dtype=float) / 300.0
    etg: dict[str, object] = {
        "POR": np.column_stack(
            [np.linspace(0.1, 0.8, n), np.linspace(0.2, 0.9, n)]
        ),
        "Confidence": np.linspace(0.5, 1.0, n),
        "SceneResolution": np.array([1920.0, 1080.0]),
    }
    if include_labels:
        etg["Labels"] = np.ones(n, dtype=float)
    if etg_updates:
        etg.update(etg_updates)

    process: dict[str, object] = {
        "PrIdx": 2,
        "TrIdx": 2,
        "SR": 300.0,
        "T": times,
        "ETG": etg,
    }
    if process_updates:
        process.update(process_updates)

    payload: dict[str, object] = {"ProcessData": process}
    if top_level_labeldata:
        payload["LabelData"] = {"T": times, "Labels": np.ones(n)}
    savemat(path, payload)


def _record_from_preflight(path: Path) -> dict[str, object]:
    preflight = preflight_gaze_in_wild_processdata(path)
    return build_gaze_in_wild_processdata_preflight_record(
        preflight,
        source_repository="https://example.invalid/first-party",
        source_revision="a" * 40,
        archive_path="bundle.zip",
        archive_sha256="b" * 64,
        member_path="exports/ProcessData.mat",
        parent_evidence_fingerprint_sha256="c" * 64,
    )


def _refingerprint(payload: dict[str, object]) -> None:
    body = copy.deepcopy(payload)
    body.pop("record_fingerprint_sha256", None)
    payload["record_fingerprint_sha256"] = benchmark_fingerprint(body)


def test_happy_path_verifies_adapter_fields(tmp_path: Path) -> None:
    path = tmp_path / "ProcessData.mat"
    _write_processdata(path)
    result = preflight_gaze_in_wild_processdata(path)

    assert result.participant_index == 2
    assert result.trial_index == 2
    assert result.stored_rate_hz == pytest.approx(300.0)
    assert result.inferred_processed_rate_hz == pytest.approx(300.0)
    assert result.timestamp_count == 6
    assert result.por_shape == (6, 2)
    assert result.confidence_shape == (6,)
    assert result.scene_resolution_px == (1920, 1080)
    assert result.labels_present is True
    assert result.labels_shape == (6,)
    assert result.top_level_labeldata_present is False
    assert result.adapter_coordinate_fields_compatible is True


def test_transposed_por_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "ProcessData.mat"
    n = 6
    por = np.vstack([np.linspace(0.1, 0.8, n), np.linspace(0.2, 0.9, n)])
    _write_processdata(path, n=n, etg_updates={"POR": por})
    assert preflight_gaze_in_wild_processdata(path).por_shape == (2, n)


def test_confidence_nan_matches_adapter_missingness_semantics(tmp_path: Path) -> None:
    path = tmp_path / "ProcessData.mat"
    confidence = np.array([1.0, np.nan, 0.8, 0.7, np.nan, 0.9])
    _write_processdata(path, etg_updates={"Confidence": confidence})
    result = preflight_gaze_in_wild_processdata(path)
    assert result.confidence_shape == (6,)


def test_labels_are_optional_and_do_not_imply_labeldata(tmp_path: Path) -> None:
    path = tmp_path / "ProcessData.mat"
    _write_processdata(path, include_labels=False)
    result = preflight_gaze_in_wild_processdata(path)
    assert result.labels_present is False
    assert result.labels_shape is None
    assert result.top_level_labeldata_present is False


def test_top_level_labeldata_observation_does_not_promote_boundary(tmp_path: Path) -> None:
    path = tmp_path / "ProcessData.mat"
    _write_processdata(path, top_level_labeldata=True)
    result = preflight_gaze_in_wild_processdata(path)
    assert result.top_level_labeldata_present is True
    record = _record_from_preflight(path)
    assert record["scientific_boundary"]["separate_labeldata_recovered"] is False
    assert record["scientific_boundary"]["empirical_evidence_eligible"] is False


def test_missing_processdata_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "not_process.mat"
    savemat(path, {"Other": np.array([1.0])})
    with pytest.raises(SchemaError, match="does not contain MATLAB variable 'ProcessData'"):
        preflight_gaze_in_wild_processdata(path)


def test_missing_required_etg_field_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "ProcessData.mat"
    _write_processdata(path, etg_updates={"POR": None})
    with pytest.raises(SchemaError):
        preflight_gaze_in_wild_processdata(path)


def test_non_strict_timestamps_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "ProcessData.mat"
    times = np.array([0.0, 0.01, 0.02, 0.02, 0.04, 0.05])
    _write_processdata(path, process_updates={"T": times})
    with pytest.raises(SchemaError, match="strictly increasing"):
        preflight_gaze_in_wild_processdata(path)


def test_bad_por_shape_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "ProcessData.mat"
    _write_processdata(path, etg_updates={"POR": np.zeros((6, 3))})
    with pytest.raises(SchemaError, match="N×2 or 2×N"):
        preflight_gaze_in_wild_processdata(path)


def test_confidence_length_mismatch_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "ProcessData.mat"
    _write_processdata(path, etg_updates={"Confidence": np.ones(5)})
    with pytest.raises(SchemaError, match="Confidence must match"):
        preflight_gaze_in_wild_processdata(path)


def test_invalid_scene_resolution_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "ProcessData.mat"
    _write_processdata(
        path,
        etg_updates={"SceneResolution": np.array([1920.5, 1080.0])},
    )
    with pytest.raises(SchemaError, match="positive integer pixels"):
        preflight_gaze_in_wild_processdata(path)


def test_malformed_present_labels_are_rejected_not_hidden_as_absent(tmp_path: Path) -> None:
    path = tmp_path / "ProcessData.mat"
    _write_processdata(path, etg_updates={"Labels": np.ones(5)})
    with pytest.raises(SchemaError, match="Labels must match"):
        preflight_gaze_in_wild_processdata(path)


def test_expected_hash_and_size_are_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "ProcessData.mat"
    _write_processdata(path)
    observed = preflight_gaze_in_wild_processdata(path)

    with pytest.raises(SchemaError, match="byte-size mismatch"):
        preflight_gaze_in_wild_processdata(path, expected_bytes=observed.bytes + 1)
    with pytest.raises(SchemaError, match="SHA-256 mismatch"):
        preflight_gaze_in_wild_processdata(path, expected_sha256="0" * 64)


def test_built_record_validates_and_keeps_all_promotion_gates_closed(tmp_path: Path) -> None:
    path = tmp_path / "ProcessData.mat"
    _write_processdata(path)
    record = _record_from_preflight(path)
    validate_gaze_in_wild_processdata_preflight_record(record)

    boundary = record["scientific_boundary"]
    assert boundary["processdata_structural_preflight_verified"] is True
    assert boundary["adapter_coordinate_fields_compatible_for_this_sample"] is True
    assert boundary["separate_labeldata_recovered"] is False
    assert boundary["coordinate_semantics_verified"] is False
    assert boundary["source_audit_ready"] is False
    assert boundary["empirical_evidence_eligible"] is False


def test_frozen_exact_first_party_record_validates() -> None:
    payload = json.loads(FROZEN.read_text(encoding="utf-8"))
    validate_gaze_in_wild_processdata_preflight_record(payload)
    assert payload["record_fingerprint_sha256"] == (
        "d2ec4cc066302646e199b88d29e6f8c165b1ce735c61f1652b8e00b1511a75dd"
    )
    assert payload["processdata"]["sha256"] == (
        "d633bbf0a3a9224b71e286ada10a63abe7761264eec7e8c25c94fcf0bbbafc63"
    )


@pytest.mark.parametrize(
    "gate",
    [
        "authoritative_original_or_canonical_dataset_copy_obtained",
        "full_distribution_recovered",
        "original_distribution_equivalence_verified",
        "separate_labeldata_recovered",
        "independent_labeller_recoverability_verified",
        "dataset_file_rights_resolved",
        "analysis_use_permitted",
        "redistribution_authorized",
        "participant_mapping_complete",
        "trial_task_mapping_complete",
        "coordinate_semantics_verified",
        "corpus_sampling_rate_distribution_verified",
        "published_acquisition_cadence_verified_from_sample",
        "quarantine_exit_authorized",
        "source_audit_ready",
        "empirical_evidence_eligible",
    ],
)
def test_validator_rejects_every_scientific_promotion_even_with_valid_fingerprint(
    gate: str,
) -> None:
    payload = json.loads(FROZEN.read_text(encoding="utf-8"))
    payload["scientific_boundary"][gate] = True
    _refingerprint(payload)
    with pytest.raises(SchemaError, match=gate):
        validate_gaze_in_wild_processdata_preflight_record(payload)


def test_validator_rejects_downgraded_positive_structural_claim() -> None:
    payload = json.loads(FROZEN.read_text(encoding="utf-8"))
    payload["scientific_boundary"]["processdata_structural_preflight_verified"] = False
    _refingerprint(payload)
    with pytest.raises(SchemaError, match="structural preflight"):
        validate_gaze_in_wild_processdata_preflight_record(payload)
