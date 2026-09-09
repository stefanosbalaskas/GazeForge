"""Fail-closed GIW participant-validation roadmap synchronization."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_copy_rights_roadmap_sync import (
    EVIDENCE_FINGERPRINT as V2_SYNC_FINGERPRINT,
)
from .gaze_in_wild_copy_rights_roadmap_sync import (
    validate_gaze_in_wild_copy_rights_roadmap_sync,
)
from .gaze_in_wild_exact_validation_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT as PARTICIPANT_EVIDENCE_FINGERPRINT,
)
from .gaze_in_wild_exact_validation_evidence import (
    EXPECTED_PURSUIT,
    EXPECTED_REPRODUCIBILITY_SIGNATURE,
    EXPECTED_SECTION_ROW_COUNTS,
    validate_reviewed_gaze_in_wild_validation_evidence,
)

RECORD_TYPE = "gaze-in-wild-roadmap-evidence-sync-v3"
STATUS = "verified-task-agnostic-participant-validation-roadmap-split"
EVIDENCE_FINGERPRINT = (
    "426ad10551a52a4b1cae9df9ae422336b591188466051235b5b38c8e808f7aa2"
)
SOURCE_MAIN_SHA = "05f9f023ce4a89973ecef669ac857b6f22a2bea2"

BASE = Path("validation/evidence/gaze-in-wild")
V2_SYNC_PATH = BASE / "gaze-in-wild-roadmap-evidence-sync-v2.json"
PARTICIPANT_EVIDENCE_PATH = (
    BASE / "gaze-in-wild-exact-participant-disjoint-model-validation-evidence-v1.json"
)

COMPLETED_ISSUE_WORDING = (
    "Run participant-disjoint Gaze-in-the-Wild task-agnostic derived-60-Hz model "
    "validation and report event-class sensitivity."
)
OPEN_TASK_ISSUE_WORDING = (
    "Report Gaze-in-the-Wild naturalistic-task sensitivity only after authoritative "
    "distributed ProcessData-file → publication-task mapping is verified."
)
EXPECTED_CLAIM_LIMIT = (
    "This roadmap synchronization splits the already-reviewed task-agnostic "
    "participant-disjoint derived-60-Hz model validation and event-class sensitivity "
    "from the still-blocked naturalistic-task sensitivity item. It does not create "
    "new empirical performance, infer or authorize numeric task mapping, create "
    "task-stratified validation, hide the pursuit failure, or establish native "
    "60-Hz, GP3, acquisition-cadence, cross-dataset, quarantine-exit, raw-data-"
    "retention, or historical-RIT-equivalence claims."
)
EXPECTED_SUPERSEDES = {
    "record_type": "gaze-in-wild-roadmap-evidence-sync-v2",
    "evidence_fingerprint_sha256": V2_SYNC_FINGERPRINT,
    "scope": (
        "adds completion of task-agnostic participant-disjoint derived-60-Hz "
        "validation and event-class sensitivity while preserving naturalistic-task "
        "sensitivity as unresolved"
    ),
}
EXPECTED_COMPLETION = {
    "authoritative_numeric_task_mapping_item_satisfied": False,
    "event_class_sensitivity_item_satisfied": True,
    "historical_rit_archive_byte_equivalence_verified": False,
    "naturalistic_task_sensitivity_item_satisfied": False,
    (
        "official_figshare_original_publication_copy_and_current_reuse_terms_"
        "scoped_item_satisfied"
    ): True,
    "overlap_hha_item_satisfied": True,
    "processed_timestamp_grid_rate_item_satisfied": True,
    "task_agnostic_participant_disjoint_model_validation_item_satisfied": True,
    "task_stratified_validation_item_satisfied": False,
}
EXPECTED_BOUNDARY = {
    "acquisition_hardware_cadence_verified": False,
    "analysis_grid_is_derived_60hz": True,
    "cross_dataset_validation_created": False,
    "event_class_sensitivity_created": True,
    "gp3_validity_claim_created": False,
    "historical_rit_archive_byte_equivalence_verified": False,
    "native_60hz_validity_claim_created": False,
    "naturalistic_task_sensitivity_created": False,
    "new_empirical_performance_claim_created": False,
    "participant_disjoint_model_validation_created": True,
    "pursuit_failure_case_must_remain_visible": True,
    "quarantine_exit_authorized": False,
    "raw_dataset_bytes_retained": False,
    "task_mapping_used": False,
    "task_stratified_model_validation_created": False,
}
EXPECTED_PARTICIPANT_REF = {
    "analysis_sampling_rate_hz": 60.0,
    "cross_run_reproducibility_signature_sha256": (
        EXPECTED_REPRODUCIBILITY_SIGNATURE
    ),
    "event_class_sensitivity_created": True,
    "evidence_fingerprint_sha256": PARTICIPANT_EVIDENCE_FINGERPRINT,
    "oof_row_count_per_model": 157850,
    "participant_count": 12,
    "path": PARTICIPANT_EVIDENCE_PATH.as_posix(),
    "pursuit_analysis_support": 5696,
    "pursuit_reference_event_count": 327,
    "recording_count": 18,
    "task_fold_metrics_row_count": 0,
    "task_mapping_used": False,
    "task_stratified_validation_created": False,
    "task_summary_row_count": 0,
}
EXPECTED_V2_REF = {
    "evidence_fingerprint_sha256": V2_SYNC_FINGERPRINT,
    "path": V2_SYNC_PATH.as_posix(),
}


@dataclass(frozen=True, slots=True)
class GazeInWildParticipantValidationRoadmapSync:
    path: Path | None
    fingerprint_sha256: str
    participant_validation_satisfied: bool
    event_class_sensitivity_satisfied: bool
    naturalistic_task_sensitivity_satisfied: bool
    participant_count: int
    recording_count: int
    oof_row_count_per_model: int
    analysis_sampling_rate_hz: float
    pursuit_analysis_support: int
    pursuit_reference_event_count: int


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(
    value: Mapping[str, Any] | str | Path,
    label: str,
) -> tuple[dict[str, Any], Path | None]:
    if isinstance(value, Mapping):
        return dict(value), None
    path = Path(value)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"Could not load GIW {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"GIW {label} must contain one JSON object.")
    return payload, path


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(
            f"GIW participant roadmap-sync field {key!r} is missing."
        )
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(
            f"GIW participant-validation roadmap {label} drifted."
        )


def _repository_root(
    path: Path | None,
    repository_root: str | Path | None,
) -> Path:
    if repository_root is not None:
        return Path(repository_root)
    if path is not None and len(path.parents) >= 4:
        return path.parents[3]
    return Path.cwd()


def validate_gaze_in_wild_participant_validation_roadmap_sync(
    evidence_or_path: Mapping[str, Any] | str | Path,
    *,
    repository_root: str | Path | None = None,
) -> GazeInWildParticipantValidationRoadmapSync:
    """Validate the task-agnostic participant-validation roadmap split.

    The completion applies only to participant-disjoint derived-60-Hz model
    validation and event-class sensitivity. Naturalistic-task sensitivity remains
    blocked until an authoritative distributed file-to-task mapping is verified.
    """

    record, path = _load(
        evidence_or_path,
        "participant-validation roadmap sync evidence",
    )
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("reviewed_on"), "2026-09-09", "review date")
    _equal(record.get("source_main_sha"), SOURCE_MAIN_SHA, "source main SHA")
    _equal(
        record.get("evidence_fingerprint_sha256"),
        EVIDENCE_FINGERPRINT,
        "stored evidence fingerprint",
    )
    _equal(
        evidence_fingerprint(record),
        EVIDENCE_FINGERPRINT,
        "recomputed evidence fingerprint",
    )
    _equal(
        _mapping(record, "supersedes_for_roadmap_sync"),
        EXPECTED_SUPERSEDES,
        "v2 binding",
    )
    _equal(
        _mapping(record, "roadmap_completion"),
        EXPECTED_COMPLETION,
        "completion contract",
    )
    _equal(
        _mapping(record, "scientific_boundary"),
        EXPECTED_BOUNDARY,
        "scientific boundary",
    )
    _equal(
        _mapping(record, "issue_wording"),
        {
            "completed_participant_validation": COMPLETED_ISSUE_WORDING,
            "open_task_sensitivity": OPEN_TASK_ISSUE_WORDING,
        },
        "issue wording",
    )
    _equal(record.get("claim_limit"), EXPECTED_CLAIM_LIMIT, "claim limit")

    upstream = _mapping(record, "upstream_evidence")
    _equal(
        _mapping(upstream, "roadmap_sync_v2"),
        EXPECTED_V2_REF,
        "v2 reference",
    )
    _equal(
        _mapping(upstream, "participant_disjoint_validation"),
        EXPECTED_PARTICIPANT_REF,
        "participant-validation reference",
    )

    root = _repository_root(path, repository_root)
    v2 = validate_gaze_in_wild_copy_rights_roadmap_sync(
        root / V2_SYNC_PATH,
        repository_root=root,
    )
    _equal(v2.fingerprint_sha256, V2_SYNC_FINGERPRINT, "validated v2 fingerprint")
    _equal(v2.official_figshare_item_satisfied, True, "preserved copy-rights item")
    _equal(v2.raw_dataset_bytes_retained, False, "preserved raw-data boundary")
    _equal(v2.quarantine_exit_authorized, False, "preserved quarantine boundary")

    participant_record, _ = _load(
        root / PARTICIPANT_EVIDENCE_PATH,
        "participant-disjoint validation evidence",
    )
    validated = validate_reviewed_gaze_in_wild_validation_evidence(
        participant_record
    )
    _equal(
        validated.get("evidence_fingerprint_sha256"),
        PARTICIPANT_EVIDENCE_FINGERPRINT,
        "validated participant-evidence fingerprint",
    )

    boundary = _mapping(validated, "scientific_boundary")
    _equal(
        boundary.get("participant_disjoint_model_validation_created"),
        True,
        "participant-disjoint completion",
    )
    _equal(
        boundary.get("event_class_sensitivity_created"),
        True,
        "event-class sensitivity completion",
    )
    _equal(
        boundary.get("task_stratified_model_validation_created"),
        False,
        "task-stratification boundary",
    )
    _equal(
        boundary.get("complete_file_to_publication_task_mapping_verified"),
        False,
        "task-mapping boundary",
    )
    for key in (
        "cross_dataset_validation_created",
        "native_gp3_or_native_60hz_validity_created",
        "gp3_validity_claim_created",
        "new_empirical_performance_claim_created",
        "quarantine_exit_authorized",
        "acquisition_hardware_cadence_verified_by_this_validation",
        "raw_dataset_bytes_retained",
    ):
        _equal(boundary.get(key), False, key)

    scope = _mapping(validated, "validation_scope")
    _equal(scope.get("analysis_sampling_rate_hz"), 60.0, "analysis rate")
    _equal(scope.get("participant_count"), 12, "participant count")
    _equal(scope.get("recording_count"), 18, "recording count")
    _equal(scope.get("task_mapping_used"), False, "task mapping use")
    _equal(
        scope.get("task_stratified_validation_created"),
        False,
        "task-stratified scope",
    )

    split = _mapping(validated, "split_integrity")
    _equal(split.get("participant_disjoint"), True, "participant-disjoint split")
    _equal(
        split.get("all_models_share_identical_oof_rows"),
        True,
        "matched OOF rows",
    )
    _equal(split.get("oof_row_count_per_model"), 157850, "OOF row count")

    metrics = _mapping(validated, "metrics")
    rows = _mapping(metrics, "section_row_counts")
    _equal(
        rows.get("task_fold_metrics"),
        EXPECTED_SECTION_ROW_COUNTS["task_fold_metrics"],
        "empty task-fold rows",
    )
    _equal(
        rows.get("task_summary"),
        EXPECTED_SECTION_ROW_COUNTS["task_summary"],
        "empty task-summary rows",
    )
    pursuit = _mapping(metrics, "pursuit_failure_case")
    _equal(
        pursuit.get("analysis_support"),
        EXPECTED_PURSUIT["analysis_support"],
        "pursuit analysis support",
    )
    _equal(
        pursuit.get("reference_event_count"),
        EXPECTED_PURSUIT["reference_event_count"],
        "pursuit reference-event count",
    )
    _equal(pursuit.get("models"), EXPECTED_PURSUIT["models"], "pursuit failure")

    reproducibility = _mapping(validated, "reproducibility")
    _equal(
        reproducibility.get("cross_run_reproducibility_signature_sha256"),
        EXPECTED_REPRODUCIBILITY_SIGNATURE,
        "cross-run signature",
    )

    return GazeInWildParticipantValidationRoadmapSync(
        path=path,
        fingerprint_sha256=EVIDENCE_FINGERPRINT,
        participant_validation_satisfied=True,
        event_class_sensitivity_satisfied=True,
        naturalistic_task_sensitivity_satisfied=False,
        participant_count=12,
        recording_count=18,
        oof_row_count_per_model=157850,
        analysis_sampling_rate_hz=60.0,
        pursuit_analysis_support=5696,
        pursuit_reference_event_count=327,
    )
