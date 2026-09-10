"""Strict validation for reviewed Gaze-in-the-Wild task-mapping certificates."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_authoritative_task_mapping_exhaustion import EXPECTED_TASKS
from .gaze_in_wild_explicit_task_mapping_intake import (
    CERTIFICATE_RECORD_TYPE,
    CERTIFICATE_STATUS,
    TASK_MAPPING_EXHAUSTION_FINGERPRINT,
    TRIAL_INDICES,
    certificate_fingerprint,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_MAPPING_BOUNDARY = {
    "authoritative_trial_task_mapping_verified": True,
    "complete_trial_task_mapping_verified": True,
    "tridx4_explicit_in_source_verified": True,
    "tridx4_tea_making_inferred_by_elimination": False,
    "publication_order_used_as_mapping": False,
    "task_directory_order_used_as_mapping": False,
    "mapping_available_for_downstream_validation": True,
    "raw_task_mapping_copied_to_certificate": False,
}
_EXPECTED_SCIENTIFIC_BOUNDARY = {
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
}
_CERTIFICATE_TOP_LEVEL_KEYS = {
    "record_type",
    "status",
    "authoritative_task_mapping_exhaustion_fingerprint_sha256",
    "candidate_fingerprint_sha256",
    "review_fingerprint_sha256",
    "mapping_fingerprint_sha256",
    "trial_index_count",
    "trial_indices",
    "publication_task_count",
    "publication_tasks",
    "mapping_boundary",
    "scientific_boundary",
    "certificate_fingerprint_sha256",
}
_FORBIDDEN_TOP_LEVEL_FIELDS = {
    "mapping",
    "mapping_entries",
    "trial_task_mapping",
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
            f"Could not load Gaze-in-the-Wild explicit task-mapping certificate: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild explicit task-mapping certificate must be one JSON object."
        )
    return payload


def _require_sha256(value: Any, *, label: str) -> str:
    text = str(value).strip()
    if _SHA256_RE.fullmatch(text) is None:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild explicit task-mapping "
            f"{label} must be a lowercase SHA-256 digest."
        )
    return text


def validate_certificate_record(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate a reviewed certificate without reconstructing its raw mapping."""
    value = _load(record_or_path)
    leaked = sorted(_FORBIDDEN_TOP_LEVEL_FIELDS.intersection(value))
    if leaked:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild explicit task-mapping certificate contains forbidden "
            f"raw mapping fields: {leaked}."
        )
    observed_keys = set(value)
    if observed_keys != _CERTIFICATE_TOP_LEVEL_KEYS:
        missing = sorted(_CERTIFICATE_TOP_LEVEL_KEYS - observed_keys)
        extra = sorted(observed_keys - _CERTIFICATE_TOP_LEVEL_KEYS)
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild explicit task-mapping certificate schema drifted; "
            f"missing={missing}, extra={extra}."
        )
    if value.get("record_type") != CERTIFICATE_RECORD_TYPE:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild explicit task-mapping certificate type drifted."
        )
    if value.get("status") != CERTIFICATE_STATUS:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild explicit task-mapping certificate status drifted."
        )
    if value.get("authoritative_task_mapping_exhaustion_fingerprint_sha256") != (
        TASK_MAPPING_EXHAUSTION_FINGERPRINT
    ):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild explicit task-mapping exhaustion binding drifted."
        )

    for field in (
        "candidate_fingerprint_sha256",
        "review_fingerprint_sha256",
        "mapping_fingerprint_sha256",
        "certificate_fingerprint_sha256",
    ):
        _require_sha256(value.get(field), label=field)

    if value.get("trial_index_count") != len(TRIAL_INDICES):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild explicit task-mapping trial-index count drifted."
        )
    if value.get("trial_indices") != list(TRIAL_INDICES):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild explicit task-mapping canonical TrIdx ledger drifted."
        )
    if value.get("publication_task_count") != len(EXPECTED_TASKS):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild explicit task-mapping publication-task count drifted."
        )
    if value.get("publication_tasks") != list(EXPECTED_TASKS):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild explicit task-mapping publication task ledger drifted."
        )
    if value.get("mapping_boundary") != _EXPECTED_MAPPING_BOUNDARY:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild explicit task-mapping mapping boundary drifted."
        )
    if value.get("scientific_boundary") != _EXPECTED_SCIENTIFIC_BOUNDARY:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild explicit task-mapping scientific boundary drifted."
        )
    stored = value["certificate_fingerprint_sha256"]
    if stored != certificate_fingerprint(value):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild explicit task-mapping certificate fingerprint drifted."
        )
    return value
