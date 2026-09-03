"""Auditable source-manifest verification for Hollywood2EM empirical use."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .benchmarks import benchmark_fingerprint
from .exceptions import SchemaError
from .hollywood2 import load_hollywood2_directory
from .native_event import file_sha256
from .schema import GazeFrame

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_REDISTRIBUTION = {"permitted", "restricted", "unknown"}


@dataclass(slots=True)
class Hollywood2SourceFileRecord:
    """One audited Hollywood2EM ARFF file and its participant/trial identity."""

    path: str
    sha256: str
    bytes: int
    participant_id: str
    trial_id: str

    def __post_init__(self) -> None:
        """Reject unsafe paths, weak digests, and unresolved identities."""
        path = PurePosixPath(str(self.path))
        if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError("Hollywood2 manifest paths must be safe relative POSIX paths.")
        if path.suffix.lower() != ".arff":
            raise ValueError("Hollywood2 source-manifest entries must reference .arff files.")
        self.path = path.as_posix()
        self.sha256 = str(self.sha256).strip().lower()
        if _SHA256_RE.fullmatch(self.sha256) is None:
            raise ValueError("Hollywood2 source-file sha256 must contain exactly 64 hex characters.")
        if int(self.bytes) <= 0:
            raise ValueError("Hollywood2 source-file byte size must be positive.")
        self.bytes = int(self.bytes)
        for field_name in ("participant_id", "trial_id"):
            value = str(getattr(self, field_name)).strip()
            if not value or value.lower() in {"__unresolved__", "unknown", "none", "nan"}:
                raise ValueError(f"{field_name} must contain an audited resolved identity.")
            setattr(self, field_name, value)

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible record."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Hollywood2SourceFileRecord:
        """Construct one record from decoded JSON."""
        return cls(**dict(payload))


@dataclass(slots=True)
class Hollywood2SourceAuditSpec:
    """Evidence contract required before Hollywood2EM is used in frozen modelling."""

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
    expected_sampling_rate_hz: float = 500.0
    sampling_rate_tolerance_fraction: float = 0.05
    coordinate_unit: str = "pixels"
    coordinate_unit_verified: bool = False
    coordinate_verification_basis: str = ""
    participant_identity_mapping_verified: bool = False
    participant_identity_mapping_basis: str = ""
    required_annotation_columns: tuple[str, ...] = (
        "handlabeller_1",
        "handlabeller_final",
    )
    files: list[Hollywood2SourceFileRecord] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Keep templates non-empirical and make empirical audits fully explicit."""
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
        if str(self.dataset_name).strip() != "Hollywood2EM":
            raise ValueError("dataset_name must be 'Hollywood2EM'.")
        if self.dataset_status not in {"template", "empirical"}:
            raise ValueError("dataset_status must be 'template' or 'empirical'.")
        self.redistribution_status = str(self.redistribution_status).strip().lower()
        if self.redistribution_status not in _ALLOWED_REDISTRIBUTION:
            raise ValueError(
                "redistribution_status must be 'permitted', 'restricted', or 'unknown'."
            )
        rate = float(self.expected_sampling_rate_hz)
        tolerance = float(self.sampling_rate_tolerance_fraction)
        if not np.isfinite(rate) or rate <= 0:
            raise ValueError("expected_sampling_rate_hz must be finite and positive.")
        if not np.isfinite(tolerance) or not 0.0 <= tolerance < 1.0:
            raise ValueError("sampling_rate_tolerance_fraction must be in [0, 1).")
        self.expected_sampling_rate_hz = rate
        self.sampling_rate_tolerance_fraction = tolerance
        self.coordinate_unit = str(self.coordinate_unit).strip().lower()
        if self.coordinate_unit != "pixels":
            raise ValueError("Hollywood2 audited cross-dataset coordinates must be verified pixels.")
        self.required_annotation_columns = tuple(
            str(column).strip() for column in self.required_annotation_columns
        )
        if set(self.required_annotation_columns) != {"handlabeller_1", "handlabeller_final"}:
            raise ValueError(
                "required_annotation_columns must contain handlabeller_1 and handlabeller_final."
            )
        self.files = [
            item if isinstance(item, Hollywood2SourceFileRecord) else Hollywood2SourceFileRecord.from_dict(item)
            for item in self.files
        ]
        paths = [item.path for item in self.files]
        identities = [(item.participant_id, item.trial_id) for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("Hollywood2 source-manifest paths must be unique.")
        if len(identities) != len(set(identities)):
            raise ValueError("Hollywood2 participant/trial identities must be unique per ARFF file.")
        self.notes = [str(note) for note in self.notes]

        if self.dataset_status == "empirical":
            if not self.files:
                raise ValueError("Empirical Hollywood2 source audits require a non-empty file manifest.")
            if not self.reuse_terms_verified:
                raise ValueError("Empirical Hollywood2 audits require verified reuse terms.")
            if not self.analysis_use_permitted:
                raise ValueError("Empirical Hollywood2 audits require explicit permission for analysis use.")
            if not self.coordinate_unit_verified or not str(self.coordinate_verification_basis).strip():
                raise ValueError(
                    "Empirical Hollywood2 audits require a documented coordinate-unit verification basis."
                )
            if not self.participant_identity_mapping_verified or not str(
                self.participant_identity_mapping_basis
            ).strip():
                raise ValueError(
                    "Empirical Hollywood2 audits require a documented participant-identity mapping basis."
                )

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible specification mapping."""
        payload = asdict(self)
        payload["required_annotation_columns"] = list(self.required_annotation_columns)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Hollywood2SourceAuditSpec:
        """Construct a source-audit specification from decoded JSON."""
        values = dict(payload)
        if "required_annotation_columns" in values:
            values["required_annotation_columns"] = tuple(values["required_annotation_columns"])
        if "files" in values:
            values["files"] = [Hollywood2SourceFileRecord.from_dict(item) for item in values["files"]]
        if "notes" in values:
            values["notes"] = list(values["notes"])
        return cls(**values)


@dataclass(slots=True)
class Hollywood2SourceAuditRun:
    """Verified source audit plus both human annotation streams."""

    spec: Hollywood2SourceAuditSpec
    final_annotations: GazeFrame
    student_annotations: GazeFrame
    report: dict[str, Any]


def load_hollywood2_source_audit_spec(path: str | Path) -> Hollywood2SourceAuditSpec:
    """Load a Hollywood2 source-audit specification from JSON."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Hollywood2 source-audit specification must contain one JSON object.")
    return Hollywood2SourceAuditSpec.from_dict(payload)


def _data_root(root: Path) -> Path:
    return root / "ground_truth" if (root / "ground_truth").is_dir() else root


def _verify_inventory(root: Path, spec: Hollywood2SourceAuditSpec) -> dict[str, Any]:
    data_root = _data_root(root)
    actual_paths = sorted(path.relative_to(data_root).as_posix() for path in data_root.rglob("*.arff"))
    expected_paths = sorted(item.path for item in spec.files)
    missing = sorted(set(expected_paths) - set(actual_paths))
    extra = sorted(set(actual_paths) - set(expected_paths))
    if missing or extra:
        raise SchemaError(
            "Hollywood2 source inventory does not match the audited manifest: "
            f"missing={missing}, extra={extra}."
        )

    checked: list[dict[str, Any]] = []
    for record in spec.files:
        path = data_root.joinpath(*PurePosixPath(record.path).parts)
        size = path.stat().st_size
        if size != record.bytes:
            raise SchemaError(
                f"Hollywood2 byte-size mismatch for {record.path!r}: "
                f"expected={record.bytes}, observed={size}."
            )
        digest = file_sha256(path)
        if digest != record.sha256:
            raise SchemaError(f"Hollywood2 SHA-256 mismatch for {record.path!r}.")
        checked.append(record.to_dict())
    return {
        "file_count": len(checked),
        "exact_inventory_match": True,
        "files": checked,
        "source_manifest_fingerprint_sha256": benchmark_fingerprint(checked),
    }


def _identity_parser(spec: Hollywood2SourceAuditSpec):
    records = {item.path: item for item in spec.files}

    def parser(relative: Path) -> tuple[str, str]:
        key = relative.as_posix()
        if key not in records:
            raise SchemaError(f"Hollywood2 identity manifest has no entry for {key!r}.")
        item = records[key]
        return item.participant_id, item.trial_id

    return parser


def _verify_annotation_stream_identity(left: GazeFrame, right: GazeFrame) -> None:
    columns = [
        "participant_id",
        "trial_id",
        "timestamp_ms",
        "x_px",
        "y_px",
        "validity",
        "confidence",
        "source_file",
    ]
    left_frame = left.data.loc[:, columns].sort_values(
        ["participant_id", "trial_id", "timestamp_ms"], kind="stable"
    ).reset_index(drop=True)
    right_frame = right.data.loc[:, columns].sort_values(
        ["participant_id", "trial_id", "timestamp_ms"], kind="stable"
    ).reset_index(drop=True)
    if not left_frame.equals(right_frame):
        raise SchemaError(
            "Hollywood2 student and expert annotation streams do not reference identical gaze samples."
        )


def _stamp_audit_metadata(
    gaze: GazeFrame,
    *,
    spec: Hollywood2SourceAuditSpec,
    report_fingerprint_sha256: str,
    spec_fingerprint_sha256: str,
    manifest_fingerprint_sha256: str,
) -> GazeFrame:
    stamped = gaze.copy()
    stamped.metadata.update(
        {
            "source_audit_status": "verified",
            "source_audit_report_fingerprint_sha256": report_fingerprint_sha256,
            "source_audit_spec_fingerprint_sha256": spec_fingerprint_sha256,
            "source_manifest_fingerprint_sha256": manifest_fingerprint_sha256,
            "source_revision": spec.source_revision,
            "reuse_terms_verified": True,
            "analysis_use_permitted": True,
            "redistribution_status": spec.redistribution_status,
            "coordinate_verification_basis": spec.coordinate_verification_basis,
            "participant_identity_mapping_basis": spec.participant_identity_mapping_basis,
        }
    )
    return stamped


def audit_hollywood2_source(
    root: str | Path,
    spec: Hollywood2SourceAuditSpec,
) -> Hollywood2SourceAuditRun:
    """Verify an authoritative local Hollywood2EM copy before empirical modelling.

    The audit is intentionally non-statistical: it verifies exact file identity, reuse/analysis
    declarations, participant/trial mapping, coordinate-unit evidence, native sampling rate, and
    that the student and expert labels refer to the same underlying gaze samples. It does not
    produce model-performance metrics and it does not imply raw-data redistribution permission.
    """
    if not isinstance(spec, Hollywood2SourceAuditSpec):
        raise TypeError("spec must be a Hollywood2SourceAuditSpec instance.")
    if spec.dataset_status != "empirical":
        raise SchemaError(
            "Template Hollywood2 source-audit specifications cannot certify empirical data."
        )
    source_root = Path(root)
    if not source_root.exists():
        raise FileNotFoundError(source_root)

    inventory = _verify_inventory(source_root, spec)
    parser = _identity_parser(spec)
    load_kwargs = {
        "identity_parser": parser,
        "expected_sampling_rate_hz": spec.expected_sampling_rate_hz,
        "sampling_rate_tolerance": spec.sampling_rate_tolerance_fraction,
        "coordinate_unit": spec.coordinate_unit,
    }
    final = load_hollywood2_directory(source_root, annotator="final", **load_kwargs)
    student = load_hollywood2_directory(source_root, annotator="student", **load_kwargs)
    _verify_annotation_stream_identity(final, student)

    participants = sorted(final.data["participant_id"].astype(str).unique().tolist())
    trials = final.data[["participant_id", "trial_id"]].drop_duplicates()
    spec_fingerprint = benchmark_fingerprint(spec.to_dict())
    body: dict[str, Any] = {
        "audit": "Hollywood2EM-source-audit",
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
        "coordinates": {
            "unit": spec.coordinate_unit,
            "verified": spec.coordinate_unit_verified,
            "verification_basis": spec.coordinate_verification_basis,
        },
        "participant_identity": {
            "verified": spec.participant_identity_mapping_verified,
            "verification_basis": spec.participant_identity_mapping_basis,
            "participant_count": len(participants),
            "participant_ids": participants,
            "participant_trial_count": int(len(trials)),
        },
        "sampling": {
            "expected_sampling_rate_hz": spec.expected_sampling_rate_hz,
            "observed_sampling_rate_hz": float(final.sampling_rate_hz),
            "tolerance_fraction": spec.sampling_rate_tolerance_fraction,
            "sampling_origin": "native",
        },
        "annotations": {
            "student_column": "handlabeller_1",
            "expert_column": "handlabeller_final",
            "same_underlying_gaze_verified": True,
            "row_count_per_stream": int(len(final.data)),
        },
        "source_inventory": inventory,
        "spec_fingerprint_sha256": spec_fingerprint,
        "claim_limits": [
            "This artifact certifies source/provenance gates, not model performance.",
            "Analysis permission and raw-data redistribution permission are separate claims.",
            "Hollywood2EM is native 500 Hz; any 60 Hz analysis remains derived/resampled evidence.",
        ],
    }
    report_fingerprint = benchmark_fingerprint(body)
    report = {**body, "report_fingerprint_sha256": report_fingerprint}
    manifest_fingerprint = inventory["source_manifest_fingerprint_sha256"]
    final = _stamp_audit_metadata(
        final,
        spec=spec,
        report_fingerprint_sha256=report_fingerprint,
        spec_fingerprint_sha256=spec_fingerprint,
        manifest_fingerprint_sha256=manifest_fingerprint,
    )
    student = _stamp_audit_metadata(
        student,
        spec=spec,
        report_fingerprint_sha256=report_fingerprint,
        spec_fingerprint_sha256=spec_fingerprint,
        manifest_fingerprint_sha256=manifest_fingerprint,
    )
    return Hollywood2SourceAuditRun(
        spec=spec,
        final_annotations=final,
        student_annotations=student,
        report=report,
    )


def load_audited_hollywood2_directory(
    root: str | Path,
    spec: Hollywood2SourceAuditSpec,
    *,
    annotator: str = "final",
) -> GazeFrame:
    """Return one Hollywood2 annotation stream only after the full source audit passes."""
    run = audit_hollywood2_source(root, spec)
    key = str(annotator).strip().lower()
    if key in {"final", "expert"}:
        return run.final_annotations
    if key in {"student", "novice"}:
        return run.student_annotations
    raise ValueError("annotator must be 'final'/'expert' or 'student'/'novice'.")
