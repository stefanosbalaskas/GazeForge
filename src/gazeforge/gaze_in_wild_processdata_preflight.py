"""Fail-closed structural preflight for quarantined Gaze-in-the-Wild ProcessData files."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat

from .benchmarks import benchmark_fingerprint
from .exceptions import SchemaError
from .native_event import file_sha256


@dataclass(slots=True)
class GazeInWildProcessDataPreflight:
    """Structural facts extracted from one quarantined ``ProcessData`` MATLAB file.

    This object is deliberately narrower than :class:`GazeInWildSourceAuditSpec`.
    It can verify that a single first-party or candidate ``ProcessData`` object is
    structurally compatible with the coordinate side of the GazeForge adapter, but
    it cannot establish corpus identity, rights, ``LabelData`` recovery, participant
    mapping, coordinate semantics, or empirical eligibility.
    """

    path: str
    sha256: str
    bytes: int
    participant_index: int
    trial_index: int
    stored_rate_hz: float
    inferred_processed_rate_hz: float
    timestamp_count: int
    timestamp_start_s: float
    timestamp_end_s: float
    por_shape: tuple[int, int]
    confidence_shape: tuple[int]
    scene_resolution_px: tuple[int, int]
    labels_present: bool
    labels_shape: tuple[int] | None
    top_level_labeldata_present: bool
    adapter_coordinate_fields_compatible: bool
    timestamp_grid_valid: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _field(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping) and name in obj:
        return obj[name]
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, np.ndarray) and obj.dtype.names and name in obj.dtype.names:
        value = obj[name]
        while isinstance(value, np.ndarray) and value.size == 1:
            value = value.reshape(-1)[0]
        return value
    raise SchemaError(f"Gaze-in-the-Wild ProcessData is missing field {name!r}.")


def _numeric_vector(
    value: Any,
    *,
    name: str,
    require_finite: bool = True,
) -> np.ndarray:
    try:
        vector = np.asarray(value, dtype=float).reshape(-1)
    except (TypeError, ValueError) as exc:
        raise SchemaError(f"Gaze-in-the-Wild ProcessData field {name!r} must be numeric.") from exc
    if not len(vector):
        raise SchemaError(f"Gaze-in-the-Wild ProcessData field {name!r} cannot be empty.")
    if require_finite and np.any(~np.isfinite(vector)):
        raise SchemaError(f"Gaze-in-the-Wild ProcessData field {name!r} must be finite.")
    return vector


def _positive_integer_scalar(value: Any, *, name: str) -> int:
    vector = _numeric_vector(value, name=name)
    if len(vector) != 1:
        raise SchemaError(f"Gaze-in-the-Wild ProcessData field {name!r} must be scalar.")
    rounded = float(np.rint(vector[0]))
    if vector[0] <= 0 or not np.isclose(vector[0], rounded, rtol=0.0, atol=1e-9):
        raise SchemaError(
            f"Gaze-in-the-Wild ProcessData field {name!r} must be a positive integer."
        )
    return int(rounded)


def _positive_rate(value: Any, *, name: str) -> float:
    vector = _numeric_vector(value, name=name)
    if len(vector) != 1 or vector[0] <= 0:
        raise SchemaError(
            f"Gaze-in-the-Wild ProcessData field {name!r} must be one positive rate."
        )
    return float(vector[0])


def _timestamp_grid(value: Any) -> tuple[np.ndarray, float]:
    times_s = _numeric_vector(value, name="T")
    if len(times_s) < 2:
        raise SchemaError("Gaze-in-the-Wild ProcessData.T requires at least two timestamps.")
    diffs = np.diff(times_s)
    if np.any(diffs <= 0):
        raise SchemaError("Gaze-in-the-Wild ProcessData.T must be strictly increasing.")
    median_dt_s = float(np.median(diffs))
    inferred_rate_hz = 1.0 / median_dt_s
    if not np.isfinite(inferred_rate_hz) or inferred_rate_hz <= 0:
        raise SchemaError("Could not infer a valid processed rate from ProcessData.T.")
    return times_s, float(inferred_rate_hz)


def _por_shape(value: Any, *, n_samples: int) -> tuple[int, int]:
    try:
        por = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise SchemaError("Gaze-in-the-Wild ProcessData.ETG.POR must be numeric.") from exc
    por = np.squeeze(por)
    if por.ndim != 2:
        raise SchemaError("Gaze-in-the-Wild ProcessData.ETG.POR must be two-dimensional.")
    if por.shape not in {(n_samples, 2), (2, n_samples)}:
        raise SchemaError(
            "Gaze-in-the-Wild ProcessData.ETG.POR must be N×2 or 2×N and match ProcessData.T."
        )
    return int(por.shape[0]), int(por.shape[1])


def _scene_resolution(value: Any) -> tuple[int, int]:
    resolution = _numeric_vector(value, name="ETG.SceneResolution")
    if len(resolution) != 2:
        raise SchemaError("Gaze-in-the-Wild ETG.SceneResolution must contain width and height.")
    rounded = np.rint(resolution)
    if np.any(resolution <= 0) or not np.allclose(resolution, rounded, rtol=0.0, atol=1e-9):
        raise SchemaError(
            "Gaze-in-the-Wild ETG.SceneResolution must contain positive integer pixels."
        )
    return int(rounded[0]), int(rounded[1])


def preflight_gaze_in_wild_processdata(
    path: str | Path,
    *,
    expected_sha256: str | None = None,
    expected_bytes: int | None = None,
) -> GazeInWildProcessDataPreflight:
    """Inspect one quarantined ``ProcessData`` file without creating empirical evidence.

    The preflight verifies exact bytes/hash when expected values are supplied and then
    checks the fields consumed by GazeForge's coordinate adapter. It never interprets
    ``ETG.Labels`` as a substitute for separately distributed ``LabelData``.
    """
    mat_path = Path(path)
    if not mat_path.is_file():
        raise FileNotFoundError(mat_path)

    observed_bytes = mat_path.stat().st_size
    observed_sha256 = file_sha256(mat_path)
    if expected_bytes is not None and observed_bytes != int(expected_bytes):
        raise SchemaError(
            "Gaze-in-the-Wild ProcessData byte-size mismatch: "
            f"expected={int(expected_bytes)}, observed={observed_bytes}."
        )
    if expected_sha256 is not None and observed_sha256 != str(expected_sha256).lower():
        raise SchemaError("Gaze-in-the-Wild ProcessData SHA-256 mismatch.")

    raw = loadmat(mat_path, squeeze_me=True, struct_as_record=False)
    if "ProcessData" not in raw:
        raise SchemaError(f"{mat_path.name} does not contain MATLAB variable 'ProcessData'.")
    process_data = raw["ProcessData"]

    participant_index = _positive_integer_scalar(_field(process_data, "PrIdx"), name="PrIdx")
    trial_index = _positive_integer_scalar(_field(process_data, "TrIdx"), name="TrIdx")
    stored_rate_hz = _positive_rate(_field(process_data, "SR"), name="SR")
    times_s, inferred_rate_hz = _timestamp_grid(_field(process_data, "T"))
    n_samples = len(times_s)

    etg = _field(process_data, "ETG")
    por_shape = _por_shape(_field(etg, "POR"), n_samples=n_samples)
    confidence = _numeric_vector(
        _field(etg, "Confidence"),
        name="ETG.Confidence",
        require_finite=False,
    )
    if len(confidence) != n_samples:
        raise SchemaError(
            "Gaze-in-the-Wild ProcessData.ETG.Confidence must match ProcessData.T length."
        )
    scene_resolution_px = _scene_resolution(_field(etg, "SceneResolution"))

    labels_present = False
    labels_shape: tuple[int] | None = None
    try:
        labels_value = _field(etg, "Labels")
    except SchemaError:
        labels = None
    else:
        labels = _numeric_vector(labels_value, name="ETG.Labels")
    if labels is not None:
        if len(labels) != n_samples:
            raise SchemaError(
                "Gaze-in-the-Wild ProcessData.ETG.Labels must match ProcessData.T when present."
            )
        labels_present = True
        labels_shape = (int(len(labels)),)

    return GazeInWildProcessDataPreflight(
        path=mat_path.name,
        sha256=observed_sha256,
        bytes=observed_bytes,
        participant_index=participant_index,
        trial_index=trial_index,
        stored_rate_hz=stored_rate_hz,
        inferred_processed_rate_hz=inferred_rate_hz,
        timestamp_count=n_samples,
        timestamp_start_s=float(times_s[0]),
        timestamp_end_s=float(times_s[-1]),
        por_shape=por_shape,
        confidence_shape=(int(len(confidence)),),
        scene_resolution_px=scene_resolution_px,
        labels_present=labels_present,
        labels_shape=labels_shape,
        top_level_labeldata_present="LabelData" in raw,
        adapter_coordinate_fields_compatible=True,
        timestamp_grid_valid=True,
    )


def build_gaze_in_wild_processdata_preflight_record(
    preflight: GazeInWildProcessDataPreflight,
    *,
    source_repository: str,
    source_revision: str,
    archive_path: str,
    archive_sha256: str,
    member_path: str,
    parent_evidence_fingerprint_sha256: str,
) -> dict[str, Any]:
    """Build a deterministic fail-closed provenance record for one preflight result."""
    record: dict[str, Any] = {
        "record_type": "gaze-in-wild-processdata-preflight-v1",
        "source": {
            "repository": str(source_repository),
            "revision": str(source_revision),
            "archive_path": str(archive_path),
            "archive_sha256": str(archive_sha256).lower(),
            "member_path": str(member_path),
            "parent_evidence_fingerprint_sha256": str(
                parent_evidence_fingerprint_sha256
            ).lower(),
        },
        "processdata": preflight.to_dict(),
        "scientific_boundary": {
            "processdata_structural_preflight_verified": True,
            "adapter_coordinate_fields_compatible_for_this_sample": True,
            "authoritative_original_or_canonical_dataset_copy_obtained": False,
            "full_distribution_recovered": False,
            "original_distribution_equivalence_verified": False,
            "separate_labeldata_recovered": False,
            "independent_labeller_recoverability_verified": False,
            "dataset_file_rights_resolved": False,
            "analysis_use_permitted": False,
            "redistribution_authorized": False,
            "participant_mapping_complete": False,
            "trial_task_mapping_complete": False,
            "coordinate_semantics_verified": False,
            "corpus_sampling_rate_distribution_verified": False,
            "published_acquisition_cadence_verified_from_sample": False,
            "quarantine_exit_authorized": False,
            "source_audit_ready": False,
            "empirical_evidence_eligible": False,
        },
        "claim_limits": [
            "This preflight verifies structural compatibility for one quarantined ProcessData object only.",
            "ETG.Labels is not treated as separately distributed LabelData or an independent labeller stream.",
            "The stored or timestamp-inferred processed rate is not promoted to acquisition-hardware cadence or corpus-wide cadence.",
            "Presence and shape of ETG.POR/SceneResolution do not independently establish coordinate semantics for the historical distribution.",
            "The result does not establish distribution identity, dataset-file rights, analysis permission, redistribution permission, or empirical eligibility.",
        ],
    }
    record["record_fingerprint_sha256"] = benchmark_fingerprint(record)
    return record


def validate_gaze_in_wild_processdata_preflight_record(payload: Mapping[str, Any]) -> None:
    """Validate a frozen preflight record and its non-promotion boundary."""
    record = dict(payload)
    if record.get("record_type") != "gaze-in-wild-processdata-preflight-v1":
        raise SchemaError("Unexpected Gaze-in-the-Wild ProcessData preflight record type.")
    expected = str(record.pop("record_fingerprint_sha256", ""))
    if expected != benchmark_fingerprint(record):
        raise SchemaError("Gaze-in-the-Wild ProcessData preflight fingerprint mismatch.")

    boundary = record.get("scientific_boundary")
    if not isinstance(boundary, Mapping):
        raise SchemaError("ProcessData preflight record is missing scientific_boundary.")
    if boundary.get("processdata_structural_preflight_verified") is not True:
        raise SchemaError("ProcessData structural preflight must be explicitly verified.")
    if boundary.get("adapter_coordinate_fields_compatible_for_this_sample") is not True:
        raise SchemaError("Adapter field compatibility must be explicitly verified for this sample.")
    for key in (
        "authoritative_original_or_canonical_dataset_copy_obtained",
        "full_distribution_recovered",
        "original_distribution_equivalence_verified",
        "separate_labeldata_recovered",
        "independent_labeller_recoverability_verified",
        "dataset_file_rights_resolved",
        "analysis_use_permitted",
        "redistribution_authorized",
        "participant_mapping_complete",
        "trial_task_mapping_complete",
        "coordinate_semantics_verified",
        "corpus_sampling_rate_distribution_verified",
        "published_acquisition_cadence_verified_from_sample",
        "quarantine_exit_authorized",
        "source_audit_ready",
        "empirical_evidence_eligible",
    ):
        if boundary.get(key) is not False:
            raise SchemaError(f"ProcessData preflight must keep {key}=false.")
