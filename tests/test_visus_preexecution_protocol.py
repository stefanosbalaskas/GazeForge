import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError
from gazeforge.grounded_sam2 import GroundedSAM2Config, GroundedSAM2Detection
from gazeforge.video_frame_derivation import (
    FrameExtractionExecution,
    FrameExtractorIdentity,
    VideoFrameDerivationConfig,
    derive_video_frames,
)
from gazeforge.visus_audit import (
    VisusSourceAuditSpec,
    VisusSourceFileRecord,
    audit_visus_source,
)
from gazeforge.visus_preexecution_protocol import (
    VisusGroundedSAM2StimulusPlan,
    bind_grounded_sam2_to_preexecution_protocol,
    build_visus_grounded_sam2_preexecution_protocol,
    freeze_visus_grounded_sam2_preexecution_protocol,
    load_visus_grounded_sam2_preexecution_protocol,
    replay_visus_grounded_sam2_preexecution_protocol,
    run_grounded_sam2_from_preexecution_protocol,
    validation_settings_from_preexecution_protocol,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(root: Path, relative: str) -> tuple[str, int]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"fixture:{relative}\n", encoding="utf-8")
    payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest(), len(payload)


def _record(
    root: Path,
    *,
    path: str,
    role: str,
    stimulus_id: str,
    participant_id: str | None = None,
    annotation_stream_id: str | None = None,
) -> VisusSourceFileRecord:
    digest, size = _write(root, path)
    return VisusSourceFileRecord(
        path=path,
        sha256=digest,
        bytes=size,
        role=role,
        stimulus_id=stimulus_id,
        participant_id=participant_id,
        annotation_stream_id=annotation_stream_id,
    )


def _audit(root: Path):
    stimuli = [f"S{index:02d}" for index in range(1, 12)]
    files: list[VisusSourceFileRecord] = []
    for stimulus in stimuli:
        files.append(
            _record(
                root,
                path=f"video/{stimulus}.avi",
                role="video",
                stimulus_id=stimulus,
            )
        )
        files.append(
            _record(
                root,
                path=f"aoi/{stimulus}.xml",
                role="aoi_annotation",
                stimulus_id=stimulus,
                annotation_stream_id="published_curated",
            )
        )
    for index in range(1, 26):
        participant = f"P{index:02d}"
        stimulus = stimuli[(index - 1) % len(stimuli)]
        files.append(
            _record(
                root,
                path=f"gaze/{participant}-{stimulus}.tsv",
                role="gaze",
                stimulus_id=stimulus,
                participant_id=participant,
            )
        )

    spec = VisusSourceAuditSpec(
        dataset_name="VISUS",
        dataset_version="preexecution-fixture",
        source="https://example.invalid/visus",
        source_revision="fixture-snapshot",
        license="Reviewed fixture terms.",
        reuse_terms_source="https://example.invalid/terms",
        dataset_status="empirical",
        reuse_terms_verified=True,
        analysis_use_permitted=True,
        redistribution_status="restricted",
        stimulus_mapping_verified=True,
        stimulus_mapping_basis="Fixture stimulus manifest.",
        participant_mapping_verified=True,
        participant_mapping_basis="Fixture participant manifest.",
        coordinate_unit="pixels",
        coordinate_unit_verified=True,
        coordinate_verification_basis="Fixture coordinate documentation.",
        timestamp_basis_verified=True,
        timestamp_verification_basis="Fixture frame-time documentation.",
        files=files,
    )
    return audit_visus_source(root, spec)


class _FakeExtractor:
    def __init__(self, artifact: Path):
        self.artifact = artifact

    def identify(self):
        return FrameExtractorIdentity(
            name="fixture-extractor",
            version="fixture-extractor 1.0",
            artifact_path=str(self.artifact),
            artifact_sha256=_sha(self.artifact),
        )

    def extract(
        self,
        source_video,
        output_dir,
        *,
        frame_index_base,
        jpeg_quality,
    ):
        for offset in range(2):
            index = frame_index_base + offset
            (output_dir / f"{index:06d}.jpg").write_bytes(
                f"{source_video.name}:{index}:jpeg\n".encode()
            )
        return FrameExtractionExecution(
            argv=(
                str(self.artifact),
                "--fixture-extract",
                str(source_video),
                str(output_dir),
                str(frame_index_base),
                str(jpeg_quality),
            ),
            returncode=0,
            stdout="fixture extraction complete\n",
            stderr="",
        )


class _FakeRuntime:
    def __init__(self):
        self.detect_calls = 0
        self.propagate_calls = 0

    def detect(self, image_path, prompt_text, config):
        self.detect_calls += 1
        labels = [
            token.strip().rstrip(".")
            for token in prompt_text.split(".")
            if token.strip()
        ]
        return [
            GroundedSAM2Detection(
                label=label,
                score=0.9 - 0.05 * index,
                box_xyxy=(1.0 + index, 1.0, 4.0 + index, 4.0),
            )
            for index, label in enumerate(labels)
        ]

    def propagate(self, frame_dir, seeds, *, prompt_position, config):
        self.propagate_calls += 1
        result = {}
        for position in range(2):
            by_object = {}
            for seed in seeds:
                mask = np.zeros((8, 8), dtype=bool)
                start = min(seed.object_id, 4)
                mask[start : start + 2, start : start + 2] = True
                by_object[seed.object_id] = mask
            result[position] = by_object
        return result

    def runtime_metadata(self):
        return {
            "runtime": "fixture",
            "transformers_version": "fixture",
            "torch_version": "fixture",
            "sam2_version": "fixture",
        }


def _fixture(tmp_path: Path):
    source_root = tmp_path / "source"
    source_root.mkdir()
    audit = _audit(source_root)

    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    artifact = runtime_root / "fixture-extractor.bin"
    artifact.write_bytes(b"fixture extractor executable\n")
    extractor = _FakeExtractor(artifact)

    checkpoint = runtime_root / "sam2-fixture.pt"
    checkpoint.write_bytes(b"fixture sam2 checkpoint\n")
    checkpoint_sha = _sha(checkpoint)

    audited_videos = {
        str(item.record.stimulus_id): item
        for item in audit.files
        if item.record.role == "video"
    }
    plans = {}
    for index in range(1, 12):
        stimulus = f"S{index:02d}"
        video_item = audited_videos[stimulus]
        output = tmp_path / "frames" / stimulus
        derivation = derive_video_frames(
            VideoFrameDerivationConfig(
                source_video_path=video_item.local_path,
                source_video_sha256=video_item.record.sha256,
                output_dir=output,
                expected_extractor_name="fixture-extractor",
                expected_extractor_version="fixture-extractor 1.0",
                expected_extractor_sha256=_sha(artifact),
                frame_index_base=0,
                jpeg_quality=2,
            ),
            extractor=extractor,
        )
        config = GroundedSAM2Config(
            grounding_model_id="IDEA-Research/grounding-dino-tiny",
            grounding_model_revision="1" * 40,
            sam2_model_cfg="configs/sam2.1/sam2.1_hiera_s.yaml",
            sam2_checkpoint_path=checkpoint,
            sam2_checkpoint_sha256=checkpoint_sha,
            sam2_code_revision="2" * 40,
            source_video_path=video_item.local_path,
            source_video_sha256=video_item.record.sha256,
            frame_extraction_basis=(
                "GazeForge mechanically verified video-frame derivation "
                + derivation.report["report_fingerprint_sha256"]
            ),
            frame_rate_hz=25.0,
            frame_index_base=0,
            prompt_frame_index=0,
            box_threshold=0.25,
            text_threshold=0.30,
            device="cpu",
            local_files_only=True,
            min_mask_pixels=1,
        )
        labels = ("person", "red car") if index == 1 else (f"object {index}",)
        plans[stimulus] = VisusGroundedSAM2StimulusPlan(
            stimulus_id=stimulus,
            labels=labels,
            config=config,
            derivation=derivation,
        )

    timestamps = {f"S{index:02d}": [0.0, 40.0] for index in range(1, 12)}
    return audit, plans, timestamps, checkpoint


def _build(audit, plans, timestamps, **kwargs):
    options = {
        "reference_stream_id": "published_curated",
        "timestamp_grid_basis": "Fixed audited 25 Hz video-frame grid.",
        "max_interpolation_gap_ms": 80.0,
        "min_iou": 0.50,
        "require_label_match": True,
        "fixation_assignment_planned": False,
        "overlap_rule": "highest_confidence",
    }
    options.update(kwargs)
    return build_visus_grounded_sam2_preexecution_protocol(
        audit,
        plans,
        timestamps,
        **options,
    )


def _freeze(tmp_path, audit, plans, timestamps, **kwargs):
    options = {
        "reference_stream_id": "published_curated",
        "timestamp_grid_basis": "Fixed audited 25 Hz video-frame grid.",
        "max_interpolation_gap_ms": 80.0,
        "min_iou": 0.50,
        "require_label_match": True,
        "fixation_assignment_planned": False,
        "overlap_rule": "highest_confidence",
    }
    options.update(kwargs)
    return freeze_visus_grounded_sam2_preexecution_protocol(
        audit,
        plans,
        timestamps,
        tmp_path / "protocol.json",
        **options,
    )


def test_protocol_freezes_complete_model_and_evaluation_plan(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    protocol = _build(audit, plans, timestamps)

    assert protocol["status"] == "frozen-pre-execution-protocol"
    assert len(protocol["stimuli"]) == 11
    assert protocol["stimuli"][0]["stimulus_id"] == "S01"
    assert protocol["stimuli"][0]["semantic_labels"] == ["person", "red car"]
    assert protocol["stimuli"][0]["prompt_text"] == "person. red car."
    assert protocol["global_model_policy"]["box_threshold"] == pytest.approx(0.25)
    assert protocol["evaluation"]["min_iou"] == pytest.approx(0.50)
    assert protocol["evaluation"]["prediction_emission_grid_used"] is False
    assert protocol["formal_preregistration_verified"] is False
    assert protocol["empirical_performance_claim_created"] is False
    assert protocol["dataset_source_authority_promoted"] is False
    assert protocol["dataset_rights_promoted"] is False


def test_protocol_fingerprint_is_deterministic(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    first = _build(audit, plans, timestamps)
    second = _build(audit, plans, timestamps)
    assert first == second
    assert first["protocol_fingerprint_sha256"] == second[
        "protocol_fingerprint_sha256"
    ]


def test_external_registration_metadata_does_not_promote_preregistration(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    protocol = _build(
        audit,
        plans,
        timestamps,
        external_registration_reference="https://osf.example/registration/fixture",
        external_registration_timestamp="2026-09-11T12:00:00+03:00",
    )
    registration = protocol["registration"]
    assert registration["external_registration_metadata_recorded"] is True
    assert registration["formal_preregistration_verified"] is False
    assert protocol["formal_preregistration_verified"] is False


@pytest.mark.parametrize(
    ("reference", "timestamp"),
    [
        ("https://osf.example/registration/fixture", None),
        (None, "2026-09-11T12:00:00+03:00"),
        ("https://osf.example/registration/fixture", "2026-09-11T12:00:00"),
    ],
)
def test_registration_requires_complete_timezone_aware_pair(
    tmp_path,
    reference,
    timestamp,
):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    with pytest.raises(ValueError):
        _build(
            audit,
            plans,
            timestamps,
            external_registration_reference=reference,
            external_registration_timestamp=timestamp,
        )


def test_protocol_requires_exact_plan_coverage(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    plans = dict(plans)
    plans.pop("S11")
    with pytest.raises(SchemaError, match="missing"):
        _build(audit, plans, timestamps)


def test_protocol_requires_plan_key_to_equal_explicit_stimulus(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    plans = dict(plans)
    plans["S01"] = replace(plans["S01"], stimulus_id="S02")
    with pytest.raises(SchemaError, match="mapping key"):
        _build(audit, plans, timestamps)


def test_protocol_blocks_per_stimulus_threshold_tuning(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    plans = dict(plans)
    drifted = replace(plans["S02"].config, box_threshold=0.40)
    plans["S02"] = replace(plans["S02"], config=drifted)
    with pytest.raises(BenchmarkIntegrityError, match="policy drift"):
        _build(audit, plans, timestamps)


def test_protocol_rejects_source_video_substitution(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    plans = dict(plans)
    substituted = replace(
        plans["S01"].config,
        source_video_path=plans["S02"].config.source_video_path,
        source_video_sha256=plans["S02"].config.source_video_sha256,
    )
    plans["S01"] = replace(plans["S01"], config=substituted)
    with pytest.raises(BenchmarkIntegrityError, match="source path"):
        _build(audit, plans, timestamps)


def test_protocol_requires_exact_derivation_basis(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    plans = dict(plans)
    changed = replace(
        plans["S01"].config,
        frame_extraction_basis="Narrative extraction statement only.",
    )
    plans["S01"] = replace(plans["S01"], config=changed)
    with pytest.raises(BenchmarkIntegrityError, match="frame_extraction_basis"):
        _build(audit, plans, timestamps)


def test_protocol_rejects_derived_frame_byte_drift(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frame = plans["S01"].derivation.frame_dir / "000000.jpg"
    frame.write_bytes(frame.read_bytes() + b"tamper")
    with pytest.raises(BenchmarkIntegrityError, match="output frame bytes"):
        _build(audit, plans, timestamps)


def test_protocol_rejects_checkpoint_byte_drift(tmp_path):
    audit, plans, timestamps, checkpoint = _fixture(tmp_path)
    checkpoint.write_bytes(checkpoint.read_bytes() + b"tamper")
    with pytest.raises(BenchmarkIntegrityError, match="checkpoint bytes"):
        _build(audit, plans, timestamps)


@pytest.mark.parametrize(
    "grid",
    [
        [],
        [0.0, 0.0],
        [40.0, 0.0],
        [0.0, float("nan")],
        [0.0, float("inf")],
    ],
)
def test_protocol_rejects_invalid_external_timestamp_grids(tmp_path, grid):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    timestamps = dict(timestamps)
    timestamps["S01"] = grid
    with pytest.raises(SchemaError):
        _build(audit, plans, timestamps)


def test_protocol_rejects_unmanifested_reference_stream(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    with pytest.raises(SchemaError, match="reference stream"):
        _build(
            audit,
            plans,
            timestamps,
            reference_stream_id="independent_annotator_2",
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_interpolation_gap_ms": -1.0},
        {"max_interpolation_gap_ms": float("nan")},
        {"min_iou": -0.01},
        {"min_iou": 1.01},
        {"overlap_rule": "largest_area"},
    ],
)
def test_protocol_rejects_invalid_evaluation_policy(tmp_path, kwargs):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    with pytest.raises(ValueError):
        _build(audit, plans, timestamps, **kwargs)


def test_freeze_and_load_revalidate_same_protocol(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    loaded = load_visus_grounded_sam2_preexecution_protocol(frozen.protocol_path)
    assert loaded.protocol == frozen.protocol
    assert loaded.protocol_fingerprint_sha256 == frozen.protocol_fingerprint_sha256


def test_protocol_file_tamper_is_rejected(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    payload = json.loads(frozen.protocol_path.read_text(encoding="utf-8"))
    payload["evaluation"]["min_iou"] = 0.75
    frozen.protocol_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        load_visus_grounded_sam2_preexecution_protocol(frozen.protocol_path)


def test_replay_rejects_current_plan_drift(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    changed = dict(plans)
    changed_config = replace(changed["S01"].config, text_threshold=0.45)
    changed["S01"] = replace(changed["S01"], config=changed_config)
    with pytest.raises(BenchmarkIntegrityError):
        replay_visus_grounded_sam2_preexecution_protocol(
            frozen,
            audit,
            changed,
            timestamps,
        )


def test_replay_accepts_exact_local_inputs(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    replay_visus_grounded_sam2_preexecution_protocol(
        frozen,
        audit,
        plans,
        timestamps,
    )


def test_validation_settings_are_recovered_exactly(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(
        tmp_path,
        audit,
        plans,
        timestamps,
        fixation_assignment_planned=True,
        overlap_rule="smallest_area",
    )
    settings = validation_settings_from_preexecution_protocol(frozen)
    assert settings["timestamps_by_stimulus"] == timestamps
    assert settings["reference_stream_id"] == "published_curated"
    assert settings["max_interpolation_gap_ms"] == pytest.approx(80.0)
    assert settings["min_iou"] == pytest.approx(0.50)
    assert settings["require_label_match"] is True
    assert settings["fixation_assignment_planned"] is True
    assert settings["overlap_rule"] == "smallest_area"


def test_protocol_bound_runner_validates_before_inference_and_binds_output(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    runtime = _FakeRuntime()

    result = run_grounded_sam2_from_preexecution_protocol(
        frozen,
        audit,
        plans["S01"],
        runtime=runtime,
    )

    assert runtime.detect_calls == 1
    assert runtime.propagate_calls == 1
    assert result.stimulus_id == "S01"
    assert result.protocol_binding["protocol_validated_before_backend_call"] is True
    assert result.protocol_binding["local_execution_order_verified"] is True
    assert result.protocol_binding["formal_preregistration_verified"] is False
    assert result.protocol_binding["empirical_performance_claim_created"] is False
    assert (
        result.protocol_binding["protocol_fingerprint_sha256"]
        == frozen.protocol_fingerprint_sha256
    )
    assert result.frame_derivation_binding["frame_derivation_mechanically_verified"] is True


def test_protocol_bound_runner_refuses_tampered_protocol_before_runtime_call(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    payload = json.loads(frozen.protocol_path.read_text(encoding="utf-8"))
    payload["stimuli"][0]["prompt_text"] = "changed."
    frozen.protocol_path.write_text(json.dumps(payload), encoding="utf-8")
    runtime = _FakeRuntime()

    with pytest.raises(BenchmarkIntegrityError):
        run_grounded_sam2_from_preexecution_protocol(
            frozen,
            audit,
            plans["S01"],
            runtime=runtime,
        )
    assert runtime.detect_calls == 0
    assert runtime.propagate_calls == 0


def test_binding_rejects_false_preexecution_order_claim(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    runtime = _FakeRuntime()
    result = run_grounded_sam2_from_preexecution_protocol(
        frozen,
        audit,
        plans["S01"],
        runtime=runtime,
    )
    with pytest.raises(BenchmarkIntegrityError, match="before the backend call"):
        bind_grounded_sam2_to_preexecution_protocol(
            frozen,
            audit,
            plans["S01"],
            result.backend_run,
            protocol_validated_before_backend_call=False,
        )


def test_registration_or_protocol_fields_cannot_self_promote_claims(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    payload = dict(frozen.protocol)
    payload["formal_preregistration_verified"] = True
    body = {
        key: value
        for key, value in payload.items()
        if key != "protocol_fingerprint_sha256"
    }
    payload["protocol_fingerprint_sha256"] = benchmark_fingerprint(body)
    frozen.protocol_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(BenchmarkIntegrityError, match="cannot promote"):
        load_visus_grounded_sam2_preexecution_protocol(frozen.protocol_path)
