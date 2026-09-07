"""Immutable evidence for Gaze-in-the-Wild point-of-regard semantics."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "gaze-in-wild-por-coordinate-semantics-evidence-v1"
STATUS = "verified-first-party-normalized-por-semantics"
EVIDENCE_FINGERPRINT = (
    "5eb245979385283571d6d9a5dda9a5d74dea6c00165bbe3a2587fcfa80e9adfb"
)
SOURCE_REPOSITORY = "https://github.com/RSKothari/Gaze-in-Wild"
SOURCE_COMMIT = "52262d44e366a53369e10ca73c5f41daf0e8f1e5"
SOURCE_PATH = "DataExtraction/ReadData_function.m"
SOURCE_BLOB = "36d81839fb9f9eadb1274b998d2a8652fb0840ca"
LIVE_RECORD_TYPE = "gaze-in-wild-por-coordinate-live-probe-v1"

_REQUIRED_SOURCE_MARKERS = (
    "ETG.SceneResolution = [1920, 1080];",
    "ETG.POR = [Gaze_Data.norm_pos_x, Gaze_Data.norm_pos_y];",
    "ETG.POR(:, 2) = 1 - ETG.POR(:, 2);",
    "[ETG.POR, ~] = linearizeData(ETG_T, ETG.POR, 'pchip');",
    "ProcessData.ETG.SceneResolution = ETG.SceneResolution;",
    (
        "ProcessData.ETG.POR = interp1(ETG.T, ETG.POR, ProcessData.T, "
        "'pchip', 'extrap');"
    ),
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Fingerprint immutable evidence without its stored digest."""
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def probe_fingerprint(record: Mapping[str, Any]) -> str:
    """Fingerprint a metadata-only live source probe."""
    body = dict(record)
    body.pop("probe_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    """Return the Git blob SHA-1 for exact bytes."""
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload).hexdigest()  # noqa: S324


def _load_record(record_or_path: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path)
    return json.loads(Path(record_or_path).read_text(encoding="utf-8"))


def _require_false(mapping: Mapping[str, Any], *keys: str) -> None:
    for key in keys:
        if mapping.get(key) is not False:
            raise BenchmarkIntegrityError(
                f"Gaze-in-the-Wild coordinate boundary {key!r} must be false."
            )


def _normalized_source(source_text: str) -> str:
    return re.sub(r"\s+", " ", str(source_text)).strip()


def validate_first_party_por_source(source_text: str) -> dict[str, int]:
    """Require the reviewed first-party normalized-POR processing statements."""
    normalized = _normalized_source(source_text)
    missing = [
        marker
        for marker in _REQUIRED_SOURCE_MARKERS
        if _normalized_source(marker) not in normalized
    ]
    if missing:
        raise BenchmarkIntegrityError(
            f"Gaze-in-the-Wild POR source markers are missing: {missing}."
        )

    process_por_count = normalized.count("ProcessData.ETG.POR")
    if process_por_count != 1:
        raise BenchmarkIntegrityError(
            "ProcessData.ETG.POR must have exactly one reviewed first-party assignment."
        )
    return {
        "required_marker_count": len(_REQUIRED_SOURCE_MARKERS),
        "processdata_etg_por_occurrence_count": process_por_count,
    }


def validate_gaze_in_wild_por_coordinate_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the immutable first-party coordinate-semantics evidence."""
    record = _load_record(record_or_path)
    if record.get("record_type") != RECORD_TYPE or record.get("status") != STATUS:
        raise BenchmarkIntegrityError(
            "Unexpected Gaze-in-the-Wild coordinate evidence identity/status."
        )
    if record.get("evidence_fingerprint_sha256") != EVIDENCE_FINGERPRINT:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild coordinate evidence stored fingerprint drifted."
        )
    if evidence_fingerprint(record) != EVIDENCE_FINGERPRINT:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild coordinate evidence content fingerprint drifted."
        )

    source = record.get("canonical_source", {})
    if source.get("repository") != SOURCE_REPOSITORY:
        raise BenchmarkIntegrityError("Gaze-in-the-Wild source repository drifted.")
    if source.get("commit_sha1") != SOURCE_COMMIT:
        raise BenchmarkIntegrityError("Gaze-in-the-Wild source commit drifted.")
    if source.get("path") != SOURCE_PATH or source.get("git_blob_sha1") != SOURCE_BLOB:
        raise BenchmarkIntegrityError("Gaze-in-the-Wild source file/blob drifted.")

    semantics = record.get("reviewed_source_semantics", {})
    if semantics.get("pupil_source_fields") != ["norm_pos_x", "norm_pos_y"]:
        raise BenchmarkIntegrityError("Gaze-in-the-Wild normalized POR fields drifted.")
    if semantics.get("scene_resolution_px") != [1920, 1080]:
        raise BenchmarkIntegrityError("Gaze-in-the-Wild scene resolution drifted.")
    if semantics.get("scene_resolution_stored_separately") is not True:
        raise BenchmarkIntegrityError("Scene resolution must remain separate from POR.")
    if semantics.get("processdata_por_is_interpolated_from_etg_por") is not True:
        raise BenchmarkIntegrityError("ProcessData POR lineage drifted.")
    if semantics.get("por_multiplied_by_scene_resolution_in_first_party_preprocessing") is not False:
        raise BenchmarkIntegrityError("First-party POR must not be promoted to pixel POR.")

    verification = record.get("verification", {})
    if verification.get("processdata_por_coordinate_semantics_verified") is not True:
        raise BenchmarkIntegrityError("ProcessData POR semantics are not verified.")
    if verification.get("processdata_por_coordinate_space") != "normalized_scene_image":
        raise BenchmarkIntegrityError("ProcessData POR coordinate space drifted.")
    if verification.get("scene_resolution_metadata_unit") != "pixels":
        raise BenchmarkIntegrityError("Scene-resolution metadata unit drifted.")
    if verification.get("first_party_pixel_por_claim") is not False:
        raise BenchmarkIntegrityError("First-party pixel POR claim must remain false.")
    if verification.get("canonical_pixel_conversion_supported") is not True:
        raise BenchmarkIntegrityError("Canonical pixel conversion must remain supported.")
    if verification.get("canonical_pixel_conversion") != {
        "x_px": "por_x * scene_width_px",
        "y_px": "por_y * scene_height_px",
    }:
        raise BenchmarkIntegrityError("Canonical pixel conversion contract drifted.")

    contract = record.get("gaze_forge_contract", {})
    if contract.get("normalized_por_to_canonical_pixels") is not True:
        raise BenchmarkIntegrityError("GazeForge normalized-POR conversion drifted.")
    if contract.get("coordinate_output_unit_after_conversion") != "pixels":
        raise BenchmarkIntegrityError("GazeForge coordinate output unit drifted.")
    if contract.get("pixel_kinematics_requires_canonical_conversion") is not True:
        raise BenchmarkIntegrityError("Pixel-kinematics conversion boundary drifted.")

    _require_false(
        record.get("distribution_boundary", {}),
        "authoritative_full_distribution_obtained",
        "corpus_wide_por_ranges_empirically_verified",
        "exact_distributed_file_equivalence_verified",
        "quarantined_processdata_sample_promoted",
    )
    _require_false(
        record.get("mapping_boundary", {}),
        "participant_identity_mapping_verified",
        "participant_task_mapping_verified",
        "trial_index_to_task_name_mapping_verified",
    )
    _require_false(
        record.get("rights_boundary", {}),
        "analysis_use_permitted",
        "redistribution_permission_verified",
        "reuse_terms_verified",
    )
    _require_false(
        record.get("scientific_boundary", {}),
        "cross_dataset_validation_created",
        "human_human_agreement_created",
        "new_empirical_performance_claim_created",
        "participant_disjoint_model_validation_created",
        "per_file_sampling_rate_distribution_frozen",
    )
    return record


def build_first_party_por_live_probe(source_text: str) -> dict[str, Any]:
    """Build a metadata-only live probe from the exact pinned source bytes."""
    source_bytes = source_text.encode("utf-8")
    observed_blob = git_blob_sha1(source_bytes)
    if observed_blob != SOURCE_BLOB:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild live source bytes do not match the pinned Git blob."
        )
    counts = validate_first_party_por_source(source_text)
    record: dict[str, Any] = {
        "record_type": LIVE_RECORD_TYPE,
        "source_binding": {
            "repository": SOURCE_REPOSITORY,
            "commit_sha1": SOURCE_COMMIT,
            "path": SOURCE_PATH,
            "git_blob_sha1": observed_blob,
        },
        "source_semantics": {
            "pupil_source_fields": ["norm_pos_x", "norm_pos_y"],
            "matlab_y_flip_present": True,
            "scene_resolution_px": [1920, 1080],
            "scene_resolution_stored_separately": True,
            "processdata_por_direct_interpolation_present": True,
            **counts,
        },
        "verification": {
            "processdata_por_coordinate_space": "normalized_scene_image",
            "first_party_pixel_por_claim": False,
            "canonical_pixel_conversion_supported": True,
        },
        "boundaries": {
            "distribution_equivalence_verified": False,
            "participant_mapping_verified": False,
            "task_mapping_verified": False,
            "reuse_terms_verified": False,
            "analysis_use_permitted": False,
            "cross_dataset_validation_created": False,
            "new_empirical_performance_claim_created": False,
        },
    }
    record["probe_fingerprint_sha256"] = probe_fingerprint(record)
    return record


def validate_live_por_probe_against_evidence(
    live_record_or_path: Mapping[str, Any] | str | Path,
    evidence_record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Bind a fresh exact-source probe to the immutable POR evidence."""
    evidence = validate_gaze_in_wild_por_coordinate_evidence(evidence_record_or_path)
    live = _load_record(live_record_or_path)
    if live.get("record_type") != LIVE_RECORD_TYPE:
        raise BenchmarkIntegrityError("Unexpected Gaze-in-the-Wild live probe type.")
    if live.get("probe_fingerprint_sha256") != probe_fingerprint(live):
        raise BenchmarkIntegrityError("Gaze-in-the-Wild live probe fingerprint is invalid.")

    source = live.get("source_binding", {})
    expected_source = evidence["canonical_source"]
    if source != expected_source:
        raise BenchmarkIntegrityError("Gaze-in-the-Wild live source binding drifted.")

    semantics = live.get("source_semantics", {})
    if semantics.get("pupil_source_fields") != ["norm_pos_x", "norm_pos_y"]:
        raise BenchmarkIntegrityError("Gaze-in-the-Wild live POR fields drifted.")
    if semantics.get("scene_resolution_px") != [1920, 1080]:
        raise BenchmarkIntegrityError("Gaze-in-the-Wild live scene resolution drifted.")
    if semantics.get("scene_resolution_stored_separately") is not True:
        raise BenchmarkIntegrityError("Live scene resolution is no longer separate.")
    if semantics.get("processdata_por_direct_interpolation_present") is not True:
        raise BenchmarkIntegrityError("Live ProcessData POR lineage drifted.")
    if semantics.get("processdata_etg_por_occurrence_count") != 1:
        raise BenchmarkIntegrityError("Live ProcessData POR assignment count drifted.")

    verification = live.get("verification", {})
    if verification.get("processdata_por_coordinate_space") != "normalized_scene_image":
        raise BenchmarkIntegrityError("Live ProcessData POR coordinate space drifted.")
    if verification.get("first_party_pixel_por_claim") is not False:
        raise BenchmarkIntegrityError("Live first-party pixel POR claim must remain false.")
    if verification.get("canonical_pixel_conversion_supported") is not True:
        raise BenchmarkIntegrityError("Live canonical pixel conversion boundary drifted.")

    _require_false(
        live.get("boundaries", {}),
        "distribution_equivalence_verified",
        "participant_mapping_verified",
        "task_mapping_verified",
        "reuse_terms_verified",
        "analysis_use_permitted",
        "cross_dataset_validation_created",
        "new_empirical_performance_claim_created",
    )
    return evidence
