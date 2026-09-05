"""Quarantined inventory for unverified Gaze-in-the-Wild recovery candidates.

This module deliberately stops before source-audit interpretation. A candidate tree may be
fingerprinted and reviewed, but filenames are not promoted to participant, trial, labeller,
rate, task, coordinate, rights, or source-authority evidence.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "gaze-in-wild-recovery-candidate-review-v1"
CANDIDATE_STATUS = "quarantined"
_ALLOWED_CANDIDATE_KINDS = {
    "unknown_recovered_copy",
    "candidate_original_layout_unverified",
    "transformed_secondary_collection",
    "labeller_provenance_only",
}
_SCIENTIFIC_BOUNDARY = {
    "source_authority_verified": False,
    "exact_original_distribution_format_verified": False,
    "dataset_file_rights_resolved": False,
    "analysis_use_authorized": False,
    "redistribution_authorized": False,
    "participant_mapping_verified": False,
    "complete_trial_task_mapping_verified": False,
    "coordinate_unit_verified_from_candidate": False,
    "sampling_cadence_verified_from_candidate": False,
    "independent_labeller_recoverability_verified": False,
    "source_audit_ready": False,
    "empirical_evidence_eligible": False,
    "human_human_agreement_created": False,
    "participant_disjoint_model_validation_created": False,
    "cross_dataset_performance_created": False,
    "gp3_validity_created": False,
    "frozen_evidence_performance_claim_created": False,
}


@dataclass(frozen=True, slots=True)
class GazeInWildRecoveryCandidateReview:
    """Validated non-empirical identity for one quarantined candidate tree."""

    path: Path | None
    candidate_kind: str
    tree_fingerprint_sha256: str
    record_fingerprint_sha256: str
    file_count: int
    total_bytes: int


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tree_fingerprint(files: list[dict[str, Any]]) -> str:
    return hashlib.sha256(_canonical_bytes(files)).hexdigest()


def recovery_candidate_record_fingerprint(record: Mapping[str, Any]) -> str:
    """Return the canonical record fingerprint excluding the stored value."""

    body = dict(record)
    body.pop("record_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _check_root(root: str | Path) -> Path:
    raw = Path(root)
    if raw.is_symlink():
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild recovery candidate root must not be a symlink."
        )
    resolved = raw.resolve()
    if not resolved.is_dir():
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild recovery candidate root must be an existing directory."
        )
    return resolved


def _inventory(root: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    entries = sorted(root.rglob("*"), key=lambda path: path.relative_to(root).as_posix())
    for path in entries:
        if path.is_symlink():
            raise BenchmarkIntegrityError(
                "Gaze-in-the-Wild recovery candidate trees must not contain symlinks."
            )

    files: list[dict[str, Any]] = []
    extensions: Counter[str] = Counter()
    for path in entries:
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        suffix = path.suffix.lower() or "<none>"
        extensions[suffix] += 1
        files.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
                "role": "unclassified",
            }
        )
    if not files:
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild recovery candidate trees must contain at least one file."
        )
    return files, dict(sorted(extensions.items()))


def build_gaze_in_wild_recovery_candidate_review(
    root: str | Path,
    *,
    candidate_kind: str,
    provenance_source: str,
    provenance_note: str,
) -> dict[str, Any]:
    """Fingerprint a candidate tree without interpreting it as an empirical source."""

    kind = str(candidate_kind).strip().lower()
    if kind not in _ALLOWED_CANDIDATE_KINDS:
        raise BenchmarkIntegrityError(
            "Unsupported Gaze-in-the-Wild recovery candidate kind."
        )
    source = str(provenance_source).strip()
    note = str(provenance_note).strip()
    if not source or not note:
        raise BenchmarkIntegrityError(
            "Recovery candidates require explicit provenance_source and provenance_note."
        )

    resolved = _check_root(root)
    files, extension_counts = _inventory(resolved)
    payload: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "candidate_status": CANDIDATE_STATUS,
        "dataset": "Gaze-in-the-Wild",
        "candidate_kind": kind,
        "provenance": {
            "source": source,
            "note": note,
            "authority_status": "unverified",
            "rights_status": "unresolved",
        },
        "inventory": {
            "file_count": len(files),
            "total_bytes": sum(int(item["bytes"]) for item in files),
            "extension_counts": extension_counts,
            "files": files,
            "tree_fingerprint_sha256": _tree_fingerprint(files),
        },
        "interpretation_policy": {
            "all_file_roles_are_unclassified": True,
            "filename_identity_inference_permitted": False,
            "matlab_schema_inference_permitted": False,
            "license_inference_permitted": False,
            "candidate_can_materialize_empirical_audit_spec": False,
        },
        "scientific_boundary": dict(_SCIENTIFIC_BOUNDARY),
        "claim_limit": (
            "This record fingerprints an unverified recovery candidate for review only. "
            "It does not establish source authority, exact original distribution identity, "
            "dataset-file rights, participant/task/labeller identities, coordinate units, "
            "sampling cadence, independent annotation streams, empirical source-audit "
            "eligibility, agreement, model performance, cross-dataset validity, or GP3 validity."
        ),
    }
    payload["record_fingerprint_sha256"] = recovery_candidate_record_fingerprint(payload)
    return payload


def _load(
    record_or_path: Mapping[str, Any] | str | Path,
) -> tuple[dict[str, Any], Path | None]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path), None
    path = Path(record_or_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load Gaze-in-the-Wild recovery candidate review: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "Gaze-in-the-Wild recovery candidate review must contain one JSON object."
        )
    return payload, path


def validate_gaze_in_wild_recovery_candidate_review(
    record_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildRecoveryCandidateReview:
    """Fail closed if a quarantined candidate record promotes unsupported claims."""

    record, path = _load(record_or_path)
    if record.get("record_type") != RECORD_TYPE:
        raise BenchmarkIntegrityError("Recovery candidate record_type drifted.")
    if record.get("candidate_status") != CANDIDATE_STATUS:
        raise BenchmarkIntegrityError("Recovery candidate must remain quarantined.")
    if record.get("dataset") != "Gaze-in-the-Wild":
        raise BenchmarkIntegrityError("Recovery candidate dataset identity drifted.")

    kind = str(record.get("candidate_kind", "")).strip().lower()
    if kind not in _ALLOWED_CANDIDATE_KINDS:
        raise BenchmarkIntegrityError("Recovery candidate kind is invalid.")

    provenance = record.get("provenance")
    if not isinstance(provenance, Mapping):
        raise BenchmarkIntegrityError("Recovery candidate provenance is missing.")
    if not str(provenance.get("source", "")).strip():
        raise BenchmarkIntegrityError("Recovery candidate provenance source is unresolved.")
    if not str(provenance.get("note", "")).strip():
        raise BenchmarkIntegrityError("Recovery candidate provenance note is unresolved.")
    if provenance.get("authority_status") != "unverified":
        raise BenchmarkIntegrityError("Recovery candidate source authority must remain unverified.")
    if provenance.get("rights_status") != "unresolved":
        raise BenchmarkIntegrityError("Recovery candidate rights must remain unresolved.")

    inventory = record.get("inventory")
    if not isinstance(inventory, Mapping):
        raise BenchmarkIntegrityError("Recovery candidate inventory is missing.")
    files = inventory.get("files")
    if not isinstance(files, list) or not files:
        raise BenchmarkIntegrityError("Recovery candidate inventory must contain files.")
    paths: list[str] = []
    total_bytes = 0
    for item in files:
        if not isinstance(item, Mapping):
            raise BenchmarkIntegrityError("Recovery candidate file entries must be mappings.")
        file_path = str(item.get("path", ""))
        if not file_path or file_path.startswith("/") or ".." in Path(file_path).parts:
            raise BenchmarkIntegrityError("Recovery candidate file path is unsafe.")
        paths.append(file_path)
        size = item.get("bytes")
        if not isinstance(size, int) or size < 0:
            raise BenchmarkIntegrityError("Recovery candidate file byte size is invalid.")
        total_bytes += size
        digest = str(item.get("sha256", ""))
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise BenchmarkIntegrityError("Recovery candidate file SHA-256 is invalid.")
        if item.get("role") != "unclassified":
            raise BenchmarkIntegrityError(
                "Recovery candidate file roles must remain unclassified."
            )
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise BenchmarkIntegrityError(
            "Recovery candidate file paths must be sorted and unique."
        )
    if inventory.get("file_count") != len(files):
        raise BenchmarkIntegrityError("Recovery candidate file count drifted.")
    if inventory.get("total_bytes") != total_bytes:
        raise BenchmarkIntegrityError("Recovery candidate total byte count drifted.")
    observed_tree = _tree_fingerprint([dict(item) for item in files])
    if inventory.get("tree_fingerprint_sha256") != observed_tree:
        raise BenchmarkIntegrityError("Recovery candidate tree fingerprint drifted.")

    policy = record.get("interpretation_policy")
    if not isinstance(policy, Mapping):
        raise BenchmarkIntegrityError("Recovery candidate interpretation policy is missing.")
    if policy.get("all_file_roles_are_unclassified") is not True:
        raise BenchmarkIntegrityError("Recovery candidate file roles must stay unclassified.")
    for key in (
        "filename_identity_inference_permitted",
        "matlab_schema_inference_permitted",
        "license_inference_permitted",
        "candidate_can_materialize_empirical_audit_spec",
    ):
        if policy.get(key) is not False:
            raise BenchmarkIntegrityError(
                f"Recovery candidate interpretation policy must keep {key}=false."
            )

    if record.get("scientific_boundary") != _SCIENTIFIC_BOUNDARY:
        raise BenchmarkIntegrityError(
            "Recovery candidate scientific boundary cannot be promoted."
        )
    observed_record = recovery_candidate_record_fingerprint(record)
    stored_record = record.get("record_fingerprint_sha256")
    if stored_record != observed_record:
        raise BenchmarkIntegrityError("Recovery candidate record fingerprint drifted.")

    return GazeInWildRecoveryCandidateReview(
        path=path,
        candidate_kind=kind,
        tree_fingerprint_sha256=observed_tree,
        record_fingerprint_sha256=observed_record,
        file_count=len(files),
        total_bytes=total_bytes,
    )


def verify_gaze_in_wild_recovery_candidate_tree(
    root: str | Path,
    record_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildRecoveryCandidateReview:
    """Re-inventory a candidate tree and require exact equality with its review record."""

    validated = validate_gaze_in_wild_recovery_candidate_review(record_or_path)
    record, _ = _load(record_or_path)
    resolved = _check_root(root)
    files, extension_counts = _inventory(resolved)
    inventory = record["inventory"]
    if files != inventory["files"]:
        raise BenchmarkIntegrityError(
            "Recovery candidate tree no longer matches its reviewed file manifest."
        )
    if extension_counts != inventory["extension_counts"]:
        raise BenchmarkIntegrityError(
            "Recovery candidate extension inventory no longer matches its review."
        )
    return validated


def write_gaze_in_wild_recovery_candidate_review(
    record: Mapping[str, Any],
    path: str | Path,
    *,
    candidate_root: str | Path,
    overwrite: bool = False,
) -> Path:
    """Write a validated review outside the candidate tree."""

    validate_gaze_in_wild_recovery_candidate_review(record)
    root = _check_root(candidate_root)
    target = Path(path)
    resolved_target = target.resolve(strict=False)
    if resolved_target == root or root in resolved_target.parents:
        raise BenchmarkIntegrityError(
            "Recovery candidate review output must be outside the candidate tree."
        )
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dict(record), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return target
