import hashlib
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError
from gazeforge.grounded_sam2 import (
    GroundedSAM2Config,
    GroundedSAM2Detection,
)
from gazeforge.video_frame_derivation import (
    FFmpegJPEGFrameExtractor,
    FrameExtractionExecution,
    FrameExtractorIdentity,
    VideoFrameDerivationConfig,
    bind_grounded_sam2_frame_derivation,
    derive_video_frames,
    run_grounded_sam2_with_verified_frame_derivation,
    validate_video_frame_derivation_run,
)


class _FakeExtractor:
    def __init__(
        self,
        artifact: Path,
        *,
        n_frames: int = 3,
        returncode: int = 0,
        extra_file: bool = False,
        skipped_index: int | None = None,
    ) -> None:
        self.artifact = artifact
        self.n_frames = n_frames
        self.returncode = returncode
        self.extra_file = extra_file
        self.skipped_index = skipped_index
        self.version = "ffmpeg version fixture-1.0"

    def identify(self) -> FrameExtractorIdentity:
        payload = self.artifact.read_bytes()
        return FrameExtractorIdentity(
            name="ffmpeg",
            version=self.version,
            artifact_path=str(self.artifact),
            artifact_sha256=hashlib.sha256(payload).hexdigest(),
        )

    def extract(
        self,
        source_video: Path,
        output_dir: Path,
        *,
        frame_index_base: int,
        jpeg_quality: int,
    ) -> FrameExtractionExecution:
        for offset in range(self.n_frames):
            index = frame_index_base + offset
            if index == self.skipped_index:
                continue
            (output_dir / f"{index:06d}.jpg").write_bytes(
                b"derived-jpeg-fixture-" + bytes([offset])
            )
        if self.extra_file:
            (output_dir / "unexpected.txt").write_text("unexpected", encoding="utf-8")
        return FrameExtractionExecution(
            argv=(
                "fixture-ffmpeg",
                "-i",
                str(source_video),
                "-q:v",
                str(jpeg_quality),
                str(output_dir / "%06d.jpg"),
            ),
            returncode=self.returncode,
            stdout="fixture stdout",
            stderr="fixture stderr",
        )


class _FakeGroundedRuntime:
    def detect(self, image_path, prompt_text, config):
        del image_path, prompt_text, config
        return [
            GroundedSAM2Detection(
                label="red car",
                score=0.90,
                box_xyxy=(0.0, 0.0, 3.0, 3.0),
            )
        ]

    def propagate(self, frame_dir, seeds, *, prompt_position, config):
        del frame_dir, prompt_position, config
        result = {}
        for frame_position in range(3):
            mask = np.zeros((8, 8), dtype=bool)
            mask[1:4, frame_position : frame_position + 3] = True
            result[frame_position] = {seeds[0].object_id: mask}
        return result

    def runtime_metadata(self):
        return {"runtime": "fixture-grounded-runtime", "version": "1"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(
    tmp_path: Path,
    *,
    frame_index_base: int = 0,
    n_frames: int = 3,
    returncode: int = 0,
    extra_file: bool = False,
    skipped_index: int | None = None,
):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source-video-fixture")
    extractor_artifact = tmp_path / "ffmpeg-fixture"
    extractor_artifact.write_bytes(b"extractor-binary-fixture")
    extractor = _FakeExtractor(
        extractor_artifact,
        n_frames=n_frames,
        returncode=returncode,
        extra_file=extra_file,
        skipped_index=skipped_index,
    )
    identity = extractor.identify()
    derivation_config = VideoFrameDerivationConfig(
        source_video_path=source,
        source_video_sha256=_sha(source),
        output_dir=tmp_path / "derived-frames",
        expected_extractor_name=identity.name,
        expected_extractor_version=identity.version,
        expected_extractor_sha256=identity.artifact_sha256,
        frame_index_base=frame_index_base,
        jpeg_quality=2,
    )
    checkpoint = tmp_path / "sam2.1_hiera_small.pt"
    checkpoint.write_bytes(b"sam2-checkpoint-fixture")
    grounded_config = GroundedSAM2Config(
        grounding_model_id="IDEA-Research/grounding-dino-tiny",
        grounding_model_revision="1" * 40,
        sam2_model_cfg="configs/sam2.1/sam2.1_hiera_s.yaml",
        sam2_checkpoint_path=checkpoint,
        sam2_checkpoint_sha256=_sha(checkpoint),
        sam2_code_revision="2" * 40,
        source_video_path=source,
        source_video_sha256=_sha(source),
        frame_extraction_basis="Not yet mechanically verified.",
        frame_rate_hz=25.0,
        frame_index_base=frame_index_base,
        prompt_frame_index=frame_index_base,
        device="cpu",
        local_files_only=True,
    )
    return source, extractor_artifact, extractor, derivation_config, grounded_config


def test_video_frame_derivation_binds_source_tool_command_and_frames(tmp_path):
    source, artifact, extractor, config, _ = _fixture(tmp_path)
    run = derive_video_frames(config, extractor=extractor)

    assert run.source_video_path == source.resolve()
    assert run.frame_dir == Path(config.output_dir).resolve()
    assert run.report["frame_derivation_mechanically_verified"] is True
    assert run.report["empirical_performance_claim_created"] is False
    assert run.report["dataset_source_authority_implied"] is False
    assert run.report["dataset_rights_implied"] is False
    assert run.report["raw_source_redistribution_authorized"] is False
    assert run.report["source_video"]["sha256"] == _sha(source)
    assert run.report["extractor"]["artifact_sha256"] == _sha(artifact)
    assert run.report["execution"]["returncode"] == 0
    assert run.report["execution"]["argv"]
    assert run.report["frames"]["count"] == 3
    assert [row["frame_index"] for row in run.report["frames"]["manifest"]] == [0, 1, 2]
    validate_video_frame_derivation_run(run)


def test_video_frame_derivation_supports_explicit_one_based_frames(tmp_path):
    _, _, extractor, config, _ = _fixture(tmp_path, frame_index_base=1)
    run = derive_video_frames(config, extractor=extractor)

    assert run.report["frames"]["frame_index_base"] == 1
    assert run.report["frames"]["first_frame_index"] == 1
    assert run.report["frames"]["last_frame_index"] == 3


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("source_video_sha256", "bad", "64-character"),
        ("expected_extractor_sha256", "bad", "64-character"),
        ("expected_extractor_name", "VERIFY", "resolved"),
        ("frame_index_base", 2, "0 or 1"),
        ("jpeg_quality", 0, r"\[1, 31\]"),
        ("jpeg_quality", 32, r"\[1, 31\]"),
    ],
)
def test_video_frame_derivation_rejects_invalid_config(tmp_path, field, value, message):
    _, _, extractor, config, _ = _fixture(tmp_path)
    broken = replace(config, **{field: value})
    with pytest.raises(ValueError, match=message):
        derive_video_frames(broken, extractor=extractor)


def test_video_frame_derivation_rejects_source_byte_drift(tmp_path):
    source, _, extractor, config, _ = _fixture(tmp_path)
    source.write_bytes(b"changed-source-video")

    with pytest.raises(BenchmarkIntegrityError, match="Source-video SHA-256"):
        derive_video_frames(config, extractor=extractor)


def test_video_frame_derivation_rejects_extractor_identity_drift(tmp_path):
    _, _, extractor, config, _ = _fixture(tmp_path)
    broken = replace(config, expected_extractor_version="different version")

    with pytest.raises(BenchmarkIntegrityError, match="version"):
        derive_video_frames(broken, extractor=extractor)


def test_video_frame_derivation_rejects_extractor_byte_drift(tmp_path):
    _, artifact, extractor, config, _ = _fixture(tmp_path)
    expected = config.expected_extractor_sha256
    artifact.write_bytes(b"changed-extractor")
    drifted = _FakeExtractor(artifact)
    assert drifted.identify().artifact_sha256 != expected

    with pytest.raises(BenchmarkIntegrityError, match="pinned value"):
        derive_video_frames(config, extractor=drifted)


def test_video_frame_derivation_requires_absent_or_empty_output(tmp_path):
    _, _, extractor, config, _ = _fixture(tmp_path)
    output = Path(config.output_dir)
    output.mkdir()
    (output / "existing.txt").write_text("existing", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="absent or empty"):
        derive_video_frames(config, extractor=extractor)


def test_video_frame_derivation_rejects_failed_extraction(tmp_path):
    _, _, extractor, config, _ = _fixture(tmp_path, returncode=1)

    with pytest.raises(BenchmarkIntegrityError, match="non-zero"):
        derive_video_frames(config, extractor=extractor)


def test_video_frame_derivation_rejects_unexpected_output_file(tmp_path):
    _, _, extractor, config, _ = _fixture(tmp_path, extra_file=True)

    with pytest.raises(SchemaError, match="non-JPEG"):
        derive_video_frames(config, extractor=extractor)


def test_video_frame_derivation_rejects_noncontiguous_frames(tmp_path):
    _, _, extractor, config, _ = _fixture(tmp_path, skipped_index=1)

    with pytest.raises(SchemaError, match="contiguous"):
        derive_video_frames(config, extractor=extractor)


def test_video_frame_derivation_validation_rejects_frame_tamper(tmp_path):
    _, _, extractor, config, _ = _fixture(tmp_path)
    run = derive_video_frames(config, extractor=extractor)
    (run.frame_dir / "000001.jpg").write_bytes(b"changed-frame")

    with pytest.raises(BenchmarkIntegrityError, match="frame bytes or identity"):
        validate_video_frame_derivation_run(run)


def test_video_frame_derivation_validation_rejects_tool_tamper(tmp_path):
    _, artifact, extractor, config, _ = _fixture(tmp_path)
    run = derive_video_frames(config, extractor=extractor)
    artifact.write_bytes(b"changed-extractor-after-run")

    with pytest.raises(BenchmarkIntegrityError, match="executable bytes"):
        validate_video_frame_derivation_run(run)


def test_video_frame_derivation_validation_rejects_report_tamper(tmp_path):
    _, _, extractor, config, _ = _fixture(tmp_path)
    run = derive_video_frames(config, extractor=extractor)
    run.report["dataset_rights_implied"] = True

    with pytest.raises(BenchmarkIntegrityError, match="report fingerprint"):
        validate_video_frame_derivation_run(run)


def test_grounded_sam2_orchestration_attests_exact_derived_frame_binding(tmp_path):
    _, _, extractor, derivation_config, grounded_config = _fixture(tmp_path)

    combined = run_grounded_sam2_with_verified_frame_derivation(
        derivation_config,
        grounded_config,
        labels=["Red Car"],
        extractor=extractor,
        runtime=_FakeGroundedRuntime(),
    )

    binding = combined.binding_report
    backend = combined.backend_run.report
    derivation = combined.derivation.report
    assert len(combined.backend_run.canonical) == 3
    assert binding["frame_derivation_mechanically_verified"] is True
    assert binding["grounded_sam2_backend_alone_claims_derivation_verification"] is False
    assert binding["empirical_performance_claim_created"] is False
    assert binding["dataset_source_authority_implied"] is False
    assert binding["dataset_rights_implied"] is False
    assert binding["source_video_sha256"] == derivation["source_video"]["sha256"]
    assert binding["frame_manifest_fingerprint_sha256"] == derivation["frames"][
        "manifest_fingerprint_sha256"
    ]
    assert backend["frames"]["manifest"] == derivation["frames"]["manifest"]
    assert "mechanically verified video-frame derivation" in backend["source_video"][
        "frame_extraction_basis"
    ]


def test_grounded_sam2_binding_rejects_backend_source_mismatch(tmp_path):
    _, _, extractor, derivation_config, grounded_config = _fixture(tmp_path)
    combined = run_grounded_sam2_with_verified_frame_derivation(
        derivation_config,
        grounded_config,
        labels=["Red Car"],
        extractor=extractor,
        runtime=_FakeGroundedRuntime(),
    )
    combined.backend_run.report["source_video"]["sha256"] = "f" * 64

    with pytest.raises(BenchmarkIntegrityError):
        bind_grounded_sam2_frame_derivation(
            combined.derivation,
            combined.backend_run,
        )


def test_grounded_sam2_orchestration_rejects_configured_source_path_mismatch(tmp_path):
    _, _, extractor, derivation_config, grounded_config = _fixture(tmp_path)
    other = tmp_path / "other.mp4"
    other.write_bytes(b"source-video-fixture")
    broken = replace(grounded_config, source_video_path=other)

    with pytest.raises(BenchmarkIntegrityError, match="source path"):
        run_grounded_sam2_with_verified_frame_derivation(
            derivation_config,
            broken,
            labels=["Red Car"],
            extractor=extractor,
            runtime=_FakeGroundedRuntime(),
        )


def test_ffmpeg_extractor_missing_binary_fails_closed(tmp_path):
    extractor = FFmpegJPEGFrameExtractor(tmp_path / "missing-ffmpeg")
    with pytest.raises(FileNotFoundError, match="FFmpeg executable"):
        extractor.identify()
