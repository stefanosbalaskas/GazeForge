"""Metadata-only intake for a legitimately obtained original Hollywood-2 archive."""

from __future__ import annotations

import hashlib
import json
import re
import stat
import zipfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "hollywood2-participant-ledger-intake-v1"
STATUS = "metadata-only-local-archive-inspection"
EXPECTED_ARCHIVE_BASENAME = "gaze_hollywood2.zip"
MAX_MEMBER_COUNT = 20_000
MAX_TOTAL_UNCOMPRESSED_BYTES = 10 * 1024**3
MAX_METADATA_CANDIDATES = 64
MAX_METADATA_MEMBER_BYTES = 512 * 1024
MAX_TOTAL_METADATA_BYTES = 4 * 1024**2

_METADATA_NAME_TERMS = (
    "readme",
    "subject",
    "participant",
    "observer",
    "metadata",
    "license",
    "licence",
    "documentation",
    "info",
)
_METADATA_SUFFIXES = {
    ".txt",
    ".md",
    ".csv",
    ".tsv",
    ".json",
    ".xml",
    ".html",
    ".htm",
}
_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_UNIQUE_ID_RE = re.compile(
    r"\bunique\s+(?:subject|participant|observer)\s+(?:id|ids|identifiers)\b",
    flags=re.IGNORECASE,
)
_TASK_GROUP_RE = re.compile(
    r"\bactive\b.*\bfree[- ]?view(?:ing)?\b|"
    r"\bfree[- ]?view(?:ing)?\b.*\bactive\b",
    flags=re.IGNORECASE | re.DOTALL,
)
_SUBJECT_ID_RE = re.compile(
    r"\b(?:subject|participant|observer)\s*(?:id|identifier)?\s*[:=#-]?\s*[A-Za-z]*\d+\b",
    flags=re.IGNORECASE,
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def record_fingerprint(record: Mapping[str, Any]) -> str:
    """Return the SHA-256 identity excluding the self-fingerprint field."""

    body = dict(record)
    body.pop("record_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member_name(name: str) -> bool:
    if not name or "\x00" in name or "\\" in name:
        return False
    if name.startswith("/") or _DRIVE_RE.match(name):
        return False
    parts = PurePosixPath(name).parts
    return bool(parts) and all(part not in {"..", ""} for part in parts)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def _is_metadata_candidate(info: zipfile.ZipInfo) -> bool:
    if info.is_dir():
        return False
    path = PurePosixPath(info.filename)
    lower_name = path.name.lower()
    suffix = path.suffix.lower()
    return suffix in _METADATA_SUFFIXES and any(
        term in lower_name for term in _METADATA_NAME_TERMS
    )


def _text_markers(text: str) -> dict[str, Any]:
    normalized = " ".join(text.split())
    return {
        "normalized_text_sha256": hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest(),
        "normalized_text_length": len(normalized),
        "line_count": len(text.splitlines()),
        "states_unique_subject_ids": bool(_UNIQUE_ID_RE.search(normalized)),
        "mentions_active_and_free_viewing_groups": bool(_TASK_GROUP_RE.search(normalized)),
        "subject_id_like_line_count": sum(
            1 for line in text.splitlines() if _SUBJECT_ID_RE.search(line)
        ),
    }


def inspect_original_archive(
    archive_path: str | Path,
    *,
    authorized_local_copy: bool,
) -> dict[str, Any]:
    """Inspect bounded metadata only; never extract raw gaze members."""

    if authorized_local_copy is not True:
        raise BenchmarkIntegrityError(
            "Hollywood2 archive inspection requires an explicitly authorized local copy."
        )
    path = Path(archive_path)
    if not path.is_file():
        raise BenchmarkIntegrityError("Hollywood2 archive path is not a regular file.")
    if path.name.lower() != EXPECTED_ARCHIVE_BASENAME:
        raise BenchmarkIntegrityError(
            f"Expected archive basename {EXPECTED_ARCHIVE_BASENAME!r}."
        )
    if not zipfile.is_zipfile(path):
        raise BenchmarkIntegrityError("Hollywood2 local archive is not a valid ZIP file.")

    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_MEMBER_COUNT:
            raise BenchmarkIntegrityError("Hollywood2 archive member-count guardrail exceeded.")

        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise BenchmarkIntegrityError("Hollywood2 archive contains duplicate member names.")
        if any(not _safe_member_name(name) for name in names):
            raise BenchmarkIntegrityError("Hollywood2 archive contains an unsafe member path.")
        if any(_is_symlink(info) for info in infos):
            raise BenchmarkIntegrityError("Hollywood2 archive contains a symbolic-link member.")
        if any(info.flag_bits & 0x1 for info in infos):
            raise BenchmarkIntegrityError("Hollywood2 archive contains an encrypted member.")

        total_uncompressed = sum(info.file_size for info in infos)
        if total_uncompressed > MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise BenchmarkIntegrityError(
                "Hollywood2 archive uncompressed-size guardrail exceeded."
            )

        candidates = [info for info in infos if _is_metadata_candidate(info)]
        if len(candidates) > MAX_METADATA_CANDIDATES:
            raise BenchmarkIntegrityError(
                "Hollywood2 archive metadata-candidate guardrail exceeded."
            )

        inspected: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        metadata_bytes_read = 0
        for info in sorted(candidates, key=lambda item: item.filename.lower()):
            if info.file_size > MAX_METADATA_MEMBER_BYTES:
                skipped.append(
                    {
                        "member": info.filename,
                        "size_bytes": info.file_size,
                        "reason": "member_size_guardrail",
                    }
                )
                continue
            if metadata_bytes_read + info.file_size > MAX_TOTAL_METADATA_BYTES:
                skipped.append(
                    {
                        "member": info.filename,
                        "size_bytes": info.file_size,
                        "reason": "aggregate_metadata_guardrail",
                    }
                )
                continue
            raw = archive.read(info)
            metadata_bytes_read += len(raw)
            text = raw.decode("utf-8", errors="replace")
            inspected.append(
                {
                    "member": info.filename,
                    "size_bytes": info.file_size,
                    "crc32": f"{info.CRC:08x}",
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "text_summary": _text_markers(text),
                }
            )

    record: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "status": STATUS,
        "archive": {
            "basename": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
            "member_count": len(infos),
            "total_uncompressed_bytes": total_uncompressed,
        },
        "metadata_inspection": {
            "candidate_count": len(candidates),
            "inspected_count": len(inspected),
            "skipped_count": len(skipped),
            "total_metadata_bytes_read": metadata_bytes_read,
            "inspected": inspected,
            "skipped": skipped,
            "raw_gaze_members_opened": 0,
            "archive_members_extracted_to_disk": 0,
        },
        "rights_boundary": {
            "authorized_local_copy_affirmed_for_this_run": True,
            "authorization_scope_inferred_from_archive": False,
            "redistribution_authorized_by_this_intake": False,
            "raw_archive_committed_by_gazeforge": False,
            "raw_gaze_data_committed_by_gazeforge": False,
        },
        "mapping_boundary": {
            "readme_or_metadata_candidate_observed": bool(inspected),
            "original_subject_ids_recovered_as_reviewed_evidence": False,
            "original_subject_group_id_ledger_recovered_as_reviewed_evidence": False,
            "gin_token_to_original_subject_id_verified": False,
            "gin_token_to_task_group_verified": False,
            "participant_identity_mapping_verified": False,
            "participant_disjoint_model_validation_created": False,
        },
        "scientific_boundary": {
            "cross_dataset_validation_created": False,
            "new_empirical_performance_claim_created": False,
            "native_60hz_or_gp3_validity_created": False,
            "manual_evidence_review_required_before_mapping_promotion": True,
        },
        "claim_limits": [
            "Metadata markers and counts are discovery aids, not participant mapping evidence.",
            "Archive filename-count coincidence cannot establish participant identity.",
            "No raw gaze member is opened or extracted by this intake.",
            "Any future mapping promotion requires explicit authoritative ledger review.",
        ],
    }
    record["record_fingerprint_sha256"] = record_fingerprint(record)
    return record


def validate_intake_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a metadata-only intake record and reject scientific promotion."""

    value = dict(record)
    if value.get("record_type") != RECORD_TYPE or value.get("status") != STATUS:
        raise BenchmarkIntegrityError("Hollywood2 participant-ledger intake identity drifted.")
    if value.get("record_fingerprint_sha256") != record_fingerprint(value):
        raise BenchmarkIntegrityError("Hollywood2 participant-ledger intake fingerprint drifted.")

    metadata = value.get("metadata_inspection")
    rights = value.get("rights_boundary")
    mapping = value.get("mapping_boundary")
    scientific = value.get("scientific_boundary")
    if not all(isinstance(item, Mapping) for item in (metadata, rights, mapping, scientific)):
        raise BenchmarkIntegrityError("Hollywood2 participant-ledger intake sections are missing.")
    assert isinstance(metadata, Mapping)
    assert isinstance(rights, Mapping)
    assert isinstance(mapping, Mapping)
    assert isinstance(scientific, Mapping)

    if metadata.get("raw_gaze_members_opened") != 0:
        raise BenchmarkIntegrityError("Hollywood2 intake opened raw gaze members.")
    if metadata.get("archive_members_extracted_to_disk") != 0:
        raise BenchmarkIntegrityError("Hollywood2 intake extracted archive members.")
    if rights.get("authorized_local_copy_affirmed_for_this_run") is not True:
        raise BenchmarkIntegrityError("Hollywood2 intake authorization affirmation is missing.")

    for section, keys in (
        (
            rights,
            (
                "authorization_scope_inferred_from_archive",
                "redistribution_authorized_by_this_intake",
                "raw_archive_committed_by_gazeforge",
                "raw_gaze_data_committed_by_gazeforge",
            ),
        ),
        (
            mapping,
            (
                "original_subject_ids_recovered_as_reviewed_evidence",
                "original_subject_group_id_ledger_recovered_as_reviewed_evidence",
                "gin_token_to_original_subject_id_verified",
                "gin_token_to_task_group_verified",
                "participant_identity_mapping_verified",
                "participant_disjoint_model_validation_created",
            ),
        ),
        (
            scientific,
            (
                "cross_dataset_validation_created",
                "new_empirical_performance_claim_created",
                "native_60hz_or_gp3_validity_created",
            ),
        ),
    ):
        for key in keys:
            if section.get(key) is not False:
                raise BenchmarkIntegrityError(
                    f"Hollywood2 participant-ledger intake must not promote {key}."
                )
    if scientific.get("manual_evidence_review_required_before_mapping_promotion") is not True:
        raise BenchmarkIntegrityError("Hollywood2 intake manual-review gate was relaxed.")
    return value
