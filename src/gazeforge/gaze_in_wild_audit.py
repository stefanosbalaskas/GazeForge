"""Auditable source verification for Gaze-in-the-Wild empirical evidence."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
import pandas as pd

from .benchmarks import benchmark_fingerprint
from .exceptions import SchemaError
from .gaze_in_wild import load_gaze_in_wild_mat
from .native_event import file_sha256
from .schema import GazeFrame

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_REDISTRIBUTION = {"permitted", "restricted", "unknown"}
_UNRESOLVED = {"", "__unresolved__", "unknown", "none", "nan"}


def _safe_mat_path(value: str, *, field_name: str) -> str:
    path = PurePosixPath(str(value))
    unsafe = path.is_absolute() or not path.parts or any(
        part in {"", ".", ".."} for part in path.parts
    )
    if unsafe:
        raise ValueError(f"{field_name} must be a safe relative POSIX path.")
    if path.suffix.lower() != ".mat":
        raise ValueError(f"{field_name} must reference a .mat file.")
    return path.as_posix()


def _sha256(value: str, *, field_name: str) -> str:
    digest = str(value).strip().lower()
    if _SHA256_RE.fullmatch(digest) is None:
        raise ValueError(f"{field_name} must contain exactly 64 hexadecimal characters.")
    return digest


def _resolved(value: Any, *, field_name: str) -> str:
    text = str(value).strip()
    if text.lower() in _UNRESOLVED:
        raise ValueError(f"{field_name} must contain an audited resolved identity.")
    return text


@dataclass(slots=True)
class GazeInWildProcessFileRecord:
    """One audited ProcessData MATLAB file."""

    path: str
    sha256: str
    bytes: int

    def __post_init__(self) -> None:
        self.path = _safe_mat_path(self.path, field_name="process path")
        self.sha256 = _sha256(self.sha256, field_name="process sha256")
        self.bytes = int(self.bytes)
        if self.bytes <= 0:
            raise ValueError("process bytes must be positive.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> GazeInWildProcessFileRecord:
        return cls(**dict(payload))


@dataclass(slots=True)
class GazeInWildLabelFileRecord:
    """One audited human-labelled MATLAB stream and its identity mapping."""

    path: str
    sha256: str
    bytes: int
    participant_id: str
    trial_id: str
    labeller_id: int
    process_path: str

    def __post_init__(self) -> None:
        self.path = _safe_mat_path(self.path, field_name="label path")
        self.process_path = _safe_mat_path(self.process_path, field_name="process_path")
        self.sha256 = _sha256(self.sha256, field_name="label sha256")
        self.bytes = int(self.bytes)
        if self.bytes <= 0:
            raise ValueError("label bytes must be positive.")
        self.participant_id = _resolved(self.participant_id, field_name="participant_id")
        self.trial_id = _resolved(self.trial_id, field_name="trial_id")
        self.labeller_id = int(self.labeller_id)
        if self.labeller_id <= 0:
            raise ValueError("labeller_id must be a positive integer.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> GazeInWildLabelFileRecord:
        return cls(**dict(payload))


@dataclass(slots=True)
class GazeInWildSourceAuditSpec:
    """Evidence contract required before Gaze-in-the-Wild results are frozen."""

    dataset_name: str
    dataset_version: str
    source: str
    source_revision: str
    license: str
    reuse_terms_source: str
    dataset_status: str = "template"
    reuse_terms_verified: bool = False
    analysis_use_permitted: bool = False
    redistribution_status: str = "unknown"
    participant_mapping_verified: bool = False
    participant_mapping_basis: str = ""
    coordinate_unit: str = "unverified"
    coordinate_unit_verified: bool = False
    coordinate_verification_basis: str = ""
    pixel_kinematics_compatible: bool = False
    confidence_threshold: float = 0.30
    published_hardware_sampling_rate_hz: float = 120.0
    label_files: list[GazeInWildLabelFileRecord] = field(default_factory=list)
    process_files: list[GazeInWildProcessFileRecord] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for field_name in (
            "dataset_name",
            "dataset_version",
            "source",
            "source_revision",
            "license",
            "reuse_terms_source",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must not be empty.")
        if str(self.dataset_name).strip() != "Gaze-in-the-Wild":
            raise ValueError("dataset_name must be 'Gaze-in-the-Wild'.")
        if self.dataset_status not in {"template", "empirical"}:
            raise ValueError("dataset_status must be 'template' or 'empirical'.")
        self.redistribution_status = str(self.redistribution_status).strip().lower()
        if self.redistribution_status not in _ALLOWED_REDISTRIBUTION:
            raise ValueError(
                "redistribution_status must be 'permitted', 'restricted', or 'unknown'."
            )
        threshold = float(self.confidence_threshold)
        if not np.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
            raise ValueError("confidence_threshold must be finite and in [0, 1].")
        self.confidence_threshold = threshold
        hardware_rate = float(self.published_hardware_sampling_rate_hz)
        if not np.isfinite(hardware_rate) or hardware_rate <= 0:
            raise ValueError("published_hardware_sampling_rate_hz must be finite and positive.")
        self.published_hardware_sampling_rate_hz = hardware_rate
        self.coordinate_unit = str(self.coordinate_unit).strip()
        if not self.coordinate_unit:
            raise ValueError("coordinate_unit must not be empty.")
        self.label_files = [
            item
            if isinstance(item, GazeInWildLabelFileRecord)
            else GazeInWildLabelFileRecord.from_dict(item)
            for item in self.label_files
        ]
        self.process_files = [
            item
            if isinstance(item, GazeInWildProcessFileRecord)
            else GazeInWildProcessFileRecord.from_dict(item)
            for item in self.process_files
        ]
        self.notes = [str(note) for note in self.notes]

        label_paths = [item.path for item in self.label_files]
        process_paths = [item.path for item in self.process_files]
        if len(label_paths) != len(set(label_paths)):
            raise ValueError("Gaze-in-the-Wild label manifest paths must be unique.")
        if len(process_paths) != len(set(process_paths)):
            raise ValueError("Gaze-in-the-Wild process manifest paths must be unique.")
        identities = [
            (item.participant_id, item.trial_id, item.labeller_id) for item in self.label_files
        ]
        if len(identities) != len(set(identities)):
            raise ValueError(
                "Gaze-in-the-Wild participant/trial/labeller identities must be unique."
            )
        process_set = set(process_paths)
        missing_process_records = sorted(
            {item.process_path for item in self.label_files} - process_set
        )
        if missing_process_records:
            raise ValueError(
                "Every label record must reference an audited process record; missing "
                f"{missing_process_records}."
            )
        trial_process: dict[tuple[str, str], str] = {}
        for item in self.label_files:
            key = (item.participant_id, item.trial_id)
            previous = trial_process.setdefault(key, item.process_path)
            if previous != item.process_path:
                raise ValueError(
                    "All labellers for one participant/trial must reference the same "
                    "ProcessData file."
                )

        if self.dataset_status == "empirical":
            if not self.label_files or not self.process_files:
                raise ValueError(
                    "Empirical Gaze-in-the-Wild audits require non-empty label and "
                    "process manifests."
                )
            if not self.reuse_terms_verified:
                raise ValueError("Empirical audits require verified reuse terms.")
            if not self.analysis_use_permitted:
                raise ValueError("Empirical audits require explicit permission for analysis use.")
            if not self.participant_mapping_verified or not str(
                self.participant_mapping_basis
            ).strip():
                raise ValueError(
                    "Empirical audits require a documented participant/task identity mapping basis."
                )
            if not self.coordinate_unit_verified or self.coordinate_unit.lower() == "unverified":
                raise ValueError(
                    "Empirical audits require a verified point-of-regard coordinate unit."
                )
            if not str(self.coordinate_verification_basis).strip():
                raise ValueError(
                    "Empirical audits require a documented coordinate-unit verification basis."
                )
            if self.pixel_kinematics_compatible and self.coordinate_unit.lower() != "pixels":
                raise ValueError(
                    "pixel_kinematics_compatible can only be true when coordinate_unit is 'pixels'."
                )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> GazeInWildSourceAuditSpec:
        values = dict(payload)
        if "label_files" in values:
            values["label_files"] = [
                GazeInWildLabelFileRecord.from_dict(item) for item in values["label_files"]
            ]
        if "process_files" in values:
            values["process_files"] = [
                GazeInWildProcessFileRecord.from_dict(item) for item in values["process_files"]
            ]
        if "notes" in values:
            values["notes"] = list(values["notes"])
        return cls(**values)


@dataclass(slots=True)
class GazeInWildAuditedFile:
    """One verified label/process pair with its loaded gaze stream."""

    record: GazeInWildLabelFileRecord
    gaze: GazeFrame


@dataclass(slots=True)
class GazeInWildSourceAuditRun:
    """Verified source audit and all audited per-labeller streams."""

    spec: GazeInWildSourceAuditSpec
    files: list[GazeInWildAuditedFile]
    report: dict[str, Any]


def load_gaze_in_wild_source_audit_spec(path: str | Path) -> GazeInWildSourceAuditSpec:
    """Load a Gaze-in-the-Wild source-audit specification from JSON."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(
            "Gaze-in-the-Wild source-audit specification must contain one JSON object."
        )
    return GazeInWildSourceAuditSpec.from_dict(payload)


def _inventory(root: Path, records: list[Any], *, label: str) -> dict[str, Any]:
    actual = sorted(path.relative_to(root).as_posix() for path in root.rglob("*.mat"))
    expected = sorted(item.path for item in records)
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if missing or extra:
        raise SchemaError(
            f"Gaze-in-the-Wild {label} inventory does not match the audited manifest: "
            f"missing={missing}, extra={extra}."
        )
    checked: list[dict[str, Any]] = []
    for record in records:
        path = root.joinpath(*PurePosixPath(record.path).parts)
        size = path.stat().st_size
        if size != record.bytes:
            raise SchemaError(
                f"Gaze-in-the-Wild byte-size mismatch for {label} {record.path!r}: "
                f"expected={record.bytes}, observed={size}."
            )
        if file_sha256(path) != record.sha256:
            raise SchemaError(
                f"Gaze-in-the-Wild SHA-256 mismatch for {label} {record.path!r}."
            )
        checked.append(record.to_dict())
    return {
        "file_count": len(checked),
        "exact_inventory_match": True,
        "files": checked,
        "manifest_fingerprint_sha256": benchmark_fingerprint(checked),
    }


def _same_underlying_gaze(left: GazeFrame, right: GazeFrame) -> bool:
    columns = [
        "participant_id",
        "trial_id",
        "timestamp_ms",
        "x_px",
        "y_px",
        "validity",
        "confidence",
    ]
    left_frame = left.data.loc[:, columns].reset_index(drop=True)
    right_frame = right.data.loc[:, columns].reset_index(drop=True)
    return left_frame.equals(right_frame)


def _stamp_metadata(
    gaze: GazeFrame,
    *,
    spec: GazeInWildSourceAuditSpec,
    report_fingerprint: str,
    spec_fingerprint: str,
    label_manifest_fingerprint: str,
    process_manifest_fingerprint: str,
) -> GazeFrame:
    stamped = gaze.copy()
    stamped.metadata.update(
        {
            "source_audit_status": "verified",
            "source_audit_report_fingerprint_sha256": report_fingerprint,
            "source_audit_spec_fingerprint_sha256": spec_fingerprint,
            "label_manifest_fingerprint_sha256": label_manifest_fingerprint,
            "process_manifest_fingerprint_sha256": process_manifest_fingerprint,
            "source_revision": spec.source_revision,
            "reuse_terms_verified": True,
            "analysis_use_permitted": True,
            "redistribution_status": spec.redistribution_status,
            "coordinate_source_unit": spec.coordinate_unit,
            "coordinate_unit_verified": spec.coordinate_unit_verified,
            "coordinate_verification_basis": spec.coordinate_verification_basis,
            "pixel_kinematics_compatible": spec.pixel_kinematics_compatible,
            "participant_mapping_basis": spec.participant_mapping_basis,
        }
    )
    return stamped


def audit_gaze_in_wild_source(
    label_root: str | Path,
    process_root: str | Path,
    spec: GazeInWildSourceAuditSpec,
) -> GazeInWildSourceAuditRun:
    """Verify an authoritative local Gaze-in-the-Wild copy before empirical reporting.

    The audit binds exact label/process files to participant, trial, and labeller identities; checks
    current reuse declarations and coordinate evidence; infers native-file cadence from timestamps;
    and verifies that different labellers for the same trial reference identical underlying gaze.
    It produces no model-performance metrics and makes no raw-data redistribution claim.
    """
    if not isinstance(spec, GazeInWildSourceAuditSpec):
        raise TypeError("spec must be a GazeInWildSourceAuditSpec instance.")
    if spec.dataset_status != "empirical":
        raise SchemaError(
            "Template Gaze-in-the-Wild source-audit specifications cannot certify empirical data."
        )
    labels_root = Path(label_root)
    processes_root = Path(process_root)
    if not labels_root.exists():
        raise FileNotFoundError(labels_root)
    if not processes_root.exists():
        raise FileNotFoundError(processes_root)

    label_inventory = _inventory(labels_root, spec.label_files, label="label")
    process_inventory = _inventory(processes_root, spec.process_files, label="process")

    audited_files: list[GazeInWildAuditedFile] = []
    rates: list[dict[str, Any]] = []
    by_trial: dict[tuple[str, str], list[GazeInWildAuditedFile]] = {}
    for record in spec.label_files:
        label_path = labels_root.joinpath(*PurePosixPath(record.path).parts)
        process_path = processes_root.joinpath(*PurePosixPath(record.process_path).parts)
        gaze = load_gaze_in_wild_mat(
            label_path,
            process_path=process_path,
            participant_id=record.participant_id,
            trial_id=record.trial_id,
            confidence_threshold=spec.confidence_threshold,
        )
        observed_labeller = gaze.metadata.get("labeller_id")
        if observed_labeller != record.labeller_id:
            raise SchemaError(
                f"Gaze-in-the-Wild labeller mismatch for {record.path!r}: "
                f"manifest={record.labeller_id}, observed={observed_labeller}."
            )
        item = GazeInWildAuditedFile(record=record, gaze=gaze)
        audited_files.append(item)
        by_trial.setdefault((record.participant_id, record.trial_id), []).append(item)
        rates.append(
            {
                "path": record.path,
                "participant_id": record.participant_id,
                "trial_id": record.trial_id,
                "labeller_id": record.labeller_id,
                "observed_sampling_rate_hz": float(gaze.sampling_rate_hz),
            }
        )

    paired_trial_count = 0
    for identity, items in by_trial.items():
        if len(items) < 2:
            continue
        paired_trial_count += 1
        reference = items[0].gaze
        for candidate in items[1:]:
            if not _same_underlying_gaze(reference, candidate.gaze):
                raise SchemaError(
                    "Gaze-in-the-Wild labellers do not reference identical underlying gaze for "
                    f"participant/trial {identity!r}."
                )

    rate_values = np.asarray([item["observed_sampling_rate_hz"] for item in rates], dtype=float)
    participants = sorted({record.participant_id for record in spec.label_files})
    trials = sorted({(record.participant_id, record.trial_id) for record in spec.label_files})
    labellers = sorted({record.labeller_id for record in spec.label_files})
    spec_fingerprint = benchmark_fingerprint(spec.to_dict())
    body: dict[str, Any] = {
        "audit": "Gaze-in-the-Wild-source-audit",
        "status": "verified",
        "dataset": {
            "name": spec.dataset_name,
            "version": spec.dataset_version,
            "source": spec.source,
            "source_revision": spec.source_revision,
            "license": spec.license,
        },
        "reuse": {
            "terms_source": spec.reuse_terms_source,
            "terms_verified": spec.reuse_terms_verified,
            "analysis_use_permitted": spec.analysis_use_permitted,
            "redistribution_status": spec.redistribution_status,
        },
        "identity": {
            "participant_mapping_verified": spec.participant_mapping_verified,
            "participant_mapping_basis": spec.participant_mapping_basis,
            "participant_count": len(participants),
            "participant_ids": participants,
            "participant_trial_count": len(trials),
            "labeller_ids": labellers,
            "labeller_count": len(labellers),
            "multi_labeller_trial_count": paired_trial_count,
            "same_underlying_gaze_verified_for_multi_labeller_trials": paired_trial_count > 0,
        },
        "coordinates": {
            "unit": spec.coordinate_unit,
            "verified": spec.coordinate_unit_verified,
            "verification_basis": spec.coordinate_verification_basis,
            "pixel_kinematics_compatible": spec.pixel_kinematics_compatible,
        },
        "sampling": {
            "source": "inferred_from_LabelData.T_per_file",
            "published_hardware_sampling_rate_hz": spec.published_hardware_sampling_rate_hz,
            "file_count": len(rates),
            "min_observed_sampling_rate_hz": float(np.min(rate_values)),
            "median_observed_sampling_rate_hz": float(np.median(rate_values)),
            "max_observed_sampling_rate_hz": float(np.max(rate_values)),
            "files": rates,
        },
        "confidence_threshold": spec.confidence_threshold,
        "label_inventory": label_inventory,
        "process_inventory": process_inventory,
        "spec_fingerprint_sha256": spec_fingerprint,
        "claim_limits": [
            "This artifact certifies source/provenance gates, not model performance.",
            "Published 120 Hz hardware provenance is kept separate from inferred file cadence.",
            "Analysis permission and raw-data redistribution permission are separate claims.",
            "Gaze-in-the-Wild evidence is not GP3-specific validation.",
        ],
    }
    report_fingerprint = benchmark_fingerprint(body)
    report = {**body, "report_fingerprint_sha256": report_fingerprint}
    label_fingerprint = label_inventory["manifest_fingerprint_sha256"]
    process_fingerprint = process_inventory["manifest_fingerprint_sha256"]
    stamped_files = [
        GazeInWildAuditedFile(
            record=item.record,
            gaze=_stamp_metadata(
                item.gaze,
                spec=spec,
                report_fingerprint=report_fingerprint,
                spec_fingerprint=spec_fingerprint,
                label_manifest_fingerprint=label_fingerprint,
                process_manifest_fingerprint=process_fingerprint,
            ),
        )
        for item in audited_files
    ]
    return GazeInWildSourceAuditRun(spec=spec, files=stamped_files, report=report)


def audited_gaze_in_wild_files_by_labeller(
    run: GazeInWildSourceAuditRun,
) -> dict[int, list[GazeInWildAuditedFile]]:
    """Group an already verified audit run by human labeller without merging file cadences."""
    if not isinstance(run, GazeInWildSourceAuditRun):
        raise TypeError("run must be a GazeInWildSourceAuditRun instance.")
    grouped: dict[int, list[GazeInWildAuditedFile]] = {}
    for item in run.files:
        grouped.setdefault(item.record.labeller_id, []).append(item)
    for items in grouped.values():
        items.sort(
            key=lambda item: (
                item.record.participant_id,
                item.record.trial_id,
                item.record.path,
            )
        )
    return dict(sorted(grouped.items()))


def gaze_in_wild_sampling_rate_table(run: GazeInWildSourceAuditRun) -> pd.DataFrame:
    """Return the audited per-file timestamp-inferred sampling-rate ledger."""
    if not isinstance(run, GazeInWildSourceAuditRun):
        raise TypeError("run must be a GazeInWildSourceAuditRun instance.")
    return (
        pd.DataFrame(run.report["sampling"]["files"])
        .sort_values(
            ["participant_id", "trial_id", "labeller_id", "path"],
            kind="stable",
        )
        .reset_index(drop=True)
    )
