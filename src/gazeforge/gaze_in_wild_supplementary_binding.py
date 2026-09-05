"""Cross-bind Gaze-in-the-Wild supplementary identity to source-resolution governance."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_supplementary_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    PUBLISHED_PERSON_NUMBERS,
    PUBLISHED_TASK_COLUMNS,
    validate_gaze_in_wild_supplementary_identity_evidence,
)
from .source_resolution import validate_source_resolution_record

_BINDING_RECORD_TYPE = "gaze-in-wild-supplementary-identity-evidence-v1"
_EXPECTED_PROCESSING_ONLY_INDICES = (4, 5, 7, 21)


@dataclass(frozen=True, slots=True)
class GazeInWildSupplementaryBinding:
    """Validated publication-level identity binding without file-level promotion."""

    source_record_fingerprint_sha256: str
    evidence_fingerprint_sha256: str
    published_person_numbers: tuple[int, ...]
    published_task_columns: tuple[str, ...]
    exact_distributed_identity_mapping_verified: bool
    complete_tridx_to_task_mapping_verified: bool


def _load_json(path: str | Path, *, label: str) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"Could not load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"{label} must be a JSON object.")
    return payload


def _mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild supplementary binding requires {key!r}."
        )
    return value


def validate_gaze_in_wild_supplementary_binding(
    source_resolution_path: str | Path,
    supplementary_evidence_path: str | Path,
) -> GazeInWildSupplementaryBinding:
    """Validate exact cross-record identities while preserving unresolved file mapping."""

    evidence = validate_gaze_in_wild_supplementary_identity_evidence(
        supplementary_evidence_path
    )
    source_summary = validate_source_resolution_record(source_resolution_path)
    if source_summary.get("dataset_key") != "gaze-in-the-wild":
        raise BenchmarkIntegrityError(
            "Supplementary identity evidence may bind only to Gaze-in-the-Wild source resolution."
        )

    checkpoint = _load_json(
        source_resolution_path,
        label="Gaze-in-the-Wild source-resolution checkpoint",
    )
    binding = _mapping(checkpoint, "supplementary_identity_evidence")
    mapping = _mapping(checkpoint, "mapping_and_coordinates")

    if binding.get("record_type") != _BINDING_RECORD_TYPE:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild supplementary binding record type drifted."
        )
    if binding.get("evidence_fingerprint_sha256") != EXPECTED_EVIDENCE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild source checkpoint is not bound to the reviewed supplementary evidence."
        )
    if binding.get("evidence_fingerprint_sha256") != evidence.get(
        "evidence_fingerprint_sha256"
    ):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild supplementary evidence fingerprint does not match its checkpoint binding."
        )

    bound_people = tuple(int(value) for value in binding.get("published_person_numbers", []))
    mapped_people = tuple(
        int(value) for value in mapping.get("published_included_participant_ids", [])
    )
    if bound_people != PUBLISHED_PERSON_NUMBERS or mapped_people != PUBLISHED_PERSON_NUMBERS:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild publication-level 19-person identity set drifted."
        )

    bound_tasks = tuple(str(value) for value in binding.get("published_task_columns", []))
    mapped_tasks = tuple(str(value) for value in mapping.get("published_task_columns", []))
    if bound_tasks != PUBLISHED_TASK_COLUMNS or mapped_tasks != PUBLISHED_TASK_COLUMNS:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild publication-level task-column identity drifted."
        )

    processing_only = tuple(
        int(value)
        for value in mapping.get("processing_indices_absent_from_published_included_set", [])
    )
    if processing_only != _EXPECTED_PROCESSING_ONLY_INDICES:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild processing-only participant-index set drifted."
        )

    if binding.get("published_included_participant_set_verified") is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild publication-level included participant set must remain verified."
        )
    if mapping.get("published_included_participant_set_verified") is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild source checkpoint must preserve the verified publication-level set."
        )
    if mapping.get("published_task_columns_verified") is not True:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild source checkpoint must preserve the verified task columns."
        )

    unresolved_flags = {
        "binding exact distributed identity": binding.get(
            "published_person_number_to_exact_distributed_participant_identity_verified"
        ),
        "mapping exact distributed identity": mapping.get(
            "published_person_number_to_exact_distributed_participant_identity_verified"
        ),
        "binding complete TrIdx-to-task mapping": binding.get(
            "complete_tridx_to_task_mapping_verified"
        ),
        "mapping complete TrIdx-to-task mapping": mapping.get(
            "trial_index_to_published_task_mapping_verified"
        ),
        "mapping exact-copy participant/task mapping": mapping.get(
            "participant_task_mapping_verified_from_exact_copy"
        ),
    }
    promoted = [label for label, value in unresolved_flags.items() if value is not False]
    if promoted:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild supplementary binding must not promote unresolved file-level identity: "
            + ", ".join(promoted)
        )

    discrepancy = _mapping(mapping, "participant_18_age_metadata_discrepancy")
    if dict(discrepancy) != {
        "supplementary_table_age": 34,
        "processing_metadata_age": 45,
        "identity_mapping_from_age_permitted": False,
    }:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild participant-18 age discrepancy must remain preserved and non-identifying."
        )

    return GazeInWildSupplementaryBinding(
        source_record_fingerprint_sha256=str(
            source_summary["record_fingerprint_sha256"]
        ),
        evidence_fingerprint_sha256=EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        published_person_numbers=PUBLISHED_PERSON_NUMBERS,
        published_task_columns=PUBLISHED_TASK_COLUMNS,
        exact_distributed_identity_mapping_verified=False,
        complete_tridx_to_task_mapping_verified=False,
    )
