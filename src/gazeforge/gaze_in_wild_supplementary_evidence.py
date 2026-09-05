"""Frozen publication-level participant/task context for Gaze-in-the-Wild."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "gaze-in-wild-supplementary-identity-evidence-v1"
STATUS = (
    "published_19_participant_set_verified_task_columns_documented_"
    "raw_trial_mapping_unresolved"
)
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "a84d64342b6001adb4a2b5893db0da5ae997f6a9067d22f8cb8c72c5dcaf4db3"
)
PUBLICATION_DOI = "10.1038/s41598-020-59251-5"
OFFICIAL_PROCESSING_COMMIT = "52262d44e366a53369e10ca73c5f41daf0e8f1e5"
GET_PARTICIPANT_INFO_BLOB = "6c21df7554891015a1ae09182867b5d707b6a505"
PLOT_LABELS_BLOB = "511581250e04c62037c71d2da16271be4979d434"
PUBLISHED_PERSON_NUMBERS = (
    1,
    2,
    3,
    6,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    22,
    23,
)
PUBLISHED_TASK_COLUMNS = (
    "Indoor navigation",
    "Ball catching",
    "Visual search",
    "Tea making",
)


@dataclass(frozen=True, slots=True)
class GazeInWildSupplementaryIdentityEvidence:
    """Compact identity for reviewed publication-level GIW participant context."""

    path: Path | None
    fingerprint_sha256: str
    published_person_numbers: tuple[int, ...]
    published_task_columns: tuple[str, ...]
    exact_distributed_identity_mapping_verified: bool
    complete_tridx_to_task_mapping_verified: bool


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return canonical SHA-256 excluding the stored fingerprint field."""

    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(
    record_or_path: Mapping[str, Any] | str | Path,
) -> tuple[dict[str, Any], Path | None]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path), None
    path = Path(record_or_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load Gaze-in-the-Wild supplementary identity evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild supplementary identity evidence must be a JSON object."
        )
    return payload, path


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild supplementary identity field {key!r} is missing."
        )
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild supplementary identity {label} drifted."
        )


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild supplementary identity must preserve {label}."
        )


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild supplementary identity must not promote {label}."
        )


def validate_gaze_in_wild_supplementary_identity_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate frozen publication-level GIW participant/task context fail-closed."""

    record, _ = _load(record_or_path)
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("checked_on"), "2026-09-05", "review date")
    _equal(
        record.get("dataset"),
        "Gaze-in-the-Wild naturalistic eye-head event benchmark",
        "dataset identity",
    )

    publication = _mapping(record, "publication")
    _equal(publication.get("doi"), PUBLICATION_DOI, "publication DOI")
    _equal(publication.get("published_participant_count"), 19, "participant count")
    _true(
        publication.get(
            "publication_states_supplementary_table_1_lists_calibration_tasks_and_labelling_status"
        ),
        "publication statement about Supplementary Table 1",
    )
    supplement_url = str(publication.get("supplementary_information_url", ""))
    if "41598_2020_59251_MOESM1_ESM.pdf" not in supplement_url:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild supplementary identity official supplement URL drifted."
        )
    _false(
        publication.get("supplementary_information_bytes_fingerprinted"),
        "an authoritative supplementary-PDF byte fingerprint",
    )

    table = _mapping(record, "supplementary_table_1")
    _equal(table.get("table_title"), "Dataset status and error measures.", "table title")
    _equal(
        tuple(int(value) for value in table.get("person_numbers", [])),
        PUBLISHED_PERSON_NUMBERS,
        "published person-number set",
    )
    _equal(table.get("person_count"), 19, "published table row count")
    _equal(
        tuple(str(value) for value in table.get("task_columns", [])),
        PUBLISHED_TASK_COLUMNS,
        "published task columns",
    )
    _true(
        table.get("published_included_participant_set_verified"),
        "publication-level 19-person set",
    )
    _true(table.get("published_task_columns_verified"), "published task columns")
    _false(
        table.get("per_person_task_status_matrix_frozen"),
        "a frozen per-person task/status matrix",
    )

    context = _mapping(record, "cross_source_processing_context")
    _equal(
        context.get("repository"),
        "https://github.com/RSKothari/Gaze-in-Wild",
        "processing repository",
    )
    _equal(
        context.get("pinned_commit_sha1"),
        OFFICIAL_PROCESSING_COMMIT,
        "processing commit",
    )
    _equal(
        context.get("get_participant_info_git_blob_sha1"),
        GET_PARTICIPANT_INFO_BLOB,
        "GetParticipantInfo blob",
    )
    _equal(context.get("plot_labels_git_blob_sha1"), PLOT_LABELS_BLOB, "PlotLabels blob")
    _equal(
        context.get("processing_metadata_highest_participant_index"),
        23,
        "highest processing participant index",
    )
    _equal(
        tuple(
            int(value)
            for value in context.get(
                "processing_indices_absent_from_published_19_person_table", []
            )
        ),
        (4, 5, 7, 21),
        "processing-only index set",
    )
    _true(
        context.get("plot_labels_tridx_1_indoor_walk_context_found"),
        "TrIdx=1 indoor-walk code context",
    )
    _false(
        context.get("complete_tridx_to_task_mapping_verified"),
        "complete TrIdx-to-task mapping",
    )
    _false(
        context.get("published_person_number_to_exact_distributed_participant_identity_verified"),
        "published-person to distributed-file identity mapping",
    )
    _false(
        context.get("participant_task_mapping_verified_from_exact_copy"),
        "exact-copy participant/task mapping",
    )

    discrepancy = _mapping(record, "metadata_discrepancy")
    _equal(discrepancy.get("field"), "age", "metadata discrepancy field")
    _equal(discrepancy.get("participant_number"), 18, "metadata discrepancy participant")
    _equal(discrepancy.get("supplementary_table_value"), 34, "supplementary age")
    _equal(discrepancy.get("processing_metadata_value"), 45, "processing age")
    _true(discrepancy.get("discrepancy_verified"), "preserved age discrepancy")
    _false(
        discrepancy.get("identity_mapping_can_be_inferred_from_age"),
        "identity mapping from age metadata",
    )

    boundary = _mapping(record, "scientific_boundary")
    _true(
        boundary.get("published_19_participant_table_set_verified"),
        "published 19-person table set",
    )
    _true(
        boundary.get("published_four_task_column_names_verified"),
        "published four-task column names",
    )
    for key, label in (
        ("authoritative_supplement_bytes_fingerprinted", "supplement byte fingerprinting"),
        ("per_person_task_status_matrix_frozen", "per-person task/status freezing"),
        (
            "published_person_number_to_exact_distributed_participant_identity_verified",
            "published-person to distributed-file mapping",
        ),
        ("complete_tridx_to_task_mapping_verified", "complete TrIdx-to-task mapping"),
        ("exact_dataset_copy_obtained", "exact dataset acquisition"),
        ("dataset_file_rights_resolved", "dataset-file rights resolution"),
        ("source_audit_ready", "source-audit readiness"),
        ("human_human_agreement_created", "human-human agreement"),
        ("participant_disjoint_model_validation_created", "participant-disjoint validation"),
        ("cross_dataset_validation_created", "cross-dataset validation"),
        ("gp3_validity_claim_created", "GP3 validity"),
    ):
        _false(boundary.get(key), label)

    limits = record.get("claim_limits")
    actions = record.get("next_required_actions")
    if not isinstance(limits, list) or not limits:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild supplementary identity must preserve claim limits."
        )
    if not isinstance(actions, list) or not actions:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild supplementary identity must preserve next required actions."
        )

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    calculated = evidence_fingerprint(record)
    if stored != calculated:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild supplementary identity self-fingerprint is invalid."
        )
    if stored != EXPECTED_EVIDENCE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild supplementary identity immutable v1 fingerprint drifted."
        )
    return record


def load_gaze_in_wild_supplementary_identity_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildSupplementaryIdentityEvidence:
    """Return typed publication-level identity only after complete validation."""

    record, path = _load(record_or_path)
    validated = validate_gaze_in_wild_supplementary_identity_evidence(record)
    table = _mapping(validated, "supplementary_table_1")
    context = _mapping(validated, "cross_source_processing_context")
    return GazeInWildSupplementaryIdentityEvidence(
        path=path,
        fingerprint_sha256=str(validated["evidence_fingerprint_sha256"]),
        published_person_numbers=tuple(int(value) for value in table["person_numbers"]),
        published_task_columns=tuple(str(value) for value in table["task_columns"]),
        exact_distributed_identity_mapping_verified=bool(
            context["published_person_number_to_exact_distributed_participant_identity_verified"]
        ),
        complete_tridx_to_task_mapping_verified=bool(
            context["complete_tridx_to_task_mapping_verified"]
        ),
    )
