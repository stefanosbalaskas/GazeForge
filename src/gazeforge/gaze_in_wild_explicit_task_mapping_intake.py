"""Two-stage intake and review gate for an explicit Gaze-in-the-Wild task mapping."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_authoritative_task_mapping_exhaustion import (
    EXPECTED_EVIDENCE_FINGERPRINT as TASK_MAPPING_EXHAUSTION_FINGERPRINT,
)
from .gaze_in_wild_authoritative_task_mapping_exhaustion import EXPECTED_TASKS

SOURCE_RECORD_TYPE = "gaze-in-wild-explicit-task-mapping-source-v1"
CANDIDATE_RECORD_TYPE = "gaze-in-wild-explicit-task-mapping-candidate-v1"
REVIEW_RECORD_TYPE = "gaze-in-wild-explicit-task-mapping-review-v1"
CERTIFICATE_RECORD_TYPE = "gaze-in-wild-explicit-task-mapping-certificate-v1"
CANDIDATE_STATUS = "syntactic-candidate-manual-review-required"
CERTIFICATE_STATUS = "explicit-authoritative-task-mapping-reviewed"
TRIAL_INDICES = (1, 2, 3, 4)
MAX_SOURCE_BYTES = 8 * 1024**2
MAX_MANIFEST_BYTES = 512 * 1024
MAX_TEXT_FIELD_LENGTH = 4096
_ALLOWED_AUTHORITY_CLAIMS = {
    "author_statement",
    "first_party_repository_record",
    "original_distribution_metadata",
    "publication_supplement",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CANDIDATE_TOP_LEVEL_KEYS = {
    "record_type",
    "status",
    "authoritative_task_mapping_exhaustion_fingerprint_sha256",
    "source",
    "manifest",
    "mapping_summary",
    "review_boundary",
    "scientific_boundary",
    "candidate_fingerprint_sha256",
}
_SOURCE_KEYS = {
    "basename",
    "size_bytes",
    "sha256",
    "source_reference",
    "source_authority_claim",
    "authorized_channel_affirmed",
}
_MANIFEST_KEYS = {"basename", "size_bytes", "sha256"}
_MAPPING_SUMMARY_KEYS = {
    "entry_count",
    "trial_indices_present",
    "publication_task_count",
    "complete_trial_index_coverage",
    "complete_publication_task_coverage",
    "complete_one_to_one_mapping",
    "mapping_fingerprint_sha256",
    "tridx4_present_in_transcription",
    "raw_task_mapping_copied_to_candidate_record",
}
_REVIEW_BOUNDARY_KEYS = {
    "source_authority_verified",
    "mapping_explicit_in_source_verified",
    "mapping_transcription_verified",
    "publication_task_semantics_verified",
    "source_version_scope_verified",
    "tridx4_explicit_in_source_verified",
    "no_elimination_or_order_inference_used_verified",
    "authoritative_trial_task_mapping_verified",
    "complete_trial_task_mapping_verified",
    "manual_review_required",
}
_SCIENTIFIC_BOUNDARY_KEYS = {
    "task_stratified_validation_created",
    "participant_disjoint_validation_created",
    "cross_dataset_validation_created",
    "new_empirical_performance_claim_created",
    "native_60hz_validity_created",
    "gp3_validity_created",
    "acquisition_hardware_cadence_verified",
    "quarantine_exit_authorized",
    "rights_scope_promoted",
    "raw_data_retention_claim_created",
}
_REVIEW_RECORD_KEYS = {
    "record_type",
    "decision",
    "candidate_fingerprint_sha256",
    "reviewer",
    "reviewed_at",
    "source_authority_verified",
    "source_authority_evidence",
    "mapping_explicit_in_source_verified",
    "mapping_explicitness_evidence",
    "mapping_transcription_verified",
    "mapping_transcription_evidence",
    "publication_task_semantics_verified",
    "publication_task_semantics_evidence",
    "source_version_scope_verified",
    "source_version_scope_evidence",
    "tridx4_explicit_in_source_verified",
    "tridx4_explicitness_evidence",
    "no_elimination_or_order_inference_used_verified",
    "no_elimination_or_order_inference_evidence",
    "rights_scope_promoted",
    "empirical_validation_created",
    "quarantine_exit_authorized",
    "review_fingerprint_sha256",
}
_UNRESOLVED = {
    "",
    "review_required",
    "__unresolved__",
    "unknown",
    "none",
    "nan",
    "todo",
    "tbd",
}


@dataclass(frozen=True, slots=True)
class ReviewedGazeInWildTaskMapping:
    """In-memory reviewed mapping plus a non-empirical certificate."""

    mapping: dict[int, str]
    certificate: dict[str, Any]


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _fingerprint(value: Mapping[str, Any], *, field: str) -> str:
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def candidate_fingerprint(record: Mapping[str, Any]) -> str:
    """Fingerprint a candidate record excluding its self-fingerprint."""
    return _fingerprint(record, field="candidate_fingerprint_sha256")


def review_fingerprint(record: Mapping[str, Any]) -> str:
    """Fingerprint a review record excluding its self-fingerprint."""
    return _fingerprint(record, field="review_fingerprint_sha256")


def certificate_fingerprint(record: Mapping[str, Any]) -> str:
    """Fingerprint a certificate excluding its self-fingerprint."""
    return _fingerprint(record, field="certificate_fingerprint_sha256")


def _require_exact_keys(
    value: Mapping[str, Any],
    expected: set[str],
    *,
    label: str,
) -> None:
    observed = set(value)
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild task-mapping {label} schema drifted; "
            f"missing={missing}, extra={extra}."
        )


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_bounded(path: Path, *, max_bytes: int, label: str) -> bytes:
    if not path.is_file():
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild task-mapping {label} is not a regular file."
        )
    size = path.stat().st_size
    if size <= 0 or size > max_bytes:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild task-mapping {label} size is outside the allowed bound."
        )
    return path.read_bytes()


def _load_json_bytes(data: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild task-mapping {label} must be valid UTF-8 JSON."
        ) from exc
    if not isinstance(value, dict):
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild task-mapping {label} must contain one JSON object."
        )
    return value


def _resolved_text(value: Any, *, label: str) -> str:
    text = "" if value is None else str(value).strip()
    if text.lower() in _UNRESOLVED:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild task mapping requires resolved {label}."
        )
    if len(text) > MAX_TEXT_FIELD_LENGTH:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild task-mapping {label} exceeds the text-size guardrail."
        )
    return text


def _sha256(value: Any, *, label: str) -> str:
    text = str(value).strip()
    if _SHA256_RE.fullmatch(text) is None:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild task-mapping {label} must be a lowercase SHA-256 digest."
        )
    return text


def _trial_index(value: Any) -> int:
    if isinstance(value, bool):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task mapping trial_index must be an integer in {1,2,3,4}."
        )
    try:
        index = int(value)
    except (TypeError, ValueError) as exc:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task mapping trial_index must be an integer in {1,2,3,4}."
        ) from exc
    if value != index and str(value).strip() != str(index):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task mapping trial_index must be an integer in {1,2,3,4}."
        )
    if index not in TRIAL_INDICES:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild task mapping contains unknown TrIdx {index!r}."
        )
    return index


def _validate_manifest(
    manifest: Mapping[str, Any],
    *,
    source_sha256: str,
) -> list[dict[str, Any]]:
    if manifest.get("record_type") != SOURCE_RECORD_TYPE:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping source record type drifted."
        )
    _resolved_text(manifest.get("source_reference"), label="source_reference")
    authority = str(manifest.get("source_authority_claim", "")).strip().lower()
    if authority not in _ALLOWED_AUTHORITY_CLAIMS:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping source_authority_claim is unsupported."
        )
    declared_sha = _sha256(
        manifest.get("source_file_sha256"),
        label="source_file_sha256",
    )
    if declared_sha != source_sha256:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping source bytes do not match the declared SHA-256."
        )
    if manifest.get("obtained_via_authorized_channel_affirmed") is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping intake requires an authorized-channel affirmation."
        )

    raw_entries = manifest.get("mapping_entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping source manifest requires mapping_entries."
        )
    if len(raw_entries) > len(TRIAL_INDICES):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping source manifest has too many TrIdx entries."
        )

    entries: list[dict[str, Any]] = []
    seen_indices: set[int] = set()
    seen_tasks: set[str] = set()
    for raw in raw_entries:
        if not isinstance(raw, Mapping):
            raise BenchmarkIntegrityError(
                "Gaze-in-the-Wild task-mapping entries must be JSON objects."
            )
        index = _trial_index(raw.get("trial_index"))
        if index in seen_indices:
            raise BenchmarkIntegrityError(
                f"Gaze-in-the-Wild task mapping duplicates TrIdx {index!r}."
            )
        seen_indices.add(index)
        task = _resolved_text(
            raw.get("task_label"),
            label=f"task_label for TrIdx {index}",
        )
        if task not in EXPECTED_TASKS:
            raise BenchmarkIntegrityError(
                f"Gaze-in-the-Wild task mapping contains unknown publication task {task!r}."
            )
        if task in seen_tasks:
            raise BenchmarkIntegrityError(
                f"Gaze-in-the-Wild task mapping duplicates publication task {task!r}."
            )
        seen_tasks.add(task)
        entries.append({"trial_index": index, "task_label": task})
    return sorted(entries, key=lambda item: item["trial_index"])


def inspect_explicit_task_mapping_candidate(
    source_path: str | Path,
    manifest_path: str | Path,
) -> dict[str, Any]:
    """Validate a local transcription without promoting task identity."""
    source = Path(source_path)
    manifest_file = Path(manifest_path)
    source_bytes = _read_bounded(
        source,
        max_bytes=MAX_SOURCE_BYTES,
        label="source file",
    )
    manifest_bytes = _read_bounded(
        manifest_file,
        max_bytes=MAX_MANIFEST_BYTES,
        label="manifest",
    )
    source_sha = _sha256_bytes(source_bytes)
    manifest = _load_json_bytes(manifest_bytes, label="manifest")
    entries = _validate_manifest(manifest, source_sha256=source_sha)

    indices = [item["trial_index"] for item in entries]
    tasks = [item["task_label"] for item in entries]
    complete_indices = tuple(indices) == TRIAL_INDICES
    complete_tasks = set(tasks) == set(EXPECTED_TASKS)
    complete = complete_indices and complete_tasks
    mapping_sha = _sha256_bytes(_canonical_bytes({"mapping_entries": entries}))

    record: dict[str, Any] = {
        "record_type": CANDIDATE_RECORD_TYPE,
        "status": CANDIDATE_STATUS,
        "authoritative_task_mapping_exhaustion_fingerprint_sha256": (
            TASK_MAPPING_EXHAUSTION_FINGERPRINT
        ),
        "source": {
            "basename": source.name,
            "size_bytes": len(source_bytes),
            "sha256": source_sha,
            "source_reference": str(manifest["source_reference"]).strip(),
            "source_authority_claim": str(manifest["source_authority_claim"])
            .strip()
            .lower(),
            "authorized_channel_affirmed": True,
        },
        "manifest": {
            "basename": manifest_file.name,
            "size_bytes": len(manifest_bytes),
            "sha256": _sha256_bytes(manifest_bytes),
        },
        "mapping_summary": {
            "entry_count": len(entries),
            "trial_indices_present": indices,
            "publication_task_count": len(set(tasks)),
            "complete_trial_index_coverage": complete_indices,
            "complete_publication_task_coverage": complete_tasks,
            "complete_one_to_one_mapping": complete,
            "mapping_fingerprint_sha256": mapping_sha,
            "tridx4_present_in_transcription": 4 in indices,
            "raw_task_mapping_copied_to_candidate_record": False,
        },
        "review_boundary": {
            "source_authority_verified": False,
            "mapping_explicit_in_source_verified": False,
            "mapping_transcription_verified": False,
            "publication_task_semantics_verified": False,
            "source_version_scope_verified": False,
            "tridx4_explicit_in_source_verified": False,
            "no_elimination_or_order_inference_used_verified": False,
            "authoritative_trial_task_mapping_verified": False,
            "complete_trial_task_mapping_verified": False,
            "manual_review_required": True,
        },
        "scientific_boundary": {
            "task_stratified_validation_created": False,
            "participant_disjoint_validation_created": False,
            "cross_dataset_validation_created": False,
            "new_empirical_performance_claim_created": False,
            "native_60hz_validity_created": False,
            "gp3_validity_created": False,
            "acquisition_hardware_cadence_verified": False,
            "quarantine_exit_authorized": False,
            "rights_scope_promoted": False,
            "raw_data_retention_claim_created": False,
        },
    }
    record["candidate_fingerprint_sha256"] = candidate_fingerprint(record)
    return record


def validate_candidate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a candidate and ensure it cannot itself promote task identity."""
    value = dict(record)
    if value.get("record_type") != CANDIDATE_RECORD_TYPE:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate record type drifted."
        )
    if value.get("status") != CANDIDATE_STATUS:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate status drifted."
        )
    if value.get("authoritative_task_mapping_exhaustion_fingerprint_sha256") != (
        TASK_MAPPING_EXHAUSTION_FINGERPRINT
    ):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate exhaustion binding drifted."
        )
    stored = str(value.get("candidate_fingerprint_sha256", ""))
    if stored != candidate_fingerprint(value):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate fingerprint drifted."
        )
    _require_exact_keys(
        value,
        _CANDIDATE_TOP_LEVEL_KEYS,
        label="candidate top-level",
    )

    source = value.get("source")
    manifest = value.get("manifest")
    summary = value.get("mapping_summary")
    review = value.get("review_boundary")
    scientific = value.get("scientific_boundary")
    if not all(
        isinstance(item, Mapping)
        for item in (source, manifest, summary, review, scientific)
    ):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate sections are missing."
        )
    assert isinstance(source, Mapping)
    assert isinstance(manifest, Mapping)
    assert isinstance(summary, Mapping)
    assert isinstance(review, Mapping)
    assert isinstance(scientific, Mapping)

    _require_exact_keys(source, _SOURCE_KEYS, label="candidate source")
    _require_exact_keys(manifest, _MANIFEST_KEYS, label="candidate manifest")
    _require_exact_keys(summary, _MAPPING_SUMMARY_KEYS, label="candidate mapping summary")
    _require_exact_keys(review, _REVIEW_BOUNDARY_KEYS, label="candidate review boundary")
    _require_exact_keys(
        scientific,
        _SCIENTIFIC_BOUNDARY_KEYS,
        label="candidate scientific boundary",
    )

    if source.get("source_authority_claim") not in _ALLOWED_AUTHORITY_CLAIMS:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate authority class drifted."
        )
    if source.get("authorized_channel_affirmed") is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate authorization drifted."
        )
    _sha256(source.get("sha256"), label="candidate source sha256")
    _sha256(manifest.get("sha256"), label="candidate manifest sha256")

    indices = summary.get("trial_indices_present")
    if not isinstance(indices, list):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate TrIdx ledger is missing."
        )
    if any(not isinstance(index, int) or index not in TRIAL_INDICES for index in indices):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate TrIdx coverage is invalid."
        )
    if indices != sorted(indices) or len(indices) != len(set(indices)):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate TrIdx ledger drifted."
        )
    entry_count = summary.get("entry_count")
    if entry_count != len(indices):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate entry count drifted."
        )
    task_count = summary.get("publication_task_count")
    if not isinstance(task_count, int) or task_count < 1 or task_count > len(EXPECTED_TASKS):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate task count is invalid."
        )
    if task_count != entry_count:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate task count drifted from entries."
        )
    complete_indices = tuple(indices) == TRIAL_INDICES
    if summary.get("complete_trial_index_coverage") is not complete_indices:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate TrIdx completeness drifted."
        )
    if summary.get("complete_publication_task_coverage") is not (task_count == len(EXPECTED_TASKS)):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate task completeness drifted."
        )
    complete = complete_indices and task_count == len(EXPECTED_TASKS)
    if summary.get("complete_one_to_one_mapping") is not complete:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate one-to-one completeness drifted."
        )
    if summary.get("tridx4_present_in_transcription") is not (4 in indices):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate TrIdx 4 presence drifted."
        )
    _sha256(
        summary.get("mapping_fingerprint_sha256"),
        label="mapping_fingerprint_sha256",
    )
    if summary.get("raw_task_mapping_copied_to_candidate_record") is not False:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate leaked the raw mapping."
        )

    for key in (
        "source_authority_verified",
        "mapping_explicit_in_source_verified",
        "mapping_transcription_verified",
        "publication_task_semantics_verified",
        "source_version_scope_verified",
        "tridx4_explicit_in_source_verified",
        "no_elimination_or_order_inference_used_verified",
        "authoritative_trial_task_mapping_verified",
        "complete_trial_task_mapping_verified",
    ):
        if review.get(key) is not False:
            raise BenchmarkIntegrityError(
                f"Gaze-in-the-Wild task-mapping candidate must not promote {key}."
            )
    if review.get("manual_review_required") is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping manual-review gate was relaxed."
        )

    for key in (
        "task_stratified_validation_created",
        "participant_disjoint_validation_created",
        "cross_dataset_validation_created",
        "new_empirical_performance_claim_created",
        "native_60hz_validity_created",
        "gp3_validity_created",
        "acquisition_hardware_cadence_verified",
        "quarantine_exit_authorized",
        "rights_scope_promoted",
        "raw_data_retention_claim_created",
    ):
        if scientific.get(key) is not False:
            raise BenchmarkIntegrityError(
                f"Gaze-in-the-Wild task-mapping candidate must not promote {key}."
            )
    return value


def _load_review(path: Path) -> dict[str, Any]:
    data = _read_bounded(
        path,
        max_bytes=MAX_MANIFEST_BYTES,
        label="review record",
    )
    return _load_json_bytes(data, label="review record")


def _validate_review_timestamp(value: Any) -> str:
    text = _resolved_text(value, label="reviewed_at")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping reviewed_at must be an ISO-8601 timestamp."
        ) from exc
    if parsed.tzinfo is None:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping reviewed_at must include a timezone offset."
        )
    return text


def require_reviewed_explicit_task_mapping(
    source_path: str | Path,
    manifest_path: str | Path,
    candidate_record: Mapping[str, Any],
    review_path: str | Path,
) -> ReviewedGazeInWildTaskMapping:
    """Return the mapping only after a separately bound authoritative manual review."""
    candidate = validate_candidate_record(candidate_record)
    replayed = inspect_explicit_task_mapping_candidate(source_path, manifest_path)
    if replayed["candidate_fingerprint_sha256"] != candidate["candidate_fingerprint_sha256"]:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping candidate no longer matches source/manifest."
        )

    summary = candidate["mapping_summary"]
    assert isinstance(summary, Mapping)
    if summary.get("complete_trial_index_coverage") is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild review requires complete TrIdx 1..4 coverage."
        )
    if summary.get("complete_publication_task_coverage") is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild review requires all four publication tasks."
        )
    if summary.get("complete_one_to_one_mapping") is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild review requires a complete one-to-one task mapping."
        )
    if summary.get("tridx4_present_in_transcription") is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild review requires a transcribed TrIdx 4 entry."
        )

    review = _load_review(Path(review_path))
    _require_exact_keys(review, _REVIEW_RECORD_KEYS, label="review")
    if review.get("record_type") != REVIEW_RECORD_TYPE:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping review record type drifted."
        )
    if review.get("decision") != "approved":
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task mapping requires decision='approved'."
        )
    if review.get("candidate_fingerprint_sha256") != candidate[
        "candidate_fingerprint_sha256"
    ]:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping review is not bound to this exact candidate."
        )
    _resolved_text(review.get("reviewer"), label="reviewer")
    _validate_review_timestamp(review.get("reviewed_at"))

    evidence_fields = (
        "source_authority_evidence",
        "mapping_explicitness_evidence",
        "mapping_transcription_evidence",
        "publication_task_semantics_evidence",
        "source_version_scope_evidence",
        "tridx4_explicitness_evidence",
        "no_elimination_or_order_inference_evidence",
    )
    for field in evidence_fields:
        _resolved_text(review.get(field), label=field)

    verification_fields = (
        "source_authority_verified",
        "mapping_explicit_in_source_verified",
        "mapping_transcription_verified",
        "publication_task_semantics_verified",
        "source_version_scope_verified",
        "tridx4_explicit_in_source_verified",
        "no_elimination_or_order_inference_used_verified",
    )
    for field in verification_fields:
        if review.get(field) is not True:
            raise BenchmarkIntegrityError(
                f"Gaze-in-the-Wild approved review requires {field}=true."
            )
    if review.get("rights_scope_promoted") is not False:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping review cannot promote dataset rights."
        )
    if review.get("empirical_validation_created") is not False:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping review cannot create empirical validation."
        )
    if review.get("quarantine_exit_authorized") is not False:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping review cannot authorize quarantine exit."
        )

    stored_review_fp = str(review.get("review_fingerprint_sha256", ""))
    if stored_review_fp != review_fingerprint(review):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild task-mapping review fingerprint drifted."
        )

    manifest_bytes = _read_bounded(
        Path(manifest_path),
        max_bytes=MAX_MANIFEST_BYTES,
        label="manifest",
    )
    manifest = _load_json_bytes(manifest_bytes, label="manifest")
    source_bytes = _read_bounded(
        Path(source_path),
        max_bytes=MAX_SOURCE_BYTES,
        label="source file",
    )
    entries = _validate_manifest(
        manifest,
        source_sha256=_sha256_bytes(source_bytes),
    )
    mapping = {entry["trial_index"]: entry["task_label"] for entry in entries}

    certificate: dict[str, Any] = {
        "record_type": CERTIFICATE_RECORD_TYPE,
        "status": CERTIFICATE_STATUS,
        "authoritative_task_mapping_exhaustion_fingerprint_sha256": (
            TASK_MAPPING_EXHAUSTION_FINGERPRINT
        ),
        "candidate_fingerprint_sha256": candidate["candidate_fingerprint_sha256"],
        "review_fingerprint_sha256": stored_review_fp,
        "mapping_fingerprint_sha256": summary["mapping_fingerprint_sha256"],
        "trial_index_count": len(mapping),
        "trial_indices": list(TRIAL_INDICES),
        "publication_task_count": len(EXPECTED_TASKS),
        "publication_tasks": list(EXPECTED_TASKS),
        "mapping_boundary": {
            "authoritative_trial_task_mapping_verified": True,
            "complete_trial_task_mapping_verified": True,
            "tridx4_explicit_in_source_verified": True,
            "tridx4_tea_making_inferred_by_elimination": False,
            "publication_order_used_as_mapping": False,
            "task_directory_order_used_as_mapping": False,
            "mapping_available_for_downstream_validation": True,
            "raw_task_mapping_copied_to_certificate": False,
        },
        "scientific_boundary": {
            "task_stratified_validation_created": False,
            "participant_disjoint_validation_created": False,
            "cross_dataset_validation_created": False,
            "new_empirical_performance_claim_created": False,
            "native_60hz_validity_created": False,
            "gp3_validity_created": False,
            "acquisition_hardware_cadence_verified": False,
            "quarantine_exit_authorized": False,
            "rights_scope_promoted": False,
            "raw_data_retention_claim_created": False,
        },
    }
    certificate["certificate_fingerprint_sha256"] = certificate_fingerprint(certificate)
    return ReviewedGazeInWildTaskMapping(mapping=mapping, certificate=certificate)
