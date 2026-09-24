from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gazeforge.gaze_in_wild_exact_validation_v2 as exact
import gazeforge.gaze_in_wild_processdata_preflight as preflight
from gazeforge.benchmarks import BenchmarkDatasetCard
from gazeforge.exceptions import (
    BenchmarkIntegrityError,
    SchemaError,
)

V2_PATH = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-exact-model-execution-protocol-evidence-v2.json"
)


# ============================================================
# EXACT V2 HELPERS
# ============================================================


def _load_v2():
    return json.loads(V2_PATH.read_text(encoding="utf-8"))


def _deep_record(
    monkeypatch,
):
    monkeypatch.setattr(
        exact,
        "benchmark_fingerprint",
        lambda payload: exact.EXECUTION_PROTOCOL_V2_FINGERPRINT,
    )

    return _load_v2()


def test_exact_v2_valid():
    record = exact.validate_exact_execution_protocol_v2(_load_v2())

    assert record["execution_protocol"]["temporal_max_iter"] == 1000


def test_exact_v2_record_type():
    record = _load_v2()

    record["record_type"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="protocol v2 type",
    ):
        exact.validate_exact_execution_protocol_v2(record)


def test_exact_v2_stored_fingerprint():
    record = _load_v2()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint drifted",
    ):
        exact.validate_exact_execution_protocol_v2(record)


def test_exact_v2_body_fingerprint():
    record = _load_v2()

    record["extra"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="body drifted",
    ):
        exact.validate_exact_execution_protocol_v2(record)


def test_exact_v2_amendment_missing(
    monkeypatch,
):
    record = _deep_record(monkeypatch)

    record["amendment"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="amendment is missing",
    ):
        exact.validate_exact_execution_protocol_v2(record)


@pytest.mark.parametrize(
    "field",
    [
        "acceptance_rule",
        ("performance_metrics_used_to_choose_amendment"),
        "reason",
        ("unchanged_protocol_fields_required"),
    ],
)
def test_exact_v2_amendment_fields(
    monkeypatch,
    field,
):
    record = _deep_record(monkeypatch)

    record["amendment"][field] = "__drift__"

    with pytest.raises(
        BenchmarkIntegrityError,
        match=field,
    ):
        exact.validate_exact_execution_protocol_v2(record)


def test_exact_v2_changed_fields(
    monkeypatch,
):
    record = _deep_record(monkeypatch)

    record["amendment"]["changed_fields"] = {}

    with pytest.raises(
        BenchmarkIntegrityError,
        match="changed extra fields",
    ):
        exact.validate_exact_execution_protocol_v2(record)


def test_exact_v2_parent_missing(
    monkeypatch,
):
    record = _deep_record(monkeypatch)

    record["parent_evidence"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="parent evidence is missing",
    ):
        exact.validate_exact_execution_protocol_v2(record)


@pytest.mark.parametrize(
    "field",
    [
        ("model_execution_protocol_v1_fingerprint_sha256"),
        ("discovery_fingerprint_sha256"),
        ("discovery_benchmark_report_fingerprint_sha256"),
        "discovery_workflow_run_id",
        "discovery_workflow_job_id",
        "discovery_workflow_head_sha",
        "discovery_artifact_id",
        ("discovery_artifact_zip_sha256"),
        ("observed_contextmlp_convergence_warning_count"),
    ],
)
def test_exact_v2_parent_fields(
    monkeypatch,
    field,
):
    record = _deep_record(monkeypatch)

    record["parent_evidence"][field] = "__drift__"

    with pytest.raises(
        BenchmarkIntegrityError,
        match=field,
    ):
        exact.validate_exact_execution_protocol_v2(record)


def test_exact_v2_protocol_missing(
    monkeypatch,
):
    record = _deep_record(monkeypatch)

    record["execution_protocol"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="payload is missing",
    ):
        exact.validate_exact_execution_protocol_v2(record)


@pytest.mark.parametrize(
    "field",
    [
        "selected_labeller_id",
        "selected_participant_count",
        "selected_recording_count",
        "task_mapping_used",
        ("task_stratified_validation_authorized"),
        "source_confidence_threshold",
        "analysis_sampling_rate_hz",
        "min_label_purity",
        "max_coordinate_gap_factor",
        "n_splits",
        "group_splitter",
        ("ivt_velocity_threshold_px_s"),
        "model_min_confidence",
        "random_state",
        ("random_forest_n_estimators"),
        "context_radius_ms",
        "rolling_window_ms",
        "temporal_solver",
        "temporal_max_iter",
        "calibration_bins",
        "event_min_iou",
        ("models_refit_by_event_class"),
        ("raw_mat_retention_authorized"),
        ("context_mlp_convergence_warning_policy"),
    ],
)
def test_exact_v2_protocol_fields(
    monkeypatch,
    field,
):
    record = _deep_record(monkeypatch)

    record["execution_protocol"][field] = "__drift__"

    with pytest.raises(
        BenchmarkIntegrityError,
        match=field,
    ):
        exact.validate_exact_execution_protocol_v2(record)


@pytest.mark.parametrize(
    (
        "field",
        "replacement",
        "message",
    ),
    [
        (
            "models",
            [],
            "model family",
        ),
        (
            "hidden_layer_sizes",
            [],
            "topology",
        ),
        (
            "scene_resolution_px",
            [],
            "scene resolution",
        ),
        (
            "excluded_event_labels",
            [],
            "exclusions",
        ),
        (
            ("label_process_timestamp_vector_alignment_required"),
            "approximate",
            "timestamp rule",
        ),
    ],
)
def test_exact_v2_structural_protocol_fields(
    monkeypatch,
    field,
    replacement,
    message,
):
    record = _deep_record(monkeypatch)

    record["execution_protocol"][field] = replacement

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        exact.validate_exact_execution_protocol_v2(record)


def test_exact_v2_boundary_missing(
    monkeypatch,
):
    record = _deep_record(monkeypatch)

    record["scientific_boundary"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="boundary is missing",
    ):
        exact.validate_exact_execution_protocol_v2(record)


def test_exact_v2_not_authorized(
    monkeypatch,
):
    record = _deep_record(monkeypatch)

    record["scientific_boundary"]["exact_distribution_model_execution_authorized"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not authorized",
    ):
        exact.validate_exact_execution_protocol_v2(record)


@pytest.mark.parametrize(
    "field",
    [
        ("participant_disjoint_model_validation_created"),
        ("task_stratified_model_validation_created"),
        ("complete_file_to_publication_task_mapping_verified"),
        ("cross_dataset_validation_created"),
        "gp3_validity_claim_created",
        "quarantine_exit_authorized",
        ("new_empirical_performance_claim_created"),
    ],
)
def test_exact_v2_boundary_promotions(
    monkeypatch,
    field,
):
    record = _deep_record(monkeypatch)

    record["scientific_boundary"][field] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match=field,
    ):
        exact.validate_exact_execution_protocol_v2(record)


# ============================================================
# EXACT V2 RUN WRAPPER — ALL COMPUTE MOCKED
# ============================================================


def _prepared():
    card = BenchmarkDatasetCard(
        name="GIW fixture",
        version="test",
        source="synthetic-test",
        license="test",
        task="event classification",
        sampling_rates_hz=[
            60.0,
        ],
        participant_count=2,
        split_unit="participant_id",
        validation_scope="test",
        annotation_origin="human-manual",
        sampling_origin="resampled",
        reference_strength="human-reference",
        human_annotator_count=1,
    )

    data = pd.DataFrame(
        {
            "participant_id": [
                "P01",
                "P02",
            ],
            "trial_id": [
                "T01",
                "T02",
            ],
            "event_label": [
                "fixation",
                "saccade",
            ],
            "timestamp_ms": [
                0.0,
                0.0,
            ],
        }
    )

    return exact.GazeInWildExactPreparedBenchmark(
        data=data,
        dataset_card=card,
        preparation_report={
            "label_counts_analysis": {
                "fixation": 1,
                "saccade": 1,
            }
        },
    )


def test_exact_v2_run_wrapper_without_fitting(
    monkeypatch,
):
    predictions = pd.DataFrame(
        {
            "participant_id": [
                "P01",
                "P02",
            ],
            "trial_id": [
                "T01",
                "T02",
            ],
            "event_label": [
                "fixation",
                "saccade",
            ],
            "model": [
                "I-VT",
                "I-VT",
            ],
        }
    )

    fold_metrics = pd.DataFrame(
        {
            "fold": [
                1,
            ],
            "model": [
                "I-VT",
            ],
            "accuracy": [
                1.0,
            ],
        }
    )

    summary = pd.DataFrame(
        {
            "model": [
                "I-VT",
            ],
            "accuracy": [
                1.0,
            ],
        }
    )

    comparison = SimpleNamespace(
        predictions=predictions,
        fold_metrics=fold_metrics,
        summary=summary,
        design={
            "splitter": "mock",
        },
    )

    paired = SimpleNamespace(
        summary=pd.DataFrame(
            {
                "metric": [
                    "accuracy",
                ],
                "difference": [
                    0.0,
                ],
            }
        ),
        deltas=pd.DataFrame(
            {
                "fold": [
                    1,
                ],
                "delta": [
                    0.0,
                ],
            }
        ),
        design={
            "paired": True,
        },
    )

    monkeypatch.setattr(
        exact,
        "compare_event_models_grouped",
        lambda *args, **kwargs: comparison,
    )

    monkeypatch.setattr(
        exact,
        "_split_integrity",
        lambda value: {
            "participant_disjoint": True,
        },
    )

    monkeypatch.setattr(
        exact,
        "paired_model_metric_differences",
        lambda value: paired,
    )

    monkeypatch.setattr(
        exact,
        "_sample_class_sensitivity",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "event_label": [
                    "fixation",
                ],
                "score": [
                    1.0,
                ],
            }
        ),
    )

    monkeypatch.setattr(
        exact,
        "_event_class_sensitivity",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "event_label": [
                    "fixation",
                ],
                "score": [
                    1.0,
                ],
            }
        ),
    )

    result = exact.run_exact_gaze_in_wild_model_validation_v2(
        _prepared(),
        _load_v2(),
    )

    assert result.comparison is comparison

    assert result.paired_model_differences is paired

    assert result.split_integrity["participant_disjoint"] is True

    assert result.report["protocol"]["contextmlp_convergence_warning_count"] == 0

    assert result.report["metrics"]["task_summary"] == []


# ============================================================
# PROCESSDATA DATACLASS
# ============================================================


def _preflight_object():
    return preflight.GazeInWildProcessDataPreflight(
        path="ProcessData.mat",
        sha256="a" * 64,
        bytes=100,
        participant_index=1,
        trial_index=2,
        stored_rate_hz=300.0,
        inferred_processed_rate_hz=300.0,
        timestamp_count=3,
        timestamp_start_s=0.0,
        timestamp_end_s=0.01,
        por_shape=(
            3,
            2,
        ),
        confidence_shape=(3,),
        scene_resolution_px=(
            1920,
            1080,
        ),
        labels_present=False,
        labels_shape=None,
        top_level_labeldata_present=False,
        adapter_coordinate_fields_compatible=True,
        timestamp_grid_valid=True,
    )


def test_process_preflight_to_dict():
    payload = _preflight_object().to_dict()

    assert payload["participant_index"] == 1


# ============================================================
# PROCESSDATA FIELD ACCESS
# ============================================================


def test_process_field_mapping():
    assert (
        preflight._field(
            {
                "x": 5,
            },
            "x",
        )
        == 5
    )


def test_process_field_attribute():
    value = SimpleNamespace(x=6)

    assert (
        preflight._field(
            value,
            "x",
        )
        == 6
    )


def test_process_field_structured_array():
    value = np.zeros(
        1,
        dtype=[
            (
                "x",
                object,
            )
        ],
    )

    value["x"][0] = np.array(
        [
            7,
        ]
    )

    observed = preflight._field(
        value,
        "x",
    )

    assert int(np.asarray(observed).reshape(-1)[0]) == 7


def test_process_field_missing():
    with pytest.raises(
        SchemaError,
        match="missing field",
    ):
        preflight._field(
            {},
            "x",
        )


# ============================================================
# NUMERIC VECTOR
# ============================================================


def test_process_numeric_vector_valid():
    observed = preflight._numeric_vector(
        [
            1,
            2,
        ],
        name="x",
    )

    assert observed.tolist() == [
        1.0,
        2.0,
    ]


def test_process_numeric_vector_nonnumeric():
    with pytest.raises(
        SchemaError,
        match="must be numeric",
    ):
        preflight._numeric_vector(
            [
                "bad",
            ],
            name="x",
        )


def test_process_numeric_vector_empty():
    with pytest.raises(
        SchemaError,
        match="cannot be empty",
    ):
        preflight._numeric_vector(
            [],
            name="x",
        )


def test_process_numeric_vector_nonfinite():
    with pytest.raises(
        SchemaError,
        match="must be finite",
    ):
        preflight._numeric_vector(
            [
                np.nan,
            ],
            name="x",
        )


def test_process_numeric_vector_nonfinite_allowed():
    observed = preflight._numeric_vector(
        [
            np.nan,
        ],
        name="x",
        require_finite=False,
    )

    assert np.isnan(observed[0])


# ============================================================
# POSITIVE INTEGER + RATE
# ============================================================


def test_process_positive_integer_scalar():
    assert (
        preflight._positive_integer_scalar(
            [
                2.0,
            ],
            name="x",
        )
        == 2
    )


def test_process_positive_integer_not_scalar():
    with pytest.raises(
        SchemaError,
        match="must be scalar",
    ):
        preflight._positive_integer_scalar(
            [
                1,
                2,
            ],
            name="x",
        )


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        1.5,
    ],
)
def test_process_positive_integer_bad(
    value,
):
    with pytest.raises(
        SchemaError,
        match="positive integer",
    ):
        preflight._positive_integer_scalar(
            [
                value,
            ],
            name="x",
        )


def test_process_positive_rate():
    assert (
        preflight._positive_rate(
            [
                120,
            ],
            name="SR",
        )
        == 120.0
    )


@pytest.mark.parametrize(
    "value",
    [
        [
            1,
            2,
        ],
        [
            0,
        ],
        [
            -1,
        ],
    ],
)
def test_process_positive_rate_bad(
    value,
):
    with pytest.raises(
        SchemaError,
        match="one positive rate",
    ):
        preflight._positive_rate(
            value,
            name="SR",
        )


# ============================================================
# TIMESTAMPS
# ============================================================


def test_process_timestamp_grid_valid():
    times, rate = preflight._timestamp_grid(
        [
            0.0,
            0.01,
            0.02,
        ]
    )

    assert len(times) == 3

    assert rate == pytest.approx(100.0)


def test_process_timestamp_too_short():
    with pytest.raises(
        SchemaError,
        match="at least two",
    ):
        preflight._timestamp_grid(
            [
                0.0,
            ]
        )


@pytest.mark.parametrize(
    "values",
    [
        [
            0.0,
            0.0,
        ],
        [
            1.0,
            0.0,
        ],
    ],
)
def test_process_timestamp_not_increasing(
    values,
):
    with pytest.raises(
        SchemaError,
        match="strictly increasing",
    ):
        preflight._timestamp_grid(values)


# ============================================================
# POR
# ============================================================


def test_process_por_n_by_2():
    assert preflight._por_shape(
        np.zeros(
            (
                3,
                2,
            )
        ),
        n_samples=3,
    ) == (
        3,
        2,
    )


def test_process_por_2_by_n():
    assert preflight._por_shape(
        np.zeros(
            (
                2,
                3,
            )
        ),
        n_samples=3,
    ) == (
        2,
        3,
    )


def test_process_por_nonnumeric():
    with pytest.raises(
        SchemaError,
        match="must be numeric",
    ):
        preflight._por_shape(
            [
                [
                    "bad",
                ]
            ],
            n_samples=1,
        )


def test_process_por_not_2d():
    with pytest.raises(
        SchemaError,
        match="two-dimensional",
    ):
        preflight._por_shape(
            [
                1,
                2,
                3,
            ],
            n_samples=3,
        )


def test_process_por_shape_mismatch():
    with pytest.raises(
        SchemaError,
        match="N×2 or 2×N",
    ):
        preflight._por_shape(
            np.zeros(
                (
                    3,
                    3,
                )
            ),
            n_samples=3,
        )


# ============================================================
# SCENE RESOLUTION
# ============================================================


def test_process_scene_resolution_valid():
    assert preflight._scene_resolution(
        [
            1920,
            1080,
        ]
    ) == (
        1920,
        1080,
    )


def test_process_scene_resolution_length():
    with pytest.raises(
        SchemaError,
        match="width and height",
    ):
        preflight._scene_resolution(
            [
                1920,
            ]
        )


@pytest.mark.parametrize(
    "value",
    [
        [
            0,
            1080,
        ],
        [
            1920.5,
            1080,
        ],
    ],
)
def test_process_scene_resolution_invalid(
    value,
):
    with pytest.raises(
        SchemaError,
        match="positive integer pixels",
    ):
        preflight._scene_resolution(value)


# ============================================================
# PREFLIGHT WITH MOCKED MATLAB PAYLOAD
# ============================================================


def _raw_process(
    *,
    labels=True,
    top_labeldata=False,
):
    etg = {
        "POR": np.zeros(
            (
                3,
                2,
            )
        ),
        "Confidence": np.array(
            [
                1.0,
                np.nan,
                0.8,
            ]
        ),
        "SceneResolution": np.array(
            [
                1920,
                1080,
            ]
        ),
    }

    if labels:
        etg["Labels"] = np.array(
            [
                1,
                2,
                3,
            ]
        )

    raw = {
        "ProcessData": {
            "PrIdx": 1,
            "TrIdx": 2,
            "SR": 300.0,
            "T": np.array(
                [
                    0.0,
                    1 / 300,
                    2 / 300,
                ]
            ),
            "ETG": etg,
        }
    }

    if top_labeldata:
        raw["LabelData"] = {
            "x": 1,
        }

    return raw


def test_process_preflight_file_missing(
    tmp_path,
):
    with pytest.raises(
        FileNotFoundError,
    ):
        preflight.preflight_gaze_in_wild_processdata(tmp_path / "missing.mat")


def test_process_preflight_expected_bytes(
    tmp_path,
):
    path = tmp_path / "ProcessData.mat"

    path.write_bytes(b"x")

    with pytest.raises(
        SchemaError,
        match="byte-size mismatch",
    ):
        preflight.preflight_gaze_in_wild_processdata(
            path,
            expected_bytes=2,
        )


def test_process_preflight_expected_sha(
    tmp_path,
):
    path = tmp_path / "ProcessData.mat"

    path.write_bytes(b"x")

    with pytest.raises(
        SchemaError,
        match="SHA-256 mismatch",
    ):
        preflight.preflight_gaze_in_wild_processdata(
            path,
            expected_sha256=("0" * 64),
        )


def test_process_preflight_missing_processdata(
    monkeypatch,
    tmp_path,
):
    path = tmp_path / "ProcessData.mat"

    path.write_bytes(b"x")

    monkeypatch.setattr(
        preflight,
        "loadmat",
        lambda *args, **kwargs: {
            "Other": 1,
        },
    )

    with pytest.raises(
        SchemaError,
        match="does not contain MATLAB variable",
    ):
        preflight.preflight_gaze_in_wild_processdata(path)


@pytest.mark.parametrize(
    (
        "labels",
        "top_labeldata",
    ),
    [
        (
            True,
            False,
        ),
        (
            False,
            False,
        ),
        (
            True,
            True,
        ),
    ],
)
def test_process_preflight_mocked_success(
    monkeypatch,
    tmp_path,
    labels,
    top_labeldata,
):
    path = tmp_path / "ProcessData.mat"

    path.write_bytes(b"fixture")

    monkeypatch.setattr(
        preflight,
        "loadmat",
        lambda *args, **kwargs: _raw_process(
            labels=labels,
            top_labeldata=top_labeldata,
        ),
    )

    result = preflight.preflight_gaze_in_wild_processdata(path)

    assert result.participant_index == 1

    assert result.trial_index == 2

    assert result.labels_present is labels

    assert result.top_level_labeldata_present is top_labeldata


def test_process_preflight_confidence_length(
    monkeypatch,
    tmp_path,
):
    path = tmp_path / "ProcessData.mat"

    path.write_bytes(b"x")

    raw = _raw_process()

    raw["ProcessData"]["ETG"]["Confidence"] = [
        1,
        2,
    ]

    monkeypatch.setattr(
        preflight,
        "loadmat",
        lambda *args, **kwargs: raw,
    )

    with pytest.raises(
        SchemaError,
        match="Confidence must match",
    ):
        preflight.preflight_gaze_in_wild_processdata(path)


def test_process_preflight_labels_length(
    monkeypatch,
    tmp_path,
):
    path = tmp_path / "ProcessData.mat"

    path.write_bytes(b"x")

    raw = _raw_process()

    raw["ProcessData"]["ETG"]["Labels"] = [
        1,
        2,
    ]

    monkeypatch.setattr(
        preflight,
        "loadmat",
        lambda *args, **kwargs: raw,
    )

    with pytest.raises(
        SchemaError,
        match="Labels must match",
    ):
        preflight.preflight_gaze_in_wild_processdata(path)


# ============================================================
# PREFLIGHT RECORD BUILD
# ============================================================


def test_process_build_record():
    record = preflight.build_gaze_in_wild_processdata_preflight_record(
        _preflight_object(),
        source_repository=("repo"),
        source_revision=("abc"),
        archive_path=("archive.zip"),
        archive_sha256=("A" * 64),
        member_path=("ProcessData.mat"),
        parent_evidence_fingerprint_sha256=("B" * 64),
    )

    assert record["source"]["archive_sha256"] == "a" * 64

    assert record["source"]["parent_evidence_fingerprint_sha256"] == "b" * 64

    assert len(record["record_fingerprint_sha256"]) == 64

    preflight.validate_gaze_in_wild_processdata_preflight_record(record)


def _record():
    return preflight.build_gaze_in_wild_processdata_preflight_record(
        _preflight_object(),
        source_repository="repo",
        source_revision="abc",
        archive_path="archive.zip",
        archive_sha256="a" * 64,
        member_path="ProcessData.mat",
        parent_evidence_fingerprint_sha256=("b" * 64),
    )


def _refingerprint(
    record,
):
    body = copy.deepcopy(record)

    body.pop(
        "record_fingerprint_sha256",
        None,
    )

    record["record_fingerprint_sha256"] = preflight.benchmark_fingerprint(body)


# ============================================================
# PREFLIGHT RECORD VALIDATOR
# ============================================================


def test_process_record_type():
    record = _record()

    record["record_type"] = "wrong"

    _refingerprint(record)

    with pytest.raises(
        SchemaError,
        match="record type",
    ):
        preflight.validate_gaze_in_wild_processdata_preflight_record(record)


def test_process_record_fingerprint():
    record = _record()

    record["record_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        SchemaError,
        match="fingerprint mismatch",
    ):
        preflight.validate_gaze_in_wild_processdata_preflight_record(record)


def test_process_record_boundary_missing():
    record = _record()

    record["scientific_boundary"] = None

    _refingerprint(record)

    with pytest.raises(
        SchemaError,
        match="missing scientific_boundary",
    ):
        preflight.validate_gaze_in_wild_processdata_preflight_record(record)


def test_process_record_structural_false():
    record = _record()

    record["scientific_boundary"]["processdata_structural_preflight_verified"] = False

    _refingerprint(record)

    with pytest.raises(
        SchemaError,
        match="structural preflight",
    ):
        preflight.validate_gaze_in_wild_processdata_preflight_record(record)


def test_process_record_adapter_false():
    record = _record()

    record["scientific_boundary"]["adapter_coordinate_fields_compatible_for_this_sample"] = False

    _refingerprint(record)

    with pytest.raises(
        SchemaError,
        match="Adapter field compatibility",
    ):
        preflight.validate_gaze_in_wild_processdata_preflight_record(record)


@pytest.mark.parametrize(
    "field",
    [
        ("authoritative_original_or_canonical_dataset_copy_obtained"),
        "full_distribution_recovered",
        ("original_distribution_equivalence_verified"),
        "separate_labeldata_recovered",
        ("independent_labeller_recoverability_verified"),
        "dataset_file_rights_resolved",
        "analysis_use_permitted",
        "redistribution_authorized",
        "participant_mapping_complete",
        "trial_task_mapping_complete",
        "coordinate_semantics_verified",
        ("corpus_sampling_rate_distribution_verified"),
        ("published_acquisition_cadence_verified_from_sample"),
        "quarantine_exit_authorized",
        "source_audit_ready",
        "empirical_evidence_eligible",
    ],
)
def test_process_record_promotions(
    field,
):
    record = _record()

    record["scientific_boundary"][field] = True

    _refingerprint(record)

    with pytest.raises(
        SchemaError,
        match=field,
    ):
        preflight.validate_gaze_in_wild_processdata_preflight_record(record)
