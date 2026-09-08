"""Fail-closed validation for reviewed Gaze-in-the-Wild exact ProcessData structure evidence."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_coordinate_evidence import (
    validate_gaze_in_wild_por_coordinate_evidence,
)
from .gaze_in_wild_figshare_exact_bytes_evidence import (
    validate_gaze_in_wild_figshare_exact_bytes_evidence,
)

RECORD_TYPE = "gaze-in-wild-exact-processdata-structure-evidence-v1"
STATUS = "verified-exact-original-processdata-structure-rate-pairing-and-normalized-por-binding"
EVIDENCE_FINGERPRINT_SHA256 = (
    "cffcc8a10d176cc5eb8c15c080cf450e3e1b1404ced00ea8907cdd4ee3c3517f"
)
IDENTITY_RECORD_TYPE = "gaze-in-wild-processdata-exact-sha256-ledger-v1"
IDENTITY_EVIDENCE_FINGERPRINT_SHA256 = (
    "85f131389315a1185e3a8973629c8e5ee3417bb73704de8054366e508af0a2e2"
)
IDENTITY_MANIFEST_SHA256 = (
    "162bf688fbd0bfdaf79a11d423f3689abd31bea9a4e8423bc03020ebd598354d"
)
RATE_RECORD_TYPE = "gaze-in-wild-processdata-processed-rate-ledger-v1"
RATE_EVIDENCE_FINGERPRINT_SHA256 = (
    "1bd6643bd0c75faec9d070f74fb719f9178caa2da7e90bcbe356a0dbc5f38905"
)
EXACT_BYTE_EVIDENCE_FINGERPRINT_SHA256 = (
    "dbf277d698266fe53e337a15fc342e9af1835460d2bcc69c3992635de8fa0a00"
)
POR_EVIDENCE_FINGERPRINT_SHA256 = (
    "5eb245979385283571d6d9a5dda9a5d74dea6c00165bbe3a2587fcfa80e9adfb"
)
STABLE_FILE_STRUCTURE_MANIFEST_SHA256 = (
    "d82c3db448d71676240dabc66452fa7ef3c030f8390e3b0bb0fa56b30392e7fb"
)
STABLE_CORPUS_STRUCTURE_FINGERPRINT_SHA256 = (
    "86c4c94742ada7eceee3d44ef9c1c11a81621acd533bbb4e28aef3f6e3976443"
)
DISCOVERY_PROBE_FINGERPRINT_SHA256 = (
    "bbd7b0498f4d3b48e435bb0a79efd72d794e59e38fa31ccc73c2577bb95dd66b"
)
EXPECTED_PROCESS_PARTICIPANTS = [
    1, 2, 3, 4, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23
]
EXPECTED_LABEL_PARTICIPANTS = [1, 2, 3, 4, 6, 8, 9, 10, 12, 15, 16, 17, 18, 19, 20, 22]
EXPECTED_LABELLERS = [1, 2, 3, 5, 6]
RATE_COLUMNS = [
    "name",
    "sha256",
    "participant_index",
    "trial_index",
    "stored_rate_hz",
    "inferred_processed_rate_hz",
    "timestamp_count",
]


@dataclass(frozen=True, slots=True)
class GazeInWildExactProcessDataStructureEvidence:
    path: Path | None
    fingerprint_sha256: str
    processdata_file_count: int
    processdata_participant_count: int
    labelled_recording_count: int
    labelled_participant_count: int
    normalized_por_semantics_bound: bool
    participant_disjoint_partitioning_available: bool
    participant_disjoint_model_validation_created: bool
    quarantine_exit_authorized: bool


@dataclass(frozen=True, slots=True)
class GazeInWildFreshProcessDataStructureIdentity:
    structure_probe_fingerprint_sha256: str
    stable_file_structure_manifest_sha256: str
    processdata_file_count: int
    labelled_recording_count: int
    processed_rate_min_hz: float
    processed_rate_median_hz: float
    processed_rate_max_hz: float


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return _canonical_sha(body)


def probe_fingerprint(record: Mapping[str, Any]) -> str:
    body = dict(record)
    body.pop("structure_probe_fingerprint_sha256", None)
    return _canonical_sha(body)


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
        raise BenchmarkIntegrityError(f"Could not load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"{label} must contain one JSON object.")
    return payload, path


def _mapping(record: Mapping[str, Any], key: str, label: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"GIW exact ProcessData {label} is missing {key!r}.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"GIW exact ProcessData {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"GIW exact ProcessData must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"GIW exact ProcessData must not promote {label}.")


def _validate_identity_ledger(value: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    record, _ = _load(value, "GIW ProcessData exact SHA-256 ledger")
    _equal(record.get("record_type"), IDENTITY_RECORD_TYPE, "identity-ledger type")
    _equal(record.get("file_count"), 68, "identity-ledger file count")
    _equal(
        record.get("evidence_fingerprint_sha256"),
        IDENTITY_EVIDENCE_FINGERPRINT_SHA256,
        "identity-ledger stored fingerprint",
    )
    _equal(
        evidence_fingerprint(record),
        IDENTITY_EVIDENCE_FINGERPRINT_SHA256,
        "identity-ledger recomputed fingerprint",
    )
    _equal(
        record.get("sha256_manifest_sha256"),
        IDENTITY_MANIFEST_SHA256,
        "identity SHA-256 manifest",
    )
    files = record.get("files")
    if not isinstance(files, list) or len(files) != 68:
        raise BenchmarkIntegrityError("GIW ProcessData identity ledger must contain 68 rows.")
    names: set[str] = set()
    manifest: list[dict[str, str]] = []
    for row in files:
        if not isinstance(row, Mapping):
            raise BenchmarkIntegrityError("GIW ProcessData identity row is malformed.")
        name = row.get("name")
        sha256 = row.get("sha256")
        if not isinstance(name, str) or name in names:
            raise BenchmarkIntegrityError("GIW ProcessData identity filename is invalid/duplicate.")
        if not isinstance(sha256, str) or len(sha256) != 64:
            raise BenchmarkIntegrityError(f"GIW ProcessData SHA-256 is invalid for {name!r}.")
        names.add(name)
        manifest.append({"name": name, "sha256": sha256})
    _equal(_canonical_sha(manifest), IDENTITY_MANIFEST_SHA256, "identity manifest body")
    return record


def _validate_rate_ledger(
    value: Mapping[str, Any] | str | Path,
    identities: Mapping[str, Any],
) -> dict[str, Any]:
    record, _ = _load(value, "GIW ProcessData processed-rate ledger")
    _equal(record.get("record_type"), RATE_RECORD_TYPE, "rate-ledger type")
    _equal(record.get("reviewed_on"), "2026-09-08", "rate-ledger review date")
    _equal(record.get("file_count"), 68, "rate-ledger file count")
    _equal(record.get("columns"), RATE_COLUMNS, "rate-ledger columns")
    _equal(
        record.get("rate_semantics"),
        "median inverse delta of strictly increasing ProcessData.T processed timestamp grid",
        "rate semantics",
    )
    _equal(
        record.get("evidence_fingerprint_sha256"),
        RATE_EVIDENCE_FINGERPRINT_SHA256,
        "rate-ledger stored fingerprint",
    )
    _equal(
        evidence_fingerprint(record),
        RATE_EVIDENCE_FINGERPRINT_SHA256,
        "rate-ledger recomputed fingerprint",
    )
    rows = record.get("rows")
    if not isinstance(rows, list) or len(rows) != 68:
        raise BenchmarkIntegrityError("GIW ProcessData rate ledger must contain 68 rows.")
    identity_pairs = {
        (row["name"], row["sha256"])
        for row in identities["files"]
        if isinstance(row, Mapping)
    }
    observed_pairs: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, list) or len(row) != len(RATE_COLUMNS):
            raise BenchmarkIntegrityError("GIW ProcessData rate row shape drifted.")
        name, sha256, participant, trial, stored, inferred, count = row
        if (name, sha256) in observed_pairs:
            raise BenchmarkIntegrityError("GIW ProcessData rate row duplicated a file identity.")
        observed_pairs.add((name, sha256))
        if not isinstance(participant, int) or participant <= 0:
            raise BenchmarkIntegrityError("GIW ProcessData rate participant token is invalid.")
        if not isinstance(trial, int) or trial <= 0:
            raise BenchmarkIntegrityError("GIW ProcessData rate trial token is invalid.")
        if float(stored) != 300.0:
            raise BenchmarkIntegrityError("GIW ProcessData stored processed rate drifted from 300 Hz.")
        if not math.isfinite(float(inferred)) or not 299.98 < float(inferred) < 300.01:
            raise BenchmarkIntegrityError("GIW ProcessData inferred processed rate is invalid.")
        if not isinstance(count, int) or count < 2:
            raise BenchmarkIntegrityError("GIW ProcessData timestamp count is invalid.")
    _equal(observed_pairs, identity_pairs, "rate/identity file coverage")
    return record


def validate_gaze_in_wild_exact_processdata_structure_evidence(
    evidence_or_path: Mapping[str, Any] | str | Path,
    identities_or_path: Mapping[str, Any] | str | Path,
    rate_ledger_or_path: Mapping[str, Any] | str | Path,
    por_evidence_or_path: Mapping[str, Any] | str | Path,
    exact_byte_evidence_or_path: Mapping[str, Any] | str | Path | None = None,
    raw_metadata_or_path: Mapping[str, Any] | str | Path | None = None,
    rights_evidence_or_path: Mapping[str, Any] | str | Path | None = None,
    metadata_summary_or_path: Mapping[str, Any] | str | Path | None = None,
) -> GazeInWildExactProcessDataStructureEvidence:
    """Validate reviewed exact ProcessData structure evidence and parent bindings."""

    record, path = _load(evidence_or_path, "GIW exact ProcessData structure evidence")
    identities = _validate_identity_ledger(identities_or_path)
    rate_ledger = _validate_rate_ledger(rate_ledger_or_path, identities)
    por = validate_gaze_in_wild_por_coordinate_evidence(por_evidence_or_path)
    _equal(
        por.get("evidence_fingerprint_sha256"),
        POR_EVIDENCE_FINGERPRINT_SHA256,
        "POR parent fingerprint",
    )

    parent_args = (
        exact_byte_evidence_or_path,
        raw_metadata_or_path,
        rights_evidence_or_path,
        metadata_summary_or_path,
    )
    if any(value is not None for value in parent_args):
        if not all(value is not None for value in parent_args):
            raise BenchmarkIntegrityError(
                "GIW exact ProcessData parent exact-byte validation requires all four inputs."
            )
        exact = validate_gaze_in_wild_figshare_exact_bytes_evidence(
            exact_byte_evidence_or_path,
            raw_metadata_or_path,
            rights_evidence_or_path,
            metadata_summary_or_path,
        )
        _equal(
            exact.fingerprint_sha256,
            EXACT_BYTE_EVIDENCE_FINGERPRINT_SHA256,
            "exact-byte parent fingerprint",
        )
        _true(exact.exact_original_distribution_bytes_verified, "exact parent bytes")
        _false(exact.raw_dataset_bytes_retained, "parent raw-byte retention")

    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("reviewed_on"), "2026-09-08", "review date")
    _equal(
        record.get("evidence_fingerprint_sha256"),
        EVIDENCE_FINGERPRINT_SHA256,
        "stored evidence fingerprint",
    )
    _equal(
        evidence_fingerprint(record),
        EVIDENCE_FINGERPRINT_SHA256,
        "recomputed evidence fingerprint",
    )

    binding = _mapping(record, "source_binding", "reviewed evidence")
    expected_binding = {
        "figshare_project_id": 74580,
        "processdata_article_id": 11673645,
        "processdata_doi": "10.6084/m9.figshare.11673645.v1",
        "labeldata_article_id": 11673696,
        "labeldata_doi": "10.6084/m9.figshare.11673696.v1",
        "reviewed_exact_byte_evidence_fingerprint_sha256": EXACT_BYTE_EVIDENCE_FINGERPRINT_SHA256,
        "reviewed_por_coordinate_semantics_evidence_fingerprint_sha256": POR_EVIDENCE_FINGERPRINT_SHA256,
        "processdata_sha256_ledger_evidence_fingerprint_sha256": IDENTITY_EVIDENCE_FINGERPRINT_SHA256,
        "processdata_sha256_manifest_sha256": IDENTITY_MANIFEST_SHA256,
        "processed_rate_ledger_evidence_fingerprint_sha256": RATE_EVIDENCE_FINGERPRINT_SHA256,
        "stable_file_structure_manifest_sha256": STABLE_FILE_STRUCTURE_MANIFEST_SHA256,
        "stable_corpus_structure_fingerprint_sha256": STABLE_CORPUS_STRUCTURE_FINGERPRINT_SHA256,
        "discovery_probe_fingerprint_sha256": DISCOVERY_PROBE_FINGERPRINT_SHA256,
        "discovery_workflow_run_id": 34199996646,
        "discovery_workflow_job_id": 101976365230,
        "discovery_workflow_head_sha": "a9fa2e91ffdb1eb9eb6603d393060dc71eced9ee",
        "discovery_artifact_id": 10045524274,
        "discovery_artifact_zip_sha256": "e51138b34c6e7c4ddcc8fa3ffd825884485019bf05270072d6abee97990f638e",
    }
    for key, expected in expected_binding.items():
        _equal(binding.get(key), expected, f"source binding {key}")

    verified = _mapping(record, "verified_processdata", "reviewed evidence")
    _equal(verified.get("file_count"), 68, "ProcessData file count")
    _equal(verified.get("total_size_bytes"), 2_384_573_418, "ProcessData total bytes")
    _equal(verified.get("recording_token_count"), 68, "ProcessData recording count")
    _equal(verified.get("participant_count"), 20, "ProcessData participant count")
    _equal(verified.get("participant_indices"), EXPECTED_PROCESS_PARTICIPANTS, "ProcessData participants")
    for key in (
        "all_files_matched_frozen_size_md5_and_reviewed_sha256",
        "all_filename_internal_pridx_tridx_agree",
        "all_adapter_coordinate_fields_compatible",
        "all_timestamp_grids_valid",
        "all_scene_resolutions_1920x1080",
        "all_etg_labels_present",
    ):
        _true(verified.get(key), key)
    _false(
        verified.get("top_level_labeldata_present_in_any_processdata_file"),
        "top-level LabelData in ProcessData",
    )
    stored_summary = _mapping(verified, "stored_rate_summary", "ProcessData summary")
    _equal(stored_summary.get("count"), 68, "stored-rate count")
    _equal(stored_summary.get("distinct_rounded_6dp_hz"), [300.0], "stored-rate values")
    rate_summary = _mapping(
        verified,
        "inferred_processed_timestamp_grid_rate_summary",
        "ProcessData summary",
    )
    _equal(rate_summary.get("count"), 68, "inferred-rate count")
    for key, expected in (
        ("min_hz", 299.98859845584474),
        ("median_hz", 299.9948438624359),
        ("max_hz", 299.9976557817862),
    ):
        _equal(rate_summary.get(key), expected, f"processed-rate {key}")

    pairing = _mapping(record, "distributed_labeldata_pairing", "reviewed evidence")
    _equal(pairing.get("labeldata_file_count"), 50, "LabelData file count")
    _equal(pairing.get("recording_token_count"), 37, "labelled recording count")
    _equal(pairing.get("participant_count"), 16, "labelled participant count")
    _equal(pairing.get("participant_indices"), EXPECTED_LABEL_PARTICIPANTS, "labelled participants")
    _equal(pairing.get("labeller_indices"), EXPECTED_LABELLERS, "labeller identities")
    _equal(
        pairing.get("processdata_tokens_without_distributed_labeldata_count"),
        31,
        "unlabelled ProcessData token count",
    )
    _true(
        pairing.get("all_labeldata_recording_tokens_have_processdata_match"),
        "LabelData/ProcessData pairing",
    )
    _true(pairing.get("participant_disjoint_split_keys_available"), "participant split keys")

    coordinate = _mapping(record, "coordinate_semantics_binding", "reviewed evidence")
    _true(
        coordinate.get("all_exact_processdata_files_structurally_match_semantic_fields"),
        "exact-file POR semantic-field match",
    )
    _true(
        coordinate.get("normalized_por_to_canonical_pixels_supported"),
        "normalized POR canonical conversion",
    )
    _equal(
        coordinate.get("processdata_por_coordinate_space"),
        "normalized_scene_image",
        "POR coordinate space",
    )
    _equal(coordinate.get("scene_resolution_px"), [1920, 1080], "scene resolution")
    _false(
        coordinate.get("corpus_wide_por_value_ranges_empirically_verified"),
        "corpus-wide POR range claim",
    )

    boundary = _mapping(record, "scientific_boundary", "reviewed evidence")
    for key in (
        "exact_original_processdata_structure_verified",
        "labeldata_processdata_recording_token_pairing_complete",
        "normalized_por_semantics_bound_to_exact_distribution",
        "per_file_processed_timestamp_grid_rate_distribution_frozen",
        "task_agnostic_participant_disjoint_input_partitioning_available",
    ):
        _true(boundary.get(key), key)
    for key in (
        "acquisition_hardware_cadence_verified",
        "complete_file_to_publication_task_mapping_verified",
        "corpus_wide_por_value_ranges_empirically_verified",
        "task_stratified_model_validation_feasible",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "quarantine_exit_authorized",
        "new_model_performance_claim_created",
    ):
        _false(boundary.get(key), key)
    _false(record.get("raw_dataset_bytes_retained"), "raw dataset retention")

    _equal(
        rate_ledger.get("evidence_fingerprint_sha256"),
        binding.get("processed_rate_ledger_evidence_fingerprint_sha256"),
        "rate-ledger evidence binding",
    )

    return GazeInWildExactProcessDataStructureEvidence(
        path=path,
        fingerprint_sha256=EVIDENCE_FINGERPRINT_SHA256,
        processdata_file_count=68,
        processdata_participant_count=20,
        labelled_recording_count=37,
        labelled_participant_count=16,
        normalized_por_semantics_bound=True,
        participant_disjoint_partitioning_available=True,
        participant_disjoint_model_validation_created=False,
        quarantine_exit_authorized=False,
    )


def _stable_file_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "download_attempt"}


def validate_fresh_gaze_in_wild_processdata_structure_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    reviewed_evidence_or_path: Mapping[str, Any] | str | Path,
    identities_or_path: Mapping[str, Any] | str | Path,
    rate_ledger_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildFreshProcessDataStructureIdentity:
    """Validate a fresh 68-file structural reproduction against reviewed stable identities."""

    probe, _ = _load(probe_or_path, "GIW fresh exact ProcessData structure probe")
    reviewed, _ = _load(reviewed_evidence_or_path, "GIW reviewed ProcessData structure evidence")
    identities = _validate_identity_ledger(identities_or_path)
    rate_ledger = _validate_rate_ledger(rate_ledger_or_path, identities)

    _equal(
        probe.get("record_type"),
        "gaze-in-wild-exact-processdata-structure-probe-v1",
        "fresh probe type",
    )
    fingerprint = probe.get("structure_probe_fingerprint_sha256")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise BenchmarkIntegrityError("GIW fresh ProcessData probe fingerprint is invalid.")
    _equal(probe_fingerprint(probe), fingerprint, "fresh probe fingerprint")

    source = _mapping(probe, "source_binding", "fresh probe")
    _equal(source.get("figshare_project_id"), 74580, "fresh Figshare project")
    _equal(source.get("processdata_article_id"), 11673645, "fresh ProcessData article")
    _equal(source.get("labeldata_article_id"), 11673696, "fresh LabelData article")
    _equal(
        source.get("exact_byte_reviewed_evidence_fingerprint_sha256"),
        EXACT_BYTE_EVIDENCE_FINGERPRINT_SHA256,
        "fresh exact-byte binding",
    )
    _equal(
        source.get("exact_processdata_identity_ledger_fingerprint_sha256"),
        IDENTITY_EVIDENCE_FINGERPRINT_SHA256,
        "fresh identity-ledger binding",
    )
    _equal(
        source.get("exact_processdata_sha256_manifest_sha256"),
        IDENTITY_MANIFEST_SHA256,
        "fresh SHA manifest binding",
    )

    verified = _mapping(probe, "verified_processdata", "fresh probe")
    rows = verified.get("file_results")
    if not isinstance(rows, list) or len(rows) != 68:
        raise BenchmarkIntegrityError("GIW fresh ProcessData probe must contain 68 file rows.")
    stable_rows: list[dict[str, Any]] = []
    rate_rows: list[list[Any]] = []
    names: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise BenchmarkIntegrityError("GIW fresh ProcessData file row is malformed.")
        name = row.get("name")
        if not isinstance(name, str) or name in names:
            raise BenchmarkIntegrityError("GIW fresh ProcessData filename is invalid/duplicate.")
        names.add(name)
        _true(row.get("adapter_coordinate_fields_compatible"), f"{name} adapter compatibility")
        _true(row.get("timestamp_grid_valid"), f"{name} timestamp grid")
        _false(row.get("raw_bytes_retained"), f"{name} raw-byte retention")
        _false(row.get("top_level_labeldata_present"), f"{name} top-level LabelData")
        if row.get("scene_resolution_px") != [1920, 1080]:
            raise BenchmarkIntegrityError(f"GIW fresh scene resolution drifted for {name}.")
        count = row.get("timestamp_count")
        if row.get("por_shape") != [count, 2]:
            raise BenchmarkIntegrityError(f"GIW fresh POR shape drifted for {name}.")
        if row.get("confidence_shape") != [count] or row.get("labels_shape") != [count]:
            raise BenchmarkIntegrityError(f"GIW fresh vector shape drifted for {name}.")
        _true(row.get("labels_present"), f"{name} structural ETG.Labels presence")
        stable_rows.append(_stable_file_row(row))
        rate_rows.append(
            [
                row.get("name"),
                row.get("sha256"),
                row.get("participant_index"),
                row.get("trial_index"),
                row.get("stored_rate_hz"),
                row.get("inferred_processed_rate_hz"),
                row.get("timestamp_count"),
            ]
        )

    _equal(
        _canonical_sha(stable_rows),
        STABLE_FILE_STRUCTURE_MANIFEST_SHA256,
        "fresh stable file-structure manifest",
    )
    _equal(rate_rows, rate_ledger.get("rows"), "fresh processed-rate ledger reproduction")

    reviewed_verified = _mapping(reviewed, "verified_processdata", "reviewed evidence")
    for key in (
        "file_count",
        "total_size_bytes",
        "recording_token_count",
        "participant_count",
        "participant_indices",
        "stored_rate_summary",
        "inferred_processed_timestamp_grid_rate_summary",
    ):
        _equal(verified.get(key), reviewed_verified.get(key), f"fresh aggregate {key}")
    for key in (
        "all_files_matched_frozen_size_md5_and_reviewed_sha256",
        "all_filename_internal_pridx_tridx_agree",
        "all_adapter_coordinate_fields_compatible",
        "all_timestamp_grids_valid",
        "all_raw_mat_bytes_deleted_after_inspection",
    ):
        _true(verified.get(key), f"fresh {key}")
    _false(
        verified.get("top_level_labeldata_present_in_any_processdata_file"),
        "fresh top-level LabelData presence",
    )

    pairing = _mapping(probe, "distributed_labeldata_pairing", "fresh probe")
    reviewed_pairing = _mapping(reviewed, "distributed_labeldata_pairing", "reviewed evidence")
    expected_pairing = {
        "file_count": reviewed_pairing.get("labeldata_file_count"),
        "recording_token_count": reviewed_pairing.get("recording_token_count"),
        "participant_count": reviewed_pairing.get("participant_count"),
        "participant_indices": reviewed_pairing.get("participant_indices"),
        "labeller_indices": reviewed_pairing.get("labeller_indices"),
        "all_labeldata_recording_tokens_have_processdata_match": reviewed_pairing.get(
            "all_labeldata_recording_tokens_have_processdata_match"
        ),
        "processdata_tokens_without_distributed_labeldata_count": reviewed_pairing.get(
            "processdata_tokens_without_distributed_labeldata_count"
        ),
        "participant_disjoint_split_keys_available": reviewed_pairing.get(
            "participant_disjoint_split_keys_available"
        ),
    }
    for key, expected in expected_pairing.items():
        _equal(pairing.get(key), expected, f"fresh pairing {key}")
    _equal(pairing.get("matched_recording_token_count"), 37, "fresh matched recording count")

    boundary = _mapping(probe, "scientific_boundary", "fresh probe")
    for key in (
        "exact_original_processdata_structure_verified",
        "processdata_timestamp_grid_rate_distribution_verified",
        "filename_internal_pridx_tridx_alignment_complete",
        "labeldata_processdata_recording_token_pairing_complete",
        "participant_disjoint_split_keys_available",
        "coordinate_adapter_fields_available_for_all_processdata",
    ):
        _true(boundary.get(key), f"fresh {key}")
    for key in (
        "coordinate_semantics_verified_for_exact_distribution",
        "acquisition_hardware_cadence_verified",
        "complete_file_to_publication_task_mapping_verified",
        "task_stratified_model_validation_feasible",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "quarantine_exit_authorized",
        "new_model_performance_claim_created",
    ):
        _false(boundary.get(key), f"fresh {key}")
    _false(probe.get("raw_dataset_bytes_retained"), "fresh raw dataset retention")
    excluded = _mapping(probe, "excluded_cleaned_deposit", "fresh probe")
    _equal(excluded.get("article_id"), 11673717, "fresh cleaned article id")
    _false(excluded.get("downloaded"), "fresh cleaned-data download")

    rate_summary = _mapping(
        verified,
        "inferred_processed_timestamp_grid_rate_summary",
        "fresh ProcessData summary",
    )
    return GazeInWildFreshProcessDataStructureIdentity(
        structure_probe_fingerprint_sha256=fingerprint,
        stable_file_structure_manifest_sha256=STABLE_FILE_STRUCTURE_MANIFEST_SHA256,
        processdata_file_count=68,
        labelled_recording_count=37,
        processed_rate_min_hz=float(rate_summary["min_hz"]),
        processed_rate_median_hz=float(rate_summary["median_hz"]),
        processed_rate_max_hz=float(rate_summary["max_hz"]),
    )
