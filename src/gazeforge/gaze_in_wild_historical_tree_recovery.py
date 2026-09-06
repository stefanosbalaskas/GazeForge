"""Validate frozen Gaze-in-the-Wild historical-tree recovery evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

RECORD_TYPE = "gaze-in-wild-historical-tree-recovery-evidence-v1"
PINNED_REPOSITORY = "https://github.com/RSKothari/Gaze-in-Wild"
PINNED_COMMIT = "52262d44e366a53369e10ca73c5f41daf0e8f1e5"
EMBEDDED_MEMBER_SHA256 = "d633bbf0a3a9224b71e286ada10a63abe7761264eec7e8c25c94fcf0bbbafc63"
EXPECTED_PARENT_FINGERPRINTS = {
    "distribution_availability_fingerprint_sha256":
        "2400c81a0897fb414285069c368a8a9d96de1d18eb185b1073cf15bb1c8bd1da",
    "repository_history_fingerprint_sha256":
        "800d84d71d1d4b1a07e3b6d07c3bb7093c679284f49db0930a9836d77da30ad3",
    "layout_convergence_fingerprint_sha256":
        "b9c006e7bc367d7a66a4e78577d4d267b488eec298619b7e2e6707468172ac12",
}
FALSE_BOUNDARIES = (
    "full_distribution_recovered",
    "authoritative_original_or_canonical_dataset_copy_obtained",
    "original_distribution_equivalence_verified",
    "dataset_file_rights_resolved",
    "analysis_use_permitted",
    "redistribution_authorized",
    "quarantine_exit_authorized",
    "source_audit_ready",
    "participant_mapping_complete",
    "trial_task_mapping_complete",
    "published_acquisition_cadence_verified_from_embedded_sample",
    "coordinate_semantics_verified",
    "independent_labeller_recoverability_verified",
    "empirical_evidence_eligible",
)


class HistoricalTreeRecoveryEvidenceError(ValueError):
    """Raised when historical-tree recovery evidence violates the reviewed contract."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: dict[str, Any]) -> str:
    """Return the canonical SHA-256 fingerprint of a record."""
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def load_evidence(path: str | Path) -> dict[str, Any]:
    """Load and validate one frozen evidence JSON file."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HistoricalTreeRecoveryEvidenceError(
            f"Could not load historical-tree recovery evidence: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise HistoricalTreeRecoveryEvidenceError("Evidence root must be a JSON object.")
    return validate_evidence(value)


def validate_evidence(record: dict[str, Any]) -> dict[str, Any]:
    """Fail closed unless the record matches the reviewed evidence boundary."""
    if record.get("record_type") != RECORD_TYPE:
        raise HistoricalTreeRecoveryEvidenceError("Unexpected evidence record type.")

    scope = _mapping(record, "scope")
    if scope.get("repository") != PINNED_REPOSITORY:
        raise HistoricalTreeRecoveryEvidenceError("First-party repository identity drifted.")
    if scope.get("pinned_commit_sha1") != PINNED_COMMIT:
        raise HistoricalTreeRecoveryEvidenceError("Pinned first-party commit drifted.")
    if scope.get("reachable_commit_count") != 56:
        raise HistoricalTreeRecoveryEvidenceError("Reachable commit count drifted.")

    parents = _mapping(record, "parent_evidence")
    if parents != EXPECTED_PARENT_FINGERPRINTS:
        raise HistoricalTreeRecoveryEvidenceError("Parent evidence binding drifted.")

    history = _mapping(record, "reachable_history")
    _require_true(history, "all_reachable_commit_trees_checked")
    expected_zeroes = (
        "tracked_mat_path_count_across_reachable_trees",
        "exact_distribution_filename_path_count",
        "alternate_labeller_mat_path_count",
        "tag_ref_count",
        "release_count",
    )
    for key in expected_zeroes:
        if history.get(key) != 0:
            raise HistoricalTreeRecoveryEvidenceError(f"Unexpected historical count for {key}.")
    if history.get("archive_path_count") != 1:
        raise HistoricalTreeRecoveryEvidenceError("Tracked archive count drifted.")
    if history.get("only_branch") != "master":
        raise HistoricalTreeRecoveryEvidenceError("Unexpected first-party branch inventory.")

    archive = _mapping(record, "preprocessing_archive")
    if archive.get("path") != "DataExtraction/all_preprocessing_steps.zip":
        raise HistoricalTreeRecoveryEvidenceError("Preprocessing archive path drifted.")
    if archive.get("git_blob_sha1") != "284a64bcf52e686a19a09ff65d83f2328251eb71":
        raise HistoricalTreeRecoveryEvidenceError("Preprocessing archive Git blob drifted.")
    if archive.get("sha256") != (
        "5deef95a4d847b7b21a37c5d746212549b63217bd64159bec72992d82b575956"
    ):
        raise HistoricalTreeRecoveryEvidenceError("Preprocessing archive SHA-256 drifted.")
    if archive.get("member_count") != 12:
        raise HistoricalTreeRecoveryEvidenceError("Preprocessing archive member count drifted.")
    _require_false(archive, "labeldata_member_present")
    _require_false(archive, "exact_distribution_filename_member_present")

    embedded = _mapping(record, "embedded_processdata")
    if embedded.get("member_path") != "exports/ProcessData.mat":
        raise HistoricalTreeRecoveryEvidenceError("Embedded ProcessData path drifted.")
    if embedded.get("member_sha256") != EMBEDDED_MEMBER_SHA256:
        raise HistoricalTreeRecoveryEvidenceError("Embedded ProcessData SHA-256 drifted.")
    if embedded.get("member_size_bytes") != 40_528_499:
        raise HistoricalTreeRecoveryEvidenceError("Embedded ProcessData size drifted.")
    identity = _mapping(embedded, "identity")
    expected_identity = {
        "PrIdx": 2,
        "TrIdx": 2,
        "SR": 300,
        "DepthPresent": 0,
        "timestamp_count": 106_225,
        "ETG.POR_shape": [106_225, 2],
        "ETG.Labels_shape": [106_225],
        "ETG.Confidence_shape": [106_225],
        "IMU.HeadVector_shape": [106_225, 3],
        "ZED.FrameNo_shape": [106_225],
        "GIW.GIWvector_shape": [106_225, 3],
        "Path2Data_sha256":
            "8058c7143cf9104f3802ee7578792db8c48ad74d2515d27e993c435ed126ff4d",
    }
    if identity != expected_identity:
        raise HistoricalTreeRecoveryEvidenceError("Embedded ProcessData identity drifted.")
    _require_true(embedded, "first_party_data_bearing_processdata_object_verified")
    _require_false(embedded, "published_distribution_filename_match")
    _require_false(embedded, "exact_distribution_file_equivalence_verified")
    _require_false(embedded, "separate_labeldata_recovered")
    _require_false(embedded, "independent_labeller_streams_recovered")

    _reject_raw_path_key(record)

    boundary = _mapping(record, "scientific_boundary")
    for key in FALSE_BOUNDARIES:
        _require_false(boundary, key)

    observed_fp = record.get("evidence_fingerprint_sha256")
    expected_fp = evidence_fingerprint(record)
    if observed_fp != expected_fp:
        raise HistoricalTreeRecoveryEvidenceError("Evidence fingerprint mismatch.")
    return record


def _mapping(record: dict[str, Any], key: str) -> dict[str, Any]:
    value = record.get(key)
    if not isinstance(value, dict):
        raise HistoricalTreeRecoveryEvidenceError(f"{key} must be an object.")
    return value


def _require_true(record: dict[str, Any], key: str) -> None:
    if record.get(key) is not True:
        raise HistoricalTreeRecoveryEvidenceError(f"{key} must be true.")


def _require_false(record: dict[str, Any], key: str) -> None:
    if record.get(key) is not False:
        raise HistoricalTreeRecoveryEvidenceError(f"{key} must be false.")


def _reject_raw_path_key(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.lower() in {"path2data", "raw_path2data", "path2data_raw"}:
                raise HistoricalTreeRecoveryEvidenceError("Raw Path2Data disclosure is forbidden.")
            _reject_raw_path_key(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_raw_path_key(nested)
