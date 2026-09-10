"""Optional Grounding DINO + SAM 2 backend for auditable dynamic AOI tracking."""

from __future__ import annotations

import hashlib
import importlib.metadata
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd

from .benchmarks import benchmark_fingerprint
from .dynamic_aoi import DynamicAOIKeyframe
from .exceptions import BenchmarkIntegrityError, OptionalDependencyError, SchemaError
from .provenance import fingerprint_frame

_HEX = frozenset("0123456789abcdef")
_IMAGE_SUFFIXES = {".jpg", ".jpeg"}
_GROUNDED_SAM2_REFERENCE = (
    "IDEA-Research/Grounded-SAM-2@"
    "b7a9c29f196edff0eb54dbe14588d7ae5e3dde28/grounded_sam2_tracking_demo.py"
)


@dataclass(frozen=True, slots=True)
class GroundedSAM2Detection:
    """One text-grounded detector box used to seed SAM 2 video propagation."""

    label: str
    score: float
    box_xyxy: tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class GroundedSAM2Seed:
    """Deterministically identified detector seed passed to the video tracker."""

    object_id: int
    aoi_id: str
    label: str
    score: float
    box_xyxy: tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class GroundedSAM2Config:
    """Pinned model/runtime settings for the optional Grounded-SAM-2 bridge."""

    grounding_model_id: str
    grounding_model_revision: str
    sam2_model_cfg: str
    sam2_checkpoint_path: str | Path
    sam2_checkpoint_sha256: str
    sam2_code_revision: str
    source_video_path: str | Path
    source_video_sha256: str
    frame_extraction_basis: str
    frame_rate_hz: float
    frame_index_base: int = 0
    prompt_frame_index: int = 0
    box_threshold: float = 0.25
    text_threshold: float = 0.30
    device: str = "cuda"
    local_files_only: bool = False
    min_mask_pixels: int = 1


@dataclass(slots=True)
class GroundedSAM2DynamicAOIRun:
    """Canonical tracked AOIs plus an integrity/provenance report."""

    canonical: pd.DataFrame
    keyframes: list[DynamicAOIKeyframe]
    report: dict[str, Any]


@dataclass(slots=True)
class GroundedSAM2DynamicAOIProvider:
    """DynamicAOIProvider-compatible wrapper around the optional backend."""

    config: GroundedSAM2Config
    runtime: GroundedSAM2Runtime | None = None
    last_run: GroundedSAM2DynamicAOIRun | None = None
    model_name: str = "Grounding DINO + SAM 2"

    @property
    def model_version(self) -> str:
        """Return the configured immutable model identity before execution."""
        values = _validate_config(self.config)
        return (
            f"{values['grounding_model_id']}@{values['grounding_model_revision']}+"
            f"sam2@{values['sam2_code_revision']}+"
            f"{values['sam2_model_cfg']}@{values['sam2_checkpoint_sha256'][:12]}"
        )

    def track(self, stimulus: Any, labels: Sequence[str]) -> list[DynamicAOIKeyframe]:
        """Execute the backend on an integer-named JPEG frame directory."""
        run = run_grounded_sam2_dynamic_aoi(
            stimulus,
            labels=labels,
            config=self.config,
            runtime=self.runtime,
        )
        self.last_run = run
        return list(run.keyframes)


class GroundedSAM2Runtime(Protocol):
    """Narrow runtime contract implemented by the optional third-party bridge."""

    def detect(
        self,
        image_path: Path,
        prompt_text: str,
        config: GroundedSAM2Config,
    ) -> Sequence[GroundedSAM2Detection]:
        """Detect prompt-conditioned boxes on one frame."""

    def propagate(
        self,
        frame_dir: Path,
        seeds: Sequence[GroundedSAM2Seed],
        *,
        prompt_position: int,
        config: GroundedSAM2Config,
    ) -> Mapping[int, Mapping[int, np.ndarray]]:
        """Propagate seeded objects across frame positions."""

    def runtime_metadata(self) -> Mapping[str, Any]:
        """Return package/runtime versions for provenance."""


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


def _git_revision(value: Any, *, label: str) -> str:
    revision = str(value).strip().lower()
    if len(revision) != 40 or any(character not in _HEX for character in revision):
        raise ValueError(
            f"{label} must be an immutable 40-character Git commit SHA, not a branch/tag."
        )
    return revision


def _file_sha256(path: Path, *, label: str) -> tuple[int, str]:
    if not path.is_file():
        raise FileNotFoundError(f"Grounded-SAM-2 {label} does not exist: {path}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    if size <= 0:
        raise BenchmarkIntegrityError(f"Grounded-SAM-2 {label} cannot be empty.")
    return size, digest.hexdigest()


def _frame_manifest(frame_dir: Path, *, frame_index_base: int) -> list[dict[str, Any]]:
    if not frame_dir.is_dir():
        raise FileNotFoundError(f"Grounded-SAM-2 frame directory does not exist: {frame_dir}")
    candidates = [
        path
        for path in frame_dir.iterdir()
        if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES
    ]
    if not candidates:
        raise SchemaError("Grounded-SAM-2 requires at least one numeric JPEG frame.")

    indexed: list[tuple[int, Path]] = []
    for path in candidates:
        try:
            index = int(path.stem)
        except ValueError as exc:
            raise SchemaError(
                "Grounded-SAM-2 frame filenames must be integer indices such as 0.jpg."
            ) from exc
        indexed.append((index, path))
    indexed.sort(key=lambda item: item[0])
    indices = [index for index, _ in indexed]
    if len(indices) != len(set(indices)):
        raise SchemaError("Grounded-SAM-2 frame indices must be unique.")
    expected = list(range(frame_index_base, frame_index_base + len(indices)))
    if indices != expected:
        raise SchemaError(
            "Grounded-SAM-2 frame indices must be contiguous from the explicit frame_index_base."
        )

    manifest: list[dict[str, Any]] = []
    for position, (frame_index, path) in enumerate(indexed):
        size, digest = _file_sha256(path, label="frame file")
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


def _normalize_label(value: Any) -> str:
    return " ".join(str(value).strip().rstrip(".").lower().split())


def _prompt_labels(labels: Sequence[str]) -> tuple[list[str], dict[str, str], str]:
    if not labels:
        raise ValueError("Grounded-SAM-2 requires at least one semantic AOI label.")
    canonical: list[str] = []
    by_normalized: dict[str, str] = {}
    for value in labels:
        exact = _resolved(value, label="semantic AOI label")
        normalized = _normalize_label(exact)
        if not normalized:
            raise ValueError("Grounded-SAM-2 semantic AOI labels cannot be empty.")
        if normalized in by_normalized:
            raise ValueError("Grounded-SAM-2 semantic AOI labels must be unique ignoring case.")
        canonical.append(exact)
        by_normalized[normalized] = exact
    prompt = " ".join(f"{_normalize_label(label)}." for label in canonical)
    return canonical, by_normalized, prompt


def _validate_config(config: GroundedSAM2Config) -> dict[str, Any]:
    if not isinstance(config, GroundedSAM2Config):
        raise TypeError("config must be a GroundedSAM2Config instance.")
    model_id = _resolved(config.grounding_model_id, label="grounding_model_id")
    grounding_revision = _git_revision(
        config.grounding_model_revision,
        label="grounding_model_revision",
    )
    sam2_cfg = _resolved(config.sam2_model_cfg, label="sam2_model_cfg")
    sam2_revision = _git_revision(config.sam2_code_revision, label="sam2_code_revision")
    checkpoint_sha = _sha256(
        config.sam2_checkpoint_sha256,
        label="sam2_checkpoint_sha256",
    )
    source_video_sha = _sha256(
        config.source_video_sha256,
        label="source_video_sha256",
    )
    extraction_basis = _resolved(
        config.frame_extraction_basis,
        label="frame_extraction_basis",
    )
    frame_rate = float(config.frame_rate_hz)
    if not np.isfinite(frame_rate) or frame_rate <= 0:
        raise ValueError("frame_rate_hz must be finite and positive.")
    if int(config.frame_index_base) not in {0, 1}:
        raise ValueError("frame_index_base must be explicitly 0 or 1.")
    if int(config.prompt_frame_index) < int(config.frame_index_base):
        raise ValueError("prompt_frame_index cannot precede frame_index_base.")
    for name, value in (
        ("box_threshold", config.box_threshold),
        ("text_threshold", config.text_threshold),
    ):
        threshold = float(value)
        if not np.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
            raise ValueError(f"{name} must be finite and lie in [0, 1].")
    if int(config.min_mask_pixels) < 1:
        raise ValueError("min_mask_pixels must be at least 1.")
    device = _resolved(config.device, label="device")
    return {
        "grounding_model_id": model_id,
        "grounding_model_revision": grounding_revision,
        "sam2_model_cfg": sam2_cfg,
        "sam2_code_revision": sam2_revision,
        "sam2_checkpoint_sha256": checkpoint_sha,
        "source_video_sha256": source_video_sha,
        "frame_extraction_basis": extraction_basis,
        "frame_rate_hz": frame_rate,
        "frame_index_base": int(config.frame_index_base),
        "prompt_frame_index": int(config.prompt_frame_index),
        "box_threshold": float(config.box_threshold),
        "text_threshold": float(config.text_threshold),
        "device": device,
        "local_files_only": bool(config.local_files_only),
        "min_mask_pixels": int(config.min_mask_pixels),
    }


def _validate_box(box: Sequence[float], *, label: str) -> tuple[float, float, float, float]:
    if len(box) != 4:
        raise SchemaError(f"Grounded-SAM-2 detection {label!r} must contain four box coordinates.")
    values = tuple(float(value) for value in box)
    if not np.isfinite(np.asarray(values, dtype=float)).all():
        raise SchemaError(f"Grounded-SAM-2 detection {label!r} has non-finite geometry.")
    xmin, ymin, xmax, ymax = values
    if xmax <= xmin or ymax <= ymin:
        raise SchemaError(f"Grounded-SAM-2 detection {label!r} has invalid xyxy geometry.")
    return values


def _prepare_seeds(
    detections: Sequence[GroundedSAM2Detection],
    *,
    label_lookup: Mapping[str, str],
) -> list[GroundedSAM2Seed]:
    prepared: list[tuple[str, float, tuple[float, float, float, float]]] = []
    for detection in detections:
        if not isinstance(detection, GroundedSAM2Detection):
            raise TypeError("runtime.detect must return GroundedSAM2Detection objects.")
        normalized = _normalize_label(detection.label)
        if normalized not in label_lookup:
            raise SchemaError(
                "Grounded-SAM-2 detector returned a label outside the requested semantic prompt: "
                f"{detection.label!r}."
            )
        score = float(detection.score)
        if not np.isfinite(score) or not 0.0 <= score <= 1.0:
            raise SchemaError("Grounded-SAM-2 detector scores must lie in [0, 1].")
        exact_label = label_lookup[normalized]
        box = _validate_box(detection.box_xyxy, label=exact_label)
        prepared.append((exact_label, score, box))
    if not prepared:
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 produced no seed detections for the requested AOI labels."
        )

    prepared.sort(key=lambda item: (_normalize_label(item[0]), -item[1], *item[2]))
    counts: dict[str, int] = {}
    seeds: list[GroundedSAM2Seed] = []
    for object_id, (label, score, box) in enumerate(prepared, start=1):
        normalized = _normalize_label(label)
        counts[normalized] = counts.get(normalized, 0) + 1
        ordinal = counts[normalized]
        slug = normalized.replace(" ", "-")
        aoi_id = f"grounded-sam2:{slug}:{ordinal}"
        seeds.append(
            GroundedSAM2Seed(
                object_id=object_id,
                aoi_id=aoi_id,
                label=label,
                score=score,
                box_xyxy=box,
            )
        )
    return seeds


def _mask_box(
    mask: np.ndarray,
    *,
    min_mask_pixels: int,
) -> tuple[float, float, float, float] | None:
    values = np.asarray(mask)
    while values.ndim > 2 and values.shape[0] == 1:
        values = values[0]
    if values.ndim != 2:
        raise SchemaError("Grounded-SAM-2 propagated masks must be two-dimensional per object.")
    foreground = values.astype(bool)
    ys, xs = np.nonzero(foreground)
    if len(xs) < min_mask_pixels:
        return None
    xmin = float(xs.min())
    ymin = float(ys.min())
    xmax = float(xs.max() + 1)
    ymax = float(ys.max() + 1)
    return xmin, ymin, xmax, ymax


def _canonical_from_segments(
    segments: Mapping[int, Mapping[int, np.ndarray]],
    *,
    seeds: Sequence[GroundedSAM2Seed],
    manifest: Sequence[Mapping[str, Any]],
    frame_rate_hz: float,
    frame_index_base: int,
    min_mask_pixels: int,
) -> tuple[pd.DataFrame, int, tuple[int, int]]:
    by_object = {seed.object_id: seed for seed in seeds}
    if len(by_object) != len(seeds):
        raise BenchmarkIntegrityError("Grounded-SAM-2 seed object IDs must be unique.")
    by_position = {int(item["position"]): int(item["frame_index"]) for item in manifest}
    rows: list[dict[str, Any]] = []
    empty_masks = 0
    mask_shapes: set[tuple[int, int]] = set()
    for raw_position, raw_objects in sorted(segments.items(), key=lambda item: int(item[0])):
        position = int(raw_position)
        if position not in by_position:
            raise SchemaError(
                "Grounded-SAM-2 propagation returned a frame position outside the input ledger."
            )
        if not isinstance(raw_objects, Mapping):
            raise TypeError("runtime.propagate must map frame positions to object/mask mappings.")
        frame_index = by_position[position]
        for raw_object_id, mask in sorted(raw_objects.items(), key=lambda item: int(item[0])):
            object_id = int(raw_object_id)
            seed = by_object.get(object_id)
            if seed is None:
                raise SchemaError(
                    "Grounded-SAM-2 propagation returned an object ID that was not detector-seeded."
                )
            raw_mask = np.asarray(mask)
            squeezed = raw_mask
            while squeezed.ndim > 2 and squeezed.shape[0] == 1:
                squeezed = squeezed[0]
            if squeezed.ndim != 2:
                raise SchemaError(
                    "Grounded-SAM-2 propagated masks must be two-dimensional per object."
                )
            mask_shapes.add((int(squeezed.shape[0]), int(squeezed.shape[1])))
            if len(mask_shapes) > 1:
                raise SchemaError(
                    "Grounded-SAM-2 propagated masks must keep one frame geometry."
                )
            box = _mask_box(squeezed, min_mask_pixels=min_mask_pixels)
            if box is None:
                empty_masks += 1
                continue
            xmin, ymin, xmax, ymax = box
            rows.append(
                {
                    "frame_index": frame_index,
                    "aoi_id": seed.aoi_id,
                    "label": seed.label,
                    "xmin": xmin,
                    "ymin": ymin,
                    "xmax": xmax,
                    "ymax": ymax,
                    "confidence": seed.score,
                    "seed_detection_confidence": seed.score,
                    "sam2_mask_pixels": int(np.count_nonzero(squeezed)),
                    "timestamp_ms": (
                        float(frame_index - frame_index_base) * 1000.0 / frame_rate_hz
                    ),
                }
            )
    if not rows:
        raise BenchmarkIntegrityError("Grounded-SAM-2 propagation produced no non-empty AOI masks.")
    canonical = pd.DataFrame(rows).sort_values(
        ["aoi_id", "frame_index"], kind="stable"
    ).reset_index(drop=True)
    if canonical.duplicated(["aoi_id", "frame_index"]).any():
        raise SchemaError("Grounded-SAM-2 output contains duplicate AOI/frame identities.")
    if len(mask_shapes) != 1:
        raise BenchmarkIntegrityError("Grounded-SAM-2 output did not establish mask geometry.")
    mask_height, mask_width = next(iter(mask_shapes))
    return canonical, empty_masks, (mask_width, mask_height)


def _to_keyframes(
    canonical: pd.DataFrame,
    *,
    model_name: str,
    model_version: str,
) -> list[DynamicAOIKeyframe]:
    return [
        DynamicAOIKeyframe(
            aoi_id=str(row.aoi_id),
            label=str(row.label),
            timestamp_ms=float(row.timestamp_ms),
            xmin=float(row.xmin),
            ymin=float(row.ymin),
            xmax=float(row.xmax),
            ymax=float(row.ymax),
            confidence=float(row.confidence),
            source="model",
            model_name=model_name,
            model_version=model_version,
        )
        for row in canonical.itertuples(index=False)
    ]


def run_grounded_sam2_dynamic_aoi(
    frame_dir: str | Path,
    *,
    labels: Sequence[str],
    config: GroundedSAM2Config,
    runtime: GroundedSAM2Runtime | None = None,
) -> GroundedSAM2DynamicAOIRun:
    """Run text-grounded detection followed by SAM 2 video propagation.

    The input is a directory of contiguous, integer-named JPEG frames. The function hashes every
    frame and the local SAM 2 checkpoint, requires immutable code/model revisions, and emits a
    canonical per-frame bounding-box table suitable for later VISUS prediction intake. Detector
    seed confidence is propagated as provenance; it is not interpreted as per-frame tracking
    confidence or empirical performance.
    """
    config_values = _validate_config(config)
    frame_path = Path(frame_dir).resolve()
    manifest = _frame_manifest(
        frame_path,
        frame_index_base=config_values["frame_index_base"],
    )
    frame_indices = [int(item["frame_index"]) for item in manifest]
    prompt_frame_index = config_values["prompt_frame_index"]
    if prompt_frame_index not in frame_indices:
        raise SchemaError("prompt_frame_index must identify one of the exact input frames.")
    prompt_position = frame_indices.index(prompt_frame_index)

    checkpoint_path = Path(config.sam2_checkpoint_path).resolve()
    checkpoint_size, observed_checkpoint_sha = _file_sha256(
        checkpoint_path, label="SAM 2 checkpoint"
    )
    if observed_checkpoint_sha != config_values["sam2_checkpoint_sha256"]:
        raise BenchmarkIntegrityError("SAM 2 checkpoint SHA-256 does not match the pinned config.")

    source_video_path = Path(config.source_video_path).resolve()
    source_video_size, observed_source_video_sha = _file_sha256(
        source_video_path, label="source video"
    )
    if observed_source_video_sha != config_values["source_video_sha256"]:
        raise BenchmarkIntegrityError("Source-video SHA-256 does not match the pinned config.")

    canonical_labels, label_lookup, prompt_text = _prompt_labels(labels)
    selected_runtime: GroundedSAM2Runtime
    if runtime is None:
        selected_runtime = HuggingFaceGroundedSAM2Runtime()
    else:
        selected_runtime = runtime

    prompt_image = frame_path / str(manifest[prompt_position]["basename"])
    detections = selected_runtime.detect(prompt_image, prompt_text, config)
    seeds = _prepare_seeds(detections, label_lookup=label_lookup)
    segments = selected_runtime.propagate(
        frame_path,
        seeds,
        prompt_position=prompt_position,
        config=config,
    )
    canonical, empty_masks, mask_resolution_px = _canonical_from_segments(
        segments,
        seeds=seeds,
        manifest=manifest,
        frame_rate_hz=config_values["frame_rate_hz"],
        frame_index_base=config_values["frame_index_base"],
        min_mask_pixels=config_values["min_mask_pixels"],
    )

    model_name = "Grounding DINO + SAM 2"
    model_version = (
        f"{config_values['grounding_model_id']}@{config_values['grounding_model_revision']}+"
        f"sam2@{config_values['sam2_code_revision']}+"
        f"{config_values['sam2_model_cfg']}@{observed_checkpoint_sha[:12]}"
    )
    keyframes = _to_keyframes(
        canonical,
        model_name=model_name,
        model_version=model_version,
    )
    runtime_metadata = dict(selected_runtime.runtime_metadata())
    body = {
        "status": "verified-backend-output",
        "backend": "grounding-dino-plus-sam2",
        "backend_scope": "optional-dynamic-aoi-detection-and-tracking",
        "integration_contract_reference": _GROUNDED_SAM2_REFERENCE,
        "model_name": model_name,
        "model_version": model_version,
        "semantic_labels": canonical_labels,
        "prompt_text": prompt_text,
        "config": {
            key: value
            for key, value in config_values.items()
            if key not in {"sam2_checkpoint_sha256", "source_video_sha256"}
        },
        "model_identity": {
            "grounding_model_id": config_values["grounding_model_id"],
            "grounding_model_revision": config_values["grounding_model_revision"],
            "sam2_code_revision": config_values["sam2_code_revision"],
            "sam2_model_cfg": config_values["sam2_model_cfg"],
            "sam2_checkpoint_basename": checkpoint_path.name,
            "sam2_checkpoint_bytes": checkpoint_size,
            "sam2_checkpoint_sha256": observed_checkpoint_sha,
        },
        "runtime": runtime_metadata,
        "source_video": {
            "basename": source_video_path.name,
            "bytes": source_video_size,
            "sha256": observed_source_video_sha,
            "frame_extraction_basis": config_values["frame_extraction_basis"],
            "frame_derivation_mechanically_verified": False,
        },
        "frames": {
            "directory_basename": frame_path.name,
            "count": len(manifest),
            "frame_index_base": config_values["frame_index_base"],
            "first_frame_index": frame_indices[0],
            "last_frame_index": frame_indices[-1],
            "prompt_frame_index": prompt_frame_index,
            "manifest_fingerprint_sha256": benchmark_fingerprint(manifest),
            "manifest": manifest,
        },
        "detections": {
            "count": len(seeds),
            "seeds": [asdict(seed) for seed in seeds],
        },
        "output": {
            "row_count": int(len(canonical)),
            "track_count": int(canonical["aoi_id"].nunique()),
            "empty_or_too_small_masks_skipped": int(empty_masks),
            "mask_resolution_px": list(mask_resolution_px),
            "canonical_table_fingerprint_sha256": fingerprint_frame(canonical),
        },
        "confidence_semantics": (
            "confidence is the Grounding DINO seed-detection score propagated across SAM 2 "
            "mask-derived boxes; it is not a per-frame SAM 2 confidence score"
        ),
        "evaluation_timestamp_grid_generated": False,
        "empirical_performance_claim_created": False,
        "visus_source_authority_implied": False,
        "claim_limits": [
            "Backend execution does not establish VISUS source authority or dataset rights.",
            "Backend output is model prediction provenance, not empirical model-human validity.",
            "Prediction frames do not define the later model-human evaluation timestamp grid.",
            "Seed detector confidence must not be reported as per-frame tracking confidence.",
            (
                "Source video and extracted frames are both hash-bound, but frame derivation is "
                "not mechanically re-decoded by this backend."
            ),
        ],
    }
    report = {**body, "report_fingerprint_sha256": benchmark_fingerprint(body)}
    return GroundedSAM2DynamicAOIRun(
        canonical=canonical,
        keyframes=keyframes,
        report=report,
    )


def validate_grounded_sam2_run(
    run: GroundedSAM2DynamicAOIRun,
) -> GroundedSAM2DynamicAOIRun:
    """Revalidate a backend run before it is reused downstream."""
    if not isinstance(run, GroundedSAM2DynamicAOIRun):
        raise TypeError("run must be a GroundedSAM2DynamicAOIRun instance.")
    report = run.report
    if report.get("status") != "verified-backend-output":
        raise BenchmarkIntegrityError("Grounded-SAM-2 backend status drifted.")
    if report.get("backend") != "grounding-dino-plus-sam2":
        raise BenchmarkIntegrityError("Grounded-SAM-2 backend identity drifted.")
    if report.get("integration_contract_reference") != _GROUNDED_SAM2_REFERENCE:
        raise BenchmarkIntegrityError("Grounded-SAM-2 integration reference drifted.")
    if report.get("evaluation_timestamp_grid_generated") is not False:
        raise BenchmarkIntegrityError("Grounded-SAM-2 must not create an evaluation grid.")
    if report.get("empirical_performance_claim_created") is not False:
        raise BenchmarkIntegrityError("Grounded-SAM-2 backend output is not empirical validity.")
    if report.get("visus_source_authority_implied") is not False:
        raise BenchmarkIntegrityError("Grounded-SAM-2 backend cannot imply VISUS source authority.")

    output = report.get("output")
    if not isinstance(output, Mapping):
        raise BenchmarkIntegrityError("Grounded-SAM-2 output provenance is missing.")
    observed_table_fp = fingerprint_frame(run.canonical)
    if output.get("canonical_table_fingerprint_sha256") != observed_table_fp:
        raise BenchmarkIntegrityError("Grounded-SAM-2 canonical output fingerprint drifted.")
    if output.get("row_count") != len(run.canonical):
        raise BenchmarkIntegrityError("Grounded-SAM-2 canonical row count drifted.")
    if output.get("track_count") != run.canonical["aoi_id"].nunique():
        raise BenchmarkIntegrityError("Grounded-SAM-2 canonical track count drifted.")

    stored_report_fp = str(report.get("report_fingerprint_sha256", ""))
    body = {key: value for key, value in report.items() if key != "report_fingerprint_sha256"}
    if benchmark_fingerprint(body) != stored_report_fp:
        raise BenchmarkIntegrityError("Grounded-SAM-2 report fingerprint drifted.")
    if len(run.keyframes) != len(run.canonical):
        raise BenchmarkIntegrityError("Grounded-SAM-2 keyframe/cardinality binding drifted.")
    return run


def grounded_sam2_to_visus_prediction_table(
    run: GroundedSAM2DynamicAOIRun,
    *,
    stimulus_id: str,
) -> pd.DataFrame:
    """Convert one backend run to the schema accepted by VISUS prediction intake."""
    validate_grounded_sam2_run(run)
    stimulus = _resolved(stimulus_id, label="stimulus_id")
    required = [
        "frame_index",
        "aoi_id",
        "label",
        "xmin",
        "ymin",
        "xmax",
        "ymax",
        "confidence",
    ]
    missing = [column for column in required if column not in run.canonical.columns]
    if missing:
        raise SchemaError(f"Grounded-SAM-2 canonical output is missing columns: {missing}")
    table = run.canonical.loc[:, required].copy()
    table.insert(0, "stimulus_id", stimulus)
    return table


class HuggingFaceGroundedSAM2Runtime:
    """Lazy optional runtime using Transformers Grounding DINO and Meta SAM 2 APIs."""

    def __init__(self) -> None:
        self._versions: dict[str, str] = {}

    @staticmethod
    def _imports():
        try:
            import torch
            from PIL import Image
            from sam2.build_sam import build_sam2_video_predictor
            from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
        except ImportError as exc:
            raise OptionalDependencyError(
                "Grounded-SAM-2 runtime requires optional vision packages plus the official "
                "facebookresearch/sam2 package. Install GazeForge vision dependencies and SAM 2 "
                "from its official repository; base GazeForge intentionally does not vendor them."
            ) from exc
        return (
            torch,
            Image,
            build_sam2_video_predictor,
            AutoProcessor,
            AutoModelForZeroShotObjectDetection,
        )

    def detect(
        self,
        image_path: Path,
        prompt_text: str,
        config: GroundedSAM2Config,
    ) -> Sequence[GroundedSAM2Detection]:
        torch, Image, _, AutoProcessor, AutoModel = self._imports()
        processor = AutoProcessor.from_pretrained(
            config.grounding_model_id,
            revision=config.grounding_model_revision,
            local_files_only=bool(config.local_files_only),
        )
        model = AutoModel.from_pretrained(
            config.grounding_model_id,
            revision=config.grounding_model_revision,
            local_files_only=bool(config.local_files_only),
        ).to(config.device)
        image = Image.open(image_path).convert("RGB")
        inputs = processor(images=image, text=prompt_text, return_tensors="pt").to(config.device)
        with torch.no_grad():
            outputs = model(**inputs)
        results = processor.post_process_grounded_object_detection(
            outputs,
            inputs.input_ids,
            threshold=float(config.box_threshold),
            text_threshold=float(config.text_threshold),
            target_sizes=[image.size[::-1]],
        )[0]
        boxes = results["boxes"].detach().cpu().numpy()
        scores = results["scores"].detach().cpu().numpy()
        labels = results["labels"]
        return [
            GroundedSAM2Detection(
                label=str(label),
                score=float(score),
                box_xyxy=tuple(float(value) for value in box),
            )
            for label, score, box in zip(labels, scores, boxes, strict=True)
        ]

    def propagate(
        self,
        frame_dir: Path,
        seeds: Sequence[GroundedSAM2Seed],
        *,
        prompt_position: int,
        config: GroundedSAM2Config,
    ) -> Mapping[int, Mapping[int, np.ndarray]]:
        torch, _, build_predictor, _, _ = self._imports()
        predictor = build_predictor(
            config.sam2_model_cfg,
            str(Path(config.sam2_checkpoint_path).resolve()),
            device=config.device,
        )
        state = predictor.init_state(video_path=str(frame_dir))
        for seed in seeds:
            box = np.asarray(seed.box_xyxy, dtype=np.float32)
            predictor.add_new_points_or_box(
                inference_state=state,
                frame_idx=int(prompt_position),
                obj_id=int(seed.object_id),
                box=box,
            )
        segments: dict[int, dict[int, np.ndarray]] = {}
        with torch.inference_mode():
            for frame_position, object_ids, mask_logits in predictor.propagate_in_video(state):
                segments[int(frame_position)] = {
                    int(object_id): (mask_logits[index] > 0.0).detach().cpu().numpy()
                    for index, object_id in enumerate(object_ids)
                }
        return segments

    def runtime_metadata(self) -> Mapping[str, Any]:
        versions: dict[str, str] = {}
        for distribution in ("torch", "transformers", "Pillow"):
            try:
                versions[distribution] = importlib.metadata.version(distribution)
            except importlib.metadata.PackageNotFoundError:
                versions[distribution] = "unavailable"
        versions["sam2_code_revision_source"] = "caller-pinned-config"
        self._versions = versions
        return dict(versions)
