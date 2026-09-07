"""Fail-closed validation for reviewed Gaze-in-the-Wild exact Figshare bytes."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_figshare_evidence import validate_gaze_in_wild_figshare_evidence

RECORD_TYPE = "gaze-in-wild-figshare-exact-bytes-evidence-v1"
STATUS = "exact_original_publication_processdata_and_labeldata_bytes_verified"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "dbf277d698266fe53e337a15fc342e9af1835460d2bcc69c3992635de8fa0a00"
)
EXPECTED_DISCOVERY_PROBE_FINGERPRINT_SHA256 = (
    "96645a517bb5aec84aec1920683625c9a5ca47f609afd8fd9725fb9b77f8bb3d"
)
EXPECTED_STABLE_IDENTITY_FINGERPRINT_SHA256 = (
    "8d36884daf76e26ded3d31c32bd334bf8f358b49efdb7accbb20c6c569abdda0"
)
EXPECTED_PROCESSDATA_STABLE_MANIFEST_SHA256 = (
    "7e48396fcfe30e2170708c9d5910caea785ceff1dd06b0455e5715a01e52d3ea"
)
EXPECTED_LABELDATA_STABLE_MANIFEST_SHA256 = (
    "9ffbbab106bbd6f5a6ac8d7dd1e666ab70f3df486a1057b4ff690c82fae2a1ec"
)
EXPECTED_ARTIFACT_ZIP_SHA256 = (
    "123f705f79aa5de261d73a8b1347646a681c3a45dca509933c9aa72d2bc96798"
)
EXPECTED_LIVE_METADATA_FINGERPRINT_SHA256 = (
    "2fc9b441f90dae01e1ef41918d61924458f7cd0e0556021db3daa3a6732251f4"
)
EXPECTED_RAW_METADATA_FINGERPRINT_SHA256 = (
    "5df3f539b1d28adfcd4b4e26392622654612e5acdb3415ffe911d3acedda50b5"
)
EXPECTED_RIGHTS_EVIDENCE_FINGERPRINT_SHA256 = (
    "25d4b56e1dc4888b034b5de91cb14f712aaa0e3470cde7a1246f30c3880e63c7"
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class GazeInWildExactBytesEvidence:
    path: Path | None
    fingerprint_sha256: str
    exact_original_distribution_bytes_verified: bool
    verified_file_count: int
    verified_total_size_bytes: int
    raw_dataset_bytes_retained: bool
    quarantine_exit_authorized: bool


@dataclass(frozen=True, slots=True)
class GazeInWildFreshByteIdentity:
    stable_identity_fingerprint_sha256: str
    processdata_manifest_sha256: str
    labeldata_manifest_sha256: str
    verified_file_count: int
    verified_total_size_bytes: int


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


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
        raise BenchmarkIntegrityError(f"Could not load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"{label} must contain one JSON object.")
    return payload, path


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"GIW exact-byte field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"GIW exact-byte {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"GIW exact-byte must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"GIW exact-byte must not promote {label}.")


def _validate_boundaries(record: Mapping[str, Any]) -> None:
    boundary = _mapping(record, "scientific_boundary")
    _true(boundary.get("exact_original_distribution_bytes_verified"), "exact-byte verification")
    for key in (
        "universal_tridx_to_task_mapping_verified",
        "complete_file_to_task_mapping_verified",
        "participant_disjoint_model_validation_created",
        "human_human_agreement_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "quarantine_exit_authorized",
        "new_empirical_performance_claim_created",
    ):
        _false(boundary.get(key), key)


def validate_gaze_in_wild_figshare_exact_bytes_evidence(
    evidence_or_path: Mapping[str, Any] | str | Path,
    raw_or_path: Mapping[str, Any] | str | Path,
    rights_evidence_or_path: Mapping[str, Any] | str | Path,
    summary_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildExactBytesEvidence:
    """Validate the immutable reviewed exact-byte result and its parent evidence."""

    record, path = _load(evidence_or_path, "GIW exact-byte reviewed evidence")
    rights = validate_gaze_in_wild_figshare_evidence(
        rights_evidence_or_path,
        raw_or_path,
        summary_or_path,
    )
    _true(rights.deposit_rights_resolved, "parent distribution-rights resolution")
    _true(rights.analysis_use_permitted, "parent analysis permission")

    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("reviewed_on"), "2026-09-08", "review date")
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

    binding = _mapping(record, "source_binding")
    _equal(binding.get("figshare_project_id"), 74580, "Figshare project id")
    _equal(
        binding.get("frozen_public_metadata_probe_fingerprint_sha256"),
        EXPECTED_RAW_METADATA_FINGERPRINT_SHA256,
        "frozen metadata binding",
    )
    _equal(
        binding.get("reviewed_distribution_rights_evidence_fingerprint_sha256"),
        EXPECTED_RIGHTS_EVIDENCE_FINGERPRINT_SHA256,
        "rights evidence binding",
    )
    _equal(
        binding.get("fresh_live_metadata_stable_fingerprint_sha256"),
        EXPECTED_LIVE_METADATA_FINGERPRINT_SHA256,
        "fresh metadata binding",
    )
    _equal(binding.get("workflow_run_id"), 34164582679, "workflow run id")
    _equal(binding.get("workflow_job_id"), 101872991996, "workflow job id")
    _equal(
        binding.get("workflow_head_sha"),
        "39ec2546065250c1aee29631a0ad5abe0366541e",
        "workflow head sha",
    )
    _equal(binding.get("artifact_id"), 10033806821, "artifact id")
    _equal(
        binding.get("artifact_zip_sha256"),
        EXPECTED_ARTIFACT_ZIP_SHA256,
        "artifact ZIP digest",
    )
    _equal(
        binding.get("exact_byte_probe_fingerprint_sha256"),
        EXPECTED_DISCOVERY_PROBE_FINGERPRINT_SHA256,
        "discovery probe binding",
    )

    verified = _mapping(record, "verified_distribution")
    _equal(verified.get("article_labels"), ["ProcessData", "LabelData"], "article labels")
    _equal(verified.get("file_count"), 118, "file count")
    _equal(verified.get("total_size_bytes"), 2_413_299_242, "total bytes")
    _true(verified.get("all_files_matched_frozen_size_and_md5"), "frozen size/MD5 checks")
    _true(verified.get("all_downloads_succeeded_on_first_attempt"), "discovery transport result")
    _false(verified.get("raw_dataset_bytes_retained"), "raw-byte retention")
    _equal(
        verified.get("stable_exact_byte_identity_fingerprint_sha256"),
        EXPECTED_STABLE_IDENTITY_FINGERPRINT_SHA256,
        "stable exact-byte identity",
    )

    expected = {
        "ProcessData": (
            11673645,
            "10.6084/m9.figshare.11673645.v1",
            68,
            2_384_573_418,
            "cc82a05fa64d35f76f955ebe231c27ff858d9d53de714ffa92d9d9c21828aaa8",
            EXPECTED_PROCESSDATA_STABLE_MANIFEST_SHA256,
            "b1a252480e75ff322e40fc8182af2a2b845e267d0c5bf99fd4801fbbc73b7004",
            13,
            "all_files_have_processdata_struct_1x1",
        ),
        "LabelData": (
            11673696,
            "10.6084/m9.figshare.11673696.v1",
            50,
            28_725_824,
            "65d934d3d3e2ebb04e639fc16435bf3383882340996a211159c5ccb67c71b35d",
            EXPECTED_LABELDATA_STABLE_MANIFEST_SHA256,
            "72fb67dab5085043c4dab079327354f5ddf9c8a4ec490d546688a8d7b9a3f2d2",
            1,
            "all_files_have_labeldata_struct_1x1",
        ),
    }
    for label, values in expected.items():
        section = _mapping(verified, label)
        article_id, doi, count, total, frozen_manifest, stable_manifest, discovery_manifest, schemas, struct_key = values
        _equal(section.get("figshare_id"), article_id, f"{label} article id")
        _equal(section.get("doi"), doi, f"{label} DOI")
        _equal(section.get("file_count"), count, f"{label} file count")
        _equal(section.get("total_size_bytes"), total, f"{label} total bytes")
        _equal(section.get("frozen_manifest_sha256"), frozen_manifest, f"{label} frozen manifest")
        _equal(section.get("stable_file_identity_manifest_sha256"), stable_manifest, f"{label} stable manifest")
        _equal(section.get("verified_file_identity_manifest_sha256"), discovery_manifest, f"{label} discovery manifest")
        _equal(section.get("matlab_format"), "matlab-level-5-compatible", f"{label} MATLAB format")
        _equal(section.get("distinct_container_schema_count"), schemas, f"{label} schema count")
        _true(section.get(struct_key), f"{label} primary struct")

    excluded = _mapping(record, "excluded_distribution")
    _equal(excluded.get("label"), "ProcessData_cleaned", "excluded label")
    _equal(excluded.get("figshare_id"), 11673717, "excluded article id")
    _equal(excluded.get("doi"), "10.6084/m9.figshare.11673717.v1", "excluded DOI")
    _false(excluded.get("downloaded"), "cleaned data download")
    _validate_boundaries(record)

    return GazeInWildExactBytesEvidence(
        path=path,
        fingerprint_sha256=EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        exact_original_distribution_bytes_verified=True,
        verified_file_count=118,
        verified_total_size_bytes=2_413_299_242,
        raw_dataset_bytes_retained=False,
        quarantine_exit_authorized=False,
    )


def validate_fresh_gaze_in_wild_exact_byte_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    raw_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildFreshByteIdentity:
    """Validate a fresh full-byte run against frozen metadata and reviewed identities."""

    probe, _ = _load(probe_or_path, "GIW fresh exact-byte probe")
    raw, _ = _load(raw_or_path, "GIW frozen raw metadata")
    _equal(probe.get("record_type"), "gaze-in-wild-figshare-exact-bytes-probe-v1", "fresh probe type")
    _equal(probe.get("verified_article_labels"), ["ProcessData", "LabelData"], "fresh probe labels")
    _equal(probe.get("verified_file_count"), 118, "fresh file count")
    _equal(probe.get("verified_total_size_bytes"), 2_413_299_242, "fresh total bytes")
    _true(probe.get("exact_original_distribution_bytes_verified"), "fresh exact-byte verification")
    _false(probe.get("raw_dataset_bytes_retained"), "fresh raw-byte retention")

    raw_items = raw.get("items")
    if not isinstance(raw_items, list):
        raise BenchmarkIntegrityError("GIW frozen raw metadata items are missing.")
    raw_by_label = {
        str(item.get("label")): item
        for item in raw_items
        if isinstance(item, Mapping)
    }
    verified_items = probe.get("verified_items")
    if not isinstance(verified_items, list) or [item.get("label") for item in verified_items] != [
        "ProcessData",
        "LabelData",
    ]:
        raise BenchmarkIntegrityError("GIW fresh exact-byte item ordering drifted.")

    expanded_items: list[dict[str, Any]] = []
    article_manifests: dict[str, str] = {}
    for item in verified_items:
        if not isinstance(item, Mapping):
            raise BenchmarkIntegrityError("GIW fresh exact-byte item is invalid.")
        label = str(item.get("label"))
        frozen_item = raw_by_label[label]
        fresh_files = item.get("files")
        frozen_files = frozen_item.get("files")
        if not isinstance(fresh_files, list) or not isinstance(frozen_files, list):
            raise BenchmarkIntegrityError(f"GIW fresh exact-byte {label} file manifest is missing.")
        _equal(len(fresh_files), len(frozen_files), f"fresh {label} file count")
        frozen_by_id = {
            int(row["id"]): row
            for row in frozen_files
            if isinstance(row, Mapping)
        }
        stable_rows = []
        schemas: set[bytes] = set()
        for row in fresh_files:
            if not isinstance(row, Mapping):
                raise BenchmarkIntegrityError(f"GIW fresh exact-byte {label} file row is invalid.")
            file_id = int(row.get("figshare_file_id", -1))
            if file_id not in frozen_by_id:
                raise BenchmarkIntegrityError(f"GIW fresh exact-byte {label} file id drifted.")
            frozen_row = frozen_by_id[file_id]
            _equal(row.get("name"), frozen_row.get("name"), f"fresh {label} filename")
            _equal(row.get("size_bytes"), frozen_row.get("size"), f"fresh {label} size")
            _equal(row.get("md5"), frozen_row.get("supplied_md5"), f"fresh {label} MD5")
            if HEX64.fullmatch(str(row.get("sha256", ""))) is None:
                raise BenchmarkIntegrityError(f"GIW fresh exact-byte {label} SHA-256 is invalid.")
            _false(row.get("raw_bytes_retained"), f"fresh {label} raw-byte retention")
            schema = row.get("mat_schema")
            if not isinstance(schema, Mapping):
                raise BenchmarkIntegrityError(f"GIW fresh exact-byte {label} schema is missing.")
            _equal(schema.get("format"), "matlab-level-5-compatible", f"fresh {label} MATLAB format")
            variables = schema.get("variables")
            if not isinstance(variables, list):
                raise BenchmarkIntegrityError(f"GIW fresh exact-byte {label} variables are missing.")
            primary = "ProcessData" if label == "ProcessData" else "LabelData"
            if not variables or variables[0] != {"class": "struct", "name": primary, "shape": [1, 1]}:
                raise BenchmarkIntegrityError(f"GIW fresh exact-byte {label} primary struct drifted.")
            schemas.add(_canonical_bytes(schema))
            stable_rows.append(
                {
                    "figshare_file_id": row.get("figshare_file_id"),
                    "name": row.get("name"),
                    "size_bytes": row.get("size_bytes"),
                    "md5": row.get("md5"),
                    "sha256": row.get("sha256"),
                    "mat_schema": row.get("mat_schema"),
                    "raw_bytes_retained": row.get("raw_bytes_retained"),
                }
            )
        expected_schemas = 13 if label == "ProcessData" else 1
        _equal(len(schemas), expected_schemas, f"fresh {label} schema count")
        article_manifest = hashlib.sha256(_canonical_bytes(stable_rows)).hexdigest()
        article_manifests[label] = article_manifest
        expanded_items.append(
            {
                "label": item.get("label"),
                "article_id": item.get("article_id"),
                "doi": item.get("doi"),
                "file_count": item.get("file_count"),
                "total_size_bytes": item.get("total_size_bytes"),
                "files": stable_rows,
            }
        )

    _equal(
        article_manifests["ProcessData"],
        EXPECTED_PROCESSDATA_STABLE_MANIFEST_SHA256,
        "fresh ProcessData stable manifest",
    )
    _equal(
        article_manifests["LabelData"],
        EXPECTED_LABELDATA_STABLE_MANIFEST_SHA256,
        "fresh LabelData stable manifest",
    )
    stable = hashlib.sha256(_canonical_bytes(expanded_items)).hexdigest()
    _equal(stable, EXPECTED_STABLE_IDENTITY_FINGERPRINT_SHA256, "fresh stable identity")

    excluded = _mapping(probe, "excluded_cleaned_deposit")
    _equal(excluded.get("label"), "ProcessData_cleaned", "fresh excluded label")
    _false(excluded.get("downloaded"), "fresh cleaned data download")
    boundary = _mapping(probe, "scientific_boundary")
    for key in (
        "universal_tridx_to_task_mapping_verified",
        "complete_file_to_task_mapping_verified",
        "participant_disjoint_model_validation_created",
        "human_human_agreement_created",
        "cross_dataset_validation_created",
        "gp3_validity_claim_created",
        "quarantine_exit_authorized",
        "new_empirical_performance_claim_created",
    ):
        _false(boundary.get(key), f"fresh {key}")

    return GazeInWildFreshByteIdentity(
        stable_identity_fingerprint_sha256=stable,
        processdata_manifest_sha256=article_manifests["ProcessData"],
        labeldata_manifest_sha256=article_manifests["LabelData"],
        verified_file_count=118,
        verified_total_size_bytes=2_413_299_242,
    )
