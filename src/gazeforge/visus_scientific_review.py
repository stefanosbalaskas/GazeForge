"""Explicit scientific-review approval for VISUS public Frozen Evidence publication."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .visus_authority_binding import AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD
from .visus_evidence import validate_visus_frozen_evidence_bundle

SCIENTIFIC_REVIEW_FILENAME = "visus-scientific-review.json"
SCIENTIFIC_REVIEW_SCHEMA = "gazeforge-visus-scientific-review-v1"
SCIENTIFIC_REVIEW_STATUS = "approved-for-public-frozen-evidence"
SCIENTIFIC_REVIEW_SCOPE = "gazeforge-public-frozen-evidence-dashboard"
_MAX_REVIEW_BYTES = 128 * 1024
_MAX_TEXT_LENGTH = 4096

_REVIEW_KEYS = frozenset(
    {
        "schema",
        "status",
        "decision",
        "reviewer",
        "reviewed_at",
        "review_scope",
        "review_rationale",
        "lineage",
        "scientific_boundary",
        "review_fingerprint_sha256",
    }
)
_LINEAGE_KEYS = frozenset(
    {
        "bundle",
        "suite_fingerprint_sha256",
        "pre_authority_suite_fingerprint_sha256",
        "execution_fingerprint_sha256",
        "transition_fingerprint_sha256",
        "protocol_validation_binding_fingerprint_sha256",
        "protocol_fingerprint_sha256",
        "protocol_batch_fingerprint_sha256",
        AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
        "report_count",
        "raw_execution_input_count",
        "protocol_bound_lineage_verified",
        "frozen_evidence_eligible_for_scientific_review",
    }
)
_BOUNDARY_KEYS = frozenset(
    {
        "scientific_review_completed",
        "approved_for_public_frozen_evidence",
        "empirical_performance_claim_created",
        "formal_preregistration_verified",
        "independent_human_streams_verified",
        "human_reference_ground_truth_promoted",
        "source_authority_or_rights_expanded",
        "raw_source_redistribution_authorized",
        "evaluation_grid_boundary_changed",
        "universal_performance_validity_claim_created",
    }
)
_FALSE_BOUNDARY_KEYS = (
    "empirical_performance_claim_created",
    "formal_preregistration_verified",
    "independent_human_streams_verified",
    "human_reference_ground_truth_promoted",
    "source_authority_or_rights_expanded",
    "raw_source_redistribution_authorized",
    "evaluation_grid_boundary_changed",
    "universal_performance_validity_claim_created",
)


def _require_exact_keys(value: dict[str, Any], expected: frozenset[str], *, label: str) -> None:
    observed = frozenset(value)
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise BenchmarkIntegrityError(
            f"VISUS {label} schema drifted; missing={missing}, extra={extra}."
        )


def _valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def _required_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        raise BenchmarkIntegrityError(f"VISUS scientific review {label} must be text.")
    text = value.strip()
    if not text:
        raise BenchmarkIntegrityError(f"VISUS scientific review {label} must be non-empty.")
    if len(text) > _MAX_TEXT_LENGTH:
        raise BenchmarkIntegrityError(f"VISUS scientific review {label} is too long.")
    return text


def _utc_timestamp(value: Any) -> str:
    text = _required_text(value, label="reviewed_at")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BenchmarkIntegrityError(
            "VISUS scientific review reviewed_at must be an ISO-8601 timestamp."
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise BenchmarkIntegrityError(
            "VISUS scientific review reviewed_at must use an explicit UTC offset."
        )
    return text


def _review_root(path: str | Path) -> tuple[Path, Path]:
    source = Path(path)
    if source.name == SCIENTIFIC_REVIEW_FILENAME:
        return source.parent, source
    return source, source / SCIENTIFIC_REVIEW_FILENAME


def _review_fingerprint(record: dict[str, Any]) -> str:
    body = {key: value for key, value in record.items() if key != "review_fingerprint_sha256"}
    return benchmark_fingerprint(body)


def _bundle_lineage(bundle: dict[str, Any]) -> dict[str, Any]:
    source = bundle.get("source")
    if not isinstance(source, dict):
        raise BenchmarkIntegrityError("VISUS scientific review bundle source identity is invalid.")
    authority = source.get(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD)
    if not _valid_sha256(authority):
        raise BenchmarkIntegrityError(
            "VISUS scientific review bundle authority-certificate fingerprint is invalid."
        )
    return {
        "bundle": str(bundle["bundle"]),
        "suite_fingerprint_sha256": str(bundle["suite_fingerprint_sha256"]),
        "pre_authority_suite_fingerprint_sha256": str(
            bundle["pre_authority_suite_fingerprint_sha256"]
        ),
        "execution_fingerprint_sha256": str(bundle["execution_fingerprint_sha256"]),
        "transition_fingerprint_sha256": str(bundle["transition_fingerprint_sha256"]),
        "protocol_validation_binding_fingerprint_sha256": str(
            bundle["protocol_validation_binding_fingerprint_sha256"]
        ),
        "protocol_fingerprint_sha256": str(bundle["protocol_fingerprint_sha256"]),
        "protocol_batch_fingerprint_sha256": str(bundle["protocol_batch_fingerprint_sha256"]),
        AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: str(authority),
        "report_count": int(bundle["report_count"]),
        "raw_execution_input_count": int(bundle["raw_execution_input_count"]),
        "protocol_bound_lineage_verified": bool(bundle["protocol_bound_lineage_verified"]),
        "frozen_evidence_eligible_for_scientific_review": bool(
            bundle["frozen_evidence_eligible_for_scientific_review"]
        ),
    }


def build_visus_scientific_review_approval(
    path: str | Path,
    *,
    reviewer: str,
    reviewed_at: str,
    review_rationale: str,
    protocol_validation_binding_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build an explicit manual approval bound to an already eligible VISUS v3 lineage.

    This function never derives approval from metrics. The caller supplies the reviewer identity,
    UTC review timestamp, and rationale after a separate scientific review has occurred.
    """
    root, _ = _review_root(path)
    bundle = validate_visus_frozen_evidence_bundle(
        root,
        protocol_validation_binding_path=protocol_validation_binding_path,
    )
    if bundle.get("frozen_evidence_eligible_for_scientific_review") is not True:
        raise BenchmarkIntegrityError(
            "VISUS scientific review cannot approve a bundle that is not review-eligible."
        )
    if bundle.get("scientific_review_completed") is not False:
        raise BenchmarkIntegrityError(
            "VISUS v3 eligibility unexpectedly self-promoted scientific review completion."
        )
    if bundle.get("empirical_performance_claim_created") is not False:
        raise BenchmarkIntegrityError(
            "VISUS v3 eligibility unexpectedly promoted an empirical-performance claim."
        )
    if bundle.get("formal_preregistration_verified") is not False:
        raise BenchmarkIntegrityError(
            "VISUS v3 eligibility unexpectedly promoted formal preregistration."
        )

    record: dict[str, Any] = {
        "schema": SCIENTIFIC_REVIEW_SCHEMA,
        "status": SCIENTIFIC_REVIEW_STATUS,
        "decision": "approved",
        "reviewer": _required_text(reviewer, label="reviewer"),
        "reviewed_at": _utc_timestamp(reviewed_at),
        "review_scope": SCIENTIFIC_REVIEW_SCOPE,
        "review_rationale": _required_text(review_rationale, label="review_rationale"),
        "lineage": _bundle_lineage(bundle),
        "scientific_boundary": {
            "scientific_review_completed": True,
            "approved_for_public_frozen_evidence": True,
            "empirical_performance_claim_created": False,
            "formal_preregistration_verified": False,
            "independent_human_streams_verified": False,
            "human_reference_ground_truth_promoted": False,
            "source_authority_or_rights_expanded": False,
            "raw_source_redistribution_authorized": False,
            "evaluation_grid_boundary_changed": False,
            "universal_performance_validity_claim_created": False,
        },
    }
    record["review_fingerprint_sha256"] = _review_fingerprint(record)
    return validate_visus_scientific_review_record(record, bundle=bundle)


def validate_visus_scientific_review_record(
    record: dict[str, Any],
    *,
    bundle: dict[str, Any],
) -> dict[str, Any]:
    """Validate one closed-schema review approval against an exact eligible VISUS bundle."""
    value = dict(record)
    _require_exact_keys(value, _REVIEW_KEYS, label="scientific-review approval")
    if value.get("schema") != SCIENTIFIC_REVIEW_SCHEMA:
        raise BenchmarkIntegrityError("VISUS scientific review schema is invalid.")
    if value.get("status") != SCIENTIFIC_REVIEW_STATUS:
        raise BenchmarkIntegrityError("VISUS scientific review status is invalid.")
    if value.get("decision") != "approved":
        raise BenchmarkIntegrityError("VISUS scientific review requires decision='approved'.")
    _required_text(value.get("reviewer"), label="reviewer")
    _utc_timestamp(value.get("reviewed_at"))
    if value.get("review_scope") != SCIENTIFIC_REVIEW_SCOPE:
        raise BenchmarkIntegrityError("VISUS scientific review scope drifted.")
    _required_text(value.get("review_rationale"), label="review_rationale")

    lineage = value.get("lineage")
    boundary = value.get("scientific_boundary")
    if not isinstance(lineage, dict) or not isinstance(boundary, dict):
        raise BenchmarkIntegrityError("VISUS scientific review sections are missing.")
    _require_exact_keys(lineage, _LINEAGE_KEYS, label="scientific-review lineage")
    _require_exact_keys(boundary, _BOUNDARY_KEYS, label="scientific-review boundary")

    expected_lineage = _bundle_lineage(bundle)
    if lineage != expected_lineage:
        raise BenchmarkIntegrityError(
            "VISUS scientific review is not bound to the exact current v3 evidence lineage."
        )
    if lineage["protocol_bound_lineage_verified"] is not True:
        raise BenchmarkIntegrityError(
            "VISUS scientific review requires verified protocol-bound lineage."
        )
    if lineage["frozen_evidence_eligible_for_scientific_review"] is not True:
        raise BenchmarkIntegrityError(
            "VISUS scientific review requires v3 scientific-review eligibility."
        )
    for field in (
        "suite_fingerprint_sha256",
        "pre_authority_suite_fingerprint_sha256",
        "execution_fingerprint_sha256",
        "transition_fingerprint_sha256",
        "protocol_validation_binding_fingerprint_sha256",
        "protocol_fingerprint_sha256",
        "protocol_batch_fingerprint_sha256",
        AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
    ):
        if not _valid_sha256(lineage.get(field)):
            raise BenchmarkIntegrityError(
                f"VISUS scientific review lineage fingerprint {field} is invalid."
            )
    if lineage["report_count"] <= 0 or lineage["raw_execution_input_count"] != 5:
        raise BenchmarkIntegrityError(
            "VISUS scientific review lineage cardinality is inconsistent with the v3 gate."
        )

    if boundary.get("scientific_review_completed") is not True:
        raise BenchmarkIntegrityError(
            "VISUS scientific review must explicitly record scientific_review_completed=true."
        )
    if boundary.get("approved_for_public_frozen_evidence") is not True:
        raise BenchmarkIntegrityError(
            "VISUS scientific review must explicitly approve public Frozen Evidence publication."
        )
    for field in _FALSE_BOUNDARY_KEYS:
        if boundary.get(field) is not False:
            raise BenchmarkIntegrityError(
                f"VISUS scientific review cannot promote {field}."
            )

    observed = value.get("review_fingerprint_sha256")
    if not _valid_sha256(observed) or observed != _review_fingerprint(value):
        raise BenchmarkIntegrityError("VISUS scientific review fingerprint drifted.")
    return value


def validate_visus_scientific_review_approval(
    path: str | Path,
    *,
    protocol_validation_binding_path: str | Path | None = None,
) -> dict[str, Any]:
    """Require an exact v3 lineage plus a separate explicit scientific-review approval."""
    root, review_path = _review_root(path)
    bundle = validate_visus_frozen_evidence_bundle(
        root,
        protocol_validation_binding_path=protocol_validation_binding_path,
    )
    if review_path.is_symlink() or not review_path.is_file():
        raise BenchmarkIntegrityError(
            "VISUS public Frozen Evidence requires visus-scientific-review.json."
        )
    size = int(review_path.stat().st_size)
    if size <= 0 or size > _MAX_REVIEW_BYTES:
        raise BenchmarkIntegrityError("VISUS scientific review file size is outside the allowed bound.")
    try:
        payload = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError("VISUS scientific review file is not valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError("VISUS scientific review file must contain a JSON object.")
    return validate_visus_scientific_review_record(payload, bundle=bundle)


def write_visus_scientific_review_approval(
    path: str | Path,
    *,
    reviewer: str,
    reviewed_at: str,
    review_rationale: str,
    protocol_validation_binding_path: str | Path | None = None,
    overwrite: bool = False,
) -> Path:
    """Write one explicit review approval after validating the full v3 eligibility lineage."""
    root, review_path = _review_root(path)
    if review_path.exists() and not overwrite:
        raise FileExistsError(f"VISUS scientific review approval already exists: {review_path}")
    root.mkdir(parents=True, exist_ok=True)
    record = build_visus_scientific_review_approval(
        root,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        review_rationale=review_rationale,
        protocol_validation_binding_path=protocol_validation_binding_path,
    )
    review_path.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    validate_visus_scientific_review_approval(
        root,
        protocol_validation_binding_path=protocol_validation_binding_path,
    )
    return review_path
