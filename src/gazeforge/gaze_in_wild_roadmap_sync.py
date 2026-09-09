"""Fail-closed synchronization of scoped Gaze-in-the-Wild roadmap evidence."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_overlap_hha_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256 as EXPECTED_HHA_FINGERPRINT,
)
from .gaze_in_wild_overlap_hha_evidence import (
    validate_gaze_in_wild_overlap_hha_evidence,
)

RATE_LEDGER_RECORD_TYPE = "gaze-in-wild-processdata-processed-rate-ledger-v1"
RATE_LEDGER_FINGERPRINT = (
    "1bd6643bd0c75faec9d070f74fb719f9178caa2da7e90bcbe356a0dbc5f38905"
)
RATE_LEDGER_PATH = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-processdata-processed-rate-ledger-v1.json"
)
HHA_PATH = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-distributed-overlap-human-human-agreement-evidence-v1.json"
)
SYNC_RECORD_TYPE = "gaze-in-wild-roadmap-evidence-sync-v1"
SYNC_STATUS = "verified-scoped-roadmap-evidence-synchronization"
SYNC_FINGERPRINT = (
    "c0dc3182f7fa89d325e0be2406d6d1aaf6541ebb2e90c21f49ade23398909571"
)
SOURCE_MAIN_SHA = "9b1ddbfe105a2edbe0ce3937ad818432a8d0cc8a"
EXPECTED_COLUMNS = [
    "name",
    "sha256",
    "participant_index",
    "trial_index",
    "stored_rate_hz",
    "inferred_processed_rate_hz",
    "timestamp_count",
]
EXPECTED_RATE_SOURCE_BINDING = {
    "discovery_probe_fingerprint_sha256": (
        "bbd7b0498f4d3b48e435bb0a79efd72d794e59e38fa31ccc73c2577bb95dd66b"
    ),
    "exact_processdata_sha256_ledger_evidence_fingerprint_sha256": (
        "85f131389315a1185e3a8973629c8e5ee3417bb73704de8054366e508af0a2e2"
    ),
    "stable_file_structure_manifest_sha256": (
        "d82c3db448d71676240dabc66452fa7ef3c030f8390e3b0bb0fa56b30392e7fb"
    ),
}
EXPECTED_RATE_WORDING = (
    "Freeze the 68-file Gaze-in-the-Wild ProcessData processed timestamp-grid "
    "rate distribution; this is not acquisition-hardware cadence."
)
EXPECTED_HHA_WORDING = (
    "Freeze Gaze-in-the-Wild labeller-to-labeller sample-level and event-level "
    "agreement on the distributed multi-labeller overlap subset (five recordings); "
    "no full-distribution HHA claim."
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class GazeInWildProcessedRateLedger:
    path: Path | None
    fingerprint_sha256: str
    file_count: int
    min_inferred_rate_hz: float
    max_inferred_rate_hz: float


@dataclass(frozen=True, slots=True)
class GazeInWildRoadmapSync:
    path: Path | None
    fingerprint_sha256: str
    processed_rate_file_count: int
    overlap_hha_recording_count: int
    overlap_hha_pair_count: int


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


def _load(value: Mapping[str, Any] | str | Path, label: str) -> tuple[dict[str, Any], Path | None]:
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


def _mapping(record: Mapping[str, Any], key: str, label: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"GIW {label} field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"GIW roadmap evidence {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"GIW roadmap evidence must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"GIW roadmap evidence must not promote {label}.")


def validate_gaze_in_wild_processed_rate_ledger(
    ledger_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildProcessedRateLedger:
    """Validate the immutable 68-file ProcessData processed timestamp-grid ledger."""

    record, path = _load(ledger_or_path, "processed-rate ledger")
    _equal(record.get("record_type"), RATE_LEDGER_RECORD_TYPE, "rate-ledger record type")
    _equal(record.get("reviewed_on"), "2026-09-08", "rate-ledger review date")
    _equal(record.get("columns"), EXPECTED_COLUMNS, "rate-ledger columns")
    _equal(record.get("file_count"), 68, "rate-ledger file count")
    _equal(
        record.get("rate_semantics"),
        "median inverse delta of strictly increasing ProcessData.T processed timestamp grid",
        "rate semantics",
    )
    _equal(
        record.get("stored_rate_semantics"),
        "ProcessData.SR stored processing-rate field; not promoted to acquisition-hardware cadence",
        "stored-rate semantics",
    )
    _equal(
        record.get("evidence_fingerprint_sha256"),
        RATE_LEDGER_FINGERPRINT,
        "stored rate-ledger fingerprint",
    )
    _equal(
        evidence_fingerprint(record),
        RATE_LEDGER_FINGERPRINT,
        "recomputed rate-ledger fingerprint",
    )

    binding = _mapping(record, "source_binding", "processed-rate ledger")
    for key, expected in EXPECTED_RATE_SOURCE_BINDING.items():
        _equal(binding.get(key), expected, f"rate-ledger source binding {key}")

    boundary = _mapping(record, "scientific_boundary", "processed-rate ledger")
    _true(
        boundary.get("per_file_processed_timestamp_grid_rate_distribution_frozen"),
        "per-file processed timestamp-grid rate distribution",
    )
    for key in (
        "acquisition_hardware_cadence_verified",
        "gp3_validity_claim_created",
        "new_model_performance_claim_created",
        "participant_disjoint_model_validation_created",
        "task_mapping_verified",
    ):
        _false(boundary.get(key), key)

    rows = record.get("rows")
    if not isinstance(rows, list) or len(rows) != 68:
        raise BenchmarkIntegrityError("GIW processed-rate ledger must contain 68 rows.")
    names: set[str] = set()
    rates: list[float] = []
    for row in rows:
        if not isinstance(row, list) or len(row) != 7:
            raise BenchmarkIntegrityError("GIW processed-rate ledger row shape drifted.")
        name, digest, participant, trial, stored_rate, inferred_rate, count = row
        if not isinstance(name, str) or name in names:
            raise BenchmarkIntegrityError("GIW processed-rate ledger file names are invalid.")
        names.add(name)
        if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
            raise BenchmarkIntegrityError("GIW processed-rate ledger SHA-256 identity drifted.")
        if not isinstance(participant, int) or participant <= 0:
            raise BenchmarkIntegrityError("GIW processed-rate participant identity is invalid.")
        if trial not in (1, 2, 3, 4):
            raise BenchmarkIntegrityError("GIW processed-rate trial identity is invalid.")
        if stored_rate != 300.0:
            raise BenchmarkIntegrityError("GIW ProcessData stored processing rate drifted.")
        try:
            inferred = float(inferred_rate)
        except (TypeError, ValueError) as exc:
            raise BenchmarkIntegrityError("GIW inferred processed rate must be numeric.") from exc
        if not math.isfinite(inferred) or not 299.98 < inferred < 300.01:
            raise BenchmarkIntegrityError("GIW inferred processed timestamp-grid rate drifted.")
        rates.append(inferred)
        if not isinstance(count, int) or count <= 1:
            raise BenchmarkIntegrityError("GIW processed-rate timestamp count is invalid.")

    return GazeInWildProcessedRateLedger(
        path=path,
        fingerprint_sha256=RATE_LEDGER_FINGERPRINT,
        file_count=68,
        min_inferred_rate_hz=min(rates),
        max_inferred_rate_hz=max(rates),
    )


def _repository_root(path: Path | None, repository_root: str | Path | None) -> Path:
    if repository_root is not None:
        return Path(repository_root)
    if path is not None and len(path.parents) >= 4:
        return path.parents[3]
    return Path.cwd()


def validate_gaze_in_wild_roadmap_sync(
    evidence_or_path: Mapping[str, Any] | str | Path,
    *,
    repository_root: str | Path | None = None,
) -> GazeInWildRoadmapSync:
    """Validate scoped roadmap completion without widening any scientific claim."""

    record, path = _load(evidence_or_path, "roadmap sync evidence")
    _equal(record.get("record_type"), SYNC_RECORD_TYPE, "sync record type")
    _equal(record.get("status"), SYNC_STATUS, "sync status")
    _equal(record.get("reviewed_on"), "2026-09-09", "sync review date")
    _equal(record.get("source_main_sha"), SOURCE_MAIN_SHA, "source main SHA")
    _equal(record.get("evidence_fingerprint_sha256"), SYNC_FINGERPRINT, "stored sync fingerprint")
    _equal(evidence_fingerprint(record), SYNC_FINGERPRINT, "recomputed sync fingerprint")

    upstream = _mapping(record, "upstream_evidence", "roadmap sync")
    rate_ref = _mapping(upstream, "processed_rate_ledger", "roadmap sync")
    hha_ref = _mapping(upstream, "overlap_human_human_agreement", "roadmap sync")
    _equal(rate_ref.get("path"), RATE_LEDGER_PATH.as_posix(), "processed-rate path")
    _equal(rate_ref.get("evidence_fingerprint_sha256"), RATE_LEDGER_FINGERPRINT, "processed-rate fingerprint")
    _equal(rate_ref.get("file_count"), 68, "processed-rate reference count")
    _equal(
        rate_ref.get("scope"),
        "per-file ProcessData processed timestamp-grid rate distribution",
        "processed-rate scope",
    )
    _equal(hha_ref.get("path"), HHA_PATH.as_posix(), "HHA path")
    _equal(hha_ref.get("evidence_fingerprint_sha256"), EXPECTED_HHA_FINGERPRINT, "HHA fingerprint")
    _equal(hha_ref.get("recording_count"), 5, "HHA recording count")
    _equal(hha_ref.get("labeller_pair_count"), 6, "HHA pair count")
    _equal(hha_ref.get("scope"), "distributed multi-labeller overlap subset only", "HHA scope")

    completion = _mapping(record, "roadmap_completion", "roadmap sync")
    _true(
        completion.get("processed_timestamp_grid_rate_distribution_scoped_item_satisfied"),
        "scoped processed-rate roadmap completion",
    )
    _true(
        completion.get("distributed_overlap_human_human_agreement_scoped_item_satisfied"),
        "scoped overlap-HHA roadmap completion",
    )
    _false(
        completion.get("authoritative_numeric_task_mapping_item_satisfied"),
        "authoritative numeric task mapping completion",
    )
    _false(
        completion.get("task_stratified_validation_item_satisfied"),
        "task-stratified validation completion",
    )

    boundary = _mapping(record, "scientific_boundary", "roadmap sync")
    for key in (
        "acquisition_hardware_cadence_verified",
        "full_distributed_labeldata_hha_created",
        "task_mapping_verified",
        "task_stratified_hha_created",
        "task_stratified_model_validation_created",
        "native_60hz_validity_claim_created",
        "gp3_validity_claim_created",
        "cross_dataset_validation_created",
        "quarantine_exit_authorized",
        "new_model_performance_claim_created",
    ):
        _false(boundary.get(key), key)

    wording = _mapping(record, "issue_wording", "roadmap sync")
    _equal(wording.get("processed_rate"), EXPECTED_RATE_WORDING, "processed-rate issue wording")
    _equal(wording.get("human_human_agreement"), EXPECTED_HHA_WORDING, "HHA issue wording")

    root = _repository_root(path, repository_root)
    rate = validate_gaze_in_wild_processed_rate_ledger(root / RATE_LEDGER_PATH)
    hha = validate_gaze_in_wild_overlap_hha_evidence(root / HHA_PATH)
    if not hha.overlap_hha_verified or hha.quarantine_exit_authorized:
        raise BenchmarkIntegrityError("GIW overlap-HHA upstream boundary drifted.")
    _equal(hha.recording_count, 5, "validated HHA recording count")
    _equal(hha.pair_count, 6, "validated HHA pair count")

    return GazeInWildRoadmapSync(
        path=path,
        fingerprint_sha256=SYNC_FINGERPRINT,
        processed_rate_file_count=rate.file_count,
        overlap_hha_recording_count=hha.recording_count,
        overlap_hha_pair_count=hha.pair_count,
    )
