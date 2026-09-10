"""Non-promoting candidate intake for a prospective authoritative VISUS source."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .visus_authoritative_source_common import (
    _ALLOWED_AUTHORITY_CLAIMS,
    _CANDIDATE_INVENTORY_KEYS,
    _CANDIDATE_KEYS,
    _CANDIDATE_MANIFEST_KEYS,
    _CANDIDATE_REVIEW_KEYS,
    _CANDIDATE_RIGHTS_KEYS,
    _CANDIDATE_SOURCE_KEYS,
    _SCIENTIFIC_KEYS,
    CANDIDATE_RECORD_TYPE,
    CANDIDATE_STATUS,
    EXPECTED_PARTICIPANT_COUNT,
    EXPECTED_STIMULUS_COUNT,
    MAX_MANIFEST_BYTES,
    MAX_RIGHTS_EVIDENCE_BYTES,
    SOURCE_RECHECK_FINGERPRINT,
    _hash_file,
    _outside_root,
    _read_json,
    _require_exact_keys,
    _resolved_text,
    _sha256_value,
    _validate_source_manifest,
    candidate_fingerprint,
)
from .visus_scaffold import build_visus_source_audit_scaffold


def inspect_visus_authoritative_source_candidate(
    root: str | Path,
    source_artifact_path: str | Path,
    rights_evidence_path: str | Path,
    manifest_path: str | Path,
) -> dict[str, Any]:
    """Bind exact candidate bytes without promoting source authority or rights."""
    root_path = Path(root).resolve()
    source_path = Path(source_artifact_path)
    rights_path = Path(rights_evidence_path)
    manifest_file = Path(manifest_path)
    evidence_paths = [
        source_path.resolve(strict=False),
        rights_path.resolve(strict=False),
        manifest_file.resolve(strict=False),
    ]
    if len(set(evidence_paths)) != len(evidence_paths):
        raise BenchmarkIntegrityError(
            "VISUS source artifact, rights evidence, and manifest must be distinct files."
        )
    for path, label in (
        (source_path, "source artifact"),
        (rights_path, "rights evidence"),
        (manifest_file, "source manifest"),
    ):
        _outside_root(root_path, path, label=label)

    source_size, source_sha = _hash_file(source_path, label="source artifact")
    rights_size, rights_sha = _hash_file(
        rights_path,
        label="rights evidence",
        max_bytes=MAX_RIGHTS_EVIDENCE_BYTES,
    )
    scaffold = build_visus_source_audit_scaffold(root_path)
    manifest_size, manifest_sha = _hash_file(
        manifest_file,
        label="source manifest",
        max_bytes=MAX_MANIFEST_BYTES,
    )
    manifest = _read_json(
        manifest_file,
        label="source manifest",
        max_bytes=MAX_MANIFEST_BYTES,
    )
    _validate_source_manifest(
        manifest,
        source_sha256=source_sha,
        rights_sha256=rights_sha,
        inventory_fingerprint_sha256=scaffold.inventory_fingerprint_sha256,
        file_count=scaffold.file_count,
    )

    record: dict[str, Any] = {
        "record_type": CANDIDATE_RECORD_TYPE,
        "status": CANDIDATE_STATUS,
        "authoritative_source_recheck_fingerprint_sha256": SOURCE_RECHECK_FINGERPRINT,
        "source": {
            "artifact_basename": source_path.name,
            "artifact_size_bytes": source_size,
            "artifact_sha256": source_sha,
            "source_reference": str(manifest["source_reference"]).strip(),
            "source_revision": str(manifest["source_revision"]).strip(),
            "source_authority_claim": str(manifest["source_authority_claim"]).strip().lower(),
            "authorized_channel_affirmed": True,
        },
        "rights_evidence": {
            "basename": rights_path.name,
            "size_bytes": rights_size,
            "sha256": rights_sha,
            "reference": str(manifest["rights_evidence_reference"]).strip(),
            "raw_rights_text_copied_to_candidate": False,
        },
        "manifest": {
            "basename": manifest_file.name,
            "size_bytes": manifest_size,
            "sha256": manifest_sha,
        },
        "inventory": {
            "file_count": scaffold.file_count,
            "fingerprint_sha256": scaffold.inventory_fingerprint_sha256,
            "published_participant_count": EXPECTED_PARTICIPANT_COUNT,
            "published_stimulus_count": EXPECTED_STIMULUS_COUNT,
            "file_roles_inferred": False,
            "participant_ids_inferred": False,
            "stimulus_ids_inferred": False,
        },
        "review_boundary": {
            "source_authority_verified": False,
            "current_authoritative_distribution_identity_verified": False,
            "source_artifact_matches_authoritative_distribution_verified": False,
            "extracted_tree_matches_source_artifact_verified": False,
            "rights_evidence_authoritative_verified": False,
            "analysis_use_permitted_verified": False,
            "redistribution_status_verified": False,
            "source_audit_stage_authorized": False,
            "manual_review_required": True,
        },
        "scientific_boundary": {
            "dataset_status_empirical_created": False,
            "participant_mapping_verified": False,
            "stimulus_mapping_verified": False,
            "coordinate_basis_verified": False,
            "timestamp_basis_verified": False,
            "independent_annotation_streams_verified": False,
            "human_human_agreement_created": False,
            "model_human_validation_created": False,
            "frozen_evidence_created": False,
            "raw_source_redistribution_action_authorized": False,
        },
    }
    record["candidate_fingerprint_sha256"] = candidate_fingerprint(record)
    return record


def validate_candidate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a non-promoting VISUS source-authority candidate."""
    value = dict(record)
    _require_exact_keys(value, _CANDIDATE_KEYS, label="candidate")
    if value.get("record_type") != CANDIDATE_RECORD_TYPE:
        raise BenchmarkIntegrityError("VISUS source-authority candidate type drifted.")
    if value.get("status") != CANDIDATE_STATUS:
        raise BenchmarkIntegrityError("VISUS source-authority candidate status drifted.")
    if value.get("authoritative_source_recheck_fingerprint_sha256") != SOURCE_RECHECK_FINGERPRINT:
        raise BenchmarkIntegrityError("VISUS source-authority recheck binding drifted.")
    if value.get("candidate_fingerprint_sha256") != candidate_fingerprint(value):
        raise BenchmarkIntegrityError("VISUS source-authority candidate fingerprint drifted.")

    source = value.get("source")
    rights = value.get("rights_evidence")
    manifest = value.get("manifest")
    inventory = value.get("inventory")
    review = value.get("review_boundary")
    scientific = value.get("scientific_boundary")
    if not all(
        isinstance(item, Mapping)
        for item in (source, rights, manifest, inventory, review, scientific)
    ):
        raise BenchmarkIntegrityError("VISUS source-authority candidate sections are missing.")
    assert isinstance(source, Mapping)
    assert isinstance(rights, Mapping)
    assert isinstance(manifest, Mapping)
    assert isinstance(inventory, Mapping)
    assert isinstance(review, Mapping)
    assert isinstance(scientific, Mapping)
    _require_exact_keys(source, _CANDIDATE_SOURCE_KEYS, label="candidate source")
    _require_exact_keys(rights, _CANDIDATE_RIGHTS_KEYS, label="candidate rights evidence")
    _require_exact_keys(manifest, _CANDIDATE_MANIFEST_KEYS, label="candidate manifest")
    _require_exact_keys(inventory, _CANDIDATE_INVENTORY_KEYS, label="candidate inventory")
    _require_exact_keys(review, _CANDIDATE_REVIEW_KEYS, label="candidate review boundary")
    _require_exact_keys(scientific, _SCIENTIFIC_KEYS, label="candidate scientific boundary")

    if source.get("source_authority_claim") not in _ALLOWED_AUTHORITY_CLAIMS:
        raise BenchmarkIntegrityError("VISUS source-authority candidate authority class drifted.")
    _resolved_text(source.get("source_reference"), label="candidate source_reference")
    _resolved_text(source.get("source_revision"), label="candidate source_revision")
    if not isinstance(source.get("artifact_size_bytes"), int) or source["artifact_size_bytes"] <= 0:
        raise BenchmarkIntegrityError("VISUS candidate source artifact size is invalid.")
    if source.get("authorized_channel_affirmed") is not True:
        raise BenchmarkIntegrityError("VISUS source-authority candidate authorization drifted.")
    _sha256_value(source.get("artifact_sha256"), label="candidate source artifact SHA-256")
    _sha256_value(rights.get("sha256"), label="candidate rights evidence SHA-256")
    _sha256_value(manifest.get("sha256"), label="candidate manifest SHA-256")
    _sha256_value(inventory.get("fingerprint_sha256"), label="candidate inventory SHA-256")
    _resolved_text(rights.get("reference"), label="candidate rights evidence reference")
    if not isinstance(rights.get("size_bytes"), int) or rights["size_bytes"] <= 0:
        raise BenchmarkIntegrityError("VISUS candidate rights-evidence size is invalid.")
    if not isinstance(manifest.get("size_bytes"), int) or manifest["size_bytes"] <= 0:
        raise BenchmarkIntegrityError("VISUS candidate manifest size is invalid.")
    if rights.get("raw_rights_text_copied_to_candidate") is not False:
        raise BenchmarkIntegrityError("VISUS source-authority candidate leaked raw rights text.")
    if not isinstance(inventory.get("file_count"), int) or inventory["file_count"] <= 0:
        raise BenchmarkIntegrityError("VISUS candidate inventory file count is invalid.")
    if inventory.get("published_participant_count") != EXPECTED_PARTICIPANT_COUNT:
        raise BenchmarkIntegrityError("VISUS candidate published participant count drifted.")
    if inventory.get("published_stimulus_count") != EXPECTED_STIMULUS_COUNT:
        raise BenchmarkIntegrityError("VISUS candidate published stimulus count drifted.")
    for key in ("file_roles_inferred", "participant_ids_inferred", "stimulus_ids_inferred"):
        if inventory.get(key) is not False:
            raise BenchmarkIntegrityError(f"VISUS source candidate must not infer {key}.")

    for key in (
        "source_authority_verified",
        "current_authoritative_distribution_identity_verified",
        "source_artifact_matches_authoritative_distribution_verified",
        "extracted_tree_matches_source_artifact_verified",
        "rights_evidence_authoritative_verified",
        "analysis_use_permitted_verified",
        "redistribution_status_verified",
        "source_audit_stage_authorized",
    ):
        if review.get(key) is not False:
            raise BenchmarkIntegrityError(f"VISUS source candidate must not promote {key}.")
    if review.get("manual_review_required") is not True:
        raise BenchmarkIntegrityError("VISUS source-authority manual-review gate was relaxed.")
    for key, observed in scientific.items():
        if observed is not False:
            raise BenchmarkIntegrityError(f"VISUS source candidate must not promote {key}.")
    return value
