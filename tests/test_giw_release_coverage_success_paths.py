from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest

import gazeforge.gaze_in_wild_exact_processdata_structure_evidence as structure
import gazeforge.gaze_in_wild_exact_validation as exact
import gazeforge.gaze_in_wild_exact_validation_evidence as reviewed
import gazeforge.gaze_in_wild_figshare_exact_bytes_evidence as exact_bytes
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError

ROOT = Path(__file__).parents[1]
BASE = ROOT / "validation" / "evidence" / "gaze-in-wild"

REFERENCE = BASE / "gaze-in-wild-exact-model-reference-manifest-v1.json"
PROTOCOL = BASE / "gaze-in-wild-exact-model-execution-protocol-evidence-v1.json"
REVIEWED_VALIDATION = (
    BASE / "gaze-in-wild-exact-participant-disjoint-model-validation-evidence-v1.json"
)
STRUCTURE_EVIDENCE = BASE / "gaze-in-wild-exact-processdata-structure-evidence-v1.json"
IDENTITIES = BASE / "gaze-in-wild-processdata-exact-file-identities-v1.json"
RATES = BASE / "gaze-in-wild-processdata-processed-rate-ledger-v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assembled_prepared() -> exact.GazeInWildExactPreparedBenchmark:
    parts: list[pd.DataFrame] = []
    reports: list[dict[str, Any]] = []

    for index in range(18):
        participant = f"PrIdx_{(index % 12) + 1}"
        trial = f"TrIdx_{index + 1}"

        parts.append(
            pd.DataFrame(
                {
                    "participant_id": [participant],
                    "trial_id": [trial],
                    "event_label": ["fixation" if index % 2 == 0 else "saccade"],
                }
            )
        )

        reports.append(
            {
                "source_rows": 1,
                "label_process_timestamp_vector_exactly_equal": True,
            }
        )

    return exact.assemble_exact_gaze_in_wild_benchmark(
        parts,
        reports,
        _load(REFERENCE),
        _load(PROTOCOL),
    )


def test_numeric_timestamp_helpers_fail_closed_and_hash_deterministically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = exact._numeric_vector(
        [0.0, 1.0],
        name="T",
    )

    assert values.tolist() == [0.0, 1.0]

    with pytest.raises(
        SchemaError,
        match="must be numeric",
    ):
        exact._numeric_vector(
            ["bad", "values"],
            name="T",
        )

    with pytest.raises(
        SchemaError,
        match="finite timestamps",
    ):
        exact._numeric_vector(
            [1.0],
            name="T",
        )

    with pytest.raises(
        SchemaError,
        match="finite timestamps",
    ):
        exact._numeric_vector(
            [0.0, np.nan],
            name="T",
        )

    monkeypatch.setattr(
        exact,
        "loadmat",
        lambda *args, **kwargs: {},
    )

    with pytest.raises(
        SchemaError,
        match="lacks MATLAB variable",
    ):
        exact._mat_timestamp_vector(
            Path("missing.mat"),
            "LabelData",
        )

    monkeypatch.setattr(
        exact,
        "loadmat",
        lambda *args, **kwargs: {
            "LabelData": {
                "T": [0.0, 1.0],
            }
        },
    )
    monkeypatch.setattr(
        exact,
        "_field",
        lambda value, key: value[key],
    )

    vector = exact._mat_timestamp_vector(
        Path("fake.mat"),
        "LabelData",
    )

    assert vector.tolist() == [0.0, 1.0]

    assert len(exact._float64_sha(vector)) == 64
    assert len(exact._raw_float64_sha(vector)) == 64

    assert exact._raw_float64_sha(vector) == exact._raw_float64_sha(
        np.array([0.0, 1.0], dtype=float)
    )


def test_prepare_exact_recording_success_path_without_raw_dataset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = tmp_path / "label.mat"
    process = tmp_path / "process.mat"

    label.write_bytes(b"x")
    process.write_bytes(b"x")

    times = np.array(
        [0.0, 3.3333333333333335, 6.666666666666667],
        dtype=float,
    )

    source = pd.DataFrame(
        {
            "timestamp_ms": [0.0, 3.3333333333333335, 6.666666666666667],
            "x_px": [100.0, 101.0, 102.0],
            "y_px": [200.0, 201.0, 202.0],
            "confidence": [1.0, 1.0, 1.0],
            "event_label": ["fixation", "fixation", "saccade"],
            "annotator": ["5", "5", "5"],
            "dataset_id": ["GIW", "GIW", "GIW"],
            "source_file": ["label.mat"] * 3,
        }
    )

    resampled = pd.DataFrame(
        {
            "timestamp_ms": [0.0, 5.0],
            "event_label": ["fixation", "saccade"],
        }
    )

    monkeypatch.setattr(
        exact,
        "_mat_timestamp_vector",
        lambda path, variable: times.copy(),
    )

    monkeypatch.setattr(
        exact,
        "preflight_gaze_in_wild_processdata",
        lambda path: SimpleNamespace(
            scene_resolution_px=(1920, 1080),
            participant_index=1,
            trial_index=1,
        ),
    )

    monkeypatch.setattr(
        exact,
        "load_gaze_in_wild_mat",
        lambda *args, **kwargs: SimpleNamespace(
            data=source.copy(),
            sampling_rate_hz=300.0,
        ),
    )

    monkeypatch.setattr(
        exact,
        "resample_labeled_gaze",
        lambda *args, **kwargs: SimpleNamespace(
            data=resampled.copy(),
            report={"status": "synthetic-test"},
        ),
    )

    monkeypatch.setattr(
        exact,
        "_interpolate_adjacent",
        lambda *args, **kwargs: np.array(
            [1.0, 2.0],
            dtype=float,
        ),
    )

    manifest_row = {
        "name": label.name,
        "process_filename": process.name,
        "participant_token": "PrIdx_1",
        "trial_token": "TrIdx_1",
        "timestamp_sha256_float64_le": exact._raw_float64_sha(times),
        "inferred_sampling_rate_hz": 300.0,
    }

    prepared, report = exact.prepare_exact_gaze_in_wild_recording(
        label,
        process,
        manifest_row,
        _load(PROTOCOL),
    )

    assert len(prepared) == 2
    assert prepared["validity"].all()
    assert prepared["human_labeller_id"].eq(5).all()

    assert report["participant_id"] == "PrIdx_1"
    assert report["trial_id"] == "TrIdx_1"
    assert report["label_process_timestamp_vector_exactly_equal"] is True
    assert report["raw_bytes_retained_by_preparation"] is False


def test_prepare_exact_recording_fail_closed_guards(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = tmp_path / "process.mat"
    process.write_bytes(b"x")

    with pytest.raises(FileNotFoundError):
        exact.prepare_exact_gaze_in_wild_recording(
            tmp_path / "missing.mat",
            process,
            {},
            _load(PROTOCOL),
        )

    label = tmp_path / "label.mat"
    label.write_bytes(b"x")

    monkeypatch.setattr(
        exact,
        "_mat_timestamp_vector",
        lambda path, variable: (
            np.array([0.0, 1.0]) if variable == "LabelData" else np.array([0.0, 2.0])
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="timestamps differ",
    ):
        exact.prepare_exact_gaze_in_wild_recording(
            label,
            process,
            {},
            _load(PROTOCOL),
        )


def test_assemble_exact_benchmark_success_and_guards() -> None:
    prepared = _assembled_prepared()

    assert len(prepared.data) == 18
    assert prepared.data["participant_id"].nunique() == 12
    assert prepared.preparation_report["participant_trial_count"] == 18
    assert prepared.preparation_report["task_mapping"] is None
    assert prepared.preparation_report["task_mapping_used"] is False

    parts = [
        pd.DataFrame(
            {
                "participant_id": ["PrIdx_1"],
                "trial_id": ["TrIdx_1"],
                "event_label": ["fixation"],
            }
        )
    ]

    reports = [
        {
            "source_rows": 1,
            "label_process_timestamp_vector_exactly_equal": True,
        }
    ]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires all 18",
    ):
        exact.assemble_exact_gaze_in_wild_benchmark(
            parts,
            reports,
            _load(REFERENCE),
            _load(PROTOCOL),
        )

    parts18 = parts * 18
    reports18 = reports * 18

    with pytest.raises(
        SchemaError,
        match="insufficient event classes",
    ):
        exact.assemble_exact_gaze_in_wild_benchmark(
            parts18,
            reports18,
            _load(REFERENCE),
            _load(PROTOCOL),
        )

    unknown_parts: list[pd.DataFrame] = []

    for index in range(18):
        unknown_parts.append(
            pd.DataFrame(
                {
                    "participant_id": [f"PrIdx_{(index % 12) + 1}"],
                    "trial_id": [f"TrIdx_{index + 1}"],
                    "event_label": [
                        "unknown_99"
                        if index == 0
                        else ("fixation" if index % 2 == 0 else "saccade")
                    ],
                }
            )
        )

    with pytest.raises(
        SchemaError,
        match="unsupported label codes",
    ):
        exact.assemble_exact_gaze_in_wild_benchmark(
            unknown_parts,
            [
                {
                    "source_rows": 1,
                    "label_process_timestamp_vector_exactly_equal": True,
                }
                for _ in range(18)
            ],
            _load(REFERENCE),
            _load(PROTOCOL),
        )


def test_run_exact_validation_orchestration_without_expensive_fitting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _assembled_prepared()

    prediction_rows: list[dict[str, Any]] = []

    assignments = [
        (1, "PrIdx_1", [0, 1]),
        (2, "PrIdx_2", [2, 3]),
    ]

    for model in (
        "I-VT",
        "RandomForest",
        "ContextMLP",
    ):
        for fold, participant, positions in assignments:
            for position in positions:
                prediction_rows.append(
                    {
                        "comparison_model": model,
                        "validation_fold": fold,
                        "participant_id": participant,
                        "comparison_row_position": position,
                    }
                )

    comparison = SimpleNamespace(
        predictions=pd.DataFrame(prediction_rows),
        summary=pd.DataFrame(
            {
                "model": [
                    "I-VT",
                    "RandomForest",
                    "ContextMLP",
                ]
            }
        ),
        fold_metrics=pd.DataFrame(
            {
                "comparison_model": ["I-VT"],
                "validation_fold": [1],
            }
        ),
        design={"kind": "synthetic-test"},
    )

    paired = SimpleNamespace(
        summary=pd.DataFrame(
            {
                "contrast": ["A-B"],
            }
        ),
        deltas=pd.DataFrame(
            {
                "delta": [0.0],
            }
        ),
        design={"paired": True},
    )

    sample_class = pd.DataFrame(
        {
            "model": ["I-VT"],
            "event_label": ["fixation"],
        }
    )

    event_class = pd.DataFrame(
        {
            "model": ["I-VT"],
            "event_label": ["fixation"],
        }
    )

    monkeypatch.setattr(
        exact,
        "compare_event_models_grouped",
        lambda *args, **kwargs: comparison,
    )

    monkeypatch.setattr(
        exact,
        "paired_model_metric_differences",
        lambda *args, **kwargs: paired,
    )

    monkeypatch.setattr(
        exact,
        "_sample_class_sensitivity",
        lambda *args, **kwargs: sample_class,
    )

    monkeypatch.setattr(
        exact,
        "_event_class_sensitivity",
        lambda *args, **kwargs: event_class,
    )

    monkeypatch.setattr(
        exact,
        "build_benchmark_report",
        lambda **kwargs: {
            "status": "synthetic",
            "metrics": kwargs["metrics"],
            "protocol": kwargs["protocol"],
        },
    )

    result = exact.run_exact_gaze_in_wild_model_validation(
        prepared,
        _load(PROTOCOL),
    )

    assert result.report["status"] == "synthetic"
    assert result.split_integrity["participant_disjoint"] is True
    assert result.split_integrity["fold_count"] == 2
    assert result.comparison is comparison
    assert result.paired_model_differences is paired


def _fresh_structure_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    reviewed_record = _load(STRUCTURE_EVIDENCE)
    rate_record = _load(RATES)

    file_rows: list[dict[str, Any]] = []

    for row in rate_record["rows"]:
        (
            name,
            sha256,
            participant,
            trial,
            stored_rate,
            inferred_rate,
            timestamp_count,
        ) = row

        file_rows.append(
            {
                "name": name,
                "sha256": sha256,
                "participant_index": participant,
                "trial_index": trial,
                "stored_rate_hz": stored_rate,
                "inferred_processed_rate_hz": inferred_rate,
                "timestamp_count": timestamp_count,
                "adapter_coordinate_fields_compatible": True,
                "timestamp_grid_valid": True,
                "raw_bytes_retained": False,
                "top_level_labeldata_present": False,
                "scene_resolution_px": [1920, 1080],
                "por_shape": [timestamp_count, 2],
                "confidence_shape": [timestamp_count],
                "labels_shape": [timestamp_count],
                "labels_present": True,
            }
        )

    stable_rows = [structure._stable_file_row(row) for row in file_rows]

    monkeypatch.setattr(
        structure,
        "STABLE_FILE_STRUCTURE_MANIFEST_SHA256",
        structure._canonical_sha(stable_rows),
    )

    verified = copy.deepcopy(reviewed_record["verified_processdata"])

    verified["file_results"] = file_rows
    verified["all_raw_mat_bytes_deleted_after_inspection"] = True

    reviewed_pairing = reviewed_record["distributed_labeldata_pairing"]

    pairing = {
        "file_count": reviewed_pairing["labeldata_file_count"],
        "recording_token_count": reviewed_pairing["recording_token_count"],
        "participant_count": reviewed_pairing["participant_count"],
        "participant_indices": reviewed_pairing["participant_indices"],
        "labeller_indices": reviewed_pairing["labeller_indices"],
        "all_labeldata_recording_tokens_have_processdata_match": (
            reviewed_pairing["all_labeldata_recording_tokens_have_processdata_match"]
        ),
        "processdata_tokens_without_distributed_labeldata_count": (
            reviewed_pairing["processdata_tokens_without_distributed_labeldata_count"]
        ),
        "participant_disjoint_split_keys_available": (
            reviewed_pairing["participant_disjoint_split_keys_available"]
        ),
        "matched_recording_token_count": 37,
    }

    true_boundary = (
        "exact_original_processdata_structure_verified",
        "processdata_timestamp_grid_rate_distribution_verified",
        "filename_internal_pridx_tridx_alignment_complete",
        "labeldata_processdata_recording_token_pairing_complete",
        "participant_disjoint_split_keys_available",
        "coordinate_adapter_fields_available_for_all_processdata",
    )

    false_boundary = (
        "coordinate_semantics_verified_for_exact_distribution",
        "acquisition_hardware_cadence_verified",
        "complete_file_to_publication_task_mapping_verified",
        "task_stratified_model_validation_feasible",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "quarantine_exit_authorized",
        "new_model_performance_claim_created",
    )

    boundary = {key: True for key in true_boundary}

    boundary.update({key: False for key in false_boundary})

    probe: dict[str, Any] = {
        "record_type": ("gaze-in-wild-exact-processdata-structure-probe-v1"),
        "source_binding": {
            "figshare_project_id": 74580,
            "processdata_article_id": 11673645,
            "labeldata_article_id": 11673696,
            "exact_byte_reviewed_evidence_fingerprint_sha256": (
                structure.EXACT_BYTE_EVIDENCE_FINGERPRINT_SHA256
            ),
            "exact_processdata_identity_ledger_fingerprint_sha256": (
                structure.IDENTITY_EVIDENCE_FINGERPRINT_SHA256
            ),
            "exact_processdata_sha256_manifest_sha256": (structure.IDENTITY_MANIFEST_SHA256),
        },
        "verified_processdata": verified,
        "distributed_labeldata_pairing": pairing,
        "scientific_boundary": boundary,
        "raw_dataset_bytes_retained": False,
        "excluded_cleaned_deposit": {
            "article_id": 11673717,
            "downloaded": False,
        },
    }

    probe["structure_probe_fingerprint_sha256"] = structure.probe_fingerprint(probe)

    return probe


def test_fresh_processdata_structure_success_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _fresh_structure_probe(monkeypatch)

    result = structure.validate_fresh_gaze_in_wild_processdata_structure_probe(
        probe,
        STRUCTURE_EVIDENCE,
        IDENTITIES,
        RATES,
    )

    assert result.processdata_file_count == 68
    assert result.labelled_recording_count == 37
    assert result.processed_rate_min_hz > 299.98
    assert result.processed_rate_max_hz < 300.01


def _fresh_exact_byte_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_items: list[dict[str, Any]] = []
    verified_items: list[dict[str, Any]] = []

    for label, count in (
        ("ProcessData", 13),
        ("LabelData", 1),
    ):
        frozen_files: list[dict[str, Any]] = []
        fresh_files: list[dict[str, Any]] = []

        for index in range(count):
            file_id = index + 1 if label == "ProcessData" else 1000 + index

            name = f"{label}_{index}.mat"
            size = 100 + index
            md5 = f"{index + 1:032x}"[-32:]
            sha256 = f"{index + 1:064x}"[-64:]

            primary = {
                "class": "struct",
                "name": label,
                "shape": [1, 1],
            }

            variables = [primary]

            if label == "ProcessData":
                variables.append(
                    {
                        "class": "double",
                        "name": f"Unique_{index}",
                        "shape": [index + 1, 1],
                    }
                )

            schema = {
                "format": "matlab-level-5-compatible",
                "variables": variables,
            }

            frozen_files.append(
                {
                    "id": file_id,
                    "name": name,
                    "size": size,
                    "supplied_md5": md5,
                }
            )

            fresh_files.append(
                {
                    "figshare_file_id": file_id,
                    "name": name,
                    "size_bytes": size,
                    "md5": md5,
                    "sha256": sha256,
                    "mat_schema": schema,
                    "raw_bytes_retained": False,
                }
            )

        raw_items.append(
            {
                "label": label,
                "files": frozen_files,
            }
        )

        verified_items.append(
            {
                "label": label,
                "article_id": (11673645 if label == "ProcessData" else 11673696),
                "doi": (
                    "10.6084/m9.figshare.11673645.v1"
                    if label == "ProcessData"
                    else "10.6084/m9.figshare.11673696.v1"
                ),
                "file_count": count,
                "total_size_bytes": sum(row["size_bytes"] for row in fresh_files),
                "files": fresh_files,
            }
        )

    raw = {
        "items": raw_items,
    }

    article_manifests: dict[str, str] = {}

    expanded_items: list[dict[str, Any]] = []

    for item in verified_items:
        stable_rows = [exact_bytes._stable_row(row) for row in item["files"]]

        manifest = exact_bytes.hashlib.sha256(exact_bytes._canonical_bytes(stable_rows)).hexdigest()

        article_manifests[item["label"]] = manifest

        expanded_items.append(
            {
                "label": item["label"],
                "article_id": item["article_id"],
                "doi": item["doi"],
                "file_count": item["file_count"],
                "total_size_bytes": item["total_size_bytes"],
                "files": stable_rows,
            }
        )

    stable_identity = exact_bytes.hashlib.sha256(
        exact_bytes._canonical_bytes(expanded_items)
    ).hexdigest()

    monkeypatch.setattr(
        exact_bytes,
        "EXPECTED_PROCESSDATA_STABLE_MANIFEST_SHA256",
        article_manifests["ProcessData"],
    )

    monkeypatch.setattr(
        exact_bytes,
        "EXPECTED_LABELDATA_STABLE_MANIFEST_SHA256",
        article_manifests["LabelData"],
    )

    monkeypatch.setattr(
        exact_bytes,
        "EXPECTED_STABLE_IDENTITY_FINGERPRINT_SHA256",
        stable_identity,
    )

    probe = {
        "record_type": "gaze-in-wild-figshare-exact-bytes-probe-v1",
        "verified_article_labels": [
            "ProcessData",
            "LabelData",
        ],
        "verified_file_count": 118,
        "verified_total_size_bytes": 2_413_299_242,
        "exact_original_distribution_bytes_verified": True,
        "raw_dataset_bytes_retained": False,
        "verified_items": verified_items,
        "excluded_cleaned_deposit": {
            "label": "ProcessData_cleaned",
            "downloaded": False,
        },
        "scientific_boundary": {key: False for key in exact_bytes._boundary_keys()},
    }

    return probe, raw


def test_fresh_exact_byte_probe_success_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe, raw = _fresh_exact_byte_probe(monkeypatch)

    result = exact_bytes.validate_fresh_gaze_in_wild_exact_byte_probe(
        probe,
        raw,
    )

    assert result.verified_file_count == 118
    assert result.verified_total_size_bytes == 2_413_299_242
    assert len(result.stable_identity_fingerprint_sha256) == 64
    assert len(result.processdata_manifest_sha256) == 64
    assert len(result.labeldata_manifest_sha256) == 64


def _fresh_validation_metrics() -> dict[str, Any]:
    summary = []

    for model, values in reviewed.EXPECTED_MODEL_SUMMARY.items():
        summary.append(
            {
                "model": model,
                "n_folds": 5,
                **values,
            }
        )

    sample_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []

    for model, values in reviewed.EXPECTED_PURSUIT["models"].items():
        sample_rows.append(
            {
                "model": model,
                "event_label": "pursuit",
                "support": reviewed.EXPECTED_PURSUIT["analysis_support"],
                "f1": values["sample_f1"],
                "precision": values["sample_precision"],
                "recall": values["sample_recall"],
            }
        )

        event_rows.append(
            {
                "model": model,
                "event_label": "pursuit",
                "n_reference_events": reviewed.EXPECTED_PURSUIT["reference_event_count"],
                "f1": values["event_f1"],
                "precision": values["event_precision"],
                "recall": values["event_recall"],
                "true_positive": values["matched_reference_events"],
                "n_predicted_events": values["predicted_events"],
            }
        )

    return {
        "analysis_label_counts": dict(reviewed.EXPECTED_ANALYSIS_COUNTS),
        "event_class_performance": event_rows,
        "fold_metrics": [],
        "paired_model_difference_summary": [],
        "paired_model_fold_deltas": [],
        "sample_event_class_performance": sample_rows,
        "summary": summary,
        "task_fold_metrics": [],
        "task_summary": [],
    }


def test_fresh_validation_discovery_success_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reviewed_record = _load(REVIEWED_VALIDATION)

    monkeypatch.setattr(
        reviewed,
        "validate_reviewed_gaze_in_wild_validation_evidence",
        lambda value: dict(value),
    )

    downloads: list[dict[str, Any]] = []

    for index in range(18):
        downloads.append(
            {
                "recording_token": f"recording-{index}",
                "raw_bytes_deleted_after_preparation": True,
                "label": {
                    "id": f"L{index}",
                    "sha256": f"{index + 1:064x}"[-64:],
                    "download_attempt": 1,
                },
                "process": {
                    "id": f"P{index}",
                    "sha256": f"{index + 101:064x}"[-64:],
                    "download_attempt": 1,
                },
            }
        )

    pair_manifest = reviewed._stable_pair_manifest(downloads)

    monkeypatch.setattr(
        reviewed,
        "EXPECTED_PAIR_MANIFEST",
        pair_manifest,
    )

    metrics = _fresh_validation_metrics()

    row_counts = {key: len(value) for key, value in metrics.items()}

    metric_signatures = {key: reviewed._canonical_sha(value) for key, value in metrics.items()}

    monkeypatch.setattr(
        reviewed,
        "EXPECTED_SECTION_ROW_COUNTS",
        row_counts,
    )

    monkeypatch.setattr(
        reviewed,
        "EXPECTED_REPRODUCIBILITY_SECTION_FINGERPRINTS",
        metric_signatures,
    )

    source_binding = {
        "reference_manifest_fingerprint_sha256": (reviewed.EXPECTED_REFERENCE_MANIFEST),
        "preparation_protocol_v1_fingerprint_sha256": (reviewed.EXPECTED_PREPARATION_PROTOCOL),
        "execution_protocol_v2_fingerprint_sha256": (reviewed.EXPECTED_EXECUTION_PROTOCOL_V2),
        "processdata_exact_identity_ledger_fingerprint_sha256": (
            reviewed.EXPECTED_PROCESS_IDENTITY_LEDGER
        ),
        "frozen_figshare_metadata_source_probe_fingerprint_sha256": None,
        "figshare_project_id": 74580,
        "processdata_article_id": 11673645,
        "labeldata_article_id": 11673696,
    }

    execution = {
        "downloads": downloads,
        "selected_labeller_id": 5,
        "selected_participant_count": 12,
        "selected_recording_count": 18,
        "selected_source_sample_count": 1_590_659,
        "downloaded_pair_count": 18,
        "all_selected_label_and_process_bytes_reverified": True,
        "all_label_process_timestamp_vectors_exactly_equal": True,
        "all_raw_mat_bytes_deleted_after_preparation": True,
        "processdata_cleaned_downloaded": False,
        "processdata_cleaned_article_id": 11673717,
        "contextmlp_convergence_warning_count": 0,
        "contextmlp_convergence_requirement_satisfied": True,
    }

    preparation = {
        "dataset": "Gaze-in-the-Wild",
        "distribution": ("official original Figshare ProcessData + LabelData"),
        "analysis_rows": 157850,
        "excluded_rows": 160295,
        "prepared_rows_before_exclusions": 318145,
        "analysis_sampling_rate_hz": 60.0,
        "source_rows": 1590659,
        "participant_count": 12,
        "participant_trial_count": 18,
        "selected_labeller_id": 5,
        "source_confidence_threshold": 0.3,
        "task_mapping_used": False,
        "sampling_origin": "resampled",
        "reference_strength": "derived-human-reference",
        "all_label_process_timestamp_vectors_exactly_equal": True,
        "label_counts_analysis": dict(reviewed.EXPECTED_ANALYSIS_COUNTS),
        "task_mapping": None,
    }

    split = copy.deepcopy(reviewed_record["split_integrity"])

    benchmark_report: dict[str, Any] = {
        "benchmark": {
            "name": "synthetic-test",
        },
        "model": {
            "models": [
                "I-VT",
                "RandomForest",
                "ContextMLP",
            ],
        },
        "protocol": {
            "source": "synthetic-test",
        },
        "metrics": metrics,
    }

    report_body = copy.deepcopy(benchmark_report)

    benchmark_report["report_fingerprint_sha256"] = reviewed._sha(report_body)

    envelope = {
        "benchmark": benchmark_report["benchmark"],
        "model": benchmark_report["model"],
        "protocol": benchmark_report["protocol"],
    }

    envelope_fingerprint = reviewed._canonical_sha(envelope)

    monkeypatch.setattr(
        reviewed,
        "EXPECTED_BENCHMARK_ENVELOPE_FINGERPRINT",
        envelope_fingerprint,
    )

    boundary = {
        "empirical_metrics_computed": True,
        "participant_disjoint_model_validation_executed": True,
        "contextmlp_convergence_requirement_satisfied": True,
        "performance_evidence_reviewed": False,
        "participant_disjoint_model_validation_created": False,
        "task_stratified_model_validation_created": False,
        "complete_file_to_publication_task_mapping_verified": False,
        "cross_dataset_validation_created": False,
        "gp3_validity_claim_created": False,
        "quarantine_exit_authorized": False,
        "new_empirical_performance_claim_created": False,
    }

    fresh: dict[str, Any] = {
        "record_type": reviewed.DISCOVERY_TYPE,
        "source_binding": source_binding,
        "execution": execution,
        "preparation": preparation,
        "split_integrity": split,
        "benchmark_report": benchmark_report,
        "scientific_boundary": boundary,
        "raw_dataset_bytes_retained": False,
    }

    fresh["discovery_fingerprint_sha256"] = reviewed._sha(fresh)

    expected_signature = reviewed._fresh_reproducibility_signature(
        fresh,
        metric_signatures,
    )

    monkeypatch.setattr(
        reviewed,
        "EXPECTED_REPRODUCIBILITY_SIGNATURE",
        expected_signature,
    )

    signature = reviewed.validate_fresh_gaze_in_wild_validation_discovery(
        fresh,
        reviewed_record,
    )

    assert signature == expected_signature


def test_fresh_validation_helper_guards() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="18 verified source pairs",
    ):
        reviewed._stable_pair_manifest([])

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a collection",
    ):
        reviewed._section_count(
            1,
            "bad",
        )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint is malformed",
    ):
        reviewed._validate_internal_fingerprint(
            {},
            "fingerprint",
            "test",
        )
