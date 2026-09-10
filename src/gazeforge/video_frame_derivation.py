"""Mechanically auditable source-video to JPEG-frame derivation for model inputs."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError, SchemaError

_HEX = frozenset("0123456789abcdef")
_ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg"}


@dataclass(frozen=True, slots=True)
class FrameExtractorIdentity:
    """Exact local extraction-tool identity observed before frame derivation."""

    name: str
    version: str
    artifact_path: str
    artifact_sha256: str


@dataclass(frozen=True, slots=True)
class FrameExtractionExecution:
    """Exact extraction invocation and process result."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True, slots=True)
class VideoFrameDerivationConfig:
    """Pinned source/tool/output contract for one frame-derivation run."""

    source_video_path: str | Path
    source_video_sha256: str
    output_dir: str | Path
    expected_extractor_name: str
    expected_extractor_version: str
    expected_extractor_sha256: str
    frame_index_base: int = 0
    jpeg_quality: int = 2


@dataclass(slots=True)
class VideoFrameDerivationRun:
    """Derived frame directory plus a replayable provenance report."""

    source_video_path: Path
    frame_dir: Path
    report: dict[str, Any]


@dataclass(slots=True)
class GroundedSAM2VerifiedFrameRun:
    """Grounded-SAM-2 execution paired with a verified frame-derivation binding."""

    derivation: VideoFrameDerivationRun
    backend_run: Any
    binding_report: dict[str, Any]


class VideoFrameExtractor(Protocol):
    """Narrow protocol for a local source-video frame extractor."""

    def identify(self) -> FrameExtractorIdentity:
        """Return exact tool identity before extraction."""

    def extract(
        self,
        source_video: Path,
        output_dir: Path,
        *,
        frame_index_base: int,
        jpeg_quality: int,
    ) -> FrameExtractionExecution:
        """Extract numeric JPEG frames into an initially empty directory."""


@dataclass(frozen=True, slots=True)
class FFmpegJPEGFrameExtractor:
    """FFmpeg-backed JPEG extractor with byte-bound executable identity."""

    executable_path: str | Path = "ffmpeg"

    def _resolved_executable(self) -> Path:
        raw = Path(self.executable_path)
        if raw.is_file():
            return raw.resolve()
        located = shutil.which(str(self.executable_path))
        if located is None:
            raise FileNotFoundError(f"FFmpeg executable not found: {self.executable_path}")
        return Path(located).resolve()

    def identify(self) -> FrameExtractorIdentity:
        executable = self._resolved_executable()
        _, digest = _file_sha256(executable, label="frame extractor executable")
        completed = subprocess.run(
            [str(executable), "-version"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise BenchmarkIntegrityError(
                "Frame extractor identification failed with a non-zero return code."
            )
        lines = completed.stdout.splitlines()
        if not lines:
            raise BenchmarkIntegrityError("Frame extractor version output is empty.")
        return FrameExtractorIdentity(
            name="ffmpeg",
            version=lines[0].strip(),
            artifact_path=str(executable),
            artifact_sha256=digest,
        )

    def extract(
        self,
        source_video: Path,
        output_dir: Path,
        *,
        frame_index_base: int,
        jpeg_quality: int,
    ) -> FrameExtractionExecution:
        executable = self._resolved_executable()
        pattern = output_dir / "%06d.jpg"
        argv = (
            str(executable),
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source_video),
            "-map",
            "0:v:0",
            "-fps_mode",
            "passthrough",
            "-q:v",
            str(jpeg_quality),
            "-start_number",
            str(frame_index_base),
            str(pattern),
        )
        completed = subprocess.run(
            list(argv),
            check=False,
            capture_output=True,
            text=True,
        )
        return FrameExtractionExecution(
            argv=argv,
            returncode=int(completed.returncode),
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def _resolved(value: Any, *, label: str) -> str:
    text = str(value).strip()
    upper = text.upper()
    if not text or "REPLACE" in upper or "VERIFY" in upper:
        raise ValueError(f"{label} must be an explicit resolved value.")
    return text


def _sha256(value: Any, *, label: str) -> str:
    digest = str(value).strip().lower()
    if len(digest) != 64 or any(character not in _HEX for character in digest):
        raise ValueError(f"{label} must be a 64-character hexadecimal SHA-256.")
    return digest


def _file_sha256(path: Path, *, label: str) -> tuple[int, str]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    if size <= 0:
        raise BenchmarkIntegrityError(f"{label} cannot be empty.")
    return size, digest.hexdigest()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validate_config(config: VideoFrameDerivationConfig) -> dict[str, Any]:
    if not isinstance(config, VideoFrameDerivationConfig):
        raise TypeError("config must be a VideoFrameDerivationConfig instance.")
    source_sha = _sha256(config.source_video_sha256, label="source_video_sha256")
    extractor_name = _resolved(config.expected_extractor_name, label="expected_extractor_name")
    extractor_version = _resolved(
        config.expected_extractor_version,
        label="expected_extractor_version",
    )
    extractor_sha = _sha256(
        config.expected_extractor_sha256,
        label="expected_extractor_sha256",
    )
    frame_index_base = int(config.frame_index_base)
    if frame_index_base not in {0, 1}:
        raise ValueError("frame_index_base must be explicitly 0 or 1.")
    jpeg_quality = int(config.jpeg_quality)
    if not 1 <= jpeg_quality <= 31:
        raise ValueError("jpeg_quality must be an FFmpeg q:v value in [1, 31].")
    return {
        "source_video_sha256": source_sha,
        "expected_extractor_name": extractor_name,
        "expected_extractor_version": extractor_version,
        "expected_extractor_sha256": extractor_sha,
        "frame_index_base": frame_index_base,
        "jpeg_quality": jpeg_quality,
    }


def _validate_identity(
    identity: FrameExtractorIdentity,
    *,
    expected_name: str,
    expected_version: str,
    expected_sha256: str,
) -> tuple[Path, int]:
    if not isinstance(identity, FrameExtractorIdentity):
        raise TypeError("extractor.identify() must return FrameExtractorIdentity.")
    name = _resolved(identity.name, label="extractor identity name")
    version = _resolved(identity.version, label="extractor identity version")
    artifact_sha = _sha256(identity.artifact_sha256, label="extractor identity artifact_sha256")
    if name != expected_name:
        raise BenchmarkIntegrityError(
            f"Frame extractor name mismatch: expected {expected_name!r}, observed {name!r}."
        )
    if version != expected_version:
        raise BenchmarkIntegrityError("Frame extractor version does not match the pinned value.")
    if artifact_sha != expected_sha256:
        raise BenchmarkIntegrityError(
            "Frame extractor declared SHA-256 does not match the pinned value."
        )
    artifact = Path(identity.artifact_path)
    artifact_size, observed_sha = _file_sha256(
        artifact,
        label="frame extractor executable",
    )
    if observed_sha != expected_sha256:
        raise BenchmarkIntegrityError(
            "Frame extractor executable bytes do not match the pinned SHA-256."
        )
    return artifact.resolve(), artifact_size


def _prepare_empty_output_dir(path: Path) -> None:
    if path.exists() and not path.is_dir():
        raise SchemaError(f"Frame output path exists but is not a directory: {path}")
    if path.is_dir() and any(path.iterdir()):
        raise BenchmarkIntegrityError(
            "Frame output directory must be absent or empty before mechanical derivation."
        )
    path.mkdir(parents=True, exist_ok=True)


def _frame_manifest(frame_dir: Path, *, frame_index_base: int) -> list[dict[str, Any]]:
    if not frame_dir.is_dir():
        raise FileNotFoundError(f"Derived frame directory does not exist: {frame_dir}")
    children = sorted(path for path in frame_dir.iterdir() if path.is_file())
    if not children:
        raise BenchmarkIntegrityError("Frame extraction produced no files.")
    unexpected = [
        path.name for path in children if path.suffix.lower() not in _ALLOWED_IMAGE_SUFFIXES
    ]
    if unexpected:
        raise SchemaError(
            "Mechanical frame derivation output contains non-JPEG files: "
            f"{unexpected[:5]}"
        )

    indexed: list[tuple[int, Path]] = []
    for path in children:
        try:
            index = int(path.stem)
        except ValueError as exc:
            raise SchemaError(
                "Derived JPEG filenames must have integer stems such as 000000.jpg."
            ) from exc
        indexed.append((index, path))
    indexed.sort(key=lambda item: item[0])
    indices = [index for index, _ in indexed]
    if len(indices) != len(set(indices)):
        raise SchemaError("Derived JPEG frame indices must be unique.")
    expected = list(range(frame_index_base, frame_index_base + len(indices)))
    if indices != expected:
        raise SchemaError(
            "Derived JPEG frame indices must be contiguous from the explicit frame_index_base."
        )

    manifest: list[dict[str, Any]] = []
    for position, (frame_index, path) in enumerate(indexed):
        size, digest = _file_sha256(path, label="derived frame file")
        manifest.append(
            {
                "position": position,
                "frame_index": frame_index,
                "basename": path.name,
                "bytes": size,
                "sha256": digest,
            }
        )
    return manifest


def derive_video_frames(
    config: VideoFrameDerivationConfig,
    *,
    extractor: VideoFrameExtractor | None = None,
) -> VideoFrameDerivationRun:
    """Mechanically derive and hash exact JPEG model inputs from one source video."""
    values = _validate_config(config)
    source = Path(config.source_video_path).resolve()
    source_size, source_sha = _file_sha256(source, label="source video")
    if source_sha != values["source_video_sha256"]:
        raise BenchmarkIntegrityError("Source-video SHA-256 does not match the pinned value.")

    output_dir = Path(config.output_dir).resolve()
    if output_dir == source.parent or output_dir == source:
        raise SchemaError("Frame output directory must be distinct from the source-video path.")
    _prepare_empty_output_dir(output_dir)

    selected: VideoFrameExtractor = extractor or FFmpegJPEGFrameExtractor()
    identity = selected.identify()
    artifact, artifact_size = _validate_identity(
        identity,
        expected_name=values["expected_extractor_name"],
        expected_version=values["expected_extractor_version"],
        expected_sha256=values["expected_extractor_sha256"],
    )

    execution = selected.extract(
        source,
        output_dir,
        frame_index_base=values["frame_index_base"],
        jpeg_quality=values["jpeg_quality"],
    )
    if not isinstance(execution, FrameExtractionExecution):
        raise TypeError("extractor.extract() must return FrameExtractionExecution.")
    if int(execution.returncode) != 0:
        raise BenchmarkIntegrityError(
            "Mechanical frame extraction failed with a non-zero return code."
        )
    if not execution.argv:
        raise BenchmarkIntegrityError("Mechanical frame extraction must report its exact argv.")

    manifest = _frame_manifest(
        output_dir,
        frame_index_base=values["frame_index_base"],
    )
    body: dict[str, Any] = {
        "schema_version": 1,
        "derivation_type": "source-video-to-jpeg-frames",
        "source_video": {
            "path": str(source),
            "basename": source.name,
            "bytes": source_size,
            "sha256": source_sha,
        },
        "extractor": {
            "name": identity.name,
            "version": identity.version,
            "artifact_path": str(artifact),
            "artifact_bytes": artifact_size,
            "artifact_sha256": identity.artifact_sha256,
        },
        "execution": {
            "argv": list(execution.argv),
            "returncode": int(execution.returncode),
            "stdout_bytes": len(execution.stdout.encode("utf-8")),
            "stdout_sha256": _text_sha256(execution.stdout),
            "stderr_bytes": len(execution.stderr.encode("utf-8")),
            "stderr_sha256": _text_sha256(execution.stderr),
            "jpeg_quality": values["jpeg_quality"],
        },
        "frames": {
            "directory": str(output_dir),
            "directory_basename": output_dir.name,
            "count": len(manifest),
            "frame_index_base": values["frame_index_base"],
            "first_frame_index": manifest[0]["frame_index"],
            "last_frame_index": manifest[-1]["frame_index"],
            "manifest_fingerprint_sha256": benchmark_fingerprint(manifest),
            "manifest": manifest,
        },
        "frame_derivation_mechanically_verified": True,
        "empirical_performance_claim_created": False,
        "dataset_source_authority_implied": False,
        "dataset_rights_implied": False,
        "raw_source_redistribution_authorized": False,
        "scientific_boundary": [
            "This record attests only the local source-video to JPEG-frame derivation chain.",
            "It does not establish dataset authority, rights, or model performance.",
            "JPEG encoding is a derived model-input representation and is not raw-source identity.",
        ],
    }
    report = {**body, "report_fingerprint_sha256": benchmark_fingerprint(body)}
    run = VideoFrameDerivationRun(
        source_video_path=source,
        frame_dir=output_dir,
        report=report,
    )
    validate_video_frame_derivation_run(run)
    return run


def validate_video_frame_derivation_run(run: VideoFrameDerivationRun) -> None:
    """Replay all local byte and report bindings for one derivation run."""
    if not isinstance(run, VideoFrameDerivationRun):
        raise TypeError("run must be a VideoFrameDerivationRun instance.")
    report = run.report
    expected_report = report.get("report_fingerprint_sha256")
    if not isinstance(expected_report, str):
        raise BenchmarkIntegrityError("Frame-derivation report fingerprint is missing.")
    body = {key: value for key, value in report.items() if key != "report_fingerprint_sha256"}
    if benchmark_fingerprint(body) != expected_report:
        raise BenchmarkIntegrityError("Frame-derivation report fingerprint does not revalidate.")
    if report.get("frame_derivation_mechanically_verified") is not True:
        raise BenchmarkIntegrityError("Frame derivation must remain mechanically verified.")
    for forbidden in (
        "empirical_performance_claim_created",
        "dataset_source_authority_implied",
        "dataset_rights_implied",
        "raw_source_redistribution_authorized",
    ):
        if report.get(forbidden) is not False:
            raise BenchmarkIntegrityError(
                f"Frame-derivation infrastructure cannot promote {forbidden}."
            )

    source_meta = report.get("source_video")
    if not isinstance(source_meta, Mapping):
        raise BenchmarkIntegrityError("Frame-derivation source-video metadata are missing.")
    source = Path(source_meta["path"])
    source_size, source_sha = _file_sha256(source, label="source video")
    if source.resolve() != run.source_video_path.resolve():
        raise BenchmarkIntegrityError("Frame-derivation source-video path binding changed.")
    if source_size != int(source_meta["bytes"]) or source_sha != source_meta["sha256"]:
        raise BenchmarkIntegrityError("Frame-derivation source-video bytes changed.")

    extractor_meta = report.get("extractor")
    if not isinstance(extractor_meta, Mapping):
        raise BenchmarkIntegrityError("Frame-derivation extractor metadata are missing.")
    artifact = Path(extractor_meta["artifact_path"])
    artifact_size, artifact_sha = _file_sha256(
        artifact,
        label="frame extractor executable",
    )
    if (
        artifact_size != int(extractor_meta["artifact_bytes"])
        or artifact_sha != extractor_meta["artifact_sha256"]
    ):
        raise BenchmarkIntegrityError("Frame-derivation extractor executable bytes changed.")

    frame_meta = report.get("frames")
    if not isinstance(frame_meta, Mapping):
        raise BenchmarkIntegrityError("Frame-derivation frame metadata are missing.")
    if Path(frame_meta["directory"]).resolve() != run.frame_dir.resolve():
        raise BenchmarkIntegrityError("Frame-derivation output-directory binding changed.")
    observed_manifest = _frame_manifest(
        run.frame_dir,
        frame_index_base=int(frame_meta["frame_index_base"]),
    )
    if observed_manifest != frame_meta["manifest"]:
        raise BenchmarkIntegrityError("Frame-derivation output frame bytes or identity changed.")
    if benchmark_fingerprint(observed_manifest) != frame_meta["manifest_fingerprint_sha256"]:
        raise BenchmarkIntegrityError("Frame-derivation frame manifest fingerprint changed.")


def bind_grounded_sam2_frame_derivation(
    derivation: VideoFrameDerivationRun,
    backend_run: Any,
) -> dict[str, Any]:
    """Bind a Grounded-SAM-2 run to the exact mechanically derived frame set."""
    validate_video_frame_derivation_run(derivation)
    from .grounded_sam2 import validate_grounded_sam2_run

    validate_grounded_sam2_run(backend_run)
    backend_report = backend_run.report
    source = backend_report.get("source_video", {})
    frames = backend_report.get("frames", {})
    derivation_source = derivation.report["source_video"]
    derivation_frames = derivation.report["frames"]

    if source.get("sha256") != derivation_source["sha256"]:
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 source-video SHA does not match the frame-derivation source."
        )
    if frames.get("manifest") != derivation_frames["manifest"]:
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 frame manifest does not match the mechanically derived frame set."
        )
    if frames.get("manifest_fingerprint_sha256") != derivation_frames[
        "manifest_fingerprint_sha256"
    ]:
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 frame manifest fingerprint does not match frame derivation."
        )

    body = {
        "schema_version": 1,
        "binding_type": "grounded-sam2-to-mechanical-frame-derivation",
        "frame_derivation_report_fingerprint_sha256": derivation.report[
            "report_fingerprint_sha256"
        ],
        "grounded_sam2_report_fingerprint_sha256": backend_report[
            "report_fingerprint_sha256"
        ],
        "source_video_sha256": derivation_source["sha256"],
        "frame_manifest_fingerprint_sha256": derivation_frames[
            "manifest_fingerprint_sha256"
        ],
        "frame_derivation_mechanically_verified": True,
        "grounded_sam2_backend_alone_claims_derivation_verification": bool(
            source.get("frame_derivation_mechanically_verified")
        ),
        "empirical_performance_claim_created": False,
        "dataset_source_authority_implied": False,
        "dataset_rights_implied": False,
    }
    if body["grounded_sam2_backend_alone_claims_derivation_verification"]:
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 backend-alone derivation flag unexpectedly changed; "
            "mechanical verification must come from this separate binding."
        )
    return {**body, "binding_fingerprint_sha256": benchmark_fingerprint(body)}


def run_grounded_sam2_with_verified_frame_derivation(
    derivation_config: VideoFrameDerivationConfig,
    grounded_config: Any,
    *,
    labels: Sequence[str],
    extractor: VideoFrameExtractor | None = None,
    runtime: Any = None,
) -> GroundedSAM2VerifiedFrameRun:
    """Derive exact frames, run Grounded-SAM-2, then attest the source/frame binding."""
    derivation = derive_video_frames(derivation_config, extractor=extractor)
    from .grounded_sam2 import GroundedSAM2Config, run_grounded_sam2_dynamic_aoi

    if not isinstance(grounded_config, GroundedSAM2Config):
        raise TypeError("grounded_config must be a GroundedSAM2Config instance.")
    derivation_source = derivation.report["source_video"]
    configured_source = Path(grounded_config.source_video_path).resolve()
    if configured_source != derivation.source_video_path.resolve():
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 source path must equal the mechanical derivation source path."
        )
    configured_sha = _sha256(
        grounded_config.source_video_sha256,
        label="grounded_config.source_video_sha256",
    )
    if configured_sha != derivation_source["sha256"]:
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 source SHA must equal the mechanical derivation source SHA."
        )

    backend_config = replace(
        grounded_config,
        frame_index_base=int(derivation.report["frames"]["frame_index_base"]),
        frame_extraction_basis=(
            "GazeForge mechanically verified video-frame derivation "
            + derivation.report["report_fingerprint_sha256"]
        ),
    )
    backend_run = run_grounded_sam2_dynamic_aoi(
        derivation.frame_dir,
        labels=labels,
        config=backend_config,
        runtime=runtime,
    )
    binding = bind_grounded_sam2_frame_derivation(derivation, backend_run)
    return GroundedSAM2VerifiedFrameRun(
        derivation=derivation,
        backend_run=backend_run,
        binding_report=binding,
    )
