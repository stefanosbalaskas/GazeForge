"""Immutable and fresh-live validation for Hollywood2 coordinate semantics."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .hollywood2_coordinate_metadata import probe_fingerprint

RECORD_TYPE = "hollywood2-coordinate-semantics-evidence-v1"
STATUS = "verified-pixel-coordinate-semantics"
EVIDENCE_FINGERPRINT = "f08f6f01b6f4eac422572e8e13d7dff794101769ad56691a93464c7032515806"
GIN_REPOSITORY = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git"
GIN_COMMIT = "870fa6d6209c9085260918d61433a0a2c70fd497"
GROUND_TRUTH_EVIDENCE_FINGERPRINT = (
    "d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea"
)
AUTHOR_REPOSITORY = "MikhailStartsev/deep_em_classifier"
AUTHOR_COMMIT = "9a345a37aab47ac6780ce0d4b5798cc15291c75b"
AUTHOR_README_BLOB = "112f5f2a235f059ac2394db3180956474e644c06"
REVIEWED_LIVE_PROBE_FINGERPRINT = (
    "d3ed5f9bc005ec435c34df1aa8fb0cb30599d49dff4835085f00114d43e185bd"
)
EXPECTED_ATTRIBUTES = [
    "time",
    "x",
    "y",
    "confidence",
    "handlabeller_1",
    "handlabeller_final",
]
EXPECTED_METADATA_KEYS = {
    "distance_mm": 697,
    "height_mm": 697,
    "height_px": 697,
    "width_mm": 697,
    "width_px": 697,
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Fingerprint a coordinate evidence record without its stored digest."""
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _require_false(mapping: Mapping[str, Any], *keys: str) -> None:
    for key in keys:
        if mapping.get(key) is not False:
            raise BenchmarkIntegrityError(f"Hollywood2 coordinate boundary {key!r} must be false.")


def validate_hollywood2_coordinate_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the immutable combined coordinate-semantics evidence."""
    if isinstance(record_or_path, Mapping):
        record = dict(record_or_path)
    else:
        record = json.loads(Path(record_or_path).read_text(encoding="utf-8"))
    if record.get("record_type") != RECORD_TYPE or record.get("status") != STATUS:
        raise BenchmarkIntegrityError("Unexpected Hollywood2 coordinate evidence identity/status.")
    observed = evidence_fingerprint(record)
    if record.get("evidence_fingerprint_sha256") != EVIDENCE_FINGERPRINT:
        raise BenchmarkIntegrityError("Hollywood2 coordinate evidence stored fingerprint drifted.")
    if observed != EVIDENCE_FINGERPRINT:
        raise BenchmarkIntegrityError("Hollywood2 coordinate evidence content fingerprint drifted.")

    source = record.get("canonical_source", {})
    if source.get("repository") != GIN_REPOSITORY or source.get("commit_sha1") != GIN_COMMIT:
        raise BenchmarkIntegrityError("Hollywood2 coordinate evidence source binding drifted.")
    if (
        source.get("authoritative_ground_truth_evidence_fingerprint_sha256")
        != GROUND_TRUTH_EVIDENCE_FINGERPRINT
    ):
        raise BenchmarkIntegrityError("Hollywood2 ground-truth evidence binding drifted.")

    author = record.get("author_input_convention", {})
    if author.get("repository") != AUTHOR_REPOSITORY:
        raise BenchmarkIntegrityError("Hollywood2 author implementation repository drifted.")
    if author.get("commit_sha1") != AUTHOR_COMMIT:
        raise BenchmarkIntegrityError("Hollywood2 author implementation commit drifted.")
    if author.get("readme_git_blob_sha1") != AUTHOR_README_BLOB:
        raise BenchmarkIntegrityError("Hollywood2 author README Git blob drifted.")
    if author.get("coordinate_unit") != "pixels" or author.get("time_unit") != "microseconds":
        raise BenchmarkIntegrityError("Hollywood2 author input-unit semantics drifted.")
    if author.get("required_geometry_metadata_keys") != [
        "width_px",
        "height_px",
        "width_mm",
        "height_mm",
        "distance_mm",
    ]:
        raise BenchmarkIntegrityError("Hollywood2 author geometry metadata keys drifted.")

    reviewed = record.get("reviewed_header_probe", {})
    if reviewed.get("probe_fingerprint_sha256") != REVIEWED_LIVE_PROBE_FINGERPRINT:
        raise BenchmarkIntegrityError("Hollywood2 reviewed header-probe fingerprint drifted.")
    if reviewed.get("arff_file_count") != 697:
        raise BenchmarkIntegrityError("Hollywood2 reviewed ARFF count drifted.")
    if reviewed.get("required_gaze_schema_file_count") != 697:
        raise BenchmarkIntegrityError("Hollywood2 reviewed gaze-schema count drifted.")
    if reviewed.get("author_convention_metadata_complete_file_count") != 697:
        raise BenchmarkIntegrityError("Hollywood2 reviewed metadata-complete count drifted.")
    if reviewed.get("metadata_key_file_counts") != EXPECTED_METADATA_KEYS:
        raise BenchmarkIntegrityError("Hollywood2 reviewed metadata-key coverage drifted.")
    if reviewed.get("metadata_signature_count") != 24:
        raise BenchmarkIntegrityError("Hollywood2 reviewed geometry signature count drifted.")
    if reviewed.get("attribute_signature") != EXPECTED_ATTRIBUTES:
        raise BenchmarkIntegrityError("Hollywood2 reviewed attribute signature drifted.")
    _require_false(
        reviewed,
        "raw_source_rows_read",
        "raw_source_rows_embedded",
        "source_filenames_embedded",
    )

    verification = record.get("verification", {})
    if verification.get("coordinate_unit") != "pixels":
        raise BenchmarkIntegrityError("Hollywood2 combined coordinate unit is not pixels.")
    if verification.get("coordinate_unit_verified") is not True:
        raise BenchmarkIntegrityError("Hollywood2 combined coordinate verification is not true.")

    _require_false(
        record.get("rights_boundary", {}),
        "new_analysis_permission_created",
        "new_redistribution_permission_created",
        "exact_annotation_repository_license_verified",
    )
    _require_false(
        record.get("scientific_boundary", {}),
        "pixel_to_visual_angle_conversion_verified",
        "participant_identity_mapping_verified",
        "source_token_to_participant_mapping_verified",
        "participant_disjoint_validation_created",
        "cross_dataset_validation_created",
        "unit_sensitive_cross_dataset_modelling_executed",
        "new_empirical_performance_claim_created",
    )
    return record


def validate_author_input_convention(readme_text: str) -> None:
    """Fail unless the exact author README still states the reviewed unit convention."""
    normalized = re.sub(r"\s+", " ", str(readme_text)).lower()
    markers = (
        "time (in microseconds)",
        "coordinates (in pixels",
        "%@metadata width_px",
        "%@metadata height_px",
        "%@metadata width_mm",
        "%@metadata height_mm",
        "%@metadata distance_mm",
    )
    missing = [marker for marker in markers if marker not in normalized]
    if missing:
        raise BenchmarkIntegrityError(
            f"Hollywood2 author input convention markers are missing: {missing}."
        )


def validate_live_probe_against_coordinate_evidence(
    live_record_or_path: Mapping[str, Any] | str | Path,
    evidence_record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Require fresh pinned headers to reproduce the reviewed coordinate boundary."""
    evidence = validate_hollywood2_coordinate_evidence(evidence_record_or_path)
    if isinstance(live_record_or_path, Mapping):
        live = dict(live_record_or_path)
    else:
        live = json.loads(Path(live_record_or_path).read_text(encoding="utf-8"))
    if live.get("probe_fingerprint_sha256") != probe_fingerprint(live):
        raise BenchmarkIntegrityError("Hollywood2 live coordinate-probe fingerprint is invalid.")
    if live.get("probe_fingerprint_sha256") != REVIEWED_LIVE_PROBE_FINGERPRINT:
        raise BenchmarkIntegrityError("Hollywood2 live coordinate headers drifted from review.")
    source = live.get("source_binding", {})
    if source.get("repository") != GIN_REPOSITORY or source.get("commit_sha1") != GIN_COMMIT:
        raise BenchmarkIntegrityError("Hollywood2 live coordinate source binding drifted.")

    inventory = live.get("header_inventory", {})
    if inventory.get("arff_file_count") != 697:
        raise BenchmarkIntegrityError("Hollywood2 live ARFF count drifted.")
    if inventory.get("required_gaze_schema_file_count") != 697:
        raise BenchmarkIntegrityError("Hollywood2 live gaze-schema coverage drifted.")
    if inventory.get("author_convention_metadata_complete_file_count") != 697:
        raise BenchmarkIntegrityError("Hollywood2 live author-metadata coverage drifted.")
    if inventory.get("metadata_key_file_counts") != EXPECTED_METADATA_KEYS:
        raise BenchmarkIntegrityError("Hollywood2 live metadata-key coverage drifted.")
    signatures = inventory.get("attribute_signatures")
    if signatures != [{"attributes": EXPECTED_ATTRIBUTES, "file_count": 697}]:
        raise BenchmarkIntegrityError("Hollywood2 live attribute signature drifted.")
    metadata_signatures = inventory.get("metadata_signatures", [])
    if len(metadata_signatures) != 24:
        raise BenchmarkIntegrityError("Hollywood2 live geometry signature count drifted.")
    if sum(int(item.get("file_count", 0)) for item in metadata_signatures) != 697:
        raise BenchmarkIntegrityError("Hollywood2 live geometry signature coverage drifted.")

    coordinate = live.get("coordinate_boundary", {})
    if coordinate.get("all_headers_match_author_input_metadata_convention") is not True:
        raise BenchmarkIntegrityError("Hollywood2 live headers no longer match author metadata.")
    if coordinate.get("coordinate_unit_candidate") != "pixels":
        raise BenchmarkIntegrityError("Hollywood2 live coordinate candidate is not pixels.")
    _require_false(
        coordinate,
        "coordinate_unit_verified",
        "coordinate_verification_basis_created",
        "pixel_to_visual_angle_conversion_verified",
        "unit_sensitive_cross_dataset_modelling_ready",
    )
    _require_false(
        live.get("mapping_boundary", {}),
        "participant_identity_mapping_verified",
        "source_token_to_participant_mapping_verified",
    )
    _require_false(
        live.get("rights_boundary", {}),
        "new_rights_permission_created",
        "raw_source_redistribution_authorized",
    )
    _require_false(
        live.get("scientific_boundary", {}),
        "raw_source_rows_read",
        "raw_source_rows_embedded",
        "source_filenames_embedded",
        "participant_disjoint_validation_created",
        "cross_dataset_validation_created",
        "new_empirical_performance_claim_created",
    )
    return evidence
