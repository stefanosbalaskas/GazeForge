"""Authoritative-source audit contract for the VISUS dynamic-AOI benchmark."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError

_ALLOWED_ROLES = {"video", "gaze", "aoi_annotation", "other"}
_VIDEO_SUFFIXES = {".avi", ".mp4", ".mov", ".mkv"}
_HEX = set("0123456789abcdef")


def _resolved(value: str) -> bool:
    text = str(value).strip()
    return bool(text) and "REPLACE" not in text.upper() and "VERIFY" not in text.upper()


def _safe_relative_path(value: str) -> str:
    text = str(value).strip().replace("\\", "/")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError("VISUS manifest paths must be safe non-empty relative paths.")
    return path.as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class VisusSourceFileRecord:
    """One exact file identity in an audited VISUS snapshot."""

    path: str
    sha256: str
    bytes: int
    role: str
    stimulus_id: str | None = None
    participant_id: str | None = None
    participant_group: str | None = None
    annotation_stream_id: str | None = None

    def __post_init__(self) -> None:
        path = _safe_relative_path(self.path)
        object.__setattr__(self, "path", path)
        digest = str(self.sha256).strip().lower()
        if len(digest) != 64 or any(character not in _HEX for character in digest):
            raise ValueError("VISUS manifest SHA-256 values must contain exactly 64 hex digits.")
        object.__setattr__(self, "sha256", digest)
        if int(self.bytes) <= 0:
            raise ValueError("VISUS manifest byte sizes must be positive.")
        object.__setattr__(self, "bytes", int(self.bytes))

        role = str(self.role).strip().lower()
        if role not in _ALLOWED_ROLES:
            raise ValueError(f"VISUS file role must be one of {sorted(_ALLOWED_ROLES)}.")
        object.__setattr__(self, "role", role)
        suffix = PurePosixPath(path).suffix.lower()
        if role == "video" and suffix not in _VIDEO_SUFFIXES:
            raise ValueError("VISUS video records must reference a recognized video file suffix.")
        if role == "gaze" and suffix != ".tsv":
            raise ValueError("VISUS gaze records must reference TSV files.")
        if role == "aoi_annotation" and suffix != ".xml":
            raise ValueError("VISUS AOI annotation records must reference XML files.")

        stimulus = None if self.stimulus_id is None else str(self.stimulus_id).strip()
        participant = None if self.participant_id is None else str(self.participant_id).strip()
        group = None if self.participant_group is None else str(self.participant_group).strip()
        stream = (
            None if self.annotation_stream_id is None else str(self.annotation_stream_id).strip()
        )
        if role in {"video", "gaze", "aoi_annotation"} and not stimulus:
            raise ValueError(f"VISUS {role} records require an explicit stimulus_id.")
        if role == "gaze" and not participant:
            raise ValueError("VISUS gaze records require an explicit participant_id.")
        if role == "aoi_annotation" and not stream:
            raise ValueError(
                "VISUS AOI annotation records require an explicit annotation_stream_id."
            )
        if role != "aoi_annotation" and stream is not None:
            raise ValueError("annotation_stream_id is only valid for AOI annotation records.")
        object.__setattr__(self, "stimulus_id", stimulus)
        object.__setattr__(self, "participant_id", participant)
        object.__setattr__(self, "participant_group", group)
        object.__setattr__(self, "annotation_stream_id", stream)


@dataclass(slots=True)
class VisusSourceAuditSpec:
    """Reviewed provenance and exact-file contract for a VISUS dataset copy."""

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
    stimulus_mapping_verified: bool = False
    stimulus_mapping_basis: str = ""
    participant_mapping_verified: bool = False
    participant_mapping_basis: str = ""
    coordinate_unit: str = "unverified"
    coordinate_unit_verified: bool = False
    coordinate_verification_basis: str = ""
    timestamp_basis_verified: bool = False
    timestamp_verification_basis: str = ""
    published_eye_sampling_rate_hz: float = 60.0
    published_video_frame_rate_hz: float = 25.0
    published_video_resolution_px: tuple[int, int] = (1920, 1080)
    published_display_resolution_px: tuple[int, int] = (1920, 1200)
    published_stimulus_count: int = 11
    published_participant_count: int = 25
    annotation_format: str = "ViPER-compatible XML"
    annotation_process_contributor_count: int = 2
    independent_annotation_streams_verified: bool = False
    independent_annotation_streams_basis: str = ""
    files: list[VisusSourceFileRecord] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if str(self.dataset_name).strip() != "VISUS":
            raise ValueError("VISUS source audits require dataset_name='VISUS'.")
        status = str(self.dataset_status).strip().lower()
        if status not in {"template", "empirical"}:
            raise ValueError("dataset_status must be either 'template' or 'empirical'.")
        self.dataset_status = status
        if float(self.published_eye_sampling_rate_hz) <= 0:
            raise ValueError("published_eye_sampling_rate_hz must be positive.")
        if float(self.published_video_frame_rate_hz) <= 0:
            raise ValueError("published_video_frame_rate_hz must be positive.")
        for name, value in (
            ("published_video_resolution_px", self.published_video_resolution_px),
            ("published_display_resolution_px", self.published_display_resolution_px),
        ):
            if len(value) != 2 or any(int(component) <= 0 for component in value):
                raise ValueError(f"{name} must contain positive width and height.")
        self.published_video_resolution_px = tuple(
            int(component) for component in self.published_video_resolution_px
        )
        self.published_display_resolution_px = tuple(
            int(component) for component in self.published_display_resolution_px
        )
        if int(self.published_stimulus_count) != 11:
            raise ValueError("VISUS published_stimulus_count must be 11 for this benchmark version.")
        if int(self.published_participant_count) != 25:
            raise ValueError(
                "VISUS published_participant_count must be 25 for this benchmark version."
            )
        if int(self.annotation_process_contributor_count) != 2:
            raise ValueError(
                "The published VISUS AOI annotation process reports two human contributors."
            )
        if not str(self.annotation_format).strip():
            raise ValueError("annotation_format cannot be empty.")

        paths = [record.path for record in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("VISUS source-audit manifest paths must be unique.")
        annotation_keys = [
            (record.stimulus_id, record.annotation_stream_id)
            for record in self.files
            if record.role == "aoi_annotation"
        ]
        if len(annotation_keys) != len(set(annotation_keys)):
            raise ValueError(
                "VISUS AOI manifests cannot duplicate a stimulus/annotation-stream identity."
            )

        if self.independent_annotation_streams_verified:
            if not _resolved(self.independent_annotation_streams_basis):
                raise ValueError(
                    "Verified independent VISUS annotation streams require an evidence basis."
                )
            streams_by_stimulus: dict[str, set[str]] = {}
            for record in self.files:
                if record.role != "aoi_annotation":
                    continue
                streams_by_stimulus.setdefault(str(record.stimulus_id), set()).add(
                    str(record.annotation_stream_id)
                )
            if not streams_by_stimulus or any(
                len(streams) < 2 for streams in streams_by_stimulus.values()
            ):
                raise ValueError(
                    "independent_annotation_streams_verified=true requires at least two "
                    "manifested AOI streams for every annotated stimulus."
                )

        if status == "empirical":
            required_text = {
                "dataset_version": self.dataset_version,
                "source": self.source,
                "source_revision": self.source_revision,
                "license": self.license,
                "reuse_terms_source": self.reuse_terms_source,
            }
            unresolved = [name for name, value in required_text.items() if not _resolved(value)]
            if unresolved:
                raise ValueError(f"Empirical VISUS audits require resolved fields: {unresolved}")
            if not self.files:
                raise ValueError("Empirical VISUS audits require a non-empty exact file manifest.")
            if not self.reuse_terms_verified or not self.analysis_use_permitted:
                raise ValueError(
                    "Empirical VISUS audits require reviewed reuse terms and explicit analysis use."
                )
            if not self.stimulus_mapping_verified or not _resolved(
                self.stimulus_mapping_basis
            ):
                raise ValueError(
                    "Empirical VISUS audits require a verified stimulus mapping and evidence basis."
                )
            if not self.participant_mapping_verified or not _resolved(
                self.participant_mapping_basis
            ):
                raise ValueError(
                    "Empirical VISUS audits require a verified participant mapping and basis."
                )
            if (
                not self.coordinate_unit_verified
                or str(self.coordinate_unit).strip().lower() == "unverified"
                or not _resolved(self.coordinate_verification_basis)
            ):
                raise ValueError(
                    "Empirical VISUS audits require an independently verified coordinate basis."
                )
            if not self.timestamp_basis_verified or not _resolved(
                self.timestamp_verification_basis
            ):
                raise ValueError(
                    "Empirical VISUS audits require a verified timestamp/frame-time basis."
                )
            self._validate_empirical_coverage()

    def _validate_empirical_coverage(self) -> None:
        video_stimuli = {
            str(record.stimulus_id) for record in self.files if record.role == "video"
        }
        gaze_stimuli = {
            str(record.stimulus_id) for record in self.files if record.role == "gaze"
        }
        aoi_stimuli = {
            str(record.stimulus_id)
            for record in self.files
            if record.role == "aoi_annotation"
        }
        participants = {
            str(record.participant_id) for record in self.files if record.role == "gaze"
        }
        expected_stimuli = int(self.published_stimulus_count)
        if len(video_stimuli) != expected_stimuli:
            raise ValueError(
                f"Empirical VISUS audit requires {expected_stimuli} manifested video stimuli."
            )
        if aoi_stimuli != video_stimuli:
            raise ValueError(
                "VISUS AOI annotation manifest must cover exactly the manifested video stimuli."
            )
        if gaze_stimuli != video_stimuli:
            raise ValueError(
                "VISUS gaze manifest must cover exactly the manifested video stimuli."
            )
        if len(participants) != int(self.published_participant_count):
            raise ValueError(
                "Empirical VISUS gaze manifest must resolve exactly 25 participant identities."
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-ready representation."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VisusAuditedFile:
    """One verified local file paired with its manifest record."""

    record: VisusSourceFileRecord
    local_path: str


@dataclass(slots=True)
class VisusSourceAuditRun:
    """Verified VISUS snapshot and deterministic source-audit report."""

    spec: VisusSourceAuditSpec
    files: list[VisusAuditedFile]
    report: dict[str, Any]


def load_visus_source_audit_spec(path: str | Path) -> VisusSourceAuditSpec:
    """Load a VISUS source-audit specification from JSON."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("VISUS source-audit specification must contain one JSON object.")
    raw_files = payload.pop("files", [])
    if not isinstance(raw_files, list):
        raise ValueError("VISUS source-audit files must be a JSON list.")
    records = [VisusSourceFileRecord(**dict(item)) for item in raw_files]
    for field_name in ("published_video_resolution_px", "published_display_resolution_px"):
        if field_name in payload:
            payload[field_name] = tuple(payload[field_name])
    return VisusSourceAuditSpec(files=records, **payload)


def _inventory(root: Path, spec: VisusSourceAuditSpec) -> tuple[list[VisusAuditedFile], str]:
    expected = {record.path: record for record in spec.files}
    actual = {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file()
    }
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if missing or extra:
        raise BenchmarkIntegrityError(
            "VISUS source snapshot does not match the exact audited manifest: "
            f"missing={missing}, extra={extra}."
        )

    audited: list[VisusAuditedFile] = []
    manifest_rows: list[dict[str, Any]] = []
    for relative_path in sorted(expected):
        record = expected[relative_path]
        local = actual[relative_path]
        observed_bytes = int(local.stat().st_size)
        observed_sha256 = _sha256(local)
        if observed_bytes != record.bytes:
            raise BenchmarkIntegrityError(
                f"VISUS byte-size mismatch for {relative_path!r}: "
                f"expected={record.bytes}, observed={observed_bytes}."
            )
        if observed_sha256 != record.sha256:
            raise BenchmarkIntegrityError(
                f"VISUS SHA-256 mismatch for {relative_path!r}: "
                f"expected={record.sha256}, observed={observed_sha256}."
            )
        audited.append(VisusAuditedFile(record=record, local_path=str(local)))
        manifest_rows.append(asdict(record))
    return audited, benchmark_fingerprint(manifest_rows)


def _annotation_stream_summary(
    records: list[VisusSourceFileRecord],
) -> tuple[dict[str, list[str]], int]:
    streams_by_stimulus: dict[str, set[str]] = {}
    for record in records:
        if record.role != "aoi_annotation":
            continue
        streams_by_stimulus.setdefault(str(record.stimulus_id), set()).add(
            str(record.annotation_stream_id)
        )
    summary = {
        stimulus: sorted(streams)
        for stimulus, streams in sorted(streams_by_stimulus.items())
    }
    minimum = min((len(streams) for streams in summary.values()), default=0)
    return summary, minimum


def audit_visus_source(
    root: str | Path,
    spec: VisusSourceAuditSpec,
) -> VisusSourceAuditRun:
    """Verify an exact VISUS snapshot before dynamic-AOI empirical analysis.

    The published benchmark describes one manual AOI annotation process involving two human
    contributors: the first performed the main annotation and the second added/refined annotations.
    Contributor count is therefore kept separate from independently available annotation streams.
    Human-human agreement is considered ready only if independent streams are explicitly manifested
    and independently verified by the audit specification.
    """
    if not isinstance(spec, VisusSourceAuditSpec):
        raise TypeError("spec must be a VisusSourceAuditSpec instance.")
    if spec.dataset_status != "empirical":
        raise BenchmarkIntegrityError(
            "VISUS source-audit templates cannot be promoted to empirical evidence."
        )
    root_path = Path(root)
    if not root_path.is_dir():
        raise FileNotFoundError(f"VISUS source directory does not exist: {root_path}")

    audited, manifest_fingerprint = _inventory(root_path, spec)
    records = [item.record for item in audited]
    role_counts = {
        role: int(sum(record.role == role for record in records))
        for role in sorted(_ALLOWED_ROLES)
    }
    stimulus_ids = sorted(
        {
            str(record.stimulus_id)
            for record in records
            if record.stimulus_id is not None
        }
    )
    participant_ids = sorted(
        {
            str(record.participant_id)
            for record in records
            if record.participant_id is not None
        }
    )
    participant_groups = sorted(
        {
            str(record.participant_group)
            for record in records
            if record.participant_group is not None
        }
    )
    streams_by_stimulus, minimum_streams = _annotation_stream_summary(records)
    human_human_ready = bool(
        spec.independent_annotation_streams_verified and minimum_streams >= 2
    )
    spec_fingerprint = benchmark_fingerprint(spec.to_dict())

    report: dict[str, Any] = {
        "dataset": "VISUS",
        "status": "verified",
        "source": {
            "dataset_version": spec.dataset_version,
            "source": spec.source,
            "source_revision": spec.source_revision,
            "license": spec.license,
            "reuse_terms_source": spec.reuse_terms_source,
            "reuse_terms_verified": bool(spec.reuse_terms_verified),
            "analysis_use_permitted": bool(spec.analysis_use_permitted),
            "redistribution_status": spec.redistribution_status,
        },
        "published_benchmark": {
            "eye_sampling_rate_hz": float(spec.published_eye_sampling_rate_hz),
            "video_frame_rate_hz": float(spec.published_video_frame_rate_hz),
            "video_resolution_px": list(spec.published_video_resolution_px),
            "display_resolution_px": list(spec.published_display_resolution_px),
            "stimulus_count": int(spec.published_stimulus_count),
            "participant_count": int(spec.published_participant_count),
            "annotation_format": spec.annotation_format,
        },
        "mapping": {
            "stimulus_mapping_verified": bool(spec.stimulus_mapping_verified),
            "stimulus_mapping_basis": spec.stimulus_mapping_basis,
            "participant_mapping_verified": bool(spec.participant_mapping_verified),
            "participant_mapping_basis": spec.participant_mapping_basis,
            "coordinate_unit": spec.coordinate_unit,
            "coordinate_unit_verified": bool(spec.coordinate_unit_verified),
            "coordinate_verification_basis": spec.coordinate_verification_basis,
            "timestamp_basis_verified": bool(spec.timestamp_basis_verified),
            "timestamp_verification_basis": spec.timestamp_verification_basis,
        },
        "inventory": {
            "file_count": len(records),
            "role_counts": role_counts,
            "files": [asdict(record) for record in records],
            "manifest_fingerprint_sha256": manifest_fingerprint,
        },
        "identity": {
            "stimulus_ids": stimulus_ids,
            "stimulus_count": len(stimulus_ids),
            "participant_ids": participant_ids,
            "participant_count": len(participant_ids),
            "participant_groups": participant_groups,
        },
        "annotation_provenance": {
            "annotation_process_contributor_count": int(
                spec.annotation_process_contributor_count
            ),
            "published_process_interpretation": (
                "main_annotation_plus_additions_and_refinements"
            ),
            "independent_annotation_streams_verified": bool(
                spec.independent_annotation_streams_verified
            ),
            "independent_annotation_streams_basis": (
                spec.independent_annotation_streams_basis
            ),
            "streams_by_stimulus": streams_by_stimulus,
            "minimum_streams_per_annotated_stimulus": minimum_streams,
            "human_human_agreement_ready": human_human_ready,
        },
        "spec_fingerprint_sha256": spec_fingerprint,
        "notes": list(spec.notes),
        "claim_limits": [
            (
                "Two human contributors to one published annotation process do not by themselves "
                "establish two independent human-reference streams."
            ),
            (
                "Human-human dynamic-AOI agreement must remain blocked unless independent "
                "annotation streams are separately manifested and verified."
            ),
            "Source audit does not establish model-human dynamic-AOI performance.",
            "Raw dataset redistribution remains governed by the independently reviewed terms.",
        ],
    }
    report["report_fingerprint_sha256"] = benchmark_fingerprint(report)
    return VisusSourceAuditRun(spec=spec, files=audited, report=report)
