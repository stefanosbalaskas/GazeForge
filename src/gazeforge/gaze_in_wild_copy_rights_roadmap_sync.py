"""Fail-closed GIW official Figshare copy/rights roadmap synchronization."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_figshare_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256 as RIGHTS_FINGERPRINT,
)
from .gaze_in_wild_figshare_evidence import validate_gaze_in_wild_figshare_evidence
from .gaze_in_wild_figshare_exact_bytes_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256 as EXACT_BYTES_FINGERPRINT,
)
from .gaze_in_wild_figshare_exact_bytes_evidence import (
    EXPECTED_STABLE_IDENTITY_FINGERPRINT_SHA256 as STABLE_BYTE_IDENTITY,
)
from .gaze_in_wild_figshare_exact_bytes_evidence import (
    validate_gaze_in_wild_figshare_exact_bytes_evidence,
)
from .gaze_in_wild_roadmap_sync import SYNC_FINGERPRINT as V1_SYNC_FINGERPRINT
from .gaze_in_wild_roadmap_sync import validate_gaze_in_wild_roadmap_sync

RECORD_TYPE = "gaze-in-wild-roadmap-evidence-sync-v2"
STATUS = "verified-scoped-authoritative-public-copy-and-rights-roadmap-synchronization"
EVIDENCE_FINGERPRINT = (
    "8baf35fc97e59fa691a32e3e3d190e431bd1214a851d38f1877dce6d448fa215"
)
SOURCE_MAIN_SHA = "d9715f3fe8ead1a90d41ea686f85078ccb950cda"
LICENSE_NAME = "CC BY 4.0"
DEPOSIT_AUTHOR = "Rakshit Kothari"
PROJECT_ID = 74580
PROCESSDATA_DOI = "10.6084/m9.figshare.11673645.v1"
LABELDATA_DOI = "10.6084/m9.figshare.11673696.v1"
VERIFIED_FILE_COUNT = 118
VERIFIED_TOTAL_BYTES = 2_413_299_242

BASE = Path("validation/evidence/gaze-in-wild")
V1_SYNC_PATH = BASE / "gaze-in-wild-roadmap-evidence-sync-v1.json"
RIGHTS_PATH = BASE / "gaze-in-wild-figshare-distribution-rights-evidence-v1.json"
RAW_METADATA_PATH = BASE / "gaze-in-wild-figshare-public-metadata-raw-v1.json"
SUMMARY_PATH = BASE / "gaze-in-wild-figshare-public-metadata-summary-v1.json"
EXACT_BYTES_PATH = BASE / "gaze-in-wild-figshare-exact-bytes-evidence-v1.json"

EXPECTED_ISSUE_WORDING = (
    "Obtain/audit the official Gaze-in-the-Wild Figshare ProcessData + LabelData "
    "original-publication bytes and current deposit reuse terms (CC BY 4.0); "
    "raw MAT not retained."
)
EXPECTED_CLAIM_LIMIT = (
    "This roadmap synchronization closes only the official author-bound Figshare "
    "ProcessData + LabelData original-publication copy/current deposit-rights item. "
    "It does not establish byte-for-byte equivalence to the historical RIT-hosted "
    "archive, does not promote ProcessData_cleaned, does not retain raw MAT files, "
    "does not authorize quarantine exit, and does not resolve numeric task mapping "
    "or task-stratified validation."
)
EXPECTED_SUPERSEDES = {
    "record_type": "gaze-in-wild-roadmap-evidence-sync-v1",
    "evidence_fingerprint_sha256": V1_SYNC_FINGERPRINT,
    "scope": (
        "adds official Figshare original-publication copy and current deposit-rights "
        "completion while preserving v1 rate/HHA completions"
    ),
}
EXPECTED_RIGHTS_REF = {
    "path": RIGHTS_PATH.as_posix(),
    "evidence_fingerprint_sha256": RIGHTS_FINGERPRINT,
    "figshare_project_id": PROJECT_ID,
    "deposit_author_name": DEPOSIT_AUTHOR,
    "verified_license_name": LICENSE_NAME,
    "processdata_doi": PROCESSDATA_DOI,
    "labeldata_doi": LABELDATA_DOI,
}
EXPECTED_EXACT_REF = {
    "path": EXACT_BYTES_PATH.as_posix(),
    "evidence_fingerprint_sha256": EXACT_BYTES_FINGERPRINT,
    "stable_exact_byte_identity_fingerprint_sha256": STABLE_BYTE_IDENTITY,
    "verified_article_labels": ["ProcessData", "LabelData"],
    "verified_file_count": VERIFIED_FILE_COUNT,
    "verified_total_size_bytes": VERIFIED_TOTAL_BYTES,
    "raw_dataset_bytes_retained": False,
    "processdata_cleaned_downloaded": False,
}
EXPECTED_COMPLETION = {
    (
        "official_figshare_original_publication_copy_and_current_reuse_terms_"
        "scoped_item_satisfied"
    ): True,
    "historical_rit_archive_byte_equivalence_verified": False,
    "authoritative_numeric_task_mapping_item_satisfied": False,
    "task_stratified_validation_item_satisfied": False,
}
EXPECTED_BOUNDARY = {
    "official_figshare_processdata_labeldata_exact_bytes_audited": True,
    "deposit_reuse_terms_verified": True,
    "historical_rit_archive_byte_equivalence_verified": False,
    "processdata_cleaned_promoted_to_original": False,
    "raw_dataset_bytes_retained": False,
    "quarantine_exit_authorized": False,
    "task_mapping_verified": False,
    "task_stratified_model_validation_created": False,
    "cross_dataset_validation_created": False,
    "native_60hz_validity_claim_created": False,
    "gp3_validity_claim_created": False,
    "acquisition_hardware_cadence_verified": False,
    "new_empirical_performance_claim_created": False,
}


@dataclass(frozen=True, slots=True)
class GazeInWildCopyRightsRoadmapSync:
    path: Path | None
    fingerprint_sha256: str
    official_figshare_item_satisfied: bool
    license_name: str
    verified_file_count: int
    verified_total_size_bytes: int
    raw_dataset_bytes_retained: bool
    quarantine_exit_authorized: bool


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
        raise BenchmarkIntegrityError(f"GIW copy-rights sync field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"GIW copy-rights roadmap {label} drifted.")


def _repository_root(path: Path | None, repository_root: str | Path | None) -> Path:
    if repository_root is not None:
        return Path(repository_root)
    if path is not None and len(path.parents) >= 4:
        return path.parents[3]
    return Path.cwd()


def validate_gaze_in_wild_copy_rights_roadmap_sync(
    evidence_or_path: Mapping[str, Any] | str | Path,
    *,
    repository_root: str | Path | None = None,
) -> GazeInWildCopyRightsRoadmapSync:
    """Validate the scoped official-Figshare copy/rights roadmap completion.

    This validator deliberately does not authorize historical RIT archive equivalence,
    task mapping, quarantine exit, raw-data retention, device validity, or new empirical
    performance claims.
    """

    record, path = _load(evidence_or_path, "copy-rights roadmap sync evidence")
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
    _equal(_mapping(record, "supersedes_for_roadmap_sync"), EXPECTED_SUPERSEDES, "v1 binding")

    upstream = _mapping(record, "upstream_evidence")
    _equal(
        _mapping(upstream, "figshare_distribution_rights"),
        EXPECTED_RIGHTS_REF,
        "rights reference",
    )
    _equal(
        _mapping(upstream, "figshare_exact_bytes"),
        EXPECTED_EXACT_REF,
        "exact-byte reference",
    )
    _equal(_mapping(record, "roadmap_completion"), EXPECTED_COMPLETION, "completion contract")
    _equal(_mapping(record, "scientific_boundary"), EXPECTED_BOUNDARY, "scientific boundary")
    _equal(
        _mapping(record, "issue_wording"),
        {"official_copy_and_rights": EXPECTED_ISSUE_WORDING},
        "issue wording",
    )
    _equal(record.get("claim_limit"), EXPECTED_CLAIM_LIMIT, "claim limit")

    root = _repository_root(path, repository_root)
    v1 = validate_gaze_in_wild_roadmap_sync(root / V1_SYNC_PATH)
    _equal(v1.fingerprint_sha256, V1_SYNC_FINGERPRINT, "validated v1 fingerprint")
    _equal(v1.processed_rate_file_count, 68, "preserved v1 rate count")
    _equal(v1.overlap_hha_recording_count, 5, "preserved v1 HHA recording count")
    _equal(v1.overlap_hha_pair_count, 6, "preserved v1 HHA pair count")

    rights = validate_gaze_in_wild_figshare_evidence(
        root / RIGHTS_PATH,
        root / RAW_METADATA_PATH,
        root / SUMMARY_PATH,
    )
    _equal(rights.fingerprint_sha256, RIGHTS_FINGERPRINT, "validated rights fingerprint")
    _equal(rights.deposit_rights_resolved, True, "deposit-rights resolution")
    _equal(rights.analysis_use_permitted, True, "analysis permission")
    _equal(rights.redistribution_permitted, True, "redistribution permission")
    _equal(rights.quarantine_exit_authorized, False, "rights quarantine boundary")

    exact = validate_gaze_in_wild_figshare_exact_bytes_evidence(
        root / EXACT_BYTES_PATH,
        root / RAW_METADATA_PATH,
        root / RIGHTS_PATH,
        root / SUMMARY_PATH,
    )
    _equal(exact.fingerprint_sha256, EXACT_BYTES_FINGERPRINT, "validated exact-byte fingerprint")
    _equal(exact.exact_original_distribution_bytes_verified, True, "exact-byte verification")
    _equal(exact.verified_file_count, VERIFIED_FILE_COUNT, "validated file count")
    _equal(exact.verified_total_size_bytes, VERIFIED_TOTAL_BYTES, "validated total bytes")
    _equal(exact.raw_dataset_bytes_retained, False, "raw-data retention boundary")
    _equal(exact.quarantine_exit_authorized, False, "exact-byte quarantine boundary")

    rights_record, _ = _load(root / RIGHTS_PATH, "rights evidence")
    _equal(
        _mapping(rights_record, "source_binding").get("deposit_author_name"),
        DEPOSIT_AUTHOR,
        "deposit author",
    )
    deposits = _mapping(rights_record, "deposits")
    _equal(_mapping(deposits, "ProcessData").get("doi"), PROCESSDATA_DOI, "ProcessData DOI")
    _equal(_mapping(deposits, "LabelData").get("doi"), LABELDATA_DOI, "LabelData DOI")
    _equal(
        _mapping(deposits, "ProcessData").get("license_name"),
        LICENSE_NAME,
        "ProcessData licence",
    )
    _equal(_mapping(deposits, "LabelData").get("license_name"), LICENSE_NAME, "LabelData licence")
    cleaned = _mapping(deposits, "ProcessData_cleaned")
    _equal(
        cleaned.get("is_original_publication_processed_distribution"),
        False,
        "cleaned-data status",
    )

    exact_record, _ = _load(root / EXACT_BYTES_PATH, "exact-byte evidence")
    verified = _mapping(exact_record, "verified_distribution")
    _equal(
        verified.get("stable_exact_byte_identity_fingerprint_sha256"),
        STABLE_BYTE_IDENTITY,
        "stable exact-byte identity",
    )
    _equal(verified.get("article_labels"), ["ProcessData", "LabelData"], "verified labels")
    _equal(verified.get("raw_dataset_bytes_retained"), False, "verified raw retention")
    _equal(
        _mapping(exact_record, "excluded_distribution").get("downloaded"),
        False,
        "ProcessData_cleaned exclusion",
    )

    return GazeInWildCopyRightsRoadmapSync(
        path=path,
        fingerprint_sha256=EVIDENCE_FINGERPRINT,
        official_figshare_item_satisfied=True,
        license_name=LICENSE_NAME,
        verified_file_count=VERIFIED_FILE_COUNT,
        verified_total_size_bytes=VERIFIED_TOTAL_BYTES,
        raw_dataset_bytes_retained=False,
        quarantine_exit_authorized=False,
    )
