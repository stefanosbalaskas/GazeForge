import hashlib
from pathlib import Path
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from gazeforge.dynamic_aoi import DynamicAOIKeyframe, detect_dynamic_aois
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError
from gazeforge.grounded_sam2 import (
    GroundedSAM2Config,
    GroundedSAM2Detection,
    GroundedSAM2DynamicAOIProvider,
    grounded_sam2_to_visus_prediction_table,
    run_grounded_sam2_dynamic_aoi,
    validate_grounded_sam2_run,
)


GROUNDING_REVISION = "1" * 40
SAM2_REVISION = "2" * 40


class _FakeRuntime:
    def __init__(self, *, detections=None, segments=None):
        self._detections = detections
        self._segments = segments
        self.prompt_text = None
        self.prompt_position = None

    def detect(self, image_path, prompt_text, config):
        del image_path, config
        self.prompt_text = prompt_text
        if self._detections is not None:
            return self._detections
        return [
            GroundedSAM2Detection(
                label="white car",
                score=0.80,
                box_xyxy=(2.0, 2.0, 5.0, 5.0),
            ),
            GroundedSAM2Detection(
                label="red car",
                score=0.90,
                box_xyxy=(0.0, 0.0, 3.0, 3.0),
            ),
        ]

    def propagate(self, frame_dir, seeds, *, prompt_position, config):
        del frame_dir, config
        self.prompt_position = prompt_position
        if self._segments is not None:
            return self._segments
        result = {}
        for frame_position in range(3):
            objects = {}
            for seed in seeds:
                mask = np.zeros((8, 8), dtype=bool)
                if seed.label == "Red Car":
                    mask[1:4, frame_position : frame_position + 3] = True
                else:
                    mask[3:6, 2 + frame_position : 5 + frame_position] = True
                objects[seed.object_id] = mask
            result[frame_position] = objects
        return result

    def runtime_metadata(self):
        return {"runtime": "fake", "version": "1"}


def _fixture(tmp_path: Path, *, frame_index_base: int = 0):
    frame_dir = tmp_path / "frames"
    frame_dir.mkdir()
    for offset in range(3):
        index = frame_index_base + offset
        (frame_dir / f"{index}.jpg").write_bytes(b"jpeg-fixture-" + bytes([index]))
    checkpoint = tmp_path / "sam2.1_hiera_small.pt"
    checkpoint.write_bytes(b"sam2-checkpoint-fixture")
    checkpoint_sha = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    source_video = tmp_path / "stimulus.mp4"
    source_video.write_bytes(b"source-video-fixture")
    source_video_sha = hashlib.sha256(source_video.read_bytes()).hexdigest()
    config = GroundedSAM2Config(
        grounding_model_id="IDEA-Research/grounding-dino-tiny",
        grounding_model_revision=GROUNDING_REVISION,
        sam2_model_cfg="configs/sam2.1/sam2.1_hiera_s.yaml",
        sam2_checkpoint_path=checkpoint,
        sam2_checkpoint_sha256=checkpoint_sha,
        sam2_code_revision=SAM2_REVISION,
        source_video_path=source_video,
        source_video_sha256=source_video_sha,
        frame_extraction_basis="Fixture frames decoded from the exact source video.",
        frame_rate_hz=25.0,
        frame_index_base=frame_index_base,
        prompt_frame_index=frame_index_base,
        device="cpu",
        local_files_only=True,
    )
    return frame_dir, checkpoint, config


def _run(tmp_path: Path, *, runtime=None, frame_index_base: int = 0):
    frame_dir, _, config = _fixture(tmp_path, frame_index_base=frame_index_base)
    selected = _FakeRuntime() if runtime is None else runtime
    run = run_grounded_sam2_dynamic_aoi(
        frame_dir,
        labels=["Red Car", "White Car"],
        config=config,
        runtime=selected,
    )
    return run, selected


def test_grounded_sam2_fake_runtime_produces_canonical_tracks(tmp_path):
    run, runtime = _run(tmp_path)

    assert runtime.prompt_text == "red car. white car."
    assert runtime.prompt_position == 0
    assert len(run.canonical) == 6
    assert run.canonical["aoi_id"].nunique() == 2
    assert run.canonical["timestamp_ms"].tolist() == [0.0, 40.0, 80.0, 0.0, 40.0, 80.0]
    assert set(run.canonical["label"]) == {"Red Car", "White Car"}
    assert run.report["output"]["mask_resolution_px"] == [8, 8]
    assert run.report["evaluation_timestamp_grid_generated"] is False
    assert run.report["empirical_performance_claim_created"] is False
    assert run.report["visus_source_authority_implied"] is False
    assert len(run.keyframes) == 6
    assert all(isinstance(item, DynamicAOIKeyframe) for item in run.keyframes)
    assert all(item.source == "model" for item in run.keyframes)


def test_grounded_sam2_provider_implements_existing_dynamic_aoi_contract(tmp_path):
    frame_dir, _, config = _fixture(tmp_path)
    runtime = _FakeRuntime()
    provider = GroundedSAM2DynamicAOIProvider(config=config, runtime=runtime)

    keyframes = detect_dynamic_aois(
        frame_dir,
        labels=["Red Car", "White Car"],
        provider=provider,
        min_confidence=0.0,
    )

    assert len(keyframes) == 6
    assert provider.last_run is not None
    assert provider.model_name == "Grounding DINO + SAM 2"
    assert GROUNDING_REVISION in provider.model_version
    assert SAM2_REVISION in provider.model_version


def test_grounded_sam2_seed_order_is_deterministic(tmp_path):
    run, _ = _run(tmp_path)
    seeds = run.report["detections"]["seeds"]
    assert [item["label"] for item in seeds] == ["Red Car", "White Car"]
    assert [item["object_id"] for item in seeds] == [1, 2]
    assert [item["aoi_id"] for item in seeds] == [
        "grounded-sam2:red-car:1",
        "grounded-sam2:white-car:1",
    ]


def test_grounded_sam2_export_matches_visus_prediction_schema(tmp_path):
    run, _ = _run(tmp_path)
    table = grounded_sam2_to_visus_prediction_table(run, stimulus_id="S01")

    assert list(table.columns) == [
        "stimulus_id",
        "frame_index",
        "aoi_id",
        "label",
        "xmin",
        "ymin",
        "xmax",
        "ymax",
        "confidence",
    ]
    assert set(table["stimulus_id"]) == {"S01"}


def test_grounded_sam2_supports_explicit_one_based_frames(tmp_path):
    run, runtime = _run(tmp_path, frame_index_base=1)
    assert runtime.prompt_position == 0
    assert run.canonical["frame_index"].min() == 1
    assert run.canonical["timestamp_ms"].min() == pytest.approx(0.0)
    assert run.canonical["timestamp_ms"].max() == pytest.approx(80.0)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("grounding_model_revision", "main", "immutable 40-character"),
        ("sam2_code_revision", "v2.1", "immutable 40-character"),
        ("sam2_checkpoint_sha256", "bad", "64-character"),
    ],
)
def test_grounded_sam2_rejects_mutable_or_invalid_model_identity(
    tmp_path,
    field,
    value,
    message,
):
    frame_dir, _, config = _fixture(tmp_path)
    broken = replace(config, **{field: value})
    with pytest.raises(ValueError, match=message):
        run_grounded_sam2_dynamic_aoi(
            frame_dir,
            labels=["Red Car"],
            config=broken,
            runtime=_FakeRuntime(),
        )


def test_grounded_sam2_rejects_checkpoint_byte_drift(tmp_path):
    frame_dir, checkpoint, config = _fixture(tmp_path)
    checkpoint.write_bytes(b"changed-checkpoint")
    with pytest.raises(BenchmarkIntegrityError, match="checkpoint SHA-256"):
        run_grounded_sam2_dynamic_aoi(
            frame_dir,
            labels=["Red Car"],
            config=config,
            runtime=_FakeRuntime(),
        )


def test_grounded_sam2_rejects_source_video_byte_drift(tmp_path):
    frame_dir, _, config = _fixture(tmp_path)
    Path(config.source_video_path).write_bytes(b"changed-source-video")
    with pytest.raises(BenchmarkIntegrityError, match="Source-video SHA-256"):
        run_grounded_sam2_dynamic_aoi(
            frame_dir,
            labels=["Red Car"],
            config=config,
            runtime=_FakeRuntime(),
        )


def test_grounded_sam2_requires_numeric_contiguous_frame_identity(tmp_path):
    frame_dir, _, config = _fixture(tmp_path)
    (frame_dir / "2.jpg").rename(frame_dir / "3.jpg")
    with pytest.raises(SchemaError, match="contiguous"):
        run_grounded_sam2_dynamic_aoi(
            frame_dir,
            labels=["Red Car"],
            config=config,
            runtime=_FakeRuntime(),
        )

    (frame_dir / "3.jpg").rename(frame_dir / "frame-three.jpg")
    with pytest.raises(SchemaError, match="integer indices"):
        run_grounded_sam2_dynamic_aoi(
            frame_dir,
            labels=["Red Car"],
            config=config,
            runtime=_FakeRuntime(),
        )


def test_grounded_sam2_rejects_detector_label_outside_prompt(tmp_path):
    detection = GroundedSAM2Detection("bus", 0.9, (0.0, 0.0, 3.0, 3.0))
    runtime = _FakeRuntime(detections=[detection])
    frame_dir, _, config = _fixture(tmp_path)
    with pytest.raises(SchemaError, match="outside the requested semantic prompt"):
        run_grounded_sam2_dynamic_aoi(
            frame_dir,
            labels=["Red Car"],
            config=config,
            runtime=runtime,
        )


def test_grounded_sam2_rejects_invalid_detection_geometry_and_score(tmp_path):
    frame_dir, _, config = _fixture(tmp_path)
    bad_box = _FakeRuntime(
        detections=[GroundedSAM2Detection("red car", 0.9, (3.0, 0.0, 2.0, 3.0))]
    )
    with pytest.raises(SchemaError, match="invalid xyxy geometry"):
        run_grounded_sam2_dynamic_aoi(
            frame_dir,
            labels=["Red Car"],
            config=config,
            runtime=bad_box,
        )

    bad_score = _FakeRuntime(
        detections=[GroundedSAM2Detection("red car", 1.1, (0.0, 0.0, 2.0, 3.0))]
    )
    with pytest.raises(SchemaError, match="scores must lie"):
        run_grounded_sam2_dynamic_aoi(
            frame_dir,
            labels=["Red Car"],
            config=config,
            runtime=bad_score,
        )


def test_grounded_sam2_rejects_unseeded_object_and_frame_position(tmp_path):
    mask = np.ones((8, 8), dtype=bool)
    frame_dir, _, config = _fixture(tmp_path)
    unseeded = _FakeRuntime(
        detections=[GroundedSAM2Detection("red car", 0.9, (0.0, 0.0, 3.0, 3.0))],
        segments={0: {99: mask}},
    )
    with pytest.raises(SchemaError, match="not detector-seeded"):
        run_grounded_sam2_dynamic_aoi(
            frame_dir,
            labels=["Red Car"],
            config=config,
            runtime=unseeded,
        )

    outside = _FakeRuntime(
        detections=[GroundedSAM2Detection("red car", 0.9, (0.0, 0.0, 3.0, 3.0))],
        segments={3: {1: mask}},
    )
    with pytest.raises(SchemaError, match="outside the input ledger"):
        run_grounded_sam2_dynamic_aoi(
            frame_dir,
            labels=["Red Car"],
            config=config,
            runtime=outside,
        )


def test_grounded_sam2_rejects_mask_geometry_drift(tmp_path):
    frame_dir, _, config = _fixture(tmp_path)
    runtime = _FakeRuntime(
        detections=[GroundedSAM2Detection("red car", 0.9, (0.0, 0.0, 3.0, 3.0))],
        segments={
            0: {1: np.ones((8, 8), dtype=bool)},
            1: {1: np.ones((9, 8), dtype=bool)},
        },
    )
    with pytest.raises(SchemaError, match="one frame geometry"):
        run_grounded_sam2_dynamic_aoi(
            frame_dir,
            labels=["Red Car"],
            config=config,
            runtime=runtime,
        )


def test_grounded_sam2_skips_empty_masks_but_not_all_output(tmp_path):
    frame_dir, _, config = _fixture(tmp_path)
    runtime = _FakeRuntime(
        detections=[GroundedSAM2Detection("red car", 0.9, (0.0, 0.0, 3.0, 3.0))],
        segments={
            0: {1: np.zeros((8, 8), dtype=bool)},
            1: {1: np.eye(8, dtype=bool)},
        },
    )
    run = run_grounded_sam2_dynamic_aoi(
        frame_dir,
        labels=["Red Car"],
        config=config,
        runtime=runtime,
    )
    assert len(run.canonical) == 1
    assert run.report["output"]["empty_or_too_small_masks_skipped"] == 1

    all_empty = _FakeRuntime(
        detections=[GroundedSAM2Detection("red car", 0.9, (0.0, 0.0, 3.0, 3.0))],
        segments={0: {1: np.zeros((8, 8), dtype=bool)}},
    )
    with pytest.raises(BenchmarkIntegrityError, match="no non-empty AOI masks"):
        run_grounded_sam2_dynamic_aoi(
            frame_dir,
            labels=["Red Car"],
            config=config,
            runtime=all_empty,
        )


def test_grounded_sam2_run_validation_rejects_prediction_tamper(tmp_path):
    run, _ = _run(tmp_path)
    validate_grounded_sam2_run(run)
    run.canonical.loc[0, "xmin"] = 777.0
    with pytest.raises(BenchmarkIntegrityError, match="canonical output fingerprint"):
        validate_grounded_sam2_run(run)
    with pytest.raises(BenchmarkIntegrityError, match="canonical output fingerprint"):
        grounded_sam2_to_visus_prediction_table(run, stimulus_id="S01")


def test_grounded_sam2_run_validation_rejects_claim_promotion(tmp_path):
    run, _ = _run(tmp_path)
    run.report["empirical_performance_claim_created"] = True
    with pytest.raises(BenchmarkIntegrityError, match="not empirical validity"):
        validate_grounded_sam2_run(run)


def test_grounded_sam2_confidence_is_explicitly_seed_not_frame_confidence(tmp_path):
    run, _ = _run(tmp_path)
    semantics = run.report["confidence_semantics"]
    assert "seed-detection score" in semantics
    assert "not a per-frame SAM 2 confidence" in semantics
    assert np.allclose(run.canonical["confidence"], run.canonical["seed_detection_confidence"])
    assert isinstance(run.canonical, pd.DataFrame)
