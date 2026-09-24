from __future__ import annotations

import builtins
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from test_grounded_sam2 import _FakeRuntime, _fixture, _run

import gazeforge.grounded_sam2 as gs
import gazeforge.source_resolution as sr
from gazeforge.exceptions import (
    BenchmarkIntegrityError,
    OptionalDependencyError,
    SchemaError,
)

ROOT = Path(__file__).resolve().parents[1]

H2_PATH = ROOT / "validation" / "protocols" / "hollywood2-source-resolution-2026-09-05.json"

GIW_PATH = ROOT / "validation" / "protocols" / "gaze-in-wild-source-resolution-2026-09-04.json"

VISUS_PATH = ROOT / "validation" / "protocols" / "visus-source-resolution-2026-09-04.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(
    tmp_path: Path,
    payload: object,
    *,
    name: str = "record.json",
) -> Path:
    path = tmp_path / name
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def _set_path(
    payload: dict,
    path: tuple[str, ...],
    value: object,
) -> dict:
    current = payload

    for key in path[:-1]:
        current = current[key]

    current[path[-1]] = value

    return payload


def _resign_grounded_report(run) -> None:
    body = {key: value for key, value in run.report.items() if key != "report_fingerprint_sha256"}

    run.report["report_fingerprint_sha256"] = gs.benchmark_fingerprint(body)


# =====================================================================
# GROUNDED SAM2
# =====================================================================


@pytest.mark.parametrize(
    "value",
    [
        "",
        "VERIFY_ME",
        "replace-this",
    ],
)
def test_grounded_resolved_values_fail_closed(value):
    with pytest.raises(ValueError):
        gs._resolved(
            value,
            label="demo",
        )


def test_grounded_sha256_rejects_invalid_digest():
    with pytest.raises(
        ValueError,
        match="64-character",
    ):
        gs._sha256(
            "bad",
            label="demo",
        )


def test_grounded_file_digest_requires_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        gs._file_sha256(
            tmp_path / "missing.bin",
            label="demo",
        )


def test_grounded_file_digest_rejects_empty_file(tmp_path):
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot be empty",
    ):
        gs._file_sha256(
            path,
            label="demo",
        )


def test_grounded_frame_manifest_requires_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        gs._frame_manifest(
            tmp_path / "missing",
            frame_index_base=0,
        )


def test_grounded_frame_manifest_requires_jpeg(tmp_path):
    frame_dir = tmp_path / "frames"
    frame_dir.mkdir()

    with pytest.raises(
        SchemaError,
        match="at least one",
    ):
        gs._frame_manifest(
            frame_dir,
            frame_index_base=0,
        )


def test_grounded_frame_manifest_rejects_duplicate_numeric_identity(
    tmp_path,
):
    frame_dir = tmp_path / "frames"
    frame_dir.mkdir()

    (frame_dir / "1.jpg").write_bytes(b"a")
    (frame_dir / "01.jpg").write_bytes(b"b")

    with pytest.raises(
        SchemaError,
        match="unique",
    ):
        gs._frame_manifest(
            frame_dir,
            frame_index_base=1,
        )


def test_grounded_labels_cannot_be_empty():
    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        gs._prompt_labels([])


def test_grounded_normalised_label_cannot_be_empty():
    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        gs._prompt_labels(["."])


def test_grounded_labels_unique_ignoring_case():
    with pytest.raises(
        ValueError,
        match="unique ignoring case",
    ):
        gs._prompt_labels(
            [
                "Red Car",
                "red car.",
            ]
        )


def test_grounded_config_type_guard():
    with pytest.raises(
        TypeError,
        match="GroundedSAM2Config",
    ):
        gs._validate_config(object())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("frame_rate_hz", 0.0),
        ("frame_rate_hz", np.nan),
        ("frame_index_base", 2),
        ("prompt_frame_index", -1),
        ("box_threshold", -0.01),
        ("box_threshold", np.nan),
        ("text_threshold", 1.01),
        ("min_mask_pixels", 0),
        ("grounding_model_id", "VERIFY_ME"),
        ("source_video_sha256", "bad"),
        ("device", ""),
    ],
)
def test_grounded_config_guards(
    tmp_path,
    field,
    value,
):
    _, _, config = _fixture(tmp_path)

    broken = replace(
        config,
        **{field: value},
    )

    with pytest.raises(ValueError):
        gs._validate_config(broken)


def test_grounded_box_requires_four_coordinates():
    with pytest.raises(
        SchemaError,
        match="four box coordinates",
    ):
        gs._validate_box(
            [0.0, 1.0, 2.0],
            label="demo",
        )


def test_grounded_box_requires_finite_coordinates():
    with pytest.raises(
        SchemaError,
        match="non-finite",
    ):
        gs._validate_box(
            [
                0.0,
                0.0,
                np.nan,
                3.0,
            ],
            label="demo",
        )


def test_grounded_detector_contract_requires_detection_objects():
    with pytest.raises(
        TypeError,
        match="GroundedSAM2Detection",
    ):
        gs._prepare_seeds(
            [object()],
            label_lookup={},
        )


def test_grounded_detector_requires_at_least_one_seed():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="no seed detections",
    ):
        gs._prepare_seeds(
            [],
            label_lookup={
                "red car": "Red Car",
            },
        )


def test_grounded_mask_squeezes_singleton_dimension():
    mask = np.zeros(
        (1, 5, 6),
        dtype=bool,
    )
    mask[:, 1:4, 2:5] = True

    result = gs._mask_box(
        mask,
        min_mask_pixels=1,
    )

    assert result == (
        2.0,
        1.0,
        5.0,
        4.0,
    )


def test_grounded_mask_rejects_non_2d_object():
    with pytest.raises(
        SchemaError,
        match="two-dimensional",
    ):
        gs._mask_box(
            np.ones(
                (2, 5, 6),
                dtype=bool,
            ),
            min_mask_pixels=1,
        )


def _seed(
    *,
    object_id: int = 1,
    aoi_id: str = "a",
):
    return gs.GroundedSAM2Seed(
        object_id=object_id,
        aoi_id=aoi_id,
        label="A",
        score=0.9,
        box_xyxy=(
            0.0,
            0.0,
            2.0,
            2.0,
        ),
    )


def _manifest():
    return [
        {
            "position": 0,
            "frame_index": 0,
        }
    ]


def test_grounded_canonical_rejects_duplicate_seed_ids():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="object IDs must be unique",
    ):
        gs._canonical_from_segments(
            {},
            seeds=[
                _seed(
                    object_id=1,
                    aoi_id="a",
                ),
                _seed(
                    object_id=1,
                    aoi_id="b",
                ),
            ],
            manifest=_manifest(),
            frame_rate_hz=25.0,
            frame_index_base=0,
            min_mask_pixels=1,
        )


def test_grounded_canonical_requires_object_mapping():
    with pytest.raises(
        TypeError,
        match="object/mask mappings",
    ):
        gs._canonical_from_segments(
            {
                0: [1],
            },
            seeds=[_seed()],
            manifest=_manifest(),
            frame_rate_hz=25.0,
            frame_index_base=0,
            min_mask_pixels=1,
        )


def test_grounded_canonical_rejects_non_2d_propagated_mask():
    with pytest.raises(
        SchemaError,
        match="two-dimensional",
    ):
        gs._canonical_from_segments(
            {
                0: {
                    1: np.ones(
                        (2, 4, 4),
                        dtype=bool,
                    )
                }
            },
            seeds=[_seed()],
            manifest=_manifest(),
            frame_rate_hz=25.0,
            frame_index_base=0,
            min_mask_pixels=1,
        )


def test_grounded_prompt_frame_must_exist(tmp_path):
    frame_dir, _, config = _fixture(tmp_path)

    broken = replace(
        config,
        prompt_frame_index=99,
    )

    with pytest.raises(
        SchemaError,
        match="exact input frames",
    ):
        gs.run_grounded_sam2_dynamic_aoi(
            frame_dir,
            labels=["Red Car"],
            config=broken,
            runtime=_FakeRuntime(),
        )


def test_grounded_none_runtime_uses_optional_runtime_branch(
    tmp_path,
    monkeypatch,
):
    frame_dir, _, config = _fixture(tmp_path)

    monkeypatch.setattr(
        gs,
        "HuggingFaceGroundedSAM2Runtime",
        lambda: _FakeRuntime(),
    )

    run = gs.run_grounded_sam2_dynamic_aoi(
        frame_dir,
        labels=[
            "Red Car",
            "White Car",
        ],
        config=config,
        runtime=None,
    )

    assert len(run.canonical) == 6


def test_grounded_validator_requires_run_type():
    with pytest.raises(
        TypeError,
        match="GroundedSAM2DynamicAOIRun",
    ):
        gs.validate_grounded_sam2_run(object())


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("status", "bad"),
        ("backend", "bad"),
        (
            "integration_contract_reference",
            "bad",
        ),
        (
            "evaluation_timestamp_grid_generated",
            True,
        ),
        (
            "empirical_performance_claim_created",
            True,
        ),
        (
            "visus_source_authority_implied",
            True,
        ),
    ],
)
def test_grounded_validator_claim_and_identity_guards(
    tmp_path,
    key,
    value,
):
    run, _ = _run(tmp_path)

    run.report[key] = value

    with pytest.raises(BenchmarkIntegrityError):
        gs.validate_grounded_sam2_run(run)


def test_grounded_validator_requires_output_mapping(
    tmp_path,
):
    run, _ = _run(tmp_path)

    run.report["output"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="output provenance",
    ):
        gs.validate_grounded_sam2_run(run)


def test_grounded_validator_row_count_guard(
    tmp_path,
):
    run, _ = _run(tmp_path)

    run.report["output"]["row_count"] += 1

    with pytest.raises(
        BenchmarkIntegrityError,
        match="row count",
    ):
        gs.validate_grounded_sam2_run(run)


def test_grounded_validator_track_count_guard(
    tmp_path,
):
    run, _ = _run(tmp_path)

    run.report["output"]["track_count"] += 1

    with pytest.raises(
        BenchmarkIntegrityError,
        match="track count",
    ):
        gs.validate_grounded_sam2_run(run)


def test_grounded_validator_report_fingerprint_guard(
    tmp_path,
):
    run, _ = _run(tmp_path)

    run.report["report_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="report fingerprint",
    ):
        gs.validate_grounded_sam2_run(run)


def test_grounded_validator_keyframe_cardinality_guard(
    tmp_path,
):
    run, _ = _run(tmp_path)

    run.keyframes.pop()

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cardinality",
    ):
        gs.validate_grounded_sam2_run(run)


def test_grounded_export_stimulus_must_be_resolved(
    tmp_path,
):
    run, _ = _run(tmp_path)

    with pytest.raises(ValueError):
        gs.grounded_sam2_to_visus_prediction_table(
            run,
            stimulus_id="VERIFY_ME",
        )


def test_grounded_export_requires_canonical_columns(
    tmp_path,
):
    run, _ = _run(tmp_path)

    run.canonical = run.canonical.drop(columns=["confidence"])

    run.report["output"]["canonical_table_fingerprint_sha256"] = gs.fingerprint_frame(run.canonical)

    run.report["output"]["row_count"] = len(run.canonical)

    run.report["output"]["track_count"] = run.canonical["aoi_id"].nunique()

    _resign_grounded_report(run)

    with pytest.raises(
        SchemaError,
        match="missing columns",
    ):
        gs.grounded_sam2_to_visus_prediction_table(
            run,
            stimulus_id="S01",
        )


def test_grounded_optional_import_failure_is_explicit(
    monkeypatch,
):
    original_import = builtins.__import__

    def controlled_import(
        name,
        globals=None,
        locals=None,
        fromlist=(),
        level=0,
    ):
        if name.startswith("sam2"):
            raise ImportError("forced SAM2 absence")

        return original_import(
            name,
            globals,
            locals,
            fromlist,
            level,
        )

    monkeypatch.setattr(
        builtins,
        "__import__",
        controlled_import,
    )

    with pytest.raises(
        OptionalDependencyError,
        match="optional vision packages",
    ):
        gs.HuggingFaceGroundedSAM2Runtime._imports()


def test_grounded_runtime_metadata_handles_missing_distributions(
    monkeypatch,
):
    runtime = gs.HuggingFaceGroundedSAM2Runtime()

    def fake_version(name):
        if name == "torch":
            return "1.2.3"

        raise (gs.importlib.metadata.PackageNotFoundError(name))

    monkeypatch.setattr(
        gs.importlib.metadata,
        "version",
        fake_version,
    )

    metadata = runtime.runtime_metadata()

    assert metadata["torch"] == "1.2.3"
    assert metadata["transformers"] == "unavailable"
    assert metadata["Pillow"] == "unavailable"


def test_grounded_hf_detect_contract_without_real_models(
    tmp_path,
    monkeypatch,
):
    frame_dir, _, config = _fixture(tmp_path)

    class Context:
        def __enter__(self):
            return None

        def __exit__(
            self,
            exc_type,
            exc,
            traceback,
        ):
            return False

    class Torch:
        @staticmethod
        def no_grad():
            return Context()

    class Tensor:
        def __init__(self, value):
            self.value = np.asarray(value)

        def detach(self):
            return self

        def cpu(self):
            return self

        def numpy(self):
            return self.value

    class ImageValue:
        size = (8, 6)

        def convert(self, mode):
            assert mode == "RGB"
            return self

    class Image:
        @staticmethod
        def open(path):
            assert path.is_file()
            return ImageValue()

    class Inputs(dict):
        def __init__(self):
            super().__init__(input_ids=np.asarray([[1, 2]]))
            self.input_ids = self["input_ids"]

        def to(self, device):
            assert device == "cpu"
            return self

    class Processor:
        @classmethod
        def from_pretrained(
            cls,
            *args,
            **kwargs,
        ):
            return cls()

        def __call__(
            self,
            *,
            images,
            text,
            return_tensors,
        ):
            assert images is not None
            assert text == "red car."
            assert return_tensors == "pt"
            return Inputs()

        def post_process_grounded_object_detection(
            self,
            outputs,
            input_ids,
            *,
            threshold,
            text_threshold,
            target_sizes,
        ):
            assert outputs is not None
            assert input_ids is not None
            assert threshold == pytest.approx(config.box_threshold)
            assert text_threshold == pytest.approx(config.text_threshold)
            assert target_sizes == [(6, 8)]

            return [
                {
                    "boxes": Tensor(
                        [
                            [
                                1.0,
                                2.0,
                                4.0,
                                5.0,
                            ]
                        ]
                    ),
                    "scores": Tensor([0.88]),
                    "labels": ["red car"],
                }
            ]

    class Model:
        @classmethod
        def from_pretrained(
            cls,
            *args,
            **kwargs,
        ):
            return cls()

        def to(self, device):
            assert device == "cpu"
            return self

        def __call__(self, **kwargs):
            assert "input_ids" in kwargs
            return object()

    monkeypatch.setattr(
        gs.HuggingFaceGroundedSAM2Runtime,
        "_imports",
        staticmethod(
            lambda: (
                Torch,
                Image,
                object(),
                Processor,
                Model,
            )
        ),
    )

    runtime = gs.HuggingFaceGroundedSAM2Runtime()

    detections = runtime.detect(
        frame_dir / "0.jpg",
        "red car.",
        config,
    )

    assert len(detections) == 1
    assert detections[0].label == "red car"
    assert detections[0].score == pytest.approx(0.88)
    assert detections[0].box_xyxy == (
        1.0,
        2.0,
        4.0,
        5.0,
    )


def test_grounded_hf_propagation_contract_without_real_sam2(
    tmp_path,
    monkeypatch,
):
    frame_dir, _, config = _fixture(tmp_path)

    class Context:
        def __enter__(self):
            return None

        def __exit__(
            self,
            exc_type,
            exc,
            traceback,
        ):
            return False

    class Torch:
        @staticmethod
        def inference_mode():
            return Context()

    class Mask:
        def __init__(self, value):
            self.value = np.asarray(value)

        def __gt__(self, threshold):
            return Mask(self.value > threshold)

        def detach(self):
            return self

        def cpu(self):
            return self

        def numpy(self):
            return self.value

    class Predictor:
        def __init__(self):
            self.added = []

        def init_state(
            self,
            *,
            video_path,
        ):
            assert Path(video_path).resolve() == frame_dir.resolve()
            return {"video_path": video_path}

        def add_new_points_or_box(
            self,
            *,
            inference_state,
            frame_idx,
            obj_id,
            box,
        ):
            assert inference_state
            self.added.append(
                (
                    frame_idx,
                    obj_id,
                    box.copy(),
                )
            )

        def propagate_in_video(self, state):
            assert state

            yield (
                0,
                [1],
                [
                    Mask(
                        np.ones(
                            (1, 4, 5),
                            dtype=float,
                        )
                    )
                ],
            )

    predictor = Predictor()

    def build_predictor(
        model_cfg,
        checkpoint,
        *,
        device,
    ):
        assert model_cfg == (config.sam2_model_cfg)
        assert Path(checkpoint).resolve() == Path(config.sam2_checkpoint_path).resolve()
        assert device == "cpu"

        return predictor

    monkeypatch.setattr(
        gs.HuggingFaceGroundedSAM2Runtime,
        "_imports",
        staticmethod(
            lambda: (
                Torch,
                object(),
                build_predictor,
                object(),
                object(),
            )
        ),
    )

    runtime = gs.HuggingFaceGroundedSAM2Runtime()

    seed = gs.GroundedSAM2Seed(
        object_id=1,
        aoi_id="red",
        label="Red Car",
        score=0.9,
        box_xyxy=(
            0.0,
            0.0,
            3.0,
            3.0,
        ),
    )

    segments = runtime.propagate(
        frame_dir,
        [seed],
        prompt_position=0,
        config=config,
    )

    assert list(segments) == [0]
    assert list(segments[0]) == [1]
    assert segments[0][1].shape == (
        1,
        4,
        5,
    )
    assert predictor.added


# =====================================================================
# SOURCE RESOLUTION COMMON CONTRACT
# =====================================================================


def test_source_resolution_load_requires_file(
    tmp_path,
):
    with pytest.raises(FileNotFoundError):
        sr._load_payload(tmp_path / "missing.json")


def test_source_resolution_load_requires_json_object(
    tmp_path,
):
    path = _write_json(
        tmp_path,
        [],
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="JSON object",
    ):
        sr._load_payload(path)


def test_source_resolution_bool_guard():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be boolean",
    ):
        sr._require_bool(
            {"flag": 1},
            "flag",
            dataset_key="demo",
        )


def test_source_resolution_mapping_guard():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        sr._require_mapping(
            {
                "mapping": [],
            },
            "mapping",
            dataset_key="demo",
        )


@pytest.mark.parametrize(
    "value",
    [
        [],
        [""],
        [1],
        "wrong",
    ],
)
def test_source_resolution_text_list_guard(
    value,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-empty strings",
    ):
        sr._require_nonempty_string_list(
            {
                "items": value,
            },
            "items",
            dataset_key="demo",
        )


def test_source_resolution_checked_on_requires_iso_date():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="ISO calendar date",
    ):
        sr._validate_checked_on(
            {"checked_on": "not-a-date"},
            dataset_key="demo",
        )


def test_source_resolution_rights_require_known_states():
    payload = {
        "rights": {
            "analysis_use_terms_status": "invented",
            "raw_data_redistribution_terms_status": "unresolved",
            "license_inference_permitted": False,
        }
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="rights must use",
    ):
        sr._validate_rights(
            payload,
            dataset_key="demo",
        )


def test_source_resolution_rights_forbid_license_inference():
    payload = {
        "rights": {
            "analysis_use_terms_status": "unresolved",
            "raw_data_redistribution_terms_status": "unresolved",
            "license_inference_permitted": True,
        }
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot infer",
    ):
        sr._validate_rights(
            payload,
            dataset_key="demo",
        )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (
            ("record_type",),
            "wrong",
        ),
        (
            ("dataset",),
            "wrong",
        ),
        (
            ("status",),
            "wrong",
        ),
        (
            ("empirical_evidence_created",),
            False,
        ),
        (
            ("source_audit_ready",),
            True,
        ),
    ],
)
def test_source_resolution_common_state_guards(
    path,
    value,
):
    payload = _json(H2_PATH)

    _set_path(
        payload,
        path,
        value,
    )

    with pytest.raises(BenchmarkIntegrityError):
        sr._validate_common(
            payload,
            dataset=sr._HOLLYWOOD2_DATASET,
            dataset_key="hollywood2em",
        )


def test_source_resolution_common_claim_limits_required():
    payload = _json(H2_PATH)

    payload["claim_limits"] = []

    with pytest.raises(BenchmarkIntegrityError):
        sr._validate_common(
            payload,
            dataset=sr._HOLLYWOOD2_DATASET,
            dataset_key="hollywood2em",
        )


def test_source_resolution_common_next_actions_required():
    payload = _json(H2_PATH)

    payload["next_required_actions"] = []

    with pytest.raises(BenchmarkIntegrityError):
        sr._validate_common(
            payload,
            dataset=sr._HOLLYWOOD2_DATASET,
            dataset_key="hollywood2em",
        )


def test_source_resolution_common_rights_must_remain_unresolved():
    payload = _json(H2_PATH)

    payload["rights"]["analysis_use_terms_status"] = "verified"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="separately unresolved",
    ):
        sr._validate_common(
            payload,
            dataset=sr._HOLLYWOOD2_DATASET,
            dataset_key="hollywood2em",
        )


def test_optional_source_fingerprint_can_be_absent():
    sr._verify_optional_fingerprint(
        {},
        "a" * 64,
    )


def test_optional_source_fingerprint_must_be_hex():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="64 hexadecimal",
    ):
        sr._verify_optional_fingerprint(
            {"record_fingerprint_sha256": "bad"},
            "a" * 64,
        )


def test_optional_source_fingerprint_must_match():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not match",
    ):
        sr._verify_optional_fingerprint(
            {"record_fingerprint_sha256": "b" * 64},
            "a" * 64,
        )


@pytest.mark.parametrize(
    "key",
    [
        "article_cc_by_is_dataset_license",
        "repository_license_file_recovered",
        "dataset_specific_license_verified",
        "open_source_description_is_exact_license_text",
    ],
)
def test_hollywood_rights_promotion_is_forbidden(
    key,
):
    rights = _json(H2_PATH)["rights"]

    rights[key] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        sr._require_hollywood2_rights(rights)


# =====================================================================
# HOLLYWOOD2 SOURCE-RESOLUTION DEEP CONTRACT
# =====================================================================


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (
            ("canonical_distribution_identifier_found",),
            False,
        ),
        (
            ("current_retrievable_copy_verified",),
            False,
        ),
        (
            ("supersedes",),
            "wrong.json",
        ),
        (
            (
                "authoritative_repository",
                "url",
            ),
            "https://example.invalid",
        ),
        (
            (
                "authoritative_ground_truth",
                "file_count",
            ),
            0,
        ),
        (
            (
                "authoritative_ground_truth",
                "source_identity_ledger_fingerprint_sha256",
            ),
            "0" * 64,
        ),
        (
            (
                "authoritative_ground_truth",
                "schema_signature_sha256",
            ),
            "0" * 64,
        ),
        (
            (
                "authoritative_ground_truth",
                "schema_uniform_across_all_files",
            ),
            False,
        ),
        (
            (
                "authoritative_ground_truth",
                "final_label_counts",
            ),
            {},
        ),
        (
            (
                "authoritative_ground_truth",
                "student_vs_expert_corrected",
            ),
            [],
        ),
        (
            (
                "authoritative_ground_truth",
                "student_vs_expert_corrected",
                "sample_count",
            ),
            1,
        ),
        (
            (
                "authoritative_ground_truth",
                "student_vs_expert_corrected",
                "changed_sample_count",
            ),
            1,
        ),
        (
            (
                "authoritative_ground_truth",
                "student_vs_expert_corrected",
                "raw_agreement_fraction",
            ),
            0.0,
        ),
        (
            (
                "authoritative_ground_truth",
                "student_vs_expert_corrected",
                "interpretation",
            ),
            "ordinary reliability",
        ),
        (
            (
                "format_and_units",
                "arff_relation",
            ),
            "wrong",
        ),
        (
            (
                "format_and_units",
                "attributes",
            ),
            [],
        ),
        (
            (
                "format_and_units",
                "time_unit",
            ),
            "seconds",
        ),
        (
            (
                "format_and_units",
                "coordinate_unit_verified",
            ),
            False,
        ),
        (
            (
                "format_and_units",
                "time_unit_verified",
            ),
            False,
        ),
        (
            (
                "mapping",
                "trial_clip_identity_file_bound",
            ),
            False,
        ),
        (
            (
                "mapping",
                "file_subject_tokens",
            ),
            [],
        ),
        (
            (
                "mapping",
                "participant_identity_mapping_verified",
            ),
            True,
        ),
        (
            ("evidence",),
            {},
        ),
    ],
)
def test_hollywood_source_resolution_deep_guards(
    tmp_path,
    path,
    value,
):
    payload = _json(H2_PATH)

    _set_path(
        payload,
        path,
        value,
    )

    source = _write_json(
        tmp_path,
        payload,
        name="hollywood.json",
    )

    with pytest.raises(BenchmarkIntegrityError):
        sr.validate_hollywood2_source_resolution_record(source)


def test_hollywood_source_resolution_valid_baseline():
    result = sr.validate_hollywood2_source_resolution_record(H2_PATH)

    assert result["dataset_key"] == "hollywood2em"
    assert result["empirical_evidence_created"] is True


# =====================================================================
# GAZE-IN-THE-WILD SOURCE-RESOLUTION DEEP CONTRACT
# =====================================================================


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (
            ("published_distribution_identifier_found",),
            False,
        ),
        (
            ("current_institutional_dataset_listing_found",),
            False,
        ),
        (
            ("current_direct_data_endpoint_verified",),
            True,
        ),
        (
            (
                "authoritative_publication",
                "doi",
            ),
            "wrong",
        ),
        (
            (
                "authoritative_publication",
                "article_license_is_dataset_license",
            ),
            True,
        ),
        (
            (
                "rights",
                "article_cc_by_is_dataset_license",
            ),
            True,
        ),
        (
            (
                "rights",
                "publication_public_availability_is_unrestricted_redistribution_permission",
            ),
            True,
        ),
        (
            (
                "annotation_provenance",
                "published_trained_annotator_count",
            ),
            4,
        ),
        (
            (
                "annotation_provenance",
                "publication_states_annotators_decided_independently",
            ),
            False,
        ),
        (
            (
                "annotation_provenance",
                "publication_independence_evidence_present",
            ),
            False,
        ),
        (
            (
                "annotation_provenance",
                "separately_recoverable_streams_verified_from_exact_copy",
            ),
            True,
        ),
        (
            (
                "annotation_provenance",
                "human_human_agreement_execution_ready",
            ),
            True,
        ),
        (
            (
                "sampling_rate_provenance",
                "published_acquisition_hardware_rate_hz",
            ),
            100,
        ),
        (
            (
                "sampling_rate_provenance",
                "secondary_evaluation_catalog_rate_hz",
            ),
            100,
        ),
        (
            (
                "sampling_rate_provenance",
                "rates_reconciled",
            ),
            True,
        ),
        (
            (
                "sampling_rate_provenance",
                "distributed_file_analysis_cadence_verified",
            ),
            True,
        ),
        (
            (
                "sampling_rate_provenance",
                "required_resolution_method",
            ),
            "manual inspection",
        ),
        (
            (
                "mapping_and_coordinates",
                "participant_task_mapping_verified_from_exact_copy",
            ),
            True,
        ),
        (
            (
                "mapping_and_coordinates",
                "point_of_regard_coordinate_unit_verified_from_exact_copy",
            ),
            True,
        ),
        (
            (
                "mapping_and_coordinates",
                "verification_requires_exact_obtained_copy",
            ),
            False,
        ),
    ],
)
def test_giw_source_resolution_deep_guards(
    tmp_path,
    path,
    value,
):
    payload = _json(GIW_PATH)

    _set_path(
        payload,
        path,
        value,
    )

    source = _write_json(
        tmp_path,
        payload,
        name="giw.json",
    )

    with pytest.raises(BenchmarkIntegrityError):
        sr.validate_gaze_in_wild_source_resolution_record(source)


def test_giw_source_resolution_valid_baseline():
    result = sr.validate_gaze_in_wild_source_resolution_record(GIW_PATH)

    assert result["dataset_key"] == "gaze-in-the-wild"
    assert result["empirical_evidence_created"] is False


# =====================================================================
# UNIFIED SOURCE-RESOLUTION ROUTING/BUNDLE
# =====================================================================


def test_source_resolution_dispatch_rejects_wrong_record_type(
    tmp_path,
):
    payload = _json(H2_PATH)

    payload["record_type"] = "wrong"

    source = _write_json(
        tmp_path,
        payload,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record_type",
    ):
        sr.validate_source_resolution_record(source)


def test_source_resolution_dispatch_rejects_unknown_dataset(
    tmp_path,
):
    payload = _json(H2_PATH)

    payload["dataset"] = "Unreviewed Dataset"

    source = _write_json(
        tmp_path,
        payload,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Unsupported",
    ):
        sr.validate_source_resolution_record(source)


def test_source_resolution_dispatches_hollywood_and_giw():
    hollywood = sr.validate_source_resolution_record(H2_PATH)

    giw = sr.validate_source_resolution_record(GIW_PATH)

    assert hollywood["dataset_key"] == "hollywood2em"
    assert giw["dataset_key"] == "gaze-in-the-wild"


def test_source_resolution_visus_status_guard(
    tmp_path,
    monkeypatch,
):
    payload = _json(VISUS_PATH)

    source = _write_json(
        tmp_path,
        payload,
        name="visus.json",
    )

    monkeypatch.setattr(
        sr,
        "validate_visus_source_resolution_record",
        lambda path: {
            "status": "wrong",
            "dataset": sr._VISUS_DATASET,
        },
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="VISUS",
    ):
        sr.validate_source_resolution_record(source)


def test_source_resolution_bundle_requires_paths():
    with pytest.raises(
        ValueError,
        match="At least one",
    ):
        sr.validate_source_resolution_records([])


def test_source_resolution_bundle_rejects_duplicate_dataset():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="duplicate",
    ):
        sr.validate_source_resolution_records(
            [
                H2_PATH,
                H2_PATH,
            ]
        )


def test_source_resolution_bundle_valid_three_dataset_contract():
    result = sr.validate_source_resolution_records(
        [
            VISUS_PATH,
            H2_PATH,
            GIW_PATH,
        ]
    )

    assert result["record_count"] == 3

    assert {item["dataset_key"] for item in result["records"]} == {
        "visus",
        "hollywood2em",
        "gaze-in-the-wild",
    }

    assert len(result["bundle_fingerprint_sha256"]) == 64


def test_source_resolution_typed_loader():
    result = sr.load_source_resolution_record(H2_PATH)

    assert result.dataset_key == "hollywood2em"
    assert result.path == H2_PATH
