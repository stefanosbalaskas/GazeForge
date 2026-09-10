"""Two-stage intake and review gate for an explicit Hollywood2 participant crosswalk."""

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
from .hollywood2_participant_crosswalk_exhaustion import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256 as CROSSWALK_EXHAUSTION_FINGERPRINT,
)
from .hollywood2_participant_crosswalk_exhaustion import GIN_TOKENS

SOURCE_RECORD_TYPE = "hollywood2-explicit-crosswalk-source-v1"
CANDIDATE_RECORD_TYPE = "hollywood2-explicit-crosswalk-candidate-v1"
REVIEW_RECORD_TYPE = "hollywood2-explicit-crosswalk-review-v1"
CERTIFICATE_RECORD_TYPE = "hollywood2-explicit-crosswalk-certificate-v1"
CANDIDATE_STATUS = "syntactic-candidate-manual-review-required"
CERTIFICATE_STATUS = "explicit-crosswalk-reviewed"
MAX_SOURCE_BYTES = 8 * 1024**2
MAX_MANIFEST_BYTES = 512 * 1024
MAX_TEXT_FIELD_LENGTH = 4096
_ALLOWED_AUTHORITY_CLAIMS = {
    "author_statement",
    "institutional_record",
    "original_distribution_metadata",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
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
class ReviewedHollywood2Crosswalk:
    """In-memory reviewed mapping plus a non-empirical certificate."""

    mapping: dict[str, tuple[str, str]]
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


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_bounded(path: Path, *, max_bytes: int, label: str) -> bytes:
    if not path.is_file():
        raise BenchmarkIntegrityError(f"Hollywood2 crosswalk {label} is not a regular file.")
    size = path.stat().st_size
    if size <= 0 or size > max_bytes:
        raise BenchmarkIntegrityError(
            f"Hollywood2 crosswalk {label} size is outside the allowed bound."
        )
    return path.read_bytes()


def _load_json_bytes(data: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Hollywood2 crosswalk {label} must be valid UTF-8 JSON."
        ) from exc
    if not isinstance(value, dict):
        raise BenchmarkIntegrityError(
            f"Hollywood2 crosswalk {label} must contain one JSON object."
        )
    return value


def _resolved_text(value: Any, *, label: str) -> str:
    text = "" if value is None else str(value).strip()
    if text.lower() in _UNRESOLVED:
        raise BenchmarkIntegrityError(
            f"Hollywood2 crosswalk requires resolved {label}."
        )
    if len(text) > MAX_TEXT_FIELD_LENGTH:
        raise BenchmarkIntegrityError(
            f"Hollywood2 crosswalk {label} exceeds the text-size guardrail."
        )
    return text


def _sha256(value: Any, *, label: str) -> str:
    text = str(value).strip().lower()
    if _SHA256_RE.fullmatch(text) is None:
        raise BenchmarkIntegrityError(
            f"Hollywood2 crosswalk {label} must be a lowercase SHA-256 digest."
        )
    return text


def _validate_manifest(
    manifest: Mapping[str, Any],
    *,
    source_sha256: str,
) -> list[dict[str, str]]:
    if manifest.get("record_type") != SOURCE_RECORD_TYPE:
        raise BenchmarkIntegrityError("Hollywood2 crosswalk source record type drifted.")
    _resolved_text(manifest.get("source_reference"), label="source_reference")
    authority = str(manifest.get("source_authority_claim", "")).strip().lower()
    if authority not in _ALLOWED_AUTHORITY_CLAIMS:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk source_authority_claim is unsupported."
        )
    declared_sha = _sha256(
        manifest.get("source_file_sha256"),
        label="source_file_sha256",
    )
    if declared_sha != source_sha256:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk source bytes do not match the declared SHA-256."
        )
    if manifest.get("obtained_via_authorized_channel_affirmed") is not True:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk intake requires an authorized-channel affirmation."
        )

    raw_entries = manifest.get("mapping_entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk source manifest requires mapping_entries."
        )
    if len(raw_entries) > len(GIN_TOKENS):
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk source manifest has too many GIN-token entries."
        )

    entries: list[dict[str, str]] = []
    seen_tokens: set[str] = set()
    for raw in raw_entries:
        if not isinstance(raw, Mapping):
            raise BenchmarkIntegrityError(
                "Hollywood2 crosswalk mapping entries must be JSON objects."
            )
        token = str(raw.get("gin_token", "")).strip()
        if token not in GIN_TOKENS:
            raise BenchmarkIntegrityError(
                f"Hollywood2 crosswalk contains unknown GIN token {token!r}."
            )
        if token in seen_tokens:
            raise BenchmarkIntegrityError(
                f"Hollywood2 crosswalk duplicates GIN token {token!r}."
            )
        seen_tokens.add(token)
        subject_id = _resolved_text(
            raw.get("original_subject_id"),
            label=f"original_subject_id for {token}",
        )
        task_group = _resolved_text(
            raw.get("task_group"),
            label=f"task_group for {token}",
        )
        entries.append(
            {
                "gin_token": token,
                "original_subject_id": subject_id,
                "task_group": task_group,
            }
        )
    return sorted(entries, key=lambda item: item["gin_token"])


def inspect_explicit_crosswalk_candidate(
    source_path: str | Path,
    manifest_path: str | Path,
) -> dict[str, Any]:
    """Validate a local transcription without promoting participant identity.

    The exact source bytes and local manifest remain local. The returned record
    contains hashes and aggregate mapping properties but no participant IDs or
    task-group labels.
    """
    source = Path(source_path)
    manifest_file = Path(manifest_path)
    source_bytes = _read_bounded(source, max_bytes=MAX_SOURCE_BYTES, label="source file")
    manifest_bytes = _read_bounded(
        manifest_file,
        max_bytes=MAX_MANIFEST_BYTES,
        label="manifest",
    )
    source_sha = _sha256_bytes(source_bytes)
    manifest = _load_json_bytes(manifest_bytes, label="manifest")
    entries = _validate_manifest(manifest, source_sha256=source_sha)

    tokens = [item["gin_token"] for item in entries]
    subject_ids = [item["original_subject_id"] for item in entries]
    task_groups = [item["task_group"] for item in entries]
    complete = tuple(tokens) == tuple(GIN_TOKENS)
    one_to_one = len(set(subject_ids)) == len(subject_ids)
    mapping_sha = _sha256_bytes(_canonical_bytes({"mapping_entries": entries}))

    record: dict[str, Any] = {
        "record_type": CANDIDATE_RECORD_TYPE,
        "status": CANDIDATE_STATUS,
        "crosswalk_exhaustion_evidence_fingerprint_sha256": (
            CROSSWALK_EXHAUSTION_FINGERPRINT
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
            "gin_tokens_present": tokens,
            "complete_gin_token_coverage": complete,
            "unique_subject_id_count": len(set(subject_ids)),
            "one_to_one_subject_ids": one_to_one,
            "task_group_label_count": len(set(task_groups)),
            "mapping_fingerprint_sha256": mapping_sha,
            "raw_subject_ids_copied_to_candidate_record": False,
            "raw_task_group_labels_copied_to_candidate_record": False,
        },
        "review_boundary": {
            "source_authority_verified": False,
            "mapping_explicit_in_source_verified": False,
            "mapping_transcription_verified": False,
            "task_group_semantics_verified": False,
            "source_version_scope_verified": False,
            "gin_token_to_original_subject_id_verified": False,
            "gin_token_to_task_group_verified": False,
            "participant_identity_mapping_verified": False,
            "manual_review_required": True,
        },
        "scientific_boundary": {
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_validation_created": False,
            "new_empirical_performance_claim_created": False,
            "rights_scope_promoted": False,
            "raw_gaze_inspected": False,
            "raw_gaze_redistributed": False,
        },
    }
    record["candidate_fingerprint_sha256"] = candidate_fingerprint(record)
    return record


def validate_candidate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a candidate and ensure that it cannot itself promote mapping."""
    value = dict(record)
    if value.get("record_type") != CANDIDATE_RECORD_TYPE:
        raise BenchmarkIntegrityError("Hollywood2 crosswalk candidate record type drifted.")
    if value.get("status") != CANDIDATE_STATUS:
        raise BenchmarkIntegrityError("Hollywood2 crosswalk candidate status drifted.")
    if value.get("crosswalk_exhaustion_evidence_fingerprint_sha256") != (
        CROSSWALK_EXHAUSTION_FINGERPRINT
    ):
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk candidate exhaustion-evidence binding drifted."
        )
    stored = str(value.get("candidate_fingerprint_sha256", ""))
    if stored != candidate_fingerprint(value):
        raise BenchmarkIntegrityError("Hollywood2 crosswalk candidate fingerprint drifted.")

    summary = value.get("mapping_summary")
    review = value.get("review_boundary")
    scientific = value.get("scientific_boundary")
    if not all(isinstance(item, Mapping) for item in (summary, review, scientific)):
        raise BenchmarkIntegrityError("Hollywood2 crosswalk candidate sections are missing.")
    assert isinstance(summary, Mapping)
    assert isinstance(review, Mapping)
    assert isinstance(scientific, Mapping)

    tokens = tuple(summary.get("gin_tokens_present", []))
    if any(token not in GIN_TOKENS for token in tokens) or len(tokens) != len(set(tokens)):
        raise BenchmarkIntegrityError("Hollywood2 crosswalk candidate token coverage is invalid.")
    if summary.get("raw_subject_ids_copied_to_candidate_record") is not False:
        raise BenchmarkIntegrityError("Hollywood2 crosswalk candidate leaked subject IDs.")
    if summary.get("raw_task_group_labels_copied_to_candidate_record") is not False:
        raise BenchmarkIntegrityError("Hollywood2 crosswalk candidate leaked task-group labels.")

    for key in (
        "source_authority_verified",
        "mapping_explicit_in_source_verified",
        "mapping_transcription_verified",
        "task_group_semantics_verified",
        "source_version_scope_verified",
        "gin_token_to_original_subject_id_verified",
        "gin_token_to_task_group_verified",
        "participant_identity_mapping_verified",
    ):
        if review.get(key) is not False:
            raise BenchmarkIntegrityError(
                f"Hollywood2 crosswalk candidate must not promote {key}."
            )
    if review.get("manual_review_required") is not True:
        raise BenchmarkIntegrityError("Hollywood2 crosswalk manual-review gate was relaxed.")
    for key in (
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "new_empirical_performance_claim_created",
        "rights_scope_promoted",
        "raw_gaze_inspected",
        "raw_gaze_redistributed",
    ):
        if scientific.get(key) is not False:
            raise BenchmarkIntegrityError(
                f"Hollywood2 crosswalk candidate must not promote {key}."
            )
    return value


def _load_review(path: Path) -> dict[str, Any]:
    data = _read_bounded(path, max_bytes=MAX_MANIFEST_BYTES, label="review record")
    return _load_json_bytes(data, label="review record")


def _validate_review_timestamp(value: Any) -> str:
    text = _resolved_text(value, label="reviewed_at")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk reviewed_at must be an ISO-8601 timestamp."
        ) from exc
    if parsed.tzinfo is None:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk reviewed_at must include a timezone offset."
        )
    return text


def require_reviewed_explicit_crosswalk(
    source_path: str | Path,
    manifest_path: str | Path,
    candidate_record: Mapping[str, Any],
    review_path: str | Path,
) -> ReviewedHollywood2Crosswalk:
    """Return an in-memory mapping only after a separately bound manual review."""
    candidate = validate_candidate_record(candidate_record)
    replayed = inspect_explicit_crosswalk_candidate(source_path, manifest_path)
    if replayed["candidate_fingerprint_sha256"] != candidate["candidate_fingerprint_sha256"]:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk candidate no longer matches the local source/manifest."
        )

    summary = candidate["mapping_summary"]
    assert isinstance(summary, Mapping)
    if summary.get("complete_gin_token_coverage") is not True:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk review requires complete canonical GIN-token coverage."
        )
    if summary.get("one_to_one_subject_ids") is not True:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk review requires one-to-one subject identifiers."
        )

    review = _load_review(Path(review_path))
    if review.get("record_type") != REVIEW_RECORD_TYPE:
        raise BenchmarkIntegrityError("Hollywood2 crosswalk review record type drifted.")
    if review.get("decision") != "approved":
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk requires an explicit decision='approved'."
        )
    if review.get("candidate_fingerprint_sha256") != candidate[
        "candidate_fingerprint_sha256"
    ]:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk review is not bound to this exact candidate."
        )
    _resolved_text(review.get("reviewer"), label="reviewer")
    _validate_review_timestamp(review.get("reviewed_at"))
    for field in (
        "source_authority_evidence",
        "mapping_explicitness_evidence",
        "mapping_transcription_evidence",
        "task_group_semantics_evidence",
        "source_version_scope_evidence",
    ):
        _resolved_text(review.get(field), label=field)
    for field in (
        "source_authority_verified",
        "mapping_explicit_in_source_verified",
        "mapping_transcription_verified",
        "task_group_semantics_verified",
        "source_version_scope_verified",
    ):
        if review.get(field) is not True:
            raise BenchmarkIntegrityError(
                f"Hollywood2 crosswalk approved review requires {field}=true."
            )
    if review.get("rights_scope_promoted") is not False:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk review cannot promote dataset rights."
        )
    if review.get("empirical_validation_created") is not False:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk review cannot create empirical validation."
        )
    stored_review_fp = str(review.get("review_fingerprint_sha256", ""))
    if stored_review_fp != review_fingerprint(review):
        raise BenchmarkIntegrityError("Hollywood2 crosswalk review fingerprint drifted.")

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
    entries = _validate_manifest(manifest, source_sha256=_sha256_bytes(source_bytes))
    mapping = {
        entry["gin_token"]: (entry["original_subject_id"], entry["task_group"])
        for entry in entries
    }

    certificate: dict[str, Any] = {
        "record_type": CERTIFICATE_RECORD_TYPE,
        "status": CERTIFICATE_STATUS,
        "candidate_fingerprint_sha256": candidate["candidate_fingerprint_sha256"],
        "review_fingerprint_sha256": stored_review_fp,
        "mapping_fingerprint_sha256": summary["mapping_fingerprint_sha256"],
        "token_count": len(mapping),
        "gin_tokens": list(GIN_TOKENS),
        "mapping_boundary": {
            "gin_token_to_original_subject_id_verified": True,
            "gin_token_to_task_group_verified": True,
            "participant_identity_mapping_verified": True,
            "raw_subject_ids_copied_to_certificate": False,
            "raw_task_group_labels_copied_to_certificate": False,
        },
        "scientific_boundary": {
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_validation_created": False,
            "new_empirical_performance_claim_created": False,
            "rights_scope_promoted": False,
            "raw_gaze_inspected": False,
            "raw_gaze_redistributed": False,
        },
    }
    certificate["certificate_fingerprint_sha256"] = certificate_fingerprint(certificate)
    return ReviewedHollywood2Crosswalk(mapping=mapping, certificate=certificate)
