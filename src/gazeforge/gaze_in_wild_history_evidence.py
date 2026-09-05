"""Fail-closed validation for frozen Gaze-in-the-Wild repository-history evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "gaze-in-wild-repository-history-evidence-v1"
PROBE_RECORD_TYPE = "gaze-in-wild-official-repository-history-probe-v1"
STATUS = (
    "verified_complete_reachable_first_author_repository_history_"
    "dataset_copy_and_rights_unresolved"
)
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "800d84d71d1d4b1a07e3b6d07c3bb7093c679284f49db0930a9836d77da30ad3"
)
EXPECTED_PROBE_FINGERPRINT_SHA256 = (
    "d0cc0212d77e24f07412ddb22e7743c9e9621be8d2ec73ef087b231c77893f11"
)
EXPECTED_PROBE_FILE_SHA256 = (
    "bf1078de1a83518afe43b200949089be09f10ee2b8a0809c9a4f489e8d2ceaf2"
)
REPOSITORY = "https://github.com/RSKothari/Gaze-in-Wild"
PINNED_COMMIT = "52262d44e366a53369e10ca73c5f41daf0e8f1e5"
PINNED_TREE = "c0fa1ae13c101a8d95b09370970a6012ea97a3d9"
ROOT_COMMIT = "054c99d3b88f0ad46cbd0b7d66f4fc38718046f5"
COMMIT_LEDGER_FINGERPRINT = (
    "736ec7c33336f5495ab1dff02745481c92526f87aec015102edddc486492ef13"
)
KEY_PATH_FINGERPRINT = (
    "3f03b2fb6c524484509378c934389345fb38b191aa665e5ab8016cacb27b2815"
)
README_HISTORY_FINGERPRINT = (
    "b791c8127efac5801b1a5c74cc42edb4a800b009aff3f8f049c1bd39e4a8825e"
)
README_BLOBS = (
    "c7854ed43f8a853a36826dd06e436cbd7fb99482",
    "17c6cb4410604f5fd456e1d88853712533a37cdd",
    "f5d15043ae19251301a489dd03e907744fde0325",
    "37514d43b60ee31a4f074e9cf0f8dd096e77d535",
    "dba6c087af461b03d838a46bd30b5ee5f4a6a6a6",
    "5b8536d0166d8c58e33d908fccd9c3f9c2b59a12",
)
LICENSE_BLOB = "b6f41e2ee0550feabd3938efc7d93ae24c491903"
LICENSE_FIRST_SEEN = "76dc9cd3a276252ef1913ef1b70e4e001dd76cdf"


@dataclass(frozen=True, slots=True)
class GazeInWildRepositoryHistoryEvidence:
    """Compact typed identity for the reviewed first-author repository history."""

    path: Path | None
    fingerprint_sha256: str
    commit_count: int
    repository_mit_verified_for_software: bool
    exact_dataset_copy_obtained: bool
    participant_identity_mapping_verified: bool


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return canonical SHA-256 excluding the stored evidence fingerprint."""

    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def probe_fingerprint(record: Mapping[str, Any]) -> str:
    """Return canonical SHA-256 excluding the stored live-probe fingerprint."""

    body = dict(record)
    body.pop("probe_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(
    record_or_path: Mapping[str, Any] | str | Path,
    *,
    label: str,
) -> tuple[dict[str, Any], Path | None]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path), None
    path = Path(record_or_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"Could not load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"{label} must contain one JSON object.")
    return payload, path


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"Gaze-in-the-Wild history field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"Gaze-in-the-Wild history {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"Gaze-in-the-Wild history must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"Gaze-in-the-Wild history must not promote {label}.")


def _fingerprint_value(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def validate_gaze_in_wild_repository_history_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Strictly validate the immutable reviewed repository-history evidence."""

    record, _ = _load(record_or_path, label="Gaze-in-the-Wild repository-history evidence")
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("checked_on"), "2026-09-05", "review date")
    _equal(
        record.get("dataset"),
        "Gaze-in-the-Wild naturalistic eye-head event benchmark",
        "dataset identity",
    )

    scope = _mapping(record, "scope")
    _equal(scope.get("repository"), REPOSITORY, "repository")
    _equal(scope.get("pinned_commit_sha1"), PINNED_COMMIT, "pinned commit")
    _equal(scope.get("pinned_root_tree_sha1"), PINNED_TREE, "pinned tree")
    _equal(
        scope.get("history_scope"),
        "all 56 commits reachable from the pinned first-author processing-repository HEAD",
        "history scope",
    )

    execution = _mapping(record, "execution")
    _equal(execution.get("workflow_run_id"), 33979183226, "reviewed workflow run")
    _equal(
        execution.get("workflow_head_sha"),
        "4c45e355426e7cfb4345213312d3ffc6e86eead9",
        "reviewed workflow head",
    )
    _equal(execution.get("artifact_id"), 9973226510, "reviewed artifact id")
    _equal(
        execution.get("artifact_digest_sha256"),
        "b801ada9755b64da0d87a016b35a472d3fc51606e85a2d476e4e5d25edcac11b",
        "reviewed artifact digest",
    )
    _equal(
        execution.get("live_probe_record_type"),
        PROBE_RECORD_TYPE,
        "reviewed probe record type",
    )
    _equal(
        execution.get("live_probe_fingerprint_sha256"),
        EXPECTED_PROBE_FINGERPRINT_SHA256,
        "reviewed probe fingerprint",
    )
    _equal(
        execution.get("live_probe_file_sha256"),
        EXPECTED_PROBE_FILE_SHA256,
        "reviewed probe file fingerprint",
    )

    history = _mapping(record, "repository_history")
    _equal(history.get("reachable_commit_count"), 56, "commit count")
    _equal(history.get("root_commit_sha1"), ROOT_COMMIT, "root commit")
    _equal(history.get("head_commit_sha1"), PINNED_COMMIT, "head commit")
    _equal(tuple(history.get("author_names", [])), ("RSKothari", "rakshit"), "authors")
    _equal(
        history.get("commit_ledger_fingerprint_sha256"),
        COMMIT_LEDGER_FINGERPRINT,
        "commit ledger fingerprint",
    )

    key_paths = _mapping(record, "key_path_history")
    _equal(
        key_paths.get("key_path_inventory_fingerprint_sha256"),
        KEY_PATH_FINGERPRINT,
        "key-path inventory fingerprint",
    )
    expected_paths = {
        "README.md": (
            "7758a63f9876a00136fbd44901fcecd12d05081f",
            "5b8536d0166d8c58e33d908fccd9c3f9c2b59a12",
        ),
        "License.md": (LICENSE_FIRST_SEEN, LICENSE_BLOB),
        "DataExtraction/GetParticipantInfo.m": (
            "8f020ed82f456769cea4a1f6a37ce901c08620f7",
            "6c21df7554891015a1ae09182867b5d707b6a505",
        ),
        "DataExtraction/ReadData_function.m": (
            "8f020ed82f456769cea4a1f6a37ce901c08620f7",
            "36d81839fb9f9eadb1274b998d2a8652fb0840ca",
        ),
        "PlotLabels.m": (
            "7758a63f9876a00136fbd44901fcecd12d05081f",
            "511581250e04c62037c71d2da16271be4979d434",
        ),
    }
    for path, (first_seen, blob) in expected_paths.items():
        item = _mapping(key_paths, path)
        _true(item.get("present_at_pinned_head"), f"presence of {path}")
        _equal(item.get("first_seen_commit_sha1"), first_seen, f"{path} first-seen commit")
        _equal(item.get("pinned_blob_sha1"), blob, f"{path} pinned blob")

    readme = _mapping(record, "readme_history")
    _equal(readme.get("unique_blob_count"), 6, "README blob count")
    _equal(
        readme.get("revision_inventory_fingerprint_sha256"),
        README_HISTORY_FINGERPRINT,
        "README revision fingerprint",
    )
    _equal(tuple(readme.get("revision_blob_sha1s", [])), README_BLOBS, "README blobs")
    for key, label in (
        ("pinned_distribution_url_present", "historical distribution URL statement"),
        (
            "pinned_all_data_files_download_webpage_statement_present",
            "all-data-files webpage statement",
        ),
        ("pinned_raw_data_over_14tb_statement_present", ">14 TB raw-data statement"),
        ("pinned_raw_data_contact_authors_statement_present", "raw-data contact statement"),
    ):
        _true(readme.get(key), label)

    license_history = _mapping(record, "software_license_history")
    _true(license_history.get("license_file_present_at_pinned_head"), "MIT license file")
    _true(license_history.get("license_file_identifies_mit"), "MIT license identification")
    _equal(
        license_history.get("license_file_first_seen_commit_sha1"),
        LICENSE_FIRST_SEEN,
        "license first-seen commit",
    )
    _equal(license_history.get("license_file_blob_sha1"), LICENSE_BLOB, "license blob")
    _equal(
        license_history.get("license_scope"),
        "software and associated documentation files",
        "license scope",
    )
    _false(
        license_history.get("license_scope_promoted_to_external_dataset_files"),
        "MIT license promotion to external dataset files",
    )

    tree = _mapping(record, "repository_tree")
    _equal(tree.get("tracked_path_count"), 178, "tracked path count")
    _equal(
        tree.get("distributed_process_or_label_mat_path_count"),
        0,
        "distributed dataset-like path count",
    )
    _false(tree.get("repository_is_exact_compressed_dataset_copy"), "exact-copy claim")

    boundary = _mapping(record, "scientific_boundary")
    _true(boundary.get("complete_reachable_repository_history_audited"), "complete history audit")
    _true(
        boundary.get("repository_mit_license_verified_for_software"),
        "software-scoped MIT license",
    )
    for key, label in (
        ("exact_external_dataset_copy_obtained", "exact dataset acquisition"),
        ("external_dataset_file_rights_resolved", "dataset-file rights resolution"),
        ("external_dataset_file_license_verified", "dataset-file license verification"),
        ("software_mit_is_external_dataset_license", "software MIT as dataset license"),
        (
            "published_distribution_url_is_current_direct_copy_verified",
            "current direct-copy verification",
        ),
        ("participant_identity_mapping_from_history_verified", "participant mapping"),
        ("complete_trial_to_task_mapping_from_history_verified", "complete task mapping"),
        ("human_human_agreement_created", "human-human agreement"),
        ("participant_disjoint_model_validation_created", "participant-disjoint validation"),
        ("cross_dataset_validation_created", "cross-dataset validation"),
        ("gp3_validity_claim_created", "GP3 validity"),
        ("frozen_evidence_performance_claim_created", "Frozen Evidence performance"),
    ):
        _false(boundary.get(key), label)

    limits = record.get("claim_limits")
    actions = record.get("next_required_actions")
    if not isinstance(limits, list) or len(limits) < 5:
        raise BenchmarkIntegrityError("Gaze-in-the-Wild history must retain claim limits.")
    if not isinstance(actions, list) or len(actions) < 3:
        raise BenchmarkIntegrityError("Gaze-in-the-Wild history must retain next actions.")

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    calculated = evidence_fingerprint(record)
    if stored != calculated:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild repository-history evidence self-fingerprint is invalid."
        )
    if stored != EXPECTED_EVIDENCE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild immutable repository-history fingerprint drifted."
        )
    return record


def validate_gaze_in_wild_repository_history_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Bind a fresh complete-history probe to the immutable reviewed evidence."""

    probe, _ = _load(probe_or_path, label="Gaze-in-the-Wild repository-history probe")
    evidence = validate_gaze_in_wild_repository_history_evidence(evidence_or_path)

    _equal(probe.get("record_type"), PROBE_RECORD_TYPE, "live probe record type")
    _equal(probe.get("repository"), REPOSITORY, "live probe repository")
    _equal(probe.get("pinned_commit_sha1"), PINNED_COMMIT, "live pinned commit")
    _equal(probe.get("pinned_root_tree_sha1"), PINNED_TREE, "live pinned tree")
    _equal(probe.get("reachable_commit_count"), 56, "live commit count")
    _equal(probe.get("root_commit_sha1"), ROOT_COMMIT, "live root commit")
    _equal(tuple(probe.get("author_names", [])), ("RSKothari", "rakshit"), "live authors")

    stored_probe_fingerprint = str(probe.get("probe_fingerprint_sha256", ""))
    _equal(
        probe_fingerprint(probe),
        stored_probe_fingerprint,
        "live probe self-fingerprint",
    )
    _equal(
        stored_probe_fingerprint,
        EXPECTED_PROBE_FINGERPRINT_SHA256,
        "live reviewed probe fingerprint",
    )

    frozen_history = _mapping(evidence, "repository_history")
    _equal(
        _fingerprint_value(probe.get("commit_ledger")),
        frozen_history.get("commit_ledger_fingerprint_sha256"),
        "live commit ledger fingerprint",
    )

    frozen_keys = _mapping(evidence, "key_path_history")
    _equal(
        _fingerprint_value(probe.get("key_path_history")),
        frozen_keys.get("key_path_inventory_fingerprint_sha256"),
        "live key-path fingerprint",
    )

    live_readme = _mapping(probe, "readme_history")
    frozen_readme = _mapping(evidence, "readme_history")
    _equal(
        _fingerprint_value(live_readme.get("revisions")),
        frozen_readme.get("revision_inventory_fingerprint_sha256"),
        "live README revision fingerprint",
    )
    _equal(
        tuple(item.get("blob_sha1") for item in live_readme.get("revisions", [])),
        tuple(frozen_readme.get("revision_blob_sha1s", [])),
        "live README blobs",
    )

    live_license = _mapping(probe, "software_license_history")
    frozen_license = _mapping(evidence, "software_license_history")
    for key in (
        "license_file_present_at_pinned_head",
        "license_file_first_seen_commit_sha1",
        "license_file_blob_sha1",
        "license_file_identifies_mit",
        "license_scope_promoted_to_external_dataset_files",
    ):
        _equal(live_license.get(key), frozen_license.get(key), f"live license field {key}")

    live_tree = _mapping(probe, "repository_tree")
    frozen_tree = _mapping(evidence, "repository_tree")
    for key in (
        "tracked_path_count",
        "distributed_process_or_label_mat_path_count",
        "repository_is_exact_compressed_dataset_copy",
    ):
        _equal(live_tree.get(key), frozen_tree.get(key), f"live tree field {key}")

    live_boundary = _mapping(probe, "scientific_boundary")
    _true(
        live_boundary.get("official_first_author_repository_history_verified"),
        "live first-author repository history verification",
    )
    for key, label in (
        ("exact_external_dataset_copy_obtained", "live exact-copy claim"),
        ("external_dataset_file_rights_resolved", "live dataset-rights claim"),
        ("software_mit_is_external_dataset_license", "live dataset-license promotion"),
        (
            "published_distribution_url_is_current_direct_copy_verified",
            "live current-copy claim",
        ),
        ("participant_identity_mapping_from_history_verified", "live participant mapping"),
        ("complete_trial_to_task_mapping_from_history_verified", "live complete task mapping"),
        ("human_human_agreement_created", "live agreement claim"),
        ("participant_disjoint_model_validation_created", "live validation claim"),
        ("frozen_evidence_performance_claim_created", "live Frozen Evidence claim"),
    ):
        _false(live_boundary.get(key), label)
    return probe


def load_gaze_in_wild_repository_history_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildRepositoryHistoryEvidence:
    """Return typed history identity only after complete validation."""

    record, path = _load(record_or_path, label="Gaze-in-the-Wild repository-history evidence")
    validated = validate_gaze_in_wild_repository_history_evidence(record)
    history = _mapping(validated, "repository_history")
    boundary = _mapping(validated, "scientific_boundary")
    return GazeInWildRepositoryHistoryEvidence(
        path=path,
        fingerprint_sha256=str(validated["evidence_fingerprint_sha256"]),
        commit_count=int(history["reachable_commit_count"]),
        repository_mit_verified_for_software=bool(
            boundary["repository_mit_license_verified_for_software"]
        ),
        exact_dataset_copy_obtained=bool(boundary["exact_external_dataset_copy_obtained"]),
        participant_identity_mapping_verified=bool(
            boundary["participant_identity_mapping_from_history_verified"]
        ),
    )
