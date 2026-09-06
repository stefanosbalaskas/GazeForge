"""Readiness bridge from reviewed GIW first-party findings to quarantine review.

This module does not authorize quarantine exit. It combines two already conservative
records: a privacy-safe reviewed first-party response and an exact, live-reverified
candidate ProcessData screen. The result is a deterministic blocker report describing
whether the remaining independent exact-copy review can begin.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_candidate_preflight import (
    candidate_processdata_screen_fingerprint,
    verify_gaze_in_wild_candidate_processdata_screen,
)
from .gaze_in_wild_first_party_resolution import (
    DATASET,
    GazeInWildFirstPartyResolutionRequest,
    validate_gaze_in_wild_first_party_resolution_response,
)

RECORD_TYPE = "gaze-in-wild-first-party-quarantine-readiness-v1"
_ALLOWED_HANDOFF_STATUS = {
    "blocked_preconditions",
    "ready_for_independent_exact_copy_review",
}
_EXIT_ELIGIBLE_CANDIDATE_KINDS = {
    "unknown_recovered_copy",
    "candidate_original_layout_unverified",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_BLOCKER_MESSAGES = {
    "response_review_required": "Complete human review of the first-party response.",
    "source_authority_verification_required": (
        "Independently verify the respondent's authority over GIW dataset-file terms."
    ),
    "authoritative_archive_location_required": (
        "Obtain a reviewed first-party authoritative archive or canonical-source location."
    ),
    "dataset_file_analysis_permission_required": (
        "Resolve explicit permission for analysis/research use of the dataset files."
    ),
    "redistribution_terms_review_required": (
        "Resolve explicit dataset-file redistribution terms."
    ),
    "redistribution_status_mapping_review_required": (
        "Review the 'prohibited' redistribution result explicitly; do not silently map it to "
        "the quarantine-authorization vocabulary."
    ),
    "exit_eligible_candidate_required": (
        "Use an exact-copy candidate kind eligible for independent quarantine-exit review."
    ),
    "independent_exact_copy_identity_review_required": (
        "Independently verify candidate exact-copy identity against the authoritative "
        "archive/canonical source."
    ),
}

_SCIENTIFIC_BOUNDARY = {
    "first_party_response_integrity_verified": True,
    "candidate_screen_current_binding_verified": True,
    "selected_processdata_structure_compatible": True,
    "first_party_response_is_quarantine_exit_authorization": False,
    "candidate_screen_is_quarantine_exit_authorization": False,
    "independent_exact_copy_identity_verified": False,
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

CLAIM_LIMIT = (
    "This handoff is a deterministic readiness/blocker report only. It binds one validated "
    "first-party response to one live-reverified quarantined candidate ProcessData screen. "
    "It does not verify exact-copy identity, authorize quarantine exit or source-audit "
    "execution, establish dataset-file redistribution semantics beyond the reviewed response, "
    "recover separate LabelData, or create empirical evidence."
)


def first_party_readiness_fingerprint(record: Mapping[str, Any]) -> str:
    """Return canonical readiness-record SHA-256 excluding the stored fingerprint."""
    body = dict(record)
    body.pop("record_fingerprint_sha256", None)
    return benchmark_fingerprint(body)


def _load_json_object(
    value: Mapping[str, Any] | str | Path,
    *,
    label: str,
) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    path = Path(value)
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"{label} must be valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(f"{label} must contain one JSON object.")
    return payload


def _sha256(value: Any, *, label: str) -> str:
    digest = str(value).strip().lower()
    if _SHA256_RE.fullmatch(digest) is None:
        raise BenchmarkIntegrityError(f"GIW first-party readiness {label} must be SHA-256.")
    return digest


def _derive_readiness(
    *,
    review_status: str,
    authority_status: str,
    archive_status: str,
    analysis_use_status: str,
    redistribution_status: str,
    candidate_kind: str,
) -> tuple[dict[str, bool], list[dict[str, str]], str]:
    response_reviewed = review_status == "reviewed"
    authority_verified = authority_status == "verified"
    archive_provided = archive_status == "provided"
    analysis_permitted = analysis_use_status == "permitted"
    redistribution_reviewed = redistribution_status != "unresolved"
    redistribution_mapping_review = redistribution_status == "prohibited"
    candidate_exit_eligible = candidate_kind in _EXIT_ELIGIBLE_CANDIDATE_KINDS

    readiness = {
        "response_reviewed": response_reviewed,
        "source_authority_verified": authority_verified,
        "authoritative_archive_location_provided": archive_provided,
        "dataset_file_analysis_use_permitted": analysis_permitted,
        "redistribution_terms_reviewed": redistribution_reviewed,
        "redistribution_status_requires_mapping_review": redistribution_mapping_review,
        "candidate_kind_exit_eligible": candidate_exit_eligible,
        "candidate_screen_current_binding_verified": True,
        "selected_processdata_structure_compatible": True,
        "independent_exact_copy_identity_verified": False,
        "ready_for_independent_exact_copy_review": False,
        "quarantine_exit_ready": False,
    }

    blocker_ids: list[str] = []
    if not response_reviewed:
        blocker_ids.append("response_review_required")
    if not authority_verified:
        blocker_ids.append("source_authority_verification_required")
    if not archive_provided:
        blocker_ids.append("authoritative_archive_location_required")
    if not analysis_permitted:
        blocker_ids.append("dataset_file_analysis_permission_required")
    if not redistribution_reviewed:
        blocker_ids.append("redistribution_terms_review_required")
    if redistribution_mapping_review:
        blocker_ids.append("redistribution_status_mapping_review_required")
    if not candidate_exit_eligible:
        blocker_ids.append("exit_eligible_candidate_required")

    preliminary_ready = not blocker_ids
    readiness["ready_for_independent_exact_copy_review"] = preliminary_ready
    blocker_ids.append("independent_exact_copy_identity_review_required")
    blockers = [
        {"id": blocker_id, "message": _BLOCKER_MESSAGES[blocker_id]}
        for blocker_id in blocker_ids
    ]
    status = (
        "ready_for_independent_exact_copy_review"
        if preliminary_ready
        else "blocked_preconditions"
    )
    return readiness, blockers, status


def _expected_next_action(status: str) -> str:
    if status == "ready_for_independent_exact_copy_review":
        return (
            "Independently compare the quarantined candidate against the reviewed first-party "
            "authoritative archive/canonical source and document exact-copy identity. Only after "
            "that separate review may a quarantine-exit authorization record be considered."
        )
    return (
        "Resolve the listed first-party/candidate preconditions, then independently verify "
        "candidate exact-copy identity before considering any quarantine-exit authorization."
    )


def build_gaze_in_wild_first_party_quarantine_readiness(
    response_record_or_path: Mapping[str, Any] | str | Path,
    correspondence_path: str | Path,
    request: GazeInWildFirstPartyResolutionRequest,
    *,
    candidate_root: str | Path,
    recovery_record_or_path: Mapping[str, Any] | str | Path,
    candidate_screen_record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Build a non-authorizing readiness report from two independently validated inputs."""
    response = validate_gaze_in_wild_first_party_resolution_response(
        response_record_or_path,
        correspondence_path,
        request,
    )
    screen = verify_gaze_in_wild_candidate_processdata_screen(
        candidate_root,
        recovery_record_or_path,
        candidate_screen_record_or_path,
    )
    candidate_kind = str(screen["candidate_kind"])
    readiness, blockers, status = _derive_readiness(
        review_status=response.review_status,
        authority_status=response.authority_status,
        archive_status=response.authoritative_archive_location_status,
        analysis_use_status=response.analysis_use_status,
        redistribution_status=response.redistribution_status,
        candidate_kind=candidate_kind,
    )
    selected = screen["selected_file"]
    record: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "dataset": DATASET,
        "handoff_status": status,
        "first_party_binding": {
            "request_fingerprint_sha256": response.request_fingerprint_sha256,
            "response_fingerprint_sha256": response.response_fingerprint_sha256,
            "correspondence_sha256": response.correspondence_sha256,
        },
        "candidate_binding": {
            "candidate_kind": candidate_kind,
            "recovery_record_fingerprint_sha256": screen[
                "recovery_record_fingerprint_sha256"
            ],
            "recovery_tree_fingerprint_sha256": screen[
                "recovery_tree_fingerprint_sha256"
            ],
            "candidate_screen_fingerprint_sha256": candidate_processdata_screen_fingerprint(
                screen
            ),
            "selected_file": {
                "relative_path": selected["relative_path"],
                "sha256": selected["sha256"],
                "bytes": selected["bytes"],
            },
        },
        "observed_response": {
            "review_status": response.review_status,
            "authority_status": response.authority_status,
            "analysis_use_status": response.analysis_use_status,
            "redistribution_status": response.redistribution_status,
            "authoritative_archive_location_status": (
                response.authoritative_archive_location_status
            ),
        },
        "readiness": readiness,
        "blockers": blockers,
        "next_required_action": _expected_next_action(status),
        "privacy_boundary": {
            "raw_correspondence_serialized": False,
            "archive_location_serialized": False,
            "correspondence_represented_by_sha256_only": True,
        },
        "scientific_boundary": dict(_SCIENTIFIC_BOUNDARY),
        "claim_limit": CLAIM_LIMIT,
    }
    record["record_fingerprint_sha256"] = first_party_readiness_fingerprint(record)
    return record


def validate_gaze_in_wild_first_party_quarantine_readiness(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate integrity and deterministic blocker derivation without granting authorization."""
    record = _load_json_object(
        record_or_path,
        label="Gaze-in-the-Wild first-party quarantine readiness",
    )
    expected_keys = {
        "record_type",
        "dataset",
        "handoff_status",
        "first_party_binding",
        "candidate_binding",
        "observed_response",
        "readiness",
        "blockers",
        "next_required_action",
        "privacy_boundary",
        "scientific_boundary",
        "claim_limit",
        "record_fingerprint_sha256",
    }
    if set(record) != expected_keys:
        raise BenchmarkIntegrityError("GIW first-party readiness top-level schema drifted.")
    if record.get("record_type") != RECORD_TYPE:
        raise BenchmarkIntegrityError("GIW first-party readiness record_type drifted.")
    if record.get("dataset") != DATASET:
        raise BenchmarkIntegrityError("GIW first-party readiness dataset identity drifted.")

    first_party = record.get("first_party_binding")
    if not isinstance(first_party, Mapping) or set(first_party) != {
        "request_fingerprint_sha256",
        "response_fingerprint_sha256",
        "correspondence_sha256",
    }:
        raise BenchmarkIntegrityError("GIW first-party readiness response binding is invalid.")
    for key in first_party:
        _sha256(first_party[key], label=key)

    candidate = record.get("candidate_binding")
    if not isinstance(candidate, Mapping) or set(candidate) != {
        "candidate_kind",
        "recovery_record_fingerprint_sha256",
        "recovery_tree_fingerprint_sha256",
        "candidate_screen_fingerprint_sha256",
        "selected_file",
    }:
        raise BenchmarkIntegrityError("GIW first-party readiness candidate binding is invalid.")
    for key in (
        "recovery_record_fingerprint_sha256",
        "recovery_tree_fingerprint_sha256",
        "candidate_screen_fingerprint_sha256",
    ):
        _sha256(candidate[key], label=key)
    candidate_kind = str(candidate.get("candidate_kind", ""))
    if not candidate_kind:
        raise BenchmarkIntegrityError("GIW first-party readiness candidate kind is missing.")
    selected = candidate.get("selected_file")
    if not isinstance(selected, Mapping) or set(selected) != {"relative_path", "sha256", "bytes"}:
        raise BenchmarkIntegrityError("GIW first-party readiness selected-file binding is invalid.")
    relative = str(selected.get("relative_path", ""))
    relative_path = Path(relative)
    if (
        not relative
        or relative_path.is_absolute()
        or relative.startswith("/")
        or ".." in relative_path.parts
    ):
        raise BenchmarkIntegrityError("GIW first-party readiness selected-file path is unsafe.")
    _sha256(selected.get("sha256"), label="selected-file SHA-256")
    bytes_ = selected.get("bytes")
    if isinstance(bytes_, bool) or not isinstance(bytes_, int) or bytes_ < 0:
        raise BenchmarkIntegrityError("GIW first-party readiness selected-file bytes are invalid.")

    observed = record.get("observed_response")
    expected_observed_keys = {
        "review_status",
        "authority_status",
        "analysis_use_status",
        "redistribution_status",
        "authoritative_archive_location_status",
    }
    if not isinstance(observed, Mapping) or set(observed) != expected_observed_keys:
        raise BenchmarkIntegrityError("GIW first-party readiness observed response is invalid.")
    review_status = str(observed["review_status"])
    authority_status = str(observed["authority_status"])
    analysis_status = str(observed["analysis_use_status"])
    redistribution_status = str(observed["redistribution_status"])
    archive_status = str(observed["authoritative_archive_location_status"])
    if review_status not in {"pending_review", "reviewed"}:
        raise BenchmarkIntegrityError("GIW first-party readiness review status is invalid.")
    if authority_status not in {"unresolved", "verified", "not_verified"}:
        raise BenchmarkIntegrityError("GIW first-party readiness authority status is invalid.")
    rights_allowed = {"unresolved", "permitted", "restricted", "prohibited"}
    if analysis_status not in rights_allowed or redistribution_status not in rights_allowed:
        raise BenchmarkIntegrityError("GIW first-party readiness rights status is invalid.")
    if archive_status not in {"unresolved", "provided", "not_available"}:
        raise BenchmarkIntegrityError("GIW first-party readiness archive status is invalid.")

    expected_readiness, expected_blockers, expected_status = _derive_readiness(
        review_status=review_status,
        authority_status=authority_status,
        archive_status=archive_status,
        analysis_use_status=analysis_status,
        redistribution_status=redistribution_status,
        candidate_kind=candidate_kind,
    )
    if record.get("readiness") != expected_readiness:
        raise BenchmarkIntegrityError("GIW first-party readiness derivation drifted.")
    if record.get("blockers") != expected_blockers:
        raise BenchmarkIntegrityError("GIW first-party readiness blocker list drifted.")
    if record.get("handoff_status") != expected_status:
        raise BenchmarkIntegrityError("GIW first-party readiness handoff status drifted.")
    if expected_status not in _ALLOWED_HANDOFF_STATUS:
        raise BenchmarkIntegrityError("GIW first-party readiness handoff status is invalid.")
    if record.get("next_required_action") != _expected_next_action(expected_status):
        raise BenchmarkIntegrityError("GIW first-party readiness next action drifted.")

    if record.get("privacy_boundary") != {
        "raw_correspondence_serialized": False,
        "archive_location_serialized": False,
        "correspondence_represented_by_sha256_only": True,
    }:
        raise BenchmarkIntegrityError("GIW first-party readiness privacy boundary drifted.")
    if record.get("scientific_boundary") != _SCIENTIFIC_BOUNDARY:
        raise BenchmarkIntegrityError(
            "GIW first-party readiness scientific boundary cannot promote."
        )
    if record.get("claim_limit") != CLAIM_LIMIT:
        raise BenchmarkIntegrityError("GIW first-party readiness claim limit drifted.")
    stored = _sha256(record.get("record_fingerprint_sha256"), label="record fingerprint")
    if stored != first_party_readiness_fingerprint(record):
        raise BenchmarkIntegrityError("GIW first-party readiness record fingerprint drifted.")
    return record


def verify_gaze_in_wild_first_party_quarantine_readiness(
    record_or_path: Mapping[str, Any] | str | Path,
    response_record_or_path: Mapping[str, Any] | str | Path,
    correspondence_path: str | Path,
    request: GazeInWildFirstPartyResolutionRequest,
    *,
    candidate_root: str | Path,
    recovery_record_or_path: Mapping[str, Any] | str | Path,
    candidate_screen_record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Revalidate both live inputs and require exact equality with the saved readiness report."""
    expected = validate_gaze_in_wild_first_party_quarantine_readiness(record_or_path)
    rebuilt = build_gaze_in_wild_first_party_quarantine_readiness(
        response_record_or_path,
        correspondence_path,
        request,
        candidate_root=candidate_root,
        recovery_record_or_path=recovery_record_or_path,
        candidate_screen_record_or_path=candidate_screen_record_or_path,
    )
    if rebuilt != expected:
        raise BenchmarkIntegrityError(
            "GIW first-party readiness no longer matches the live response/candidate bindings."
        )
    return expected


def write_gaze_in_wild_first_party_quarantine_readiness(
    record: Mapping[str, Any],
    output: str | Path,
    *,
    response_record_or_path: Mapping[str, Any] | str | Path,
    correspondence_path: str | Path,
    request: GazeInWildFirstPartyResolutionRequest,
    candidate_root: str | Path,
    recovery_record_or_path: Mapping[str, Any] | str | Path,
    candidate_screen_record_or_path: Mapping[str, Any] | str | Path,
    overwrite: bool = False,
) -> Path:
    """Write one live-reverified readiness report outside the quarantined candidate tree."""
    verify_gaze_in_wild_first_party_quarantine_readiness(
        record,
        response_record_or_path,
        correspondence_path,
        request,
        candidate_root=candidate_root,
        recovery_record_or_path=recovery_record_or_path,
        candidate_screen_record_or_path=candidate_screen_record_or_path,
    )
    root = Path(candidate_root).resolve()
    target = Path(output)
    resolved_target = target.resolve(strict=False)
    if resolved_target == root or root in resolved_target.parents:
        raise BenchmarkIntegrityError(
            "GIW first-party readiness output must be outside the quarantined candidate tree."
        )
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dict(record), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    return target
