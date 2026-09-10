"""Fail-closed intake and review gate for an authoritative VISUS source copy."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .visus_authoritative_source_recheck import (
    EXPECTED_PARTICIPANT_COUNT,
    EXPECTED_RECORD_FINGERPRINT_SHA256 as SOURCE_RECHECK_FINGERPRINT,
    EXPECTED_STIMULUS_COUNT,
)

SOURCE_RECORD_TYPE = "visus-authoritative-source-manifest-v1"
CANDIDATE_RECORD_TYPE = "visus-authoritative-source-candidate-v1"
REVIEW_RECORD_TYPE = "visus-authoritative-source-review-v1"
CERTIFICATE_RECORD_TYPE = "visus-authoritative-source-certificate-v1"
CANDIDATE_STATUS = "source-authority-candidate-manual-review-required"
CERTIFICATE_STATUS = "authoritative-source-and-rights-reviewed"
MAX_MANIFEST_BYTES = 512 * 1024
MAX_RIGHTS_EVIDENCE_BYTES = 16 * 1024**2
MAX_TEXT_FIELD_LENGTH = 4096
_ALLOWED_AUTHORITY_CLAIMS = {
    "author_hosted_distribution",
    "institutional_repository",
    "original_distribution_copy",
}
_ALLOWED_REDISTRIBUTION_STATUS = {"permitted", "prohibited", "not_stated"}
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
_SOURCE_KEYS = {
    "record_type",
    "source_reference",
    "source_revision",
    "source_authority_claim",
    "source_artifact_sha256",
    "rights_evidence_reference",
    "rights_evidence_sha256",
    "inventory_fingerprint_sha256",
    "file_count",
    "obtained_via_authorized_channel_affirmed",
}
_CANDIDATE_KEYS = {
    "record_type",
    "status",
    "authoritative_source_recheck_fingerprint_sha256",
    "source",
    "rights_evidence",
    "manifest",
    "inventory",
    "review_boundary",
    "scientific_boundary",
    "candidate_fingerprint_sha256",
}
_REVIEW_KEYS = {
    "record_type",
    "decision",
    "candidate_fingerprint_sha256",
    "reviewer",
    "reviewed_at",
    "source_authority_verified",
    "source_authority_evidence",
    "current_authoritative_distribution_identity_verified",
    "current_distribution_identity_evidence",
    "source_artifact_matches_authoritative_distribution_verified",
    "source_artifact_match_evidence",
    "extracted_tree_matches_source_artifact_verified",
    "extracted_tree_match_evidence",
    "rights_evidence_authoritative_verified",
    "rights_evidence_authority_evidence",
    "analysis_use_permitted_verified",
    "analysis_use_evidence",
    "redistribution_status_verified",
    "redistribution_evidence",
    "license_or_terms_identifier",
    "rights_scope_limited_to_reviewed_source",
    "participant_mapping_verified",
    "stimulus_mapping_verified",
    "coordinate_basis_verified",
    "timestamp_basis_verified",
    "independent_annotation_streams_verified",
    "empirical_validation_created",
    "raw_source_redistributed",
    "review_fingerprint_sha256",
}

_CANDIDATE_SOURCE_KEYS = {
    "artifact_basename",
    "artifact_size_bytes",
    "artifact_sha256",
    "source_reference",
    "source_revision",
    "source_authority_claim",
    "authorized_channel_affirmed",
}
_CANDIDATE_RIGHTS_KEYS = {
    "basename",
    "size_bytes",
    "sha256",
    "reference",
    "raw_rights_text_copied_to_candidate",
}
_CANDIDATE_MANIFEST_KEYS = {"basename", "size_bytes", "sha256"}
_CANDIDATE_INVENTORY_KEYS = {
    "file_count",
    "fingerprint_sha256",
    "published_participant_count",
    "published_stimulus_count",
    "file_roles_inferred",
    "participant_ids_inferred",
    "stimulus_ids_inferred",
}
_CANDIDATE_REVIEW_KEYS = {
    "source_authority_verified",
    "current_authoritative_distribution_identity_verified",
    "source_artifact_matches_authoritative_distribution_verified",
    "extracted_tree_matches_source_artifact_verified",
    "rights_evidence_authoritative_verified",
    "analysis_use_permitted_verified",
    "redistribution_status_verified",
    "source_audit_stage_authorized",
    "manual_review_required",
}
_SCIENTIFIC_KEYS = {
    "dataset_status_empirical_created",
    "participant_mapping_verified",
    "stimulus_mapping_verified",
    "coordinate_basis_verified",
    "timestamp_basis_verified",
    "independent_annotation_streams_verified",
    "human_human_agreement_created",
    "model_human_validation_created",
    "frozen_evidence_created",
    "raw_source_redistribution_action_authorized",
}
_CERTIFICATE_SOURCE_KEYS = {
    "artifact_sha256",
    "source_reference",
    "source_revision",
    "source_authority_claim",
}
_CERTIFICATE_RIGHTS_KEYS = {
    "evidence_sha256",
    "evidence_reference",
    "license_or_terms_identifier",
    "analysis_use_permitted",
    "redistribution_status",
    "rights_scope_verified",
    "raw_source_redistribution_action_authorized",
    "raw_rights_text_copied_to_certificate",
}
_CERTIFICATE_INVENTORY_KEYS = {
    "file_count",
    "fingerprint_sha256",
    "published_participant_count",
    "published_stimulus_count",
}
_CERTIFICATE_AUTHORITY_KEYS = {
    "source_authority_verified",
    "current_authoritative_distribution_identity_verified",
    "source_artifact_matches_authoritative_distribution_verified",
    "extracted_tree_matches_source_artifact_verified",
    "source_audit_stage_authorized",
}

_CERTIFICATE_KEYS = {
    "record_type",
    "status",
    "authoritative_source_recheck_fingerprint_sha256",
    "candidate_fingerprint_sha256",
    "review_fingerprint_sha256",
    "source",
    "rights",
    "inventory",
    "authority_boundary",
    "scientific_boundary",
    "certificate_fingerprint_sha256",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _fingerprint(value: Mapping[str, Any], *, field: str) -> str:
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def candidate_fingerprint(record: Mapping[str, Any]) -> str:
    """Fingerprint a source-authority candidate excluding its self-fingerprint."""
    return _fingerprint(record, field="candidate_fingerprint_sha256")


def review_fingerprint(record: Mapping[str, Any]) -> str:
    """Fingerprint a source-authority review excluding its self-fingerprint."""
    return _fingerprint(record, field="review_fingerprint_sha256")


def certificate_fingerprint(record: Mapping[str, Any]) -> str:
    """Fingerprint a source-authority certificate excluding its self-fingerprint."""
    return _fingerprint(record, field="certificate_fingerprint_sha256")


def _resolved_text(value: Any, *, label: str) -> str:
    text = "" if value is None else str(value).strip()
    if text.lower() in _UNRESOLVED:
        raise BenchmarkIntegrityError(f"VISUS source authority requires resolved {label}.")
    if len(text) > MAX_TEXT_FIELD_LENGTH:
        raise BenchmarkIntegrityError(f"VISUS source authority {label} exceeds text guardrail.")
    return text


def _sha256_value(value: Any, *, label: str) -> str:
    text = str(value).strip().lower()
    if _SHA256_RE.fullmatch(text) is None:
        raise BenchmarkIntegrityError(
            f"VISUS source authority {label} must be a lowercase SHA-256 digest."
        )
    return text


def _hash_file(path: Path, *, label: str, max_bytes: int | None = None) -> tuple[int, str]:
    if path.is_symlink() or not path.is_file():
        raise BenchmarkIntegrityError(f"VISUS {label} must be a non-symlink regular file.")
    size = int(path.stat().st_size)
    if size <= 0 or (max_bytes is not None and size > max_bytes):
        raise BenchmarkIntegrityError(f"VISUS {label} size is outside the allowed bound.")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return size, digest.hexdigest()


def _read_json(path: Path, *, label: str, max_bytes: int) -> dict[str, Any]:
    _, _ = _hash_file(path, label=label, max_bytes=max_bytes)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"VISUS {label} must be valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise BenchmarkIntegrityError(f"VISUS {label} must contain one JSON object.")
    return value


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], *, label: str) -> None:
    observed = set(value)
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise BenchmarkIntegrityError(
            f"VISUS {label} schema drifted: missing={missing}, extra={extra}."
        )


def _outside_root(root: Path, path: Path, *, label: str) -> None:
    resolved = path.resolve(strict=False)
    if resolved == root or root in resolved.parents:
        raise BenchmarkIntegrityError(
            f"VISUS {label} must remain outside the inventoried source tree."
        )


def _validate_source_manifest(
    manifest: Mapping[str, Any],
    *,
    source_sha256: str,
    rights_sha256: str,
    inventory_fingerprint_sha256: str,
    file_count: int,
) -> None:
    _require_exact_keys(manifest, _SOURCE_KEYS, label="source manifest")
    if manifest.get("record_type") != SOURCE_RECORD_TYPE:
        raise BenchmarkIntegrityError("VISUS source manifest record type drifted.")
    _resolved_text(manifest.get("source_reference"), label="source_reference")
    _resolved_text(manifest.get("source_revision"), label="source_revision")
    _resolved_text(
        manifest.get("rights_evidence_reference"), label="rights_evidence_reference"
    )
    authority = str(manifest.get("source_authority_claim", "")).strip().lower()
    if authority not in _ALLOWED_AUTHORITY_CLAIMS:
        raise BenchmarkIntegrityError("VISUS source_authority_claim is unsupported.")
    if manifest.get("obtained_via_authorized_channel_affirmed") is not True:
        raise BenchmarkIntegrityError(
            "VISUS source intake requires an authorized-channel affirmation."
        )
    if _sha256_value(
        manifest.get("source_artifact_sha256"), label="source_artifact_sha256"
    ) != source_sha256:
        raise BenchmarkIntegrityError(
            "VISUS source artifact bytes do not match the declared SHA-256."
        )
    if _sha256_value(
        manifest.get("rights_evidence_sha256"), label="rights_evidence_sha256"
    ) != rights_sha256:
        raise BenchmarkIntegrityError(
            "VISUS rights evidence bytes do not match the declared SHA-256."
        )
    if _sha256_value(
        manifest.get("inventory_fingerprint_sha256"),
        label="inventory_fingerprint_sha256",
    ) != inventory_fingerprint_sha256:
        raise BenchmarkIntegrityError(
            "VISUS source-tree inventory does not match the declared fingerprint."
        )
    if manifest.get("file_count") != file_count:
        raise BenchmarkIntegrityError("VISUS source manifest file count drifted.")
