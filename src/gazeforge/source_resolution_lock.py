"""Reviewed snapshot locks for non-empirical source-resolution governance bundles."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .source_resolution_discovery import validate_source_resolution_directory

_LOCK_TYPE = "source-resolution-bundle-lock-v1"
_HEX = set("0123456789abcdef")
_BOUNDARY = {
    "non_empirical_governance_only": True,
    "authorizes_checkpoint_status_upgrade": False,
    "authorizes_source_audit_ready": False,
    "authorizes_empirical_evidence": False,
    "authorizes_frozen_evidence_publication": False,
}


def _fingerprint(payload: Mapping[str, Any]) -> str:
    canonical = dict(payload)
    canonical.pop("lock_fingerprint_sha256", None)
    encoded = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_hex(value: Any, *, field: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(character not in _HEX for character in text):
        raise BenchmarkIntegrityError(f"{field} must contain 64 hexadecimal digits.")
    return text


def _require_review_basis(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise BenchmarkIntegrityError("Source-resolution bundle lock requires review_basis entries.")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise BenchmarkIntegrityError("Source-resolution lock review_basis must be non-empty strings.")
    return tuple(str(item).strip() for item in value)


def _validated_lock_records(value: Any) -> tuple[dict[str, str], ...]:
    if not isinstance(value, list) or not value:
        raise BenchmarkIntegrityError("Source-resolution bundle lock requires record identities.")

    rows: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise BenchmarkIntegrityError("Source-resolution lock records must be JSON objects.")
        dataset_key = str(item.get("dataset_key", "")).strip()
        status = str(item.get("status", "")).strip()
        if not dataset_key or not status:
            raise BenchmarkIntegrityError(
                "Source-resolution lock records require dataset_key and status."
            )
        rows.append(
            {
                "dataset_key": dataset_key,
                "status": status,
                "record_fingerprint_sha256": _require_hex(
                    item.get("record_fingerprint_sha256"),
                    field=f"{dataset_key} record_fingerprint_sha256",
                ),
            }
        )

    rows.sort(key=lambda row: row["dataset_key"])
    dataset_keys = [row["dataset_key"] for row in rows]
    if len(dataset_keys) != len(set(dataset_keys)):
        raise BenchmarkIntegrityError(
            "Source-resolution bundle lock cannot contain duplicate dataset identities."
        )
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class SourceResolutionBundleLock:
    """Typed identity of a validated reviewed source-resolution snapshot."""

    path: Path
    reviewed_on: str
    record_count: int
    bundle_fingerprint_sha256: str
    lock_fingerprint_sha256: str
    review_basis: tuple[str, ...]
    records: tuple[dict[str, str], ...]


def build_source_resolution_bundle_lock(
    protocol_directory: str | Path,
    *,
    reviewed_on: str,
    review_basis: Sequence[str],
) -> dict[str, Any]:
    """Build a deterministic lock payload from the currently validated checkpoint bundle.

    Building a lock does not upgrade any source-resolution state. The returned payload explicitly
    records that it is a non-empirical governance snapshot and cannot authorize source audit,
    empirical evidence, or Frozen Evidence publication.
    """
    try:
        date.fromisoformat(reviewed_on)
    except ValueError as exc:
        raise BenchmarkIntegrityError("Source-resolution lock reviewed_on must be an ISO date.") from exc

    review_items = tuple(str(item).strip() for item in review_basis)
    if not review_items or not all(review_items):
        raise BenchmarkIntegrityError("Source-resolution lock review_basis cannot be empty.")

    bundle = validate_source_resolution_directory(protocol_directory)
    records = [
        {
            "dataset_key": str(record["dataset_key"]),
            "status": str(record["status"]),
            "record_fingerprint_sha256": str(record["record_fingerprint_sha256"]),
        }
        for record in bundle["records"]
    ]
    records.sort(key=lambda row: row["dataset_key"])

    payload: dict[str, Any] = {
        "lock_type": _LOCK_TYPE,
        "reviewed_on": reviewed_on,
        "record_count": int(bundle["record_count"]),
        "bundle_fingerprint_sha256": str(bundle["bundle_fingerprint_sha256"]),
        "records": records,
        "review_basis": list(review_items),
        "scientific_boundary": dict(_BOUNDARY),
    }
    payload["lock_fingerprint_sha256"] = _fingerprint(payload)
    return payload


def validate_source_resolution_bundle_lock(
    lock_path: str | Path,
    protocol_directory: str | Path,
) -> dict[str, Any]:
    """Validate one reviewed bundle lock against the complete current checkpoint directory."""
    source = Path(lock_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError("Source-resolution bundle lock must be valid UTF-8 JSON.") from exc
    if not isinstance(payload, Mapping):
        raise BenchmarkIntegrityError("Source-resolution bundle lock must be a JSON object.")
    if payload.get("lock_type") != _LOCK_TYPE:
        raise BenchmarkIntegrityError(
            f"Source-resolution bundle lock_type must be {_LOCK_TYPE!r}."
        )

    reviewed_on = str(payload.get("reviewed_on", "")).strip()
    try:
        date.fromisoformat(reviewed_on)
    except ValueError as exc:
        raise BenchmarkIntegrityError("Source-resolution lock reviewed_on must be an ISO date.") from exc

    review_basis = _require_review_basis(payload.get("review_basis"))
    boundary = payload.get("scientific_boundary")
    if boundary != _BOUNDARY:
        raise BenchmarkIntegrityError(
            "Source-resolution lock scientific_boundary must preserve the reviewed non-empirical "
            "authorization limits exactly."
        )

    records = _validated_lock_records(payload.get("records"))
    record_count = payload.get("record_count")
    if not isinstance(record_count, int) or isinstance(record_count, bool) or record_count <= 0:
        raise BenchmarkIntegrityError("Source-resolution lock record_count must be a positive integer.")
    if record_count != len(records):
        raise BenchmarkIntegrityError(
            "Source-resolution lock record_count does not match its record identity list."
        )

    locked_bundle_fingerprint = _require_hex(
        payload.get("bundle_fingerprint_sha256"),
        field="bundle_fingerprint_sha256",
    )
    stored_lock_fingerprint = _require_hex(
        payload.get("lock_fingerprint_sha256"),
        field="lock_fingerprint_sha256",
    )
    computed_lock_fingerprint = _fingerprint(payload)
    if stored_lock_fingerprint != computed_lock_fingerprint:
        raise BenchmarkIntegrityError(
            "Source-resolution bundle lock fingerprint does not match its content."
        )

    bundle = validate_source_resolution_directory(protocol_directory)
    current_bundle_fingerprint = str(bundle["bundle_fingerprint_sha256"])
    if locked_bundle_fingerprint != current_bundle_fingerprint:
        raise BenchmarkIntegrityError(
            "Source-resolution checkpoint bundle has changed since the reviewed lock was frozen. "
            "Review the checkpoint changes and intentionally replace the bundle lock."
        )
    if int(bundle["record_count"]) != record_count:
        raise BenchmarkIntegrityError(
            "Source-resolution checkpoint count differs from the reviewed bundle lock."
        )

    current_records = tuple(
        sorted(
            (
                {
                    "dataset_key": str(record["dataset_key"]),
                    "status": str(record["status"]),
                    "record_fingerprint_sha256": str(
                        record["record_fingerprint_sha256"]
                    ),
                }
                for record in bundle["records"]
            ),
            key=lambda row: row["dataset_key"],
        )
    )
    if current_records != records:
        raise BenchmarkIntegrityError(
            "Source-resolution record identities differ from the reviewed bundle lock."
        )

    return {
        "lock_type": _LOCK_TYPE,
        "reviewed_on": reviewed_on,
        "record_count": record_count,
        "bundle_fingerprint_sha256": locked_bundle_fingerprint,
        "records": list(records),
        "review_basis": list(review_basis),
        "scientific_boundary": dict(_BOUNDARY),
        "lock_fingerprint_sha256": computed_lock_fingerprint,
        "matches_current_bundle": True,
    }


def load_source_resolution_bundle_lock(
    lock_path: str | Path,
    protocol_directory: str | Path,
) -> SourceResolutionBundleLock:
    """Return a typed reviewed lock after exact current-bundle validation."""
    source = Path(lock_path)
    summary = validate_source_resolution_bundle_lock(source, protocol_directory)
    return SourceResolutionBundleLock(
        path=source,
        reviewed_on=str(summary["reviewed_on"]),
        record_count=int(summary["record_count"]),
        bundle_fingerprint_sha256=str(summary["bundle_fingerprint_sha256"]),
        lock_fingerprint_sha256=str(summary["lock_fingerprint_sha256"]),
        review_basis=tuple(str(item) for item in summary["review_basis"]),
        records=tuple(dict(row) for row in summary["records"]),
    )
