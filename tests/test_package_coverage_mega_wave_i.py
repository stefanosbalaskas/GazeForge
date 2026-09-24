from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.io import savemat

import gazeforge.gaze_in_wild as giw
import gazeforge.gaze_in_wild_coordinate_evidence as coord
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError

EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-por-coordinate-semantics-evidence-v1.json"
)


SOURCE_SNIPPET = """
ETG.SceneResolution = [1920, 1080];
ETG.POR = [Gaze_Data.norm_pos_x, Gaze_Data.norm_pos_y];
ETG.POR(:, 2) = 1 - ETG.POR(:, 2);
[ETG.POR, ~] = linearizeData(ETG_T, ETG.POR, 'pchip');
ProcessData.ETG.SceneResolution = ETG.SceneResolution;
ProcessData.ETG.POR = interp1(ETG.T, ETG.POR, ProcessData.T, 'pchip', 'extrap');
"""


# ============================================================
# GAZE-IN-THE-WILD ADAPTER HELPERS
# ============================================================


def _write_pair(
    root: Path,
    *,
    recording: str = "P01_task",
    labeller: int = 2,
    n: int = 6,
    rate: float = 120.0,
    resolution=(1920, 1080),
    confidence=None,
):
    label_root = root / "LabelData"
    process_root = root / "ProcessData"

    label_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    process_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    times = (
        np.arange(
            n,
            dtype=float,
        )
        / rate
    )

    labels = np.resize(
        np.array(
            [1, 2, 3, 4, 5, 0],
            dtype=int,
        ),
        n,
    )

    label = label_root / f"{recording}_Lbr_{labeller}.mat"

    process = process_root / f"{recording}.mat"

    savemat(
        label,
        {
            "LabelData": {
                "T": times,
                "Labels": labels,
                "LbrIdx": labeller,
            }
        },
    )

    por = np.vstack(
        [
            np.linspace(
                0.1,
                0.6,
                n,
            ),
            np.linspace(
                0.2,
                0.7,
                n,
            ),
        ]
    )

    if confidence is None:
        confidence = np.ones(
            n,
            dtype=float,
        )

    savemat(
        process,
        {
            "ProcessData": {
                "ETG": {
                    "POR": por,
                    "Confidence": confidence,
                    "SceneResolution": np.asarray(
                        resolution,
                        dtype=float,
                    ),
                }
            }
        },
    )

    return (
        label,
        process,
        label_root,
        process_root,
    )


def test_giw_field_mapping():
    assert (
        giw._field(
            {"x": 3},
            "x",
        )
        == 3
    )


def test_giw_field_attribute():
    assert (
        giw._field(
            SimpleNamespace(x=4),
            "x",
        )
        == 4
    )


def test_giw_field_structured_array():
    array = np.zeros(
        1,
        dtype=[("x", "i4")],
    )

    array["x"] = 5

    assert (
        giw._field(
            array,
            "x",
        )
        == 5
    )


def test_giw_field_missing():
    with pytest.raises(
        SchemaError,
        match="missing field",
    ):
        giw._field(
            {},
            "missing",
        )


def test_giw_load_struct_missing_key(tmp_path):
    path = tmp_path / "x.mat"

    savemat(
        path,
        {"Other": {"x": 1}},
    )

    with pytest.raises(
        SchemaError,
        match="does not contain MATLAB variable",
    ):
        giw._load_struct(
            path,
            "LabelData",
        )


@pytest.mark.parametrize(
    "value",
    [
        "not-numeric",
        object(),
    ],
)
def test_giw_numeric_vector_non_numeric(value):
    with pytest.raises(
        SchemaError,
        match="must be numeric",
    ):
        giw._numeric_vector(
            value,
            name="x",
        )


def test_giw_numeric_vector_empty():
    with pytest.raises(
        SchemaError,
        match="cannot be empty",
    ):
        giw._numeric_vector(
            [],
            name="x",
        )


def test_giw_numeric_vector_valid():
    result = giw._numeric_vector(
        [[1, 2]],
        name="x",
    )

    assert result.tolist() == [
        1.0,
        2.0,
    ]


def test_giw_label_metadata_standard():
    recording, labeller = giw._label_file_metadata(Path("P01_task_Lbr_7.mat"))

    assert recording == "P01_task"
    assert labeller == 7


def test_giw_label_metadata_nonstandard():
    recording, labeller = giw._label_file_metadata(Path("strange.mat"))

    assert recording == "strange"
    assert labeller is None


def test_giw_rate_nonfinite():
    with pytest.raises(
        SchemaError,
        match="finite",
    ):
        giw._infer_rate_from_seconds(np.array([0.0, np.nan]))


def test_giw_rate_too_short():
    with pytest.raises(
        SchemaError,
        match="At least two",
    ):
        giw._infer_rate_from_seconds(np.array([0.0]))


def test_giw_rate_non_increasing():
    with pytest.raises(
        SchemaError,
        match="strictly increasing",
    ):
        giw._infer_rate_from_seconds(np.array([0.0, 0.01, 0.01]))


def test_giw_rate_valid():
    rate = giw._infer_rate_from_seconds(np.array([0.0, 0.01, 0.02]))

    assert rate == pytest.approx(100.0)


def test_giw_por_non_numeric():
    with pytest.raises(
        SchemaError,
        match="must be numeric",
    ):
        giw._por_xy(
            [["a"]],
            1,
        )


def test_giw_por_not_2d():
    with pytest.raises(
        SchemaError,
        match="two-dimensional",
    ):
        giw._por_xy(
            [1, 2, 3],
            3,
        )


def test_giw_por_2_by_n():
    x, y = giw._por_xy(
        np.array(
            [
                [1, 2, 3],
                [4, 5, 6],
            ]
        ),
        3,
    )

    assert x.tolist() == [
        1.0,
        2.0,
        3.0,
    ]

    assert y.tolist() == [
        4.0,
        5.0,
        6.0,
    ]


def test_giw_por_n_by_2():
    x, y = giw._por_xy(
        np.array(
            [
                [1, 4],
                [2, 5],
                [3, 6],
            ]
        ),
        3,
    )

    assert x.tolist() == [
        1.0,
        2.0,
        3.0,
    ]

    assert y.tolist() == [
        4.0,
        5.0,
        6.0,
    ]


def test_giw_por_bad_shape():
    with pytest.raises(
        SchemaError,
        match="2×N or N×2",
    ):
        giw._por_xy(
            np.ones((3, 3)),
            3,
        )


@pytest.mark.parametrize(
    "value",
    [
        "bad",
        None,
    ],
)
def test_giw_scene_resolution_non_numeric(value):
    with pytest.raises(
        SchemaError,
        match="must be numeric|finite width and height",
    ):
        giw._scene_resolution(value)


@pytest.mark.parametrize(
    "value",
    [
        [1920],
        [1920, np.nan],
    ],
)
def test_giw_scene_resolution_shape_and_finite(value):
    with pytest.raises(
        SchemaError,
        match="finite width and height",
    ):
        giw._scene_resolution(value)


@pytest.mark.parametrize(
    "value",
    [
        [0, 1080],
        [-1, 1080],
        [1920.5, 1080],
    ],
)
def test_giw_scene_resolution_positive_integer(value):
    with pytest.raises(
        SchemaError,
        match="positive integer pixels",
    ):
        giw._scene_resolution(value)


def test_giw_scene_resolution_valid():
    assert giw._scene_resolution([1920, 1080]) == (1920, 1080)


# ============================================================
# LOAD ONE RECORDING
# ============================================================


def test_giw_load_missing_label(tmp_path):
    with pytest.raises(
        FileNotFoundError,
    ):
        giw.load_gaze_in_wild_mat(tmp_path / "missing.mat")


@pytest.mark.parametrize(
    "threshold",
    [
        -0.1,
        1.1,
        np.nan,
        np.inf,
    ],
)
def test_giw_invalid_threshold(
    tmp_path,
    threshold,
):
    label, _, _, _ = _write_pair(tmp_path)

    with pytest.raises(
        ValueError,
        match="confidence_threshold",
    ):
        giw.load_gaze_in_wild_mat(
            label,
            confidence_threshold=threshold,
        )


def test_giw_labels_times_length_mismatch(tmp_path):
    label = tmp_path / "P01_task_Lbr_2.mat"

    savemat(
        label,
        {
            "LabelData": {
                "T": [0.0, 0.01],
                "Labels": [1],
                "LbrIdx": 2,
            }
        },
    )

    with pytest.raises(
        SchemaError,
        match="lengths differ",
    ):
        giw.load_gaze_in_wild_mat(label)


def test_giw_missing_lbridx_is_supported(tmp_path):
    label = tmp_path / "recording.mat"

    savemat(
        label,
        {
            "LabelData": {
                "T": [
                    0.0,
                    0.01,
                ],
                "Labels": [
                    1,
                    3,
                ],
            }
        },
    )

    frame = giw.load_gaze_in_wild_mat(label)

    assert frame.data["annotator"].isna().all()


def test_giw_unknown_event_code(tmp_path):
    label = tmp_path / "P01_task_Lbr_2.mat"

    savemat(
        label,
        {
            "LabelData": {
                "T": [
                    0.0,
                    0.01,
                ],
                "Labels": [
                    99,
                    1,
                ],
                "LbrIdx": 2,
            }
        },
    )

    frame = giw.load_gaze_in_wild_mat(label)

    assert frame.data["event_label"].tolist()[0] == "unknown_99"


def test_giw_missing_process_file(tmp_path):
    label, _, _, _ = _write_pair(tmp_path)

    with pytest.raises(
        FileNotFoundError,
    ):
        giw.load_gaze_in_wild_mat(
            label,
            process_path=(tmp_path / "missing.mat"),
        )


def test_giw_confidence_length_mismatch(tmp_path):
    label, process, _, _ = _write_pair(tmp_path)

    n = 6

    savemat(
        process,
        {
            "ProcessData": {
                "ETG": {
                    "POR": np.ones((2, n)) * 0.5,
                    "Confidence": np.ones(n - 1),
                    "SceneResolution": [
                        1920,
                        1080,
                    ],
                }
            }
        },
    )

    with pytest.raises(
        SchemaError,
        match="Confidence length",
    ):
        giw.load_gaze_in_wild_mat(
            label,
            process_path=process,
        )


def test_giw_validity_filters_nonfinite_por(tmp_path):
    label, process, _, _ = _write_pair(tmp_path)

    por = np.array(
        [
            [
                0.1,
                np.nan,
                0.3,
                0.4,
                0.5,
                0.6,
            ],
            [
                0.2,
                0.3,
                0.4,
                0.5,
                0.6,
                0.7,
            ],
        ]
    )

    savemat(
        process,
        {
            "ProcessData": {
                "ETG": {
                    "POR": por,
                    "Confidence": np.ones(6),
                    "SceneResolution": [
                        1920,
                        1080,
                    ],
                }
            }
        },
    )

    frame = giw.load_gaze_in_wild_mat(
        label,
        process_path=process,
    )

    assert not bool(
        frame.data.loc[
            1,
            "validity",
        ]
    )

    assert np.isnan(
        frame.data.loc[
            1,
            "x_px",
        ]
    )


# ============================================================
# DIRECTORY LOADER
# ============================================================


def test_giw_directory_missing_root(tmp_path):
    with pytest.raises(
        FileNotFoundError,
    ):
        giw.load_gaze_in_wild_directory(tmp_path / "missing")


def test_giw_directory_missing_process_root(tmp_path):
    _, _, label_root, _ = _write_pair(tmp_path)

    with pytest.raises(
        FileNotFoundError,
    ):
        giw.load_gaze_in_wild_directory(
            label_root,
            process_root=(tmp_path / "missing-process"),
        )


def test_giw_directory_no_labels(tmp_path):
    root = tmp_path / "labels"
    root.mkdir()

    with pytest.raises(
        FileNotFoundError,
        match="No Gaze-in-the-Wild label files",
    ):
        giw.load_gaze_in_wild_directory(root)


def test_giw_directory_nonrecursive(tmp_path):
    nested = tmp_path / "LabelData" / "nested"

    nested.mkdir(parents=True)

    label = nested / "P01_task_Lbr_2.mat"

    savemat(
        label,
        {
            "LabelData": {
                "T": [
                    0.0,
                    0.01,
                ],
                "Labels": [
                    1,
                    3,
                ],
                "LbrIdx": 2,
            }
        },
    )

    with pytest.raises(
        FileNotFoundError,
    ):
        giw.load_gaze_in_wild_directory(
            tmp_path / "LabelData",
            recursive=False,
        )


def test_giw_directory_inconsistent_rates(tmp_path):
    _, _, label_root, _ = _write_pair(
        tmp_path,
        recording="P01_task",
        rate=120.0,
    )

    _write_pair(
        tmp_path,
        recording="P02_task",
        rate=60.0,
    )

    with pytest.raises(
        SchemaError,
        match="consistent inferred sampling rate",
    ):
        giw.load_gaze_in_wild_directory(
            label_root,
            labeller=2,
        )


def test_giw_directory_inconsistent_screen_sizes(tmp_path):
    _, _, label_root, process_root = _write_pair(
        tmp_path,
        recording="P01_task",
        resolution=(1920, 1080),
    )

    _write_pair(
        tmp_path,
        recording="P02_task",
        resolution=(1280, 720),
    )

    with pytest.raises(
        SchemaError,
        match="one ETG.SceneResolution",
    ):
        giw.load_gaze_in_wild_directory(
            label_root,
            process_root=process_root,
            labeller=2,
        )


def test_giw_directory_label_only_metadata(tmp_path):
    _, _, label_root, _ = _write_pair(
        tmp_path,
        recording="P01_task",
    )

    frame = giw.load_gaze_in_wild_directory(
        label_root,
        labeller=2,
        participant_parser=lambda path: "P01",
    )

    assert frame.screen_size_px is None
    assert frame.metadata["coordinate_unit_verified"] is False

    assert frame.metadata["coordinate_output_unit"] == "unavailable"


# ============================================================
# COORDINATE EVIDENCE HELPERS
# ============================================================


def _coordinate_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _live_probe():
    record = {
        "record_type": coord.LIVE_RECORD_TYPE,
        "source_binding": {
            "repository": coord.SOURCE_REPOSITORY,
            "commit_sha1": coord.SOURCE_COMMIT,
            "path": coord.SOURCE_PATH,
            "git_blob_sha1": coord.SOURCE_BLOB,
        },
        "source_semantics": {
            "pupil_source_fields": [
                "norm_pos_x",
                "norm_pos_y",
            ],
            "matlab_y_flip_present": True,
            "scene_resolution_px": [
                1920,
                1080,
            ],
            "scene_resolution_stored_separately": True,
            "processdata_por_direct_interpolation_present": True,
            "required_marker_count": 6,
            "processdata_etg_por_occurrence_count": 1,
        },
        "verification": {
            "processdata_por_coordinate_space": ("normalized_scene_image"),
            "first_party_pixel_por_claim": False,
            "canonical_pixel_conversion_supported": True,
        },
        "boundaries": {
            "distribution_equivalence_verified": False,
            "participant_mapping_verified": False,
            "task_mapping_verified": False,
            "reuse_terms_verified": False,
            "analysis_use_permitted": False,
            "cross_dataset_validation_created": False,
            "new_empirical_performance_claim_created": False,
        },
    }

    record["probe_fingerprint_sha256"] = coord.probe_fingerprint(record)

    return record


def _refingerprint_probe(record):
    record["probe_fingerprint_sha256"] = coord.probe_fingerprint(record)


def test_coord_canonical_bytes_order():
    assert coord._canonical_bytes({"b": 2, "a": 1}) == coord._canonical_bytes({"a": 1, "b": 2})


def test_coord_evidence_fingerprint_ignores_stored():
    record = {
        "x": 1,
        "evidence_fingerprint_sha256": "bad",
    }

    first = coord.evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = "other"

    assert coord.evidence_fingerprint(record) == first


def test_coord_probe_fingerprint_ignores_stored():
    record = {
        "x": 1,
        "probe_fingerprint_sha256": "bad",
    }

    first = coord.probe_fingerprint(record)

    record["probe_fingerprint_sha256"] = "other"

    assert coord.probe_fingerprint(record) == first


def test_coord_git_blob_is_deterministic():
    assert coord.git_blob_sha1(b"abc") == coord.git_blob_sha1(b"abc")


def test_coord_load_mapping_returns_copy():
    original = {"x": 1}

    result = coord._load_record(original)

    assert result == original
    assert result is not original


def test_coord_load_path(tmp_path):
    path = tmp_path / "record.json"

    path.write_text(
        '{"x": 1}',
        encoding="utf-8",
    )

    assert coord._load_record(path) == {"x": 1}


def test_coord_require_false_success():
    coord._require_false(
        {
            "a": False,
            "b": False,
        },
        "a",
        "b",
    )


def test_coord_require_false_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be false",
    ):
        coord._require_false(
            {"a": True},
            "a",
        )


def test_coord_normalized_source():
    assert coord._normalized_source(" a \n  b\t c ") == "a b c"


def test_coord_source_markers_whitespace_tolerant():
    counts = coord.validate_first_party_por_source(SOURCE_SNIPPET)

    assert counts["required_marker_count"] == 6

    assert counts["processdata_etg_por_occurrence_count"] == 1


def test_coord_source_missing_marker():
    source = SOURCE_SNIPPET.replace(
        "ETG.SceneResolution = [1920, 1080];",
        "",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="markers are missing",
    ):
        coord.validate_first_party_por_source(source)


def test_coord_source_duplicate_assignment():
    source = SOURCE_SNIPPET + "\n" + coord._REQUIRED_SOURCE_MARKERS[-1]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly one reviewed",
    ):
        coord.validate_first_party_por_source(source)


# ============================================================
# IMMUTABLE COORDINATE EVIDENCE
# ============================================================


def test_coord_evidence_valid():
    result = coord.validate_gaze_in_wild_por_coordinate_evidence(EVIDENCE)

    assert result["evidence_fingerprint_sha256"] == coord.EVIDENCE_FINGERPRINT


def test_coord_evidence_identity_guard():
    record = _coordinate_evidence()
    record["record_type"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="identity/status",
    ):
        coord.validate_gaze_in_wild_por_coordinate_evidence(record)


def test_coord_evidence_status_guard():
    record = _coordinate_evidence()
    record["status"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="identity/status",
    ):
        coord.validate_gaze_in_wild_por_coordinate_evidence(record)


def test_coord_evidence_stored_fingerprint_guard():
    record = _coordinate_evidence()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="stored fingerprint",
    ):
        coord.validate_gaze_in_wild_por_coordinate_evidence(record)


def test_coord_evidence_content_fingerprint_guard():
    record = _coordinate_evidence()

    record["extra"] = "drift"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="content fingerprint",
    ):
        coord.validate_gaze_in_wild_por_coordinate_evidence(record)


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    [
        (
            "canonical_source",
            "repository",
            "bad",
            "source repository",
        ),
        (
            "canonical_source",
            "commit_sha1",
            "0" * 40,
            "source commit",
        ),
        (
            "canonical_source",
            "path",
            "bad",
            "source file/blob",
        ),
        (
            "canonical_source",
            "git_blob_sha1",
            "0" * 40,
            "source file/blob",
        ),
        (
            "reviewed_source_semantics",
            "pupil_source_fields",
            ["x", "y"],
            "normalized POR fields",
        ),
        (
            "reviewed_source_semantics",
            "scene_resolution_px",
            [1, 1],
            "scene resolution",
        ),
        (
            "reviewed_source_semantics",
            "scene_resolution_stored_separately",
            False,
            "remain separate",
        ),
        (
            "reviewed_source_semantics",
            "processdata_por_is_interpolated_from_etg_por",
            False,
            "lineage",
        ),
        (
            "reviewed_source_semantics",
            "por_multiplied_by_scene_resolution_in_first_party_preprocessing",
            True,
            "pixel POR",
        ),
        (
            "verification",
            "processdata_por_coordinate_semantics_verified",
            False,
            "not verified",
        ),
        (
            "verification",
            "processdata_por_coordinate_space",
            "pixels",
            "coordinate space",
        ),
        (
            "verification",
            "scene_resolution_metadata_unit",
            "cm",
            "metadata unit",
        ),
        (
            "verification",
            "first_party_pixel_por_claim",
            True,
            "pixel POR claim",
        ),
        (
            "verification",
            "canonical_pixel_conversion_supported",
            False,
            "conversion",
        ),
        (
            "verification",
            "canonical_pixel_conversion",
            {},
            "conversion contract",
        ),
        (
            "gaze_forge_contract",
            "normalized_por_to_canonical_pixels",
            False,
            "conversion drifted",
        ),
        (
            "gaze_forge_contract",
            "coordinate_output_unit_after_conversion",
            "normalized",
            "output unit",
        ),
        (
            "gaze_forge_contract",
            "pixel_kinematics_requires_canonical_conversion",
            False,
            "Pixel-kinematics",
        ),
    ],
)
def test_coord_semantic_contract_guards(
    monkeypatch,
    section,
    field,
    value,
    message,
):
    record = _coordinate_evidence()

    record[section][field] = value

    monkeypatch.setattr(
        coord,
        "evidence_fingerprint",
        lambda payload: coord.EVIDENCE_FINGERPRINT,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        coord.validate_gaze_in_wild_por_coordinate_evidence(record)


@pytest.mark.parametrize(
    ("section", "key"),
    [
        (
            "distribution_boundary",
            "authoritative_full_distribution_obtained",
        ),
        (
            "distribution_boundary",
            "corpus_wide_por_ranges_empirically_verified",
        ),
        (
            "distribution_boundary",
            "exact_distributed_file_equivalence_verified",
        ),
        (
            "distribution_boundary",
            "quarantined_processdata_sample_promoted",
        ),
        (
            "mapping_boundary",
            "participant_identity_mapping_verified",
        ),
        (
            "mapping_boundary",
            "participant_task_mapping_verified",
        ),
        (
            "mapping_boundary",
            "trial_index_to_task_name_mapping_verified",
        ),
        (
            "rights_boundary",
            "analysis_use_permitted",
        ),
        (
            "rights_boundary",
            "redistribution_permission_verified",
        ),
        (
            "rights_boundary",
            "reuse_terms_verified",
        ),
        (
            "scientific_boundary",
            "cross_dataset_validation_created",
        ),
        (
            "scientific_boundary",
            "human_human_agreement_created",
        ),
        (
            "scientific_boundary",
            "new_empirical_performance_claim_created",
        ),
        (
            "scientific_boundary",
            "participant_disjoint_model_validation_created",
        ),
        (
            "scientific_boundary",
            "per_file_sampling_rate_distribution_frozen",
        ),
    ],
)
def test_coord_boundaries_cannot_promote(
    monkeypatch,
    section,
    key,
):
    record = _coordinate_evidence()

    record[section][key] = True

    monkeypatch.setattr(
        coord,
        "evidence_fingerprint",
        lambda payload: coord.EVIDENCE_FINGERPRINT,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be false",
    ):
        coord.validate_gaze_in_wild_por_coordinate_evidence(record)


# ============================================================
# LIVE PROBE
# ============================================================


def test_coord_build_live_probe_success(monkeypatch):
    monkeypatch.setattr(
        coord,
        "git_blob_sha1",
        lambda payload: coord.SOURCE_BLOB,
    )

    result = coord.build_first_party_por_live_probe(SOURCE_SNIPPET)

    assert result["record_type"] == coord.LIVE_RECORD_TYPE

    assert result["source_binding"]["git_blob_sha1"] == coord.SOURCE_BLOB


def test_coord_build_live_probe_blob_guard():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="pinned Git blob",
    ):
        coord.build_first_party_por_live_probe(SOURCE_SNIPPET)


def test_coord_live_valid():
    result = coord.validate_live_por_probe_against_evidence(
        _live_probe(),
        EVIDENCE,
    )

    assert result["evidence_fingerprint_sha256"] == coord.EVIDENCE_FINGERPRINT


def test_coord_live_type_guard():
    record = _live_probe()
    record["record_type"] = "bad"

    _refingerprint_probe(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="live probe type",
    ):
        coord.validate_live_por_probe_against_evidence(
            record,
            EVIDENCE,
        )


def test_coord_live_fingerprint_guard():
    record = _live_probe()

    record["probe_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint is invalid",
    ):
        coord.validate_live_por_probe_against_evidence(
            record,
            EVIDENCE,
        )


def test_coord_live_source_binding_guard():
    record = _live_probe()

    record["source_binding"]["commit_sha1"] = "0" * 40

    _refingerprint_probe(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source binding drifted",
    ):
        coord.validate_live_por_probe_against_evidence(
            record,
            EVIDENCE,
        )


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    [
        (
            "source_semantics",
            "pupil_source_fields",
            ["x"],
            "POR fields",
        ),
        (
            "source_semantics",
            "scene_resolution_px",
            [1, 1],
            "scene resolution",
        ),
        (
            "source_semantics",
            "scene_resolution_stored_separately",
            False,
            "no longer separate",
        ),
        (
            "source_semantics",
            "processdata_por_direct_interpolation_present",
            False,
            "POR lineage",
        ),
        (
            "source_semantics",
            "processdata_etg_por_occurrence_count",
            2,
            "assignment count",
        ),
        (
            "verification",
            "processdata_por_coordinate_space",
            "pixels",
            "coordinate space",
        ),
        (
            "verification",
            "first_party_pixel_por_claim",
            True,
            "pixel POR claim",
        ),
        (
            "verification",
            "canonical_pixel_conversion_supported",
            False,
            "conversion boundary",
        ),
    ],
)
def test_coord_live_contract_guards(
    section,
    field,
    value,
    message,
):
    record = _live_probe()

    record[section][field] = value

    _refingerprint_probe(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        coord.validate_live_por_probe_against_evidence(
            record,
            EVIDENCE,
        )


@pytest.mark.parametrize(
    "key",
    [
        "distribution_equivalence_verified",
        "participant_mapping_verified",
        "task_mapping_verified",
        "reuse_terms_verified",
        "analysis_use_permitted",
        "cross_dataset_validation_created",
        "new_empirical_performance_claim_created",
    ],
)
def test_coord_live_boundaries_cannot_promote(
    key,
):
    record = _live_probe()

    record["boundaries"][key] = True

    _refingerprint_probe(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=key,
    ):
        coord.validate_live_por_probe_against_evidence(
            record,
            EVIDENCE,
        )
