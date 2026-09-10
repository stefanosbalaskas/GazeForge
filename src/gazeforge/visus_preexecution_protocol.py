"""Frozen pre-execution protocol for VISUS Grounding DINO + SAM 2 validation."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError, SchemaError
from .grounded_sam2 import (
    GroundedSAM2Config,
    GroundedSAM2DynamicAOIRun,
    _prompt_labels,
    _validate_config,
    run_grounded_sam2_dynamic_aoi,
    validate_grounded_sam2_run,
)
from .video_frame_derivation import (
    VideoFrameDerivationRun,
    bind_grounded_sam2_frame_derivation,
    validate_video_frame_derivation_run,
)
from .visus_audit import VisusSourceAuditRun

_PROTOCOL_SCHEMA = "gazeforge-visus-grounded-sam2-preexecution-protocol-v1"
_PROTOCOL_FILENAME = "visus-grounded-sam2-preexecution-protocol.json"
_ALLOWED_OVERLAP_RULES = frozenset({"highest_confidence", "smallest_area", "first"})


@dataclass(frozen=True, slots=True)
class VisusGroundedSAM2StimulusPlan:
    """One predeclared VISUS stimulus plan before detector inference."""

    stimulus_id: str
    labels: tuple[str, ...]
    config: GroundedSAM2Config
    derivation: VideoFrameDerivationRun


@dataclass(slots=True)
class VisusGroundedSAM2PreexecutionProtocolRun:
    """Frozen protocol document and its deterministic identity."""

    protocol_path: Path
    protocol: dict[str, Any]
    protocol_fingerprint_sha256: str


@dataclass(slots=True)
class VisusProtocolBoundGroundedSAM2Run:
    """One backend execution bound to a frozen pre-execution protocol."""

    stimulus_id: str
    backend_run: GroundedSAM2DynamicAOIRun
    frame_derivation_binding: dict[str, Any]
    protocol_binding: dict[str, Any]


def _resolved(value: Any, *, label: str) -> str:
    text = str(value).strip()
    upper = text.upper()
    if not text or "REPLACE" in upper or "VERIFY" in upper:
        raise ValueError(f"{label} must be an explicit resolved value.")
    return text


def _valid_sha256(value: Any) -> bool:
    text = str(value).strip().lower()
    if len(text) != 64:
        return False
    return all(character in "0123456789abcdef" for character in text)


def _file_sha256(path: Path, *, label: str) -> tuple[int, str]:
    if path.is_symlink():
        raise BenchmarkIntegrityError(f"{label} must not be a symbolic link.")
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(block)
            digest.update(block)
    if size <= 0:
        raise BenchmarkIntegrityError(f"{label} cannot be empty.")
    return size, digest.hexdigest()


def _verify_audit(audit: VisusSourceAuditRun) -> dict[str, str]:
    if not isinstance(audit, VisusSourceAuditRun):
        raise TypeError("audit must be a VisusSourceAuditRun instance.")
    if audit.report.get("status") != "verified":
        raise BenchmarkIntegrityError(
            "VISUS pre-execution protocol requires a verified source audit."
        )
    if audit.spec.dataset_status != "empirical":
        raise BenchmarkIntegrityError(
            "VISUS pre-execution protocol requires an empirical source audit."
        )
    if not audit.spec.reuse_terms_verified or not audit.spec.analysis_use_permitted:
        raise BenchmarkIntegrityError(
            "VISUS pre-execution protocol requires reviewed reuse terms and analysis permission."
        )

    claimed = str(audit.report.get("report_fingerprint_sha256", ""))
    body = {
        key: value
        for key, value in audit.report.items()
        if key != "report_fingerprint_sha256"
    }
    if not _valid_sha256(claimed) or benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError("VISUS source-audit report fingerprint does not revalidate.")

    spec_fingerprint = str(audit.report.get("spec_fingerprint_sha256", ""))
    if (
        not _valid_sha256(spec_fingerprint)
        or benchmark_fingerprint(audit.spec.to_dict()) != spec_fingerprint
    ):
        raise BenchmarkIntegrityError("VISUS source-audit specification fingerprint drifted.")

    manifest_rows = [asdict(item.record) for item in audit.files]
    manifest_fingerprint = str(
        audit.report.get("inventory", {}).get("manifest_fingerprint_sha256", "")
    )
    if (
        not _valid_sha256(manifest_fingerprint)
        or benchmark_fingerprint(manifest_rows) != manifest_fingerprint
    ):
        raise BenchmarkIntegrityError("VISUS source-audit manifest fingerprint drifted.")

    return {
        "source_audit_report_fingerprint_sha256": claimed,
        "source_audit_spec_fingerprint_sha256": spec_fingerprint,
        "source_manifest_fingerprint_sha256": manifest_fingerprint,
    }


def _audited_videos(audit: VisusSourceAuditRun) -> dict[str, dict[str, Any]]:
    expected = {
        str(value)
        for value in audit.report.get("identity", {}).get("stimulus_ids", [])
    }
    if not expected:
        raise BenchmarkIntegrityError("VISUS source audit contains no stimulus identities.")

    grouped: dict[str, list[Any]] = {stimulus: [] for stimulus in expected}
    for item in audit.files:
        record = item.record
        if record.role == "video" and record.stimulus_id is not None:
            grouped.setdefault(str(record.stimulus_id), []).append(item)

    result: dict[str, dict[str, Any]] = {}
    for stimulus in sorted(expected):
        items = grouped.get(stimulus, [])
        if len(items) != 1:
            raise BenchmarkIntegrityError(
                "VISUS pre-execution protocol requires exactly one audited video per stimulus: "
                f"stimulus={stimulus!r}, count={len(items)}."
            )
        item = items[0]
        record = item.record
        local = Path(item.local_path).resolve()
        size, digest = _file_sha256(local, label=f"audited VISUS video {stimulus}")
        if size != int(record.bytes) or digest != record.sha256:
            raise BenchmarkIntegrityError(
                f"Audited VISUS video bytes changed for stimulus {stimulus!r}."
            )
        result[stimulus] = {
            "manifest_path": record.path,
            "local_path": local,
            "bytes": size,
            "sha256": digest,
        }
    return result


def _validate_reference_stream(
    audit: VisusSourceAuditRun,
    *,
    stimulus_ids: Sequence[str],
    reference_stream_id: str,
) -> str:
    stream = _resolved(reference_stream_id, label="reference_stream_id")
    streams = audit.report.get("annotation_provenance", {}).get(
        "streams_by_stimulus", {}
    )
    missing = [
        stimulus
        for stimulus in stimulus_ids
        if stream not in set(streams.get(stimulus, []))
    ]
    if missing:
        raise SchemaError(
            "Selected VISUS reference stream is not manifested for every stimulus: "
            f"missing={missing}."
        )
    return stream


def _timestamp_grid_record(
    stimulus_id: str,
    values: Sequence[float],
) -> dict[str, Any]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError(
            f"Timestamp grid for {stimulus_id!r} must be a sequence of numeric values."
        )
    timestamps = [float(value) for value in values]
    if not timestamps:
        raise SchemaError(f"Timestamp grid for {stimulus_id!r} cannot be empty.")
    if not all(math.isfinite(value) for value in timestamps):
        raise SchemaError(
            f"Timestamp grid for {stimulus_id!r} must contain only finite values."
        )
    if any(right <= left for left, right in zip(timestamps, timestamps[1:])):
        raise SchemaError(
            f"Timestamp grid for {stimulus_id!r} must be strictly increasing."
        )
    return {
        "stimulus_id": stimulus_id,
        "n_timestamps": len(timestamps),
        "first_timestamp_ms": timestamps[0],
        "last_timestamp_ms": timestamps[-1],
        "timestamp_grid_fingerprint_sha256": benchmark_fingerprint(timestamps),
        "timestamps_ms": timestamps,
    }


def _validate_registration(
    reference: str | None,
    timestamp: str | None,
) -> dict[str, Any]:
    if (reference is None) != (timestamp is None):
        raise ValueError(
            "external_registration_reference and external_registration_timestamp "
            "must be supplied together."
        )
    if reference is None:
        return {
            "external_registration_metadata_recorded": False,
            "external_registration_reference": None,
            "external_registration_timestamp": None,
            "formal_preregistration_verified": False,
        }

    resolved_reference = _resolved(
        reference,
        label="external_registration_reference",
    )
    resolved_timestamp = _resolved(
        timestamp,
        label="external_registration_timestamp",
    )
    try:
        parsed = datetime.fromisoformat(resolved_timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            "external_registration_timestamp must be a valid ISO-8601 timestamp."
        ) from exc
    if parsed.tzinfo is None:
        raise ValueError(
            "external_registration_timestamp must include a timezone offset."
        )
    return {
        "external_registration_metadata_recorded": True,
        "external_registration_reference": resolved_reference,
        "external_registration_timestamp": resolved_timestamp,
        "formal_preregistration_verified": False,
    }


def _plan_record(
    plan: VisusGroundedSAM2StimulusPlan,
    *,
    audited_video: Mapping[str, Any],
    audited_frame_rate_hz: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(plan, VisusGroundedSAM2StimulusPlan):
        raise TypeError(
            "plans_by_stimulus values must be VisusGroundedSAM2StimulusPlan objects."
        )
    stimulus = _resolved(plan.stimulus_id, label="stimulus_id")
    if not isinstance(plan.config, GroundedSAM2Config):
        raise TypeError("plan.config must be a GroundedSAM2Config instance.")
    validate_video_frame_derivation_run(plan.derivation)

    config_values = _validate_config(plan.config)
    canonical_labels, _, prompt_text = _prompt_labels(plan.labels)

    source_path = Path(plan.config.source_video_path).resolve()
    if source_path != audited_video["local_path"]:
        raise BenchmarkIntegrityError(
            f"Grounded-SAM-2 source path does not match audited video for {stimulus!r}."
        )
    if config_values["source_video_sha256"] != audited_video["sha256"]:
        raise BenchmarkIntegrityError(
            f"Grounded-SAM-2 source SHA does not match audited video for {stimulus!r}."
        )

    derivation_source = plan.derivation.report.get("source_video", {})
    if (
        plan.derivation.source_video_path.resolve() != audited_video["local_path"]
        or derivation_source.get("sha256") != audited_video["sha256"]
        or int(derivation_source.get("bytes", -1)) != int(audited_video["bytes"])
    ):
        raise BenchmarkIntegrityError(
            f"Frame derivation is not bound to the audited video for {stimulus!r}."
        )

    derivation_frames = plan.derivation.report.get("frames", {})
    derivation_base = int(derivation_frames.get("frame_index_base", -1))
    if config_values["frame_index_base"] != derivation_base:
        raise BenchmarkIntegrityError(
            f"Grounded-SAM-2 frame index base differs from derivation for {stimulus!r}."
        )
    if not math.isclose(
        float(config_values["frame_rate_hz"]),
        float(audited_frame_rate_hz),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise BenchmarkIntegrityError(
            f"Grounded-SAM-2 frame rate differs from audited VISUS rate for {stimulus!r}."
        )

    derivation_fingerprint = str(
        plan.derivation.report.get("report_fingerprint_sha256", "")
    )
    expected_basis = (
        "GazeForge mechanically verified video-frame derivation "
        + derivation_fingerprint
    )
    if config_values["frame_extraction_basis"] != expected_basis:
        raise BenchmarkIntegrityError(
            f"Grounded-SAM-2 frame_extraction_basis is not the exact verified "
            f"derivation identity for {stimulus!r}."
        )

    first_frame = int(derivation_frames.get("first_frame_index", -1))
    last_frame = int(derivation_frames.get("last_frame_index", -1))
    prompt_frame = int(config_values["prompt_frame_index"])
    if prompt_frame < first_frame or prompt_frame > last_frame:
        raise SchemaError(
            f"prompt_frame_index lies outside the derived frames for {stimulus!r}."
        )

    checkpoint = Path(plan.config.sam2_checkpoint_path).resolve()
    checkpoint_size, checkpoint_sha = _file_sha256(
        checkpoint,
        label="SAM 2 checkpoint",
    )
    if checkpoint_sha != config_values["sam2_checkpoint_sha256"]:
        raise BenchmarkIntegrityError(
            f"SAM 2 checkpoint bytes do not match the pinned SHA for {stimulus!r}."
        )

    model_name = "Grounding DINO + SAM 2"
    model_version = (
        f"{config_values['grounding_model_id']}@{config_values['grounding_model_revision']}+"
        f"sam2@{config_values['sam2_code_revision']}+"
        f"{config_values['sam2_model_cfg']}@{checkpoint_sha[:12]}"
    )
    model_policy = {
        "model_name": model_name,
        "model_version": model_version,
        "grounding_model_id": config_values["grounding_model_id"],
        "grounding_model_revision": config_values["grounding_model_revision"],
        "sam2_code_revision": config_values["sam2_code_revision"],
        "sam2_model_cfg": config_values["sam2_model_cfg"],
        "sam2_checkpoint_basename": checkpoint.name,
        "sam2_checkpoint_bytes": checkpoint_size,
        "sam2_checkpoint_sha256": checkpoint_sha,
        "frame_rate_hz": float(config_values["frame_rate_hz"]),
        "frame_index_base": int(config_values["frame_index_base"]),
        "box_threshold": float(config_values["box_threshold"]),
        "text_threshold": float(config_values["text_threshold"]),
        "device": config_values["device"],
        "local_files_only": bool(config_values["local_files_only"]),
        "min_mask_pixels": int(config_values["min_mask_pixels"]),
    }

    extractor = plan.derivation.report.get("extractor", {})
    record = {
        "stimulus_id": stimulus,
        "semantic_labels": canonical_labels,
        "prompt_text": prompt_text,
        "prompt_frame_index": prompt_frame,
        "source_video": {
            "manifest_path": audited_video["manifest_path"],
            "bytes": int(audited_video["bytes"]),
            "sha256": audited_video["sha256"],
        },
        "frame_derivation": {
            "report_fingerprint_sha256": derivation_fingerprint,
            "frame_manifest_fingerprint_sha256": derivation_frames[
                "manifest_fingerprint_sha256"
            ],
            "frame_count": int(derivation_frames["count"]),
            "frame_index_base": derivation_base,
            "first_frame_index": first_frame,
            "last_frame_index": last_frame,
            "extractor_name": extractor.get("name"),
            "extractor_version": extractor.get("version"),
            "extractor_artifact_sha256": extractor.get("artifact_sha256"),
        },
        "frame_extraction_basis": expected_basis,
    }
    return record, model_policy


def _exact_mapping_keys(
    mapping: Mapping[str, Any],
    expected: Sequence[str],
    *,
    label: str,
) -> None:
    observed = {str(key) for key in mapping}
    expected_set = set(expected)
    missing = sorted(expected_set - observed)
    extra = sorted(observed - expected_set)
    if missing or extra:
        raise SchemaError(
            f"{label} must exactly cover audited VISUS stimuli: "
            f"missing={missing}, extra={extra}."
        )


def build_visus_grounded_sam2_preexecution_protocol(
    audit: VisusSourceAuditRun,
    plans_by_stimulus: Mapping[str, VisusGroundedSAM2StimulusPlan],
    timestamps_by_stimulus: Mapping[str, Sequence[float]],
    *,
    reference_stream_id: str,
    timestamp_grid_basis: str,
    max_interpolation_gap_ms: float,
    min_iou: float = 0.50,
    require_label_match: bool = True,
    fixation_assignment_planned: bool = False,
    overlap_rule: str = "highest_confidence",
    external_registration_reference: str | None = None,
    external_registration_timestamp: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic protocol that must be frozen before backend inference."""
    source_identity = _verify_audit(audit)
    videos = _audited_videos(audit)
    stimuli = sorted(videos)
    if not isinstance(plans_by_stimulus, Mapping):
        raise TypeError("plans_by_stimulus must be a mapping.")
    if not isinstance(timestamps_by_stimulus, Mapping):
        raise TypeError("timestamps_by_stimulus must be a mapping.")
    _exact_mapping_keys(plans_by_stimulus, stimuli, label="plans_by_stimulus")
    _exact_mapping_keys(
        timestamps_by_stimulus,
        stimuli,
        label="timestamps_by_stimulus",
    )

    reference_stream = _validate_reference_stream(
        audit,
        stimulus_ids=stimuli,
        reference_stream_id=reference_stream_id,
    )
    grid_basis = _resolved(timestamp_grid_basis, label="timestamp_grid_basis")

    gap = float(max_interpolation_gap_ms)
    if not math.isfinite(gap) or gap < 0:
        raise ValueError("max_interpolation_gap_ms must be finite and non-negative.")
    threshold = float(min_iou)
    if not math.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("min_iou must be finite and in [0, 1].")
    overlap = str(overlap_rule).strip()
    if overlap not in _ALLOWED_OVERLAP_RULES:
        raise ValueError(
            "overlap_rule must be highest_confidence, smallest_area, or first."
        )

    audited_rate = float(audit.spec.published_video_frame_rate_hz)
    stimulus_records: list[dict[str, Any]] = []
    model_policy: dict[str, Any] | None = None
    for stimulus in stimuli:
        plan = plans_by_stimulus[stimulus]
        if str(plan.stimulus_id).strip() != stimulus:
            raise SchemaError(
                "Plan mapping key must equal the plan's explicit stimulus_id: "
                f"key={stimulus!r}, plan={plan.stimulus_id!r}."
            )
        record, policy = _plan_record(
            plan,
            audited_video=videos[stimulus],
            audited_frame_rate_hz=audited_rate,
        )
        if model_policy is None:
            model_policy = policy
        elif policy != model_policy:
            raise BenchmarkIntegrityError(
                "All VISUS stimuli must share one frozen model/checkpoint/threshold policy; "
                f"policy drift detected at {stimulus!r}."
            )
        stimulus_records.append(record)
    assert model_policy is not None

    timestamp_records = [
        _timestamp_grid_record(stimulus, timestamps_by_stimulus[stimulus])
        for stimulus in stimuli
    ]
    registration = _validate_registration(
        external_registration_reference,
        external_registration_timestamp,
    )

    body: dict[str, Any] = {
        "schema": _PROTOCOL_SCHEMA,
        "status": "frozen-pre-execution-protocol",
        "protocol_scope": (
            "immutable-model-and-evaluation-parameter-declaration-to-be-consumed-"
            "before-grounded-sam2-inference"
        ),
        "source": {
            **source_identity,
            "dataset": "VISUS",
            "analysis_use_permitted": True,
            "reuse_terms_verified": True,
        },
        "global_model_policy": model_policy,
        "stimuli": stimulus_records,
        "evaluation": {
            "reference_stream_id": reference_stream,
            "timestamp_grid_basis": grid_basis,
            "timestamp_grids": timestamp_records,
            "max_interpolation_gap_ms": gap,
            "min_iou": threshold,
            "require_label_match": bool(require_label_match),
            "fixation_assignment_planned": bool(fixation_assignment_planned),
            "overlap_rule": overlap,
            "prediction_emission_grid_used": False,
            "complete_audited_stimulus_coverage_required": True,
        },
        "registration": registration,
        "protocol_frozen_before_backend_inference_claim_scope": (
            "only executions performed through the protocol-bound runner"
        ),
        "formal_preregistration_verified": False,
        "empirical_performance_claim_created": False,
        "dataset_source_authority_promoted": False,
        "dataset_rights_promoted": False,
        "source_authority_certificate_required_separately": True,
        "claim_limits": [
            (
                "A protocol fingerprint proves immutable content identity, not that no "
                "researcher inspected earlier outputs."
            ),
            (
                "External registration metadata, when present, are recorded but are not "
                "independently verified by this layer."
            ),
            (
                "Formal preregistration requires separately trusted external timestamp or "
                "registration evidence."
            ),
            (
                "This protocol does not establish VISUS source authority, redistribution "
                "rights, human-human independence, or model performance."
            ),
            "Prediction emission frames cannot define the model-human evaluation grid.",
        ],
    }
    return {
        **body,
        "protocol_fingerprint_sha256": benchmark_fingerprint(body),
    }


def validate_visus_grounded_sam2_preexecution_protocol_payload(
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a frozen protocol document without asserting local temporal precedence."""
    if not isinstance(protocol, Mapping):
        raise TypeError("protocol must be a mapping.")
    value = dict(protocol)
    required = {
        "schema",
        "status",
        "protocol_scope",
        "source",
        "global_model_policy",
        "stimuli",
        "evaluation",
        "registration",
        "protocol_frozen_before_backend_inference_claim_scope",
        "formal_preregistration_verified",
        "empirical_performance_claim_created",
        "dataset_source_authority_promoted",
        "dataset_rights_promoted",
        "source_authority_certificate_required_separately",
        "claim_limits",
        "protocol_fingerprint_sha256",
    }
    missing = sorted(required - set(value))
    extra = sorted(set(value) - required)
    if missing or extra:
        raise BenchmarkIntegrityError(
            f"VISUS pre-execution protocol keys drifted: missing={missing}, extra={extra}."
        )
    if value["schema"] != _PROTOCOL_SCHEMA:
        raise BenchmarkIntegrityError("VISUS pre-execution protocol schema drifted.")
    if value["status"] != "frozen-pre-execution-protocol":
        raise BenchmarkIntegrityError("VISUS pre-execution protocol status drifted.")

    claimed = str(value["protocol_fingerprint_sha256"])
    body = {
        key: item
        for key, item in value.items()
        if key != "protocol_fingerprint_sha256"
    }
    if not _valid_sha256(claimed) or benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError(
            "VISUS pre-execution protocol fingerprint does not revalidate."
        )

    for field in (
        "formal_preregistration_verified",
        "empirical_performance_claim_created",
        "dataset_source_authority_promoted",
        "dataset_rights_promoted",
    ):
        if value[field] is not False:
            raise BenchmarkIntegrityError(
                f"VISUS pre-execution protocol cannot promote {field}."
            )
    if value["source_authority_certificate_required_separately"] is not True:
        raise BenchmarkIntegrityError(
            "VISUS pre-execution protocol must keep source authority separate."
        )

    source = value["source"]
    policy = value["global_model_policy"]
    stimuli = value["stimuli"]
    evaluation = value["evaluation"]
    registration = value["registration"]
    if not isinstance(source, Mapping) or not isinstance(policy, Mapping):
        raise BenchmarkIntegrityError("VISUS pre-execution source/model policy is invalid.")
    if not isinstance(stimuli, list) or not stimuli:
        raise BenchmarkIntegrityError("VISUS pre-execution stimulus plans are missing.")
    if not isinstance(evaluation, Mapping) or not isinstance(registration, Mapping):
        raise BenchmarkIntegrityError(
            "VISUS pre-execution evaluation/registration sections are invalid."
        )

    for field in (
        "source_audit_report_fingerprint_sha256",
        "source_audit_spec_fingerprint_sha256",
        "source_manifest_fingerprint_sha256",
    ):
        if not _valid_sha256(source.get(field)):
            raise BenchmarkIntegrityError(
                f"VISUS pre-execution source fingerprint {field!r} is invalid."
            )
    if source.get("analysis_use_permitted") is not True:
        raise BenchmarkIntegrityError(
            "VISUS pre-execution protocol lost analysis permission."
        )
    if source.get("reuse_terms_verified") is not True:
        raise BenchmarkIntegrityError(
            "VISUS pre-execution protocol lost reviewed reuse terms."
        )

    stimulus_ids: list[str] = []
    for record in stimuli:
        if not isinstance(record, Mapping):
            raise BenchmarkIntegrityError("VISUS pre-execution stimulus record is invalid.")
        stimulus = str(record.get("stimulus_id", "")).strip()
        if not stimulus or stimulus in stimulus_ids:
            raise BenchmarkIntegrityError(
                "VISUS pre-execution stimulus identities must be unique and resolved."
            )
        stimulus_ids.append(stimulus)
        labels = record.get("semantic_labels")
        prompt = str(record.get("prompt_text", "")).strip()
        if not isinstance(labels, list) or not labels or not prompt:
            raise BenchmarkIntegrityError(
                f"VISUS pre-execution semantic prompt is invalid for {stimulus!r}."
            )
        source_video = record.get("source_video")
        derivation = record.get("frame_derivation")
        if not isinstance(source_video, Mapping) or not isinstance(derivation, Mapping):
            raise BenchmarkIntegrityError(
                f"VISUS pre-execution source/derivation record is invalid for {stimulus!r}."
            )
        if not _valid_sha256(source_video.get("sha256")):
            raise BenchmarkIntegrityError(
                f"VISUS pre-execution video SHA is invalid for {stimulus!r}."
            )
        for field in (
            "report_fingerprint_sha256",
            "frame_manifest_fingerprint_sha256",
            "extractor_artifact_sha256",
        ):
            if not _valid_sha256(derivation.get(field)):
                raise BenchmarkIntegrityError(
                    f"VISUS pre-execution derivation {field!r} is invalid "
                    f"for {stimulus!r}."
                )

    grids = evaluation.get("timestamp_grids")
    if not isinstance(grids, list) or len(grids) != len(stimulus_ids):
        raise BenchmarkIntegrityError(
            "VISUS pre-execution timestamp-grid coverage is invalid."
        )
    grid_ids: list[str] = []
    for record in grids:
        if not isinstance(record, Mapping):
            raise BenchmarkIntegrityError(
                "VISUS pre-execution timestamp-grid record is invalid."
            )
        stimulus = str(record.get("stimulus_id", "")).strip()
        timestamps = record.get("timestamps_ms")
        if not isinstance(timestamps, list):
            raise BenchmarkIntegrityError(
                f"VISUS pre-execution timestamp values are missing for {stimulus!r}."
            )
        canonical = _timestamp_grid_record(stimulus, timestamps)
        if dict(record) != canonical:
            raise BenchmarkIntegrityError(
                f"VISUS pre-execution timestamp-grid fingerprint drifted for {stimulus!r}."
            )
        grid_ids.append(stimulus)
    if grid_ids != stimulus_ids:
        raise BenchmarkIntegrityError(
            "VISUS pre-execution stimulus/grid ordering or coverage drifted."
        )
    if evaluation.get("prediction_emission_grid_used") is not False:
        raise BenchmarkIntegrityError(
            "VISUS pre-execution protocol cannot use prediction emissions as the grid."
        )
    if evaluation.get("complete_audited_stimulus_coverage_required") is not True:
        raise BenchmarkIntegrityError(
            "VISUS pre-execution protocol requires complete stimulus coverage."
        )

    if registration.get("formal_preregistration_verified") is not False:
        raise BenchmarkIntegrityError(
            "VISUS pre-execution protocol cannot verify formal preregistration."
        )
    return value


def freeze_visus_grounded_sam2_preexecution_protocol(
    audit: VisusSourceAuditRun,
    plans_by_stimulus: Mapping[str, VisusGroundedSAM2StimulusPlan],
    timestamps_by_stimulus: Mapping[str, Sequence[float]],
    output_path: str | Path,
    *,
    reference_stream_id: str,
    timestamp_grid_basis: str,
    max_interpolation_gap_ms: float,
    min_iou: float = 0.50,
    require_label_match: bool = True,
    fixation_assignment_planned: bool = False,
    overlap_rule: str = "highest_confidence",
    external_registration_reference: str | None = None,
    external_registration_timestamp: str | None = None,
    overwrite: bool = False,
) -> VisusGroundedSAM2PreexecutionProtocolRun:
    """Freeze exact model/evaluation choices before a protocol-bound backend execution."""
    protocol = build_visus_grounded_sam2_preexecution_protocol(
        audit,
        plans_by_stimulus,
        timestamps_by_stimulus,
        reference_stream_id=reference_stream_id,
        timestamp_grid_basis=timestamp_grid_basis,
        max_interpolation_gap_ms=max_interpolation_gap_ms,
        min_iou=min_iou,
        require_label_match=require_label_match,
        fixation_assignment_planned=fixation_assignment_planned,
        overlap_rule=overlap_rule,
        external_registration_reference=external_registration_reference,
        external_registration_timestamp=external_registration_timestamp,
    )
    validated = validate_visus_grounded_sam2_preexecution_protocol_payload(protocol)
    path = Path(output_path)
    if path.exists() and path.is_dir():
        path = path / _PROTOCOL_FILENAME
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(validated, indent=2, sort_keys=True) + "\n"
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(path)

    loaded = load_visus_grounded_sam2_preexecution_protocol(path)
    return loaded


def load_visus_grounded_sam2_preexecution_protocol(
    path: str | Path,
) -> VisusGroundedSAM2PreexecutionProtocolRun:
    """Load and structurally revalidate one frozen protocol file."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkIntegrityError(
            "VISUS pre-execution protocol is not valid JSON."
        ) from exc
    validated = validate_visus_grounded_sam2_preexecution_protocol_payload(payload)
    fingerprint = str(validated["protocol_fingerprint_sha256"])
    return VisusGroundedSAM2PreexecutionProtocolRun(
        protocol_path=source,
        protocol=validated,
        protocol_fingerprint_sha256=fingerprint,
    )


def _assert_protocol_file_unchanged(
    run: VisusGroundedSAM2PreexecutionProtocolRun,
) -> dict[str, Any]:
    if not isinstance(run, VisusGroundedSAM2PreexecutionProtocolRun):
        raise TypeError(
            "protocol_run must be a VisusGroundedSAM2PreexecutionProtocolRun instance."
        )
    loaded = load_visus_grounded_sam2_preexecution_protocol(run.protocol_path)
    if (
        loaded.protocol_fingerprint_sha256 != run.protocol_fingerprint_sha256
        or loaded.protocol != run.protocol
    ):
        raise BenchmarkIntegrityError(
            "Frozen VISUS pre-execution protocol file changed after loading."
        )
    return loaded.protocol


def replay_visus_grounded_sam2_preexecution_protocol(
    protocol_run: VisusGroundedSAM2PreexecutionProtocolRun,
    audit: VisusSourceAuditRun,
    plans_by_stimulus: Mapping[str, VisusGroundedSAM2StimulusPlan],
    timestamps_by_stimulus: Mapping[str, Sequence[float]],
) -> None:
    """Rebuild the protocol from current local inputs and require exact identity."""
    protocol = _assert_protocol_file_unchanged(protocol_run)
    evaluation = protocol["evaluation"]
    registration = protocol["registration"]
    rebuilt = build_visus_grounded_sam2_preexecution_protocol(
        audit,
        plans_by_stimulus,
        timestamps_by_stimulus,
        reference_stream_id=evaluation["reference_stream_id"],
        timestamp_grid_basis=evaluation["timestamp_grid_basis"],
        max_interpolation_gap_ms=evaluation["max_interpolation_gap_ms"],
        min_iou=evaluation["min_iou"],
        require_label_match=evaluation["require_label_match"],
        fixation_assignment_planned=evaluation["fixation_assignment_planned"],
        overlap_rule=evaluation["overlap_rule"],
        external_registration_reference=registration[
            "external_registration_reference"
        ],
        external_registration_timestamp=registration[
            "external_registration_timestamp"
        ],
    )
    if rebuilt != protocol:
        raise BenchmarkIntegrityError(
            "Current VISUS model/evaluation inputs no longer match the frozen protocol."
        )


def _protocol_plan_record(
    protocol: Mapping[str, Any],
    stimulus_id: str,
) -> dict[str, Any]:
    matches = [
        dict(record)
        for record in protocol["stimuli"]
        if record.get("stimulus_id") == stimulus_id
    ]
    if len(matches) != 1:
        raise BenchmarkIntegrityError(
            f"Frozen VISUS protocol lacks one unique plan for {stimulus_id!r}."
        )
    return matches[0]


def _assert_audit_identity_matches_protocol(
    audit: VisusSourceAuditRun,
    protocol: Mapping[str, Any],
) -> None:
    identity = _verify_audit(audit)
    observed = {key: protocol["source"].get(key) for key in identity}
    if observed != identity:
        raise BenchmarkIntegrityError(
            "Current VISUS source audit does not match the frozen pre-execution protocol."
        )


def _assert_plan_matches_protocol(
    protocol: Mapping[str, Any],
    audit: VisusSourceAuditRun,
    plan: VisusGroundedSAM2StimulusPlan,
) -> dict[str, Any]:
    stimulus = str(plan.stimulus_id).strip()
    videos = _audited_videos(audit)
    if stimulus not in videos:
        raise SchemaError(f"Stimulus {stimulus!r} is not in the audited VISUS source.")
    record, policy = _plan_record(
        plan,
        audited_video=videos[stimulus],
        audited_frame_rate_hz=float(audit.spec.published_video_frame_rate_hz),
    )
    if record != _protocol_plan_record(protocol, stimulus):
        raise BenchmarkIntegrityError(
            f"Current Grounded-SAM-2 plan differs from the frozen protocol for {stimulus!r}."
        )
    if policy != protocol["global_model_policy"]:
        raise BenchmarkIntegrityError(
            f"Current model policy differs from the frozen protocol for {stimulus!r}."
        )
    return record


def bind_grounded_sam2_to_preexecution_protocol(
    protocol_run: VisusGroundedSAM2PreexecutionProtocolRun,
    audit: VisusSourceAuditRun,
    plan: VisusGroundedSAM2StimulusPlan,
    backend_run: GroundedSAM2DynamicAOIRun,
    *,
    protocol_validated_before_backend_call: bool,
) -> dict[str, Any]:
    """Bind one backend output to the exact frozen stimulus plan it consumed."""
    protocol = _assert_protocol_file_unchanged(protocol_run)
    _assert_audit_identity_matches_protocol(audit, protocol)
    plan_record = _assert_plan_matches_protocol(protocol, audit, plan)
    validate_grounded_sam2_run(backend_run)
    report = backend_run.report

    if report.get("semantic_labels") != plan_record["semantic_labels"]:
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 semantic labels differ from the frozen protocol."
        )
    if report.get("prompt_text") != plan_record["prompt_text"]:
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 prompt text differs from the frozen protocol."
        )
    policy = protocol["global_model_policy"]
    if (
        report.get("model_name") != policy["model_name"]
        or report.get("model_version") != policy["model_version"]
    ):
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 model identity differs from the frozen protocol."
        )

    model_identity = report.get("model_identity", {})
    expected_model_identity = {
        "grounding_model_id": policy["grounding_model_id"],
        "grounding_model_revision": policy["grounding_model_revision"],
        "sam2_code_revision": policy["sam2_code_revision"],
        "sam2_model_cfg": policy["sam2_model_cfg"],
        "sam2_checkpoint_basename": policy["sam2_checkpoint_basename"],
        "sam2_checkpoint_bytes": policy["sam2_checkpoint_bytes"],
        "sam2_checkpoint_sha256": policy["sam2_checkpoint_sha256"],
    }
    if {key: model_identity.get(key) for key in expected_model_identity} != (
        expected_model_identity
    ):
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 checkpoint/revision identity differs from the frozen protocol."
        )

    source = report.get("source_video", {})
    frames = report.get("frames", {})
    config = report.get("config", {})
    if source.get("sha256") != plan_record["source_video"]["sha256"]:
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 source video differs from the frozen protocol."
        )
    if (
        frames.get("manifest_fingerprint_sha256")
        != plan_record["frame_derivation"]["frame_manifest_fingerprint_sha256"]
    ):
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 frame manifest differs from the frozen protocol."
        )
    if frames.get("prompt_frame_index") != plan_record["prompt_frame_index"]:
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 prompt frame differs from the frozen protocol."
        )

    expected_config = {
        "grounding_model_id": policy["grounding_model_id"],
        "grounding_model_revision": policy["grounding_model_revision"],
        "sam2_model_cfg": policy["sam2_model_cfg"],
        "sam2_code_revision": policy["sam2_code_revision"],
        "frame_extraction_basis": plan_record["frame_extraction_basis"],
        "frame_rate_hz": policy["frame_rate_hz"],
        "frame_index_base": policy["frame_index_base"],
        "prompt_frame_index": plan_record["prompt_frame_index"],
        "box_threshold": policy["box_threshold"],
        "text_threshold": policy["text_threshold"],
        "device": policy["device"],
        "local_files_only": policy["local_files_only"],
        "min_mask_pixels": policy["min_mask_pixels"],
    }
    if {key: config.get(key) for key in expected_config} != expected_config:
        raise BenchmarkIntegrityError(
            "Grounded-SAM-2 runtime config differs from the frozen protocol."
        )

    body = {
        "schema_version": 1,
        "binding_type": "visus-grounded-sam2-preexecution-protocol-to-backend",
        "protocol_fingerprint_sha256": protocol_run.protocol_fingerprint_sha256,
        "stimulus_id": plan_record["stimulus_id"],
        "frame_derivation_report_fingerprint_sha256": plan_record[
            "frame_derivation"
        ]["report_fingerprint_sha256"],
        "grounded_sam2_report_fingerprint_sha256": report[
            "report_fingerprint_sha256"
        ],
        "protocol_validated_before_backend_call": bool(
            protocol_validated_before_backend_call
        ),
        "local_execution_order_verified": bool(
            protocol_validated_before_backend_call
        ),
        "formal_preregistration_verified": False,
        "empirical_performance_claim_created": False,
        "dataset_source_authority_promoted": False,
        "dataset_rights_promoted": False,
    }
    if not body["protocol_validated_before_backend_call"]:
        raise BenchmarkIntegrityError(
            "Pre-execution binding requires protocol validation before the backend call."
        )
    return {
        **body,
        "binding_fingerprint_sha256": benchmark_fingerprint(body),
    }


def run_grounded_sam2_from_preexecution_protocol(
    protocol_run: VisusGroundedSAM2PreexecutionProtocolRun,
    audit: VisusSourceAuditRun,
    plan: VisusGroundedSAM2StimulusPlan,
    *,
    runtime: Any = None,
) -> VisusProtocolBoundGroundedSAM2Run:
    """Validate the frozen plan first, then execute exactly that Grounded-SAM-2 plan."""
    protocol = _assert_protocol_file_unchanged(protocol_run)
    _assert_audit_identity_matches_protocol(audit, protocol)
    _assert_plan_matches_protocol(protocol, audit, plan)

    backend_run = run_grounded_sam2_dynamic_aoi(
        plan.derivation.frame_dir,
        labels=plan.labels,
        config=plan.config,
        runtime=runtime,
    )
    frame_binding = bind_grounded_sam2_frame_derivation(
        plan.derivation,
        backend_run,
    )
    protocol_binding = bind_grounded_sam2_to_preexecution_protocol(
        protocol_run,
        audit,
        plan,
        backend_run,
        protocol_validated_before_backend_call=True,
    )
    return VisusProtocolBoundGroundedSAM2Run(
        stimulus_id=plan.stimulus_id,
        backend_run=backend_run,
        frame_derivation_binding=frame_binding,
        protocol_binding=protocol_binding,
    )


def validation_settings_from_preexecution_protocol(
    protocol_run: VisusGroundedSAM2PreexecutionProtocolRun,
) -> dict[str, Any]:
    """Return the exact frozen model-human evaluation settings for downstream use."""
    protocol = _assert_protocol_file_unchanged(protocol_run)
    evaluation = protocol["evaluation"]
    timestamps = {
        record["stimulus_id"]: list(record["timestamps_ms"])
        for record in evaluation["timestamp_grids"]
    }
    return {
        "timestamps_by_stimulus": timestamps,
        "reference_stream_id": evaluation["reference_stream_id"],
        "timestamp_grid_basis": evaluation["timestamp_grid_basis"],
        "max_interpolation_gap_ms": evaluation["max_interpolation_gap_ms"],
        "min_iou": evaluation["min_iou"],
        "require_label_match": evaluation["require_label_match"],
        "fixation_assignment_planned": evaluation["fixation_assignment_planned"],
        "overlap_rule": evaluation["overlap_rule"],
    }
