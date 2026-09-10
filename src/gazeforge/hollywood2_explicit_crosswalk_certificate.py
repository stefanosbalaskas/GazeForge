"""Strict validation for reviewed Hollywood2 participant-crosswalk certificates."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .hollywood2_explicit_crosswalk_intake import (
    CERTIFICATE_RECORD_TYPE,
    CERTIFICATE_STATUS,
    GIN_TOKENS,
    certificate_fingerprint,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_MAPPING_BOUNDARY = {
    "gin_token_to_original_subject_id_verified": True,
    "gin_token_to_task_group_verified": True,
    "participant_identity_mapping_verified": True,
    "raw_subject_ids_copied_to_certificate": False,
    "raw_task_group_labels_copied_to_certificate": False,
}
_EXPECTED_SCIENTIFIC_BOUNDARY = {
    "participant_disjoint_model_validation_created": False,
    "cross_dataset_validation_created": False,
    "new_empirical_performance_claim_created": False,
    "rights_scope_promoted": False,
    "raw_gaze_inspected": False,
    "raw_gaze_redistributed": False,
}
_FORBIDDEN_TOP_LEVEL_FIELDS = {
    "mapping",
    "mapping_entries",
    "original_subject_ids",
    "subject_ids",
    "task_groups",
    "raw_mapping",
}


def _load(record_or_path: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path)
    path = Path(record_or_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load Hollywood2 explicit-crosswalk certificate: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "Hollywood2 explicit-crosswalk certificate must be one JSON object."
        )
    return payload


def _require_sha256(value: Any, *, label: str) -> str:
    text = str(value).strip()
    if _SHA256_RE.fullmatch(text) is None:
        raise BenchmarkIntegrityError(
            f"Hollywood2 explicit-crosswalk {label} must be a lowercase SHA-256 digest."
        )
    return text


def validate_certificate_record(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate a reviewed certificate without reconstructing or exposing its mapping."""
    value = _load(record_or_path)
    if value.get("record_type") != CERTIFICATE_RECORD_TYPE:
        raise BenchmarkIntegrityError("Hollywood2 explicit-crosswalk certificate type drifted.")
    if value.get("status") != CERTIFICATE_STATUS:
        raise BenchmarkIntegrityError("Hollywood2 explicit-crosswalk certificate status drifted.")

    for field in (
        "candidate_fingerprint_sha256",
        "review_fingerprint_sha256",
        "mapping_fingerprint_sha256",
        "certificate_fingerprint_sha256",
    ):
        _require_sha256(value.get(field), label=field)

    if value.get("token_count") != len(GIN_TOKENS):
        raise BenchmarkIntegrityError(
            "Hollywood2 explicit-crosswalk certificate token count drifted."
        )
    if value.get("gin_tokens") != list(GIN_TOKENS):
        raise BenchmarkIntegrityError(
            "Hollywood2 explicit-crosswalk certificate canonical token ledger drifted."
        )
    if value.get("mapping_boundary") != _EXPECTED_MAPPING_BOUNDARY:
        raise BenchmarkIntegrityError(
            "Hollywood2 explicit-crosswalk certificate mapping boundary drifted."
        )
    if value.get("scientific_boundary") != _EXPECTED_SCIENTIFIC_BOUNDARY:
        raise BenchmarkIntegrityError(
            "Hollywood2 explicit-crosswalk certificate scientific boundary drifted."
        )
    leaked = sorted(_FORBIDDEN_TOP_LEVEL_FIELDS.intersection(value))
    if leaked:
        raise BenchmarkIntegrityError(
            "Hollywood2 explicit-crosswalk certificate contains forbidden raw mapping fields: "
            f"{leaked}."
        )

    stored = value["certificate_fingerprint_sha256"]
    if stored != certificate_fingerprint(value):
        raise BenchmarkIntegrityError(
            "Hollywood2 explicit-crosswalk certificate fingerprint drifted."
        )
    return value
