"""Fail-closed validation for Gaze-in-the-Wild Figshare distribution/rights evidence."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "gaze-in-wild-figshare-distribution-rights-evidence-v1"
STATUS = "official_figshare_distribution_and_cc_by_4_0_terms_verified_bytes_not_acquired"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "25d4b56e1dc4888b034b5de91cb14f712aaa0e3470cde7a1246f30c3880e63c7"
)
EXPECTED_RAW_PROBE_FINGERPRINT_SHA256 = (
    "5df3f539b1d28adfcd4b4e26392622654612e5acdb3415ffe911d3acedda50b5"
)
EXPECTED_SUMMARY_FINGERPRINT_SHA256 = (
    "32b14b0daf4d73204fc52b1da2205d634097a934c51746798b4c2205e620389d"
)
LICENSE_NAME = "CC BY 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
PROJECT_ID = 74580
PROJECT_IDS = [11673645, 11673696, 11673717]
MD5_RE = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True, slots=True)
class GazeInWildFigshareEvidence:
    path: Path | None
    fingerprint_sha256: str
    deposit_rights_resolved: bool
    analysis_use_permitted: bool
    redistribution_permitted: bool
    exact_file_bytes_verified: bool
    quarantine_exit_authorized: bool


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _record_fingerprint(record: Mapping[str, Any], stored_key: str) -> str:
    body = dict(record)
    body.pop(stored_key, None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(
    value: Mapping[str, Any] | str | Path, label: str
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


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"GIW Figshare field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"GIW Figshare {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"GIW Figshare must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"GIW Figshare must not promote {label}.")


def _manifest_sha(files: list[Mapping[str, Any]]) -> str:
    return hashlib.sha256(_canonical_bytes(files)).hexdigest()


def _validate_raw(raw: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    _equal(
        raw.get("record_type"),
        "gaze-in-wild-figshare-exploratory-metadata-v2",
        "raw record type",
    )
    _equal(raw.get("project_id"), PROJECT_ID, "raw project id")
    _equal(
        raw.get("probe_scope"),
        "public_metadata_only_no_dataset_file_downloads",
        "raw probe scope",
    )
    _equal(
        raw.get("probe_fingerprint_sha256"),
        EXPECTED_RAW_PROBE_FINGERPRINT_SHA256,
        "stored raw fingerprint",
    )
    _equal(
        _record_fingerprint(raw, "probe_fingerprint_sha256"),
        EXPECTED_RAW_PROBE_FINGERPRINT_SHA256,
        "recomputed raw fingerprint",
    )
    articles = raw.get("project_articles")
    if not isinstance(articles, list):
        raise BenchmarkIntegrityError("GIW Figshare project article list is missing.")
    _equal([row.get("id") for row in articles], PROJECT_IDS, "project article ids")

    items = raw.get("items")
    if not isinstance(items, list) or len(items) != 3:
        raise BenchmarkIntegrityError(
            "GIW Figshare raw probe must contain exactly three items."
        )
    by_label: dict[str, Mapping[str, Any]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            raise BenchmarkIntegrityError("GIW Figshare raw item is invalid.")
        label = str(item.get("label"))
        by_label[label] = item
        _equal(item.get("defined_type_name"), "dataset", f"{label} type")
        _equal(item.get("version"), 1, f"{label} version")
        authors = item.get("authors")
        if not isinstance(authors, list) or [
            author.get("full_name") for author in authors
        ] != ["Rakshit Kothari"]:
            raise BenchmarkIntegrityError(
                f"GIW Figshare {label} author identity drifted."
            )
        license_value = item.get("license")
        if not isinstance(license_value, Mapping):
            raise BenchmarkIntegrityError(f"GIW Figshare {label} license is missing.")
        _equal(license_value.get("name"), LICENSE_NAME, f"{label} license name")
        _equal(license_value.get("url"), LICENSE_URL, f"{label} license URL")
        files = item.get("files")
        if not isinstance(files, list):
            raise BenchmarkIntegrityError(f"GIW Figshare {label} manifest is missing.")
        _equal(len(files), item.get("file_count"), f"{label} file count")
        _equal(
            sum(int(row.get("size") or 0) for row in files),
            item.get("total_size_bytes"),
            f"{label} total bytes",
        )
        _equal(
            _manifest_sha(files),
            item.get("manifest_sha256"),
            f"{label} manifest fingerprint",
        )
        for row in files:
            if not isinstance(row, Mapping):
                raise BenchmarkIntegrityError(
                    f"GIW Figshare {label} file row is invalid."
                )
            if not str(row.get("name", "")).endswith(".mat"):
                raise BenchmarkIntegrityError(
                    f"GIW Figshare {label} contains a non-MAT file."
                )
            _false(row.get("is_link_only"), f"{label} link-only file")
            supplied = str(row.get("supplied_md5", ""))
            computed = str(row.get("computed_md5", ""))
            if MD5_RE.fullmatch(supplied) is None or supplied != computed:
                raise BenchmarkIntegrityError(
                    f"GIW Figshare {label} MD5 metadata is invalid."
                )
    _equal(
        sorted(by_label),
        ["LabelData", "ProcessData", "ProcessData_cleaned"],
        "raw item labels",
    )
    return by_label


def _validate_summary(summary: Mapping[str, Any]) -> None:
    _equal(
        summary.get("record_type"),
        "gaze-in-wild-figshare-exploratory-summary-v2",
        "summary record type",
    )
    _equal(
        summary.get("source_probe_fingerprint_sha256"),
        EXPECTED_RAW_PROBE_FINGERPRINT_SHA256,
        "summary source binding",
    )
    _equal(
        summary.get("summary_fingerprint_sha256"),
        EXPECTED_SUMMARY_FINGERPRINT_SHA256,
        "stored summary fingerprint",
    )
    _equal(
        _record_fingerprint(summary, "summary_fingerprint_sha256"),
        EXPECTED_SUMMARY_FINGERPRINT_SHA256,
        "recomputed summary fingerprint",
    )
    _equal(summary.get("project_id"), PROJECT_ID, "summary project id")
    _equal(
        summary.get("project_article_ids"),
        PROJECT_IDS,
        "summary project article ids",
    )
    structure = _mapping(summary, "derived_manifest_structure")
    _equal(
        structure.get("processdata_participant_ids"),
        [1, 2, 3, 4, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23],
        "ProcessData participant ids",
    )
    _equal(
        structure.get("processdata_tridx_values"),
        [1, 2, 3, 4],
        "ProcessData TrIdx values",
    )
    _true(
        structure.get("processdata_cleaned_filename_set_equal"),
        "cleaned filename equality",
    )
    _equal(
        structure.get("labeldata_participant_trial_cell_count"),
        37,
        "LabelData cell count",
    )
    _equal(
        structure.get("labeldata_labrater_ids"),
        [1, 2, 3, 5, 6],
        "LabelData labeller ids",
    )
    _equal(
        structure.get("labeldata_multiple_labeller_cells"),
        [
            {"PrIdx": 1, "TrIdx": 1, "labellers": [1, 2, 5, 6]},
            {"PrIdx": 1, "TrIdx": 2, "labellers": [1, 2, 5, 6]},
            {"PrIdx": 2, "TrIdx": 1, "labellers": [1, 2, 5, 6]},
            {"PrIdx": 2, "TrIdx": 2, "labellers": [1, 2, 5, 6]},
            {"PrIdx": 6, "TrIdx": 2, "labellers": [5, 6]},
        ],
        "multiple-labeller cells",
    )


def validate_gaze_in_wild_figshare_evidence(
    evidence_or_path: Mapping[str, Any] | str | Path,
    raw_or_path: Mapping[str, Any] | str | Path,
    summary_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildFigshareEvidence:
    """Validate reviewed deposit rights plus frozen public metadata manifests."""

    record, path = _load(evidence_or_path, "GIW Figshare reviewed evidence")
    raw, _ = _load(raw_or_path, "GIW Figshare frozen raw metadata")
    summary, _ = _load(summary_or_path, "GIW Figshare frozen summary")

    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("checked_on"), "2026-09-07", "review date")
    _equal(
        record.get("evidence_fingerprint_sha256"),
        EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        "stored evidence fingerprint",
    )
    _equal(
        evidence_fingerprint(record),
        EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        "recomputed evidence fingerprint",
    )

    by_label = _validate_raw(raw)
    _validate_summary(summary)
    binding = _mapping(record, "source_binding")
    _equal(
        binding.get("live_metadata_probe_fingerprint_sha256"),
        EXPECTED_RAW_PROBE_FINGERPRINT_SHA256,
        "raw binding",
    )
    _equal(
        binding.get("live_metadata_summary_fingerprint_sha256"),
        EXPECTED_SUMMARY_FINGERPRINT_SHA256,
        "summary binding",
    )
    _equal(
        binding.get("project_exact_article_ids"),
        PROJECT_IDS,
        "project binding",
    )

    expected = {
        "ProcessData": (
            11673645,
            "10.6084/m9.figshare.11673645.v1",
            68,
            2384573418,
            "cc82a05fa64d35f76f955ebe231c27ff858d9d53de714ffa92d9d9c21828aaa8",
        ),
        "ProcessData_cleaned": (
            11673717,
            "10.6084/m9.figshare.11673717.v1",
            68,
            2309276802,
            "eda07ca38dfd6b8313b3240c169b274453586c5cdc94f44ca08d83adf19e4d3b",
        ),
        "LabelData": (
            11673696,
            "10.6084/m9.figshare.11673696.v1",
            50,
            28725824,
            "65d934d3d3e2ebb04e639fc16435bf3383882340996a211159c5ccb67c71b35d",
        ),
    }
    deposits = _mapping(record, "deposits")
    for label, values in expected.items():
        reviewed = _mapping(deposits, label)
        live = by_label[label]
        figshare_id, doi, count, total, manifest = values
        checks = (
            (reviewed.get("figshare_id"), figshare_id, "id"),
            (reviewed.get("doi"), doi, "DOI"),
            (reviewed.get("file_count"), count, "file count"),
            (reviewed.get("total_size_bytes"), total, "total bytes"),
            (reviewed.get("manifest_sha256"), manifest, "manifest"),
            (reviewed.get("license_name"), LICENSE_NAME, "license name"),
            (reviewed.get("license_url"), LICENSE_URL, "license URL"),
            (live.get("id"), figshare_id, "raw id"),
            (live.get("doi"), doi, "raw DOI"),
            (live.get("manifest_sha256"), manifest, "raw manifest"),
        )
        for actual, wanted, name in checks:
            _equal(actual, wanted, f"{label} {name}")

    cleaned = _mapping(deposits, "ProcessData_cleaned")
    _false(
        cleaned.get("is_original_publication_processed_distribution"),
        "cleaned data as original",
    )
    _true(
        cleaned.get(
            "publisher_description_explicitly_says_not_published_as_part_of_original_publication"
        ),
        "cleaned/original distinction",
    )

    structure = _mapping(record, "manifest_structure")
    _equal(
        structure.get("processdata_participant_count"),
        20,
        "reviewed ProcessData participant count",
    )
    _equal(
        structure.get("publication_participant_count"),
        19,
        "publication participant count",
    )
    _true(
        structure.get("distribution_contains_pridx_4_absent_from_publication_matrix"),
        "PrIdx_4 mismatch",
    )
    _false(
        structure.get("published_participant_to_distribution_mapping_complete"),
        "complete participant mapping",
    )
    _false(
        structure.get("universal_tridx_to_task_name_mapping_verified"),
        "universal TrIdx task mapping",
    )
    _true(
        structure.get("separate_labeller_specific_files_verified_in_official_manifest"),
        "separate labeller-file manifest",
    )
    _false(
        structure.get("independent_labeller_file_contents_obtained"),
        "labeller file contents",
    )

    rights = _mapping(record, "rights_boundary")
    for key in (
        "deposit_reuse_terms_verified",
        "analysis_use_permitted_by_deposit_license",
        "redistribution_permitted_by_deposit_license",
        "adaptation_permitted_by_deposit_license",
        "attribution_required",
        "license_is_not_blanket_adjudication_of_privacy_publicity_moral_or_other_rights",
    ):
        _true(rights.get(key), key)
    _equal(rights.get("verified_license_name"), LICENSE_NAME, "reviewed license")
    _equal(rights.get("license_terms_source"), LICENSE_URL, "license terms source")
    _false(
        rights.get("license_inference_from_article_or_software_license_used"),
        "license inference",
    )

    boundary = _mapping(record, "scientific_boundary")
    for key in (
        "official_figshare_distribution_identity_verified",
        "official_distribution_manifest_metadata_verified",
        "dataset_file_rights_resolved_for_named_figshare_deposits",
        "analysis_use_permitted_by_named_deposit_license",
        "redistribution_permitted_by_named_deposit_license",
    ):
        _true(boundary.get(key), key)
    for key in (
        "current_exact_authoritative_files_downloaded",
        "exact_file_bytes_verified_against_manifest",
        "quarantine_exit_authorized",
        "source_audit_ready",
        "published_participant_mapping_complete",
        "complete_trial_to_task_mapping_verified",
        "independent_labeller_stream_contents_recovered",
        "human_human_agreement_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_performance_created",
        "gp3_validity_created",
        "empirical_evidence_created",
    ):
        _false(boundary.get(key), key)

    return GazeInWildFigshareEvidence(
        path=path,
        fingerprint_sha256=EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        deposit_rights_resolved=True,
        analysis_use_permitted=True,
        redistribution_permitted=True,
        exact_file_bytes_verified=False,
        quarantine_exit_authorized=False,
    )
