"""Structured exact-copy review for quarantined Gaze-in-the-Wild recovery candidates.

This module sits between first-party quarantine readiness and the existing quarantine-exit
authorization.  It compares one live-reverified candidate tree with one separately supplied
reference tree using complete relative-path / byte-size / SHA-256 manifests.  The reference
provenance artifact is hashed locally; its contents and any private archive location are not
serialized.

A positive review means only that the candidate is byte-manifest identical to the separately
reviewed reference copy.  It does not by itself prove historical-original equivalence, authorize
quarantine exit, authorize a source audit, or create empirical evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_candidate_preflight import (
    candidate_processdata_screen_fingerprint,
    verify_gaze_in_wild_candidate_processdata_screen,
)
from .gaze_in_wild_first_party_readiness import (
    first_party_readiness_fingerprint,
    validate_gaze_in_wild_first_party_quarantine_readiness,
)
from .gaze_in_wild_quarantine_exit import GazeInWildQuarantineExitAuthorization
from .gaze_in_wild_recovery import (
    recovery_candidate_record_fingerprint,
    validate_gaze_in_wild_recovery_candidate_review,
    verify_gaze_in_wild_recovery_candidate_tree,
)
from .source_candidate import CandidateSourceInventory, build_candidate_source_inventory

RECORD_TYPE = "gaze-in-wild-exact-copy-review-v1"
_ALLOWED_REVIEW_STATUS = {"pending_review", "reviewed"}
_ALLOWED_DECISIONS = {
    "pending_review",
    "verified_against_reviewed_reference_manifest",
    "not_verified",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UNRESOLVED = {"", "review_required", "__unresolved__", "unknown", "none", "nan"}

_SCIENTIFIC_BOUNDARY = {
    "exact_copy_review_only": True,
    "reference_authority_inferred_from_manifest": False,
    "historical_original_distribution_equivalence_verified": False,
    "quarantine_exit_authorized": False,
    "source_audit_ready": False,
    "source_audit_executed": False,
    "participant_mapping_verified": False,
    "complete_trial_task_mapping_verified": False,
    "coordinate_unit_verified": False,
    "sampling_cadence_verified": False,
    "separate_labeldata_recovered": False,
    "independent_labeller_recoverability_verified": False,
    "empirical_evidence_eligible": False,
    "human_human_agreement_created": False,
    "participant_disjoint_model_validation_created": False,
    "cross_dataset_performance_created": False,
    "gp3_validity_created": False,
    "frozen_evidence_performance_claim_created": False,
    "empirical_evidence_created": False,
}

_PRIVACY_BOUNDARY = {
    "raw_first_party_correspondence_serialized": False,
    "private_archive_location_serialized": False,
    "reference_provenance_content_serialized": False,
    "reference_provenance_represented_by_sha256_only": True,
}

CLAIM_LIMIT = (
    "This record can establish only byte-manifest identity between one live-reverified GIW "
    "recovery candidate and one separately reviewed local reference copy. It does not infer "
    "reference authority from filenames, MATLAB structure, or manifest equality; it does not "
    "establish historical-original distribution equivalence, authorize quarantine exit or source "
    "audit execution, recover LabelData, or create empirical evidence."
)


@dataclass(frozen=True, slots=True)
class GazeInWildExactCopyReview:
    """Validated exact-copy decision with an ephemeral live-binding state."""

    path: Path | None
    record_fingerprint_sha256: str
    decision: str
    exact_copy_identity_verified: bool
    readiness_record_fingerprint_sha256: str
    recovery_record_fingerprint_sha256: str
    recovery_tree_fingerprint_sha256: str
    candidate_inventory_fingerprint_sha256: str
    reference_inventory_fingerprint_sha256: str
    reference_provenance_sha256: str
    _binding_validated: bool = field(default=False, repr=False, compare=False)


def exact_copy_review_fingerprint(record: Mapping[str, Any]) -> str:
    """Return canonical review SHA-256 excluding its stored fingerprint."""

    body = dict(record)
    body.pop("record_fingerprint_sha256", None)
    return benchmark_fingerprint(body)


def _sha256(value: Any, *, label: str) -> str:
    digest = str(value).strip().lower()
    if _SHA256_RE.fullmatch(digest) is None:
        raise BenchmarkIntegrityError(f"GIW exact-copy review {label} must be SHA-256.")
    return digest


def _file_sha256(path: str | Path) -> str:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolved(value: Any, *, label: str) -> str:
    text = "" if value is None else str(value).strip()
    if text.lower() in _UNRESOLVED:
        raise BenchmarkIntegrityError(f"GIW exact-copy reviewed decisions require {label}.")
    return text


def _load_json_object(
    value: Mapping[str, Any] | str | Path,
    *,
    label: str,
) -> tuple[dict[str, Any], Path | None]:
    if isinstance(value, Mapping):
        return dict(value), None
    path = Path(value)
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"{label} must be valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"{label} must contain one JSON object.")
    return payload, path


def _assert_distinct_trees(candidate_root: str | Path, reference_root: str | Path) -> tuple[Path, Path]:
    candidate = Path(candidate_root).resolve()
    reference = Path(reference_root).resolve()
    if candidate == reference or candidate in reference.parents or reference in candidate.parents:
        raise BenchmarkIntegrityError(
            "GIW exact-copy review requires separate, non-nested candidate and reference trees."
        )
    return candidate, reference


def _reference_provenance_digest(
    provenance_path: str | Path,
    *,
    candidate_root: Path,
    reference_root: Path,
) -> str:
    path = Path(provenance_path).resolve()
    if (
        path == candidate_root
        or candidate_root in path.parents
        or path == reference_root
        or reference_root in path.parents
    ):
        raise BenchmarkIntegrityError(
            "GIW reference provenance evidence must live outside both compared trees."
        )
    return _file_sha256(path)


def _recovery_manifest(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    inventory = record.get("inventory")
    if not isinstance(inventory, Mapping):
        raise BenchmarkIntegrityError("GIW exact-copy recovery inventory is missing.")
    raw = inventory.get("files")
    if not isinstance(raw, list) or not raw:
        raise BenchmarkIntegrityError("GIW exact-copy recovery file manifest is missing.")
    rows: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise BenchmarkIntegrityError("GIW exact-copy recovery manifest entry is invalid.")
        rows.append(
            {
                "path": str(item.get("path", "")),
                "sha256": str(item.get("sha256", "")),
                "bytes": int(item.get("bytes", -1)),
            }
        )
    return rows


def _inventory_manifest(inventory: CandidateSourceInventory) -> list[dict[str, Any]]:
    return [
        {"path": item.path, "sha256": item.sha256, "bytes": item.bytes}
        for item in inventory.files
    ]


def _candidate_binding(
    readiness: Mapping[str, Any],
    *,
    candidate_root: str | Path,
    recovery_record_or_path: Mapping[str, Any] | str | Path,
    candidate_screen_record_or_path: Mapping[str, Any] | str | Path,
) -> tuple[dict[str, Any], CandidateSourceInventory]:
    if readiness.get("handoff_status") != "ready_for_independent_exact_copy_review":
        raise BenchmarkIntegrityError(
            "GIW exact-copy review requires a readiness record whose preliminary blockers are "
            "already resolved."
        )
    readiness_state = readiness.get("readiness")
    if not isinstance(readiness_state, Mapping) or readiness_state.get(
        "ready_for_independent_exact_copy_review"
    ) is not True:
        raise BenchmarkIntegrityError("GIW exact-copy readiness gate is not satisfied.")

    screen = verify_gaze_in_wild_candidate_processdata_screen(
        candidate_root,
        recovery_record_or_path,
        candidate_screen_record_or_path,
    )
    recovery_record, _ = _load_json_object(
        recovery_record_or_path,
        label="Gaze-in-the-Wild recovery candidate review",
    )
    validate_gaze_in_wild_recovery_candidate_review(recovery_record)
    verify_gaze_in_wild_recovery_candidate_tree(candidate_root, recovery_record)

    saved = readiness.get("candidate_binding")
    if not isinstance(saved, Mapping):
        raise BenchmarkIntegrityError("GIW exact-copy readiness candidate binding is missing.")
    selected = screen.get("selected_file")
    if not isinstance(selected, Mapping):
        raise BenchmarkIntegrityError("GIW exact-copy ProcessData selection is missing.")
    expected = {
        "candidate_kind": str(screen["candidate_kind"]),
        "recovery_record_fingerprint_sha256": str(
            screen["recovery_record_fingerprint_sha256"]
        ),
        "recovery_tree_fingerprint_sha256": str(screen["recovery_tree_fingerprint_sha256"]),
        "candidate_screen_fingerprint_sha256": candidate_processdata_screen_fingerprint(screen),
        "selected_file": {
            "relative_path": selected["relative_path"],
            "sha256": selected["sha256"],
            "bytes": selected["bytes"],
        },
    }
    if dict(saved) != expected:
        raise BenchmarkIntegrityError(
            "GIW exact-copy readiness no longer binds the current candidate ProcessData screen."
        )

    candidate_inventory = build_candidate_source_inventory(
        candidate_root,
        dataset_key="gaze-in-the-wild",
    )
    if _recovery_manifest(recovery_record) != _inventory_manifest(candidate_inventory):
        raise BenchmarkIntegrityError(
            "GIW exact-copy recovery review and current candidate inventory disagree."
        )
    return recovery_record, candidate_inventory


def _comparison_summary(
    candidate: CandidateSourceInventory,
    reference: CandidateSourceInventory,
) -> dict[str, Any]:
    candidate_by_path = {item.path: item for item in candidate.files}
    reference_by_path = {item.path: item for item in reference.files}
    candidate_paths = set(candidate_by_path)
    reference_paths = set(reference_by_path)
    shared = candidate_paths & reference_paths
    content_mismatch_count = sum(
        1
        for path in shared
        if candidate_by_path[path].sha256 != reference_by_path[path].sha256
        or candidate_by_path[path].bytes != reference_by_path[path].bytes
    )
    exact = candidate.files == reference.files
    return {
        "method": "complete_relative_path_byte_size_sha256_manifest_equality",
        "candidate_file_count": candidate.file_count,
        "reference_file_count": reference.file_count,
        "candidate_total_bytes": sum(item.bytes for item in candidate.files),
        "reference_total_bytes": sum(item.bytes for item in reference.files),
        "shared_path_count": len(shared),
        "candidate_only_path_count": len(candidate_paths - reference_paths),
        "reference_only_path_count": len(reference_paths - candidate_paths),
        "shared_path_content_mismatch_count": content_mismatch_count,
        "path_set_equal": candidate_paths == reference_paths,
        "exact_manifest_match": exact,
    }


def _derive_result(
    *,
    review_status: str,
    reference_binding_verified: bool,
    exact_manifest_match: bool,
) -> tuple[str, dict[str, bool]]:
    exact_verified = (
        review_status == "reviewed" and reference_binding_verified and exact_manifest_match
    )
    if review_status == "pending_review":
        decision = "pending_review"
    elif exact_verified:
        decision = "verified_against_reviewed_reference_manifest"
    else:
        decision = "not_verified"
    return decision, {
        "reference_binding_verified": reference_binding_verified,
        "exact_manifest_match": exact_manifest_match,
        "exact_copy_identity_verified": exact_verified,
        "exact_copy_gate_satisfied": exact_verified,
        "historical_original_distribution_equivalence_verified": False,
        "quarantine_exit_authorized": False,
    }


def build_gaze_in_wild_exact_copy_review(
    readiness_record_or_path: Mapping[str, Any] | str | Path,
    *,
    candidate_root: str | Path,
    recovery_record_or_path: Mapping[str, Any] | str | Path,
    candidate_screen_record_or_path: Mapping[str, Any] | str | Path,
    reference_root: str | Path,
    reference_provenance_path: str | Path,
) -> dict[str, Any]:
    """Build a pending exact-copy review from complete candidate/reference manifests."""

    readiness = validate_gaze_in_wild_first_party_quarantine_readiness(readiness_record_or_path)
    recovery, candidate_inventory = _candidate_binding(
        readiness,
        candidate_root=candidate_root,
        recovery_record_or_path=recovery_record_or_path,
        candidate_screen_record_or_path=candidate_screen_record_or_path,
    )
    candidate_path, reference_path = _assert_distinct_trees(candidate_root, reference_root)
    reference_inventory = build_candidate_source_inventory(
        reference_path,
        dataset_key="gaze-in-the-wild",
    )
    provenance_sha256 = _reference_provenance_digest(
        reference_provenance_path,
        candidate_root=candidate_path,
        reference_root=reference_path,
    )
    comparison = _comparison_summary(candidate_inventory, reference_inventory)
    decision, result = _derive_result(
        review_status="pending_review",
        reference_binding_verified=False,
        exact_manifest_match=bool(comparison["exact_manifest_match"]),
    )
    recovery_inventory = recovery["inventory"]
    record: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "dataset": "Gaze-in-the-Wild",
        "readiness_record_fingerprint_sha256": first_party_readiness_fingerprint(readiness),
        "first_party_binding": dict(readiness["first_party_binding"]),
        "candidate_binding": {
            "candidate_kind": str(readiness["candidate_binding"]["candidate_kind"]),
            "recovery_record_fingerprint_sha256": recovery_candidate_record_fingerprint(recovery),
            "recovery_tree_fingerprint_sha256": str(
                recovery_inventory["tree_fingerprint_sha256"]
            ),
            "candidate_screen_fingerprint_sha256": str(
                readiness["candidate_binding"]["candidate_screen_fingerprint_sha256"]
            ),
            "candidate_inventory_fingerprint_sha256": (
                candidate_inventory.inventory_fingerprint_sha256
            ),
            "selected_file": dict(readiness["candidate_binding"]["selected_file"]),
        },
        "reference_binding": {
            "reference_inventory_fingerprint_sha256": (
                reference_inventory.inventory_fingerprint_sha256
            ),
            "reference_file_count": reference_inventory.file_count,
            "reference_total_bytes": sum(item.bytes for item in reference_inventory.files),
            "reference_provenance_sha256": provenance_sha256,
        },
        "comparison": comparison,
        "review": {
            "status": "pending_review",
            "reviewer": "REVIEW_REQUIRED",
            "reviewed_at": "REVIEW_REQUIRED",
            "reference_binding_verified": False,
            "evidence_basis": "REVIEW_REQUIRED",
        },
        "decision": decision,
        "result": result,
        "privacy_boundary": dict(_PRIVACY_BOUNDARY),
        "scientific_boundary": dict(_SCIENTIFIC_BOUNDARY),
        "claim_limit": CLAIM_LIMIT,
    }
    record["record_fingerprint_sha256"] = exact_copy_review_fingerprint(record)
    return record


def review_gaze_in_wild_exact_copy_record(
    record_or_path: Mapping[str, Any] | str | Path,
    *,
    reviewer: str,
    reviewed_at: str,
    reference_binding_verified: bool,
    evidence_basis: str,
) -> dict[str, Any]:
    """Apply the human reference-binding decision and deterministically derive exact-copy status."""

    record, _ = _load_json_object(record_or_path, label="Gaze-in-the-Wild exact-copy review")
    validate_gaze_in_wild_exact_copy_review(record)
    if not isinstance(reference_binding_verified, bool):
        raise ValueError("reference_binding_verified must be boolean.")
    record["review"] = {
        "status": "reviewed",
        "reviewer": _resolved(reviewer, label="reviewer"),
        "reviewed_at": _resolved(reviewed_at, label="reviewed_at"),
        "reference_binding_verified": reference_binding_verified,
        "evidence_basis": _resolved(evidence_basis, label="reference-binding evidence basis"),
    }
    comparison = record["comparison"]
    decision, result = _derive_result(
        review_status="reviewed",
        reference_binding_verified=reference_binding_verified,
        exact_manifest_match=bool(comparison["exact_manifest_match"]),
    )
    record["decision"] = decision
    record["result"] = result
    record["record_fingerprint_sha256"] = exact_copy_review_fingerprint(record)
    return record


def validate_gaze_in_wild_exact_copy_review(
    record_or_path: Mapping[str, Any] | str | Path,
) -> GazeInWildExactCopyReview:
    """Validate deterministic exact-copy review semantics without granting later authorization."""

    record, path = _load_json_object(
        record_or_path,
        label="Gaze-in-the-Wild exact-copy review",
    )
    expected_keys = {
        "record_type",
        "dataset",
        "readiness_record_fingerprint_sha256",
        "first_party_binding",
        "candidate_binding",
        "reference_binding",
        "comparison",
        "review",
        "decision",
        "result",
        "privacy_boundary",
        "scientific_boundary",
        "claim_limit",
        "record_fingerprint_sha256",
    }
    if set(record) != expected_keys:
        raise BenchmarkIntegrityError("GIW exact-copy review top-level schema drifted.")
    if record.get("record_type") != RECORD_TYPE:
        raise BenchmarkIntegrityError("GIW exact-copy review record_type drifted.")
    if record.get("dataset") != "Gaze-in-the-Wild":
        raise BenchmarkIntegrityError("GIW exact-copy review dataset identity drifted.")

    readiness_fingerprint = _sha256(
        record.get("readiness_record_fingerprint_sha256"),
        label="readiness fingerprint",
    )
    first_party = record.get("first_party_binding")
    if not isinstance(first_party, Mapping) or set(first_party) != {
        "request_fingerprint_sha256",
        "response_fingerprint_sha256",
        "correspondence_sha256",
    }:
        raise BenchmarkIntegrityError("GIW exact-copy first-party binding is invalid.")
    for key, value in first_party.items():
        _sha256(value, label=key)

    candidate = record.get("candidate_binding")
    candidate_keys = {
        "candidate_kind",
        "recovery_record_fingerprint_sha256",
        "recovery_tree_fingerprint_sha256",
        "candidate_screen_fingerprint_sha256",
        "candidate_inventory_fingerprint_sha256",
        "selected_file",
    }
    if not isinstance(candidate, Mapping) or set(candidate) != candidate_keys:
        raise BenchmarkIntegrityError("GIW exact-copy candidate binding is invalid.")
    candidate_kind = str(candidate.get("candidate_kind", "")).strip()
    if candidate_kind not in {"unknown_recovered_copy", "candidate_original_layout_unverified"}:
        raise BenchmarkIntegrityError("GIW exact-copy candidate kind is not exit-review eligible.")
    for key in (
        "recovery_record_fingerprint_sha256",
        "recovery_tree_fingerprint_sha256",
        "candidate_screen_fingerprint_sha256",
        "candidate_inventory_fingerprint_sha256",
    ):
        _sha256(candidate.get(key), label=key)
    selected = candidate.get("selected_file")
    if not isinstance(selected, Mapping) or set(selected) != {"relative_path", "sha256", "bytes"}:
        raise BenchmarkIntegrityError("GIW exact-copy selected-file binding is invalid.")
    relative_path = Path(str(selected.get("relative_path", "")))
    if (
        not str(selected.get("relative_path", ""))
        or relative_path.is_absolute()
        or ".." in relative_path.parts
    ):
        raise BenchmarkIntegrityError("GIW exact-copy selected-file path is unsafe.")
    _sha256(selected.get("sha256"), label="selected-file SHA-256")
    selected_bytes = selected.get("bytes")
    if isinstance(selected_bytes, bool) or not isinstance(selected_bytes, int) or selected_bytes <= 0:
        raise BenchmarkIntegrityError("GIW exact-copy selected-file bytes are invalid.")

    reference = record.get("reference_binding")
    if not isinstance(reference, Mapping) or set(reference) != {
        "reference_inventory_fingerprint_sha256",
        "reference_file_count",
        "reference_total_bytes",
        "reference_provenance_sha256",
    }:
        raise BenchmarkIntegrityError("GIW exact-copy reference binding is invalid.")
    reference_inventory_fingerprint = _sha256(
        reference.get("reference_inventory_fingerprint_sha256"),
        label="reference inventory fingerprint",
    )
    reference_provenance_sha256 = _sha256(
        reference.get("reference_provenance_sha256"),
        label="reference provenance fingerprint",
    )
    for key in ("reference_file_count", "reference_total_bytes"):
        value = reference.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise BenchmarkIntegrityError(f"GIW exact-copy {key} is invalid.")

    comparison = record.get("comparison")
    comparison_keys = {
        "method",
        "candidate_file_count",
        "reference_file_count",
        "candidate_total_bytes",
        "reference_total_bytes",
        "shared_path_count",
        "candidate_only_path_count",
        "reference_only_path_count",
        "shared_path_content_mismatch_count",
        "path_set_equal",
        "exact_manifest_match",
    }
    if not isinstance(comparison, Mapping) or set(comparison) != comparison_keys:
        raise BenchmarkIntegrityError("GIW exact-copy comparison summary is invalid.")
    if comparison.get("method") != "complete_relative_path_byte_size_sha256_manifest_equality":
        raise BenchmarkIntegrityError("GIW exact-copy comparison method drifted.")
    for key in (
        "candidate_file_count",
        "reference_file_count",
        "candidate_total_bytes",
        "reference_total_bytes",
        "shared_path_count",
        "candidate_only_path_count",
        "reference_only_path_count",
        "shared_path_content_mismatch_count",
    ):
        value = comparison.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise BenchmarkIntegrityError(f"GIW exact-copy comparison field {key} is invalid.")
    for key in ("path_set_equal", "exact_manifest_match"):
        if not isinstance(comparison.get(key), bool):
            raise BenchmarkIntegrityError(f"GIW exact-copy comparison field {key} must be boolean.")
    if comparison["reference_file_count"] != reference["reference_file_count"]:
        raise BenchmarkIntegrityError("GIW exact-copy reference file count drifted.")
    if comparison["reference_total_bytes"] != reference["reference_total_bytes"]:
        raise BenchmarkIntegrityError("GIW exact-copy reference total bytes drifted.")
    if comparison["exact_manifest_match"] != (
        str(candidate["candidate_inventory_fingerprint_sha256"])
        == reference_inventory_fingerprint
    ):
        raise BenchmarkIntegrityError("GIW exact-copy manifest-equality derivation drifted.")
    if comparison["exact_manifest_match"]:
        if not comparison["path_set_equal"]:
            raise BenchmarkIntegrityError("GIW exact-copy exact match requires identical paths.")
        if any(
            comparison[key] != 0
            for key in (
                "candidate_only_path_count",
                "reference_only_path_count",
                "shared_path_content_mismatch_count",
            )
        ):
            raise BenchmarkIntegrityError("GIW exact-copy exact match conflicts with difference counts.")

    review = record.get("review")
    if not isinstance(review, Mapping) or set(review) != {
        "status",
        "reviewer",
        "reviewed_at",
        "reference_binding_verified",
        "evidence_basis",
    }:
        raise BenchmarkIntegrityError("GIW exact-copy human review is invalid.")
    review_status = str(review.get("status", "")).strip().lower()
    if review_status not in _ALLOWED_REVIEW_STATUS:
        raise BenchmarkIntegrityError("GIW exact-copy review status is invalid.")
    reference_binding_verified = review.get("reference_binding_verified")
    if not isinstance(reference_binding_verified, bool):
        raise BenchmarkIntegrityError("GIW exact-copy reference-binding decision must be boolean.")
    if review_status == "pending_review":
        if reference_binding_verified:
            raise BenchmarkIntegrityError(
                "GIW exact-copy pending review cannot verify reference provenance binding."
            )
    else:
        _resolved(review.get("reviewer"), label="reviewer")
        _resolved(review.get("reviewed_at"), label="reviewed_at")
        _resolved(review.get("evidence_basis"), label="reference-binding evidence basis")

    expected_decision, expected_result = _derive_result(
        review_status=review_status,
        reference_binding_verified=reference_binding_verified,
        exact_manifest_match=bool(comparison["exact_manifest_match"]),
    )
    if record.get("decision") != expected_decision or expected_decision not in _ALLOWED_DECISIONS:
        raise BenchmarkIntegrityError("GIW exact-copy decision derivation drifted.")
    if record.get("result") != expected_result:
        raise BenchmarkIntegrityError("GIW exact-copy result derivation drifted.")
    if record.get("privacy_boundary") != _PRIVACY_BOUNDARY:
        raise BenchmarkIntegrityError("GIW exact-copy privacy boundary drifted.")
    if record.get("scientific_boundary") != _SCIENTIFIC_BOUNDARY:
        raise BenchmarkIntegrityError("GIW exact-copy scientific boundary cannot promote.")
    if record.get("claim_limit") != CLAIM_LIMIT:
        raise BenchmarkIntegrityError("GIW exact-copy claim limit drifted.")
    stored = _sha256(record.get("record_fingerprint_sha256"), label="record fingerprint")
    if stored != exact_copy_review_fingerprint(record):
        raise BenchmarkIntegrityError("GIW exact-copy record fingerprint drifted.")

    return GazeInWildExactCopyReview(
        path=path,
        record_fingerprint_sha256=stored,
        decision=expected_decision,
        exact_copy_identity_verified=bool(expected_result["exact_copy_identity_verified"]),
        readiness_record_fingerprint_sha256=readiness_fingerprint,
        recovery_record_fingerprint_sha256=str(candidate["recovery_record_fingerprint_sha256"]),
        recovery_tree_fingerprint_sha256=str(candidate["recovery_tree_fingerprint_sha256"]),
        candidate_inventory_fingerprint_sha256=str(
            candidate["candidate_inventory_fingerprint_sha256"]
        ),
        reference_inventory_fingerprint_sha256=reference_inventory_fingerprint,
        reference_provenance_sha256=reference_provenance_sha256,
    )


def verify_gaze_in_wild_exact_copy_review(
    record_or_path: Mapping[str, Any] | str | Path,
    *,
    readiness_record_or_path: Mapping[str, Any] | str | Path,
    candidate_root: str | Path,
    recovery_record_or_path: Mapping[str, Any] | str | Path,
    candidate_screen_record_or_path: Mapping[str, Any] | str | Path,
    reference_root: str | Path,
    reference_provenance_path: str | Path,
) -> GazeInWildExactCopyReview:
    """Freshly revalidate both complete trees, provenance digest, and readiness lineage."""

    validated = validate_gaze_in_wild_exact_copy_review(record_or_path)
    record, _ = _load_json_object(record_or_path, label="Gaze-in-the-Wild exact-copy review")
    readiness = validate_gaze_in_wild_first_party_quarantine_readiness(readiness_record_or_path)
    if validated.readiness_record_fingerprint_sha256 != first_party_readiness_fingerprint(readiness):
        raise BenchmarkIntegrityError("GIW exact-copy readiness-record identity drifted.")
    if record["first_party_binding"] != readiness["first_party_binding"]:
        raise BenchmarkIntegrityError("GIW exact-copy first-party lineage drifted.")

    recovery, candidate_inventory = _candidate_binding(
        readiness,
        candidate_root=candidate_root,
        recovery_record_or_path=recovery_record_or_path,
        candidate_screen_record_or_path=candidate_screen_record_or_path,
    )
    candidate_path, reference_path = _assert_distinct_trees(candidate_root, reference_root)
    reference_inventory = build_candidate_source_inventory(
        reference_path,
        dataset_key="gaze-in-the-wild",
    )
    provenance_sha256 = _reference_provenance_digest(
        reference_provenance_path,
        candidate_root=candidate_path,
        reference_root=reference_path,
    )
    expected_candidate = record["candidate_binding"]
    if expected_candidate["recovery_record_fingerprint_sha256"] != recovery_candidate_record_fingerprint(
        recovery
    ):
        raise BenchmarkIntegrityError("GIW exact-copy recovery-record identity drifted.")
    if expected_candidate["recovery_tree_fingerprint_sha256"] != str(
        recovery["inventory"]["tree_fingerprint_sha256"]
    ):
        raise BenchmarkIntegrityError("GIW exact-copy recovery-tree identity drifted.")
    if expected_candidate["candidate_inventory_fingerprint_sha256"] != (
        candidate_inventory.inventory_fingerprint_sha256
    ):
        raise BenchmarkIntegrityError("GIW exact-copy candidate inventory drifted.")
    reference = record["reference_binding"]
    if reference["reference_inventory_fingerprint_sha256"] != (
        reference_inventory.inventory_fingerprint_sha256
    ):
        raise BenchmarkIntegrityError("GIW exact-copy reference inventory drifted.")
    if reference["reference_provenance_sha256"] != provenance_sha256:
        raise BenchmarkIntegrityError("GIW exact-copy reference provenance digest drifted.")
    if record["comparison"] != _comparison_summary(candidate_inventory, reference_inventory):
        raise BenchmarkIntegrityError("GIW exact-copy live manifest comparison drifted.")

    return replace(validated, _binding_validated=True)


def write_gaze_in_wild_exact_copy_review(
    record: Mapping[str, Any],
    output: str | Path,
    *,
    candidate_root: str | Path,
    reference_root: str | Path,
    overwrite: bool = False,
) -> Path:
    """Write a validated record outside both compared trees."""

    validate_gaze_in_wild_exact_copy_review(record)
    candidate, reference = _assert_distinct_trees(candidate_root, reference_root)
    target = Path(output)
    resolved = target.resolve(strict=False)
    if (
        resolved == candidate
        or candidate in resolved.parents
        or resolved == reference
        or reference in resolved.parents
    ):
        raise BenchmarkIntegrityError("GIW exact-copy review output must be outside both trees.")
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dict(record), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    return target


def bind_verified_exact_copy_review_to_quarantine_exit(
    authorization: GazeInWildQuarantineExitAuthorization,
    exact_copy_review: GazeInWildExactCopyReview,
) -> GazeInWildQuarantineExitAuthorization:
    """Bind a freshly verified exact-copy artifact into a still-manual quarantine-exit record.

    The returned authorization remains pending. Authority, rights, redistribution, and the final
    quarantine-exit decision remain separate manual controls in ``gaze_in_wild_quarantine_exit``.
    """

    if not isinstance(authorization, GazeInWildQuarantineExitAuthorization):
        raise TypeError("authorization must be a GazeInWildQuarantineExitAuthorization instance.")
    if not isinstance(exact_copy_review, GazeInWildExactCopyReview):
        raise TypeError("exact_copy_review must be a GazeInWildExactCopyReview instance.")
    if authorization.decision != "pending":
        raise BenchmarkIntegrityError(
            "GIW structured exact-copy evidence can only be bound before the quarantine-exit "
            "decision is finalized."
        )
    if exact_copy_review._binding_validated is not True:
        raise BenchmarkIntegrityError(
            "GIW exact-copy review must be freshly revalidated against both current trees and the "
            "reference-provenance digest before it can support quarantine review."
        )
    if not exact_copy_review.exact_copy_identity_verified:
        raise BenchmarkIntegrityError(
            "GIW quarantine review cannot bind an exact-copy record whose identity decision is not "
            "verified."
        )
    if authorization.recovery_record_fingerprint_sha256 != (
        exact_copy_review.recovery_record_fingerprint_sha256
    ):
        raise BenchmarkIntegrityError("GIW exact-copy review does not bind this recovery record.")
    if authorization.recovery_tree_fingerprint_sha256 != (
        exact_copy_review.recovery_tree_fingerprint_sha256
    ):
        raise BenchmarkIntegrityError("GIW exact-copy review does not bind this recovery tree.")
    if authorization.candidate_inventory_fingerprint_sha256 != (
        exact_copy_review.candidate_inventory_fingerprint_sha256
    ):
        raise BenchmarkIntegrityError("GIW exact-copy review does not bind this candidate inventory.")

    fingerprint = exact_copy_review.record_fingerprint_sha256
    note = f"Structured GIW exact-copy review fingerprint: {fingerprint}"
    return replace(
        authorization,
        exact_copy_identity_verified=True,
        exact_copy_identity_evidence=note,
        notes=tuple(authorization.notes) + (note,),
    )
