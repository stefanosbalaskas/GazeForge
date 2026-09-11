"""Explicit scientific-review approval for native-event public Frozen Evidence."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .native_suite import validate_native_event_suite_manifest

NATIVE_SCIENTIFIC_REVIEW_FILENAME = "native-scientific-review.json"
NATIVE_SCIENTIFIC_REVIEW_SCHEMA = "gazeforge-native-event-scientific-review-v1"
NATIVE_SCIENTIFIC_REVIEW_STATUS = "approved-for-public-frozen-evidence"
NATIVE_SCIENTIFIC_REVIEW_SCOPE = "native-event-suite-publication-review"
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
        "suite",
        "suite_fingerprint_sha256",
        "report_count",
        "data_file_name",
        "data_file_sha256",
        "spec_file_name",
        "spec_fingerprint_sha256",
        "reports_verified",
    }
)
_BOUNDARY_KEYS = frozenset(
    {
        "scientific_review_completed",
        "approved_for_public_frozen_evidence",
        "cross_device_generalizability_claim_created",
        "gp3_general_validity_claim_created",
        "human_reference_ground_truth_promoted",
        "source_rights_expanded",
        "raw_source_redistribution_authorized",
        "universal_performance_validity_claim_created",
    }
)
_FALSE_BOUNDARY_KEYS = (
    "cross_device_generalizability_claim_created",
    "gp3_general_validity_claim_created",
    "human_reference_ground_truth_promoted",
    "source_rights_expanded",
    "raw_source_redistribution_authorized",
    "universal_performance_validity_claim_created",
)


def _require_exact_keys(
    value: dict[str, Any], expected: frozenset[str], *, label: str
) -> None:
    observed = frozenset(value)
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise BenchmarkIntegrityError(
            f"Native scientific-review {label} schema drifted; "
            f"missing={missing}, extra={extra}."
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
        raise BenchmarkIntegrityError(f"Native scientific review {label} must be text.")
    text = value.strip()
    if not text:
        raise BenchmarkIntegrityError(
            f"Native scientific review {label} must be non-empty."
        )
    if len(text) > _MAX_TEXT_LENGTH:
        raise BenchmarkIntegrityError(f"Native scientific review {label} is too long.")
    return text


def _utc_timestamp(value: Any) -> str:
    text = _required_text(value, label="reviewed_at")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BenchmarkIntegrityError(
            "Native scientific review reviewed_at must be an ISO-8601 timestamp."
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise BenchmarkIntegrityError(
            "Native scientific review reviewed_at must use an explicit UTC offset."
        )
    return text


def _review_root(path: str | Path) -> tuple[Path, Path]:
    source = Path(path)
    if source.name == NATIVE_SCIENTIFIC_REVIEW_FILENAME:
        return source.parent, source
    return source, source / NATIVE_SCIENTIFIC_REVIEW_FILENAME


def _review_fingerprint(record: dict[str, Any]) -> str:
    body = {
        key: value
        for key, value in record.items()
        if key != "review_fingerprint_sha256"
    }
    return benchmark_fingerprint(body)


def _suite_lineage(summary: dict[str, Any]) -> dict[str, Any]:
    source = summary.get("source")
    if not isinstance(source, dict):
        raise BenchmarkIntegrityError(
            "Native scientific review suite source identity is invalid."
        )
    lineage = {
        "suite": str(summary.get("suite", "")),
        "suite_fingerprint_sha256": str(
            summary.get("suite_fingerprint_sha256", "")
        ),
        "report_count": int(summary.get("report_count", 0)),
        "data_file_name": str(source.get("data_file_name", "")),
        "data_file_sha256": str(source.get("data_file_sha256", "")),
        "spec_file_name": str(source.get("spec_file_name", "")),
        "spec_fingerprint_sha256": str(
            source.get("spec_fingerprint_sha256", "")
        ),
        "reports_verified": bool(summary.get("reports_verified")),
    }
    if lineage["suite"] != "native-event-validation-v1":
        raise BenchmarkIntegrityError(
            "Native scientific review requires the native-event-validation-v1 suite."
        )
    if lineage["report_count"] != 3 or lineage["reports_verified"] is not True:
        raise BenchmarkIntegrityError(
            "Native scientific review requires the complete three-report verified suite."
        )
    for field in (
        "suite_fingerprint_sha256",
        "data_file_sha256",
        "spec_fingerprint_sha256",
    ):
        if not _valid_sha256(lineage[field]):
            raise BenchmarkIntegrityError(
                f"Native scientific review lineage fingerprint {field} is invalid."
            )
    for field in ("data_file_name", "spec_file_name"):
        _required_text(lineage[field], label=field)
    return lineage


def build_native_scientific_review_approval(
    path: str | Path,
    *,
    reviewer: str,
    reviewed_at: str,
    review_rationale: str,
) -> dict[str, Any]:
    """Build a manual approval bound to one exact complete native-event suite.

    Approval is never derived from performance metrics. The caller supplies the reviewer identity,
    UTC review timestamp, and rationale after a separate scientific review has occurred.
    """
    root, _ = _review_root(path)
    summary = validate_native_event_suite_manifest(root, verify_reports=True)
    if summary.get("status") != "complete":
        raise BenchmarkIntegrityError(
            "Native scientific review cannot approve an incomplete suite."
        )

    record: dict[str, Any] = {
        "schema": NATIVE_SCIENTIFIC_REVIEW_SCHEMA,
        "status": NATIVE_SCIENTIFIC_REVIEW_STATUS,
        "decision": "approved",
        "reviewer": _required_text(reviewer, label="reviewer"),
        "reviewed_at": _utc_timestamp(reviewed_at),
        "review_scope": NATIVE_SCIENTIFIC_REVIEW_SCOPE,
        "review_rationale": _required_text(
            review_rationale, label="review_rationale"
        ),
        "lineage": _suite_lineage(summary),
        "scientific_boundary": {
            "scientific_review_completed": True,
            "approved_for_public_frozen_evidence": True,
            "cross_device_generalizability_claim_created": False,
            "gp3_general_validity_claim_created": False,
            "human_reference_ground_truth_promoted": False,
            "source_rights_expanded": False,
            "raw_source_redistribution_authorized": False,
            "universal_performance_validity_claim_created": False,
        },
    }
    record["review_fingerprint_sha256"] = _review_fingerprint(record)
    return validate_native_scientific_review_record(record, suite=summary)


def validate_native_scientific_review_record(
    record: dict[str, Any],
    *,
    suite: dict[str, Any],
) -> dict[str, Any]:
    """Validate one closed-schema native approval against the exact current suite."""
    value = dict(record)
    _require_exact_keys(value, _REVIEW_KEYS, label="approval")
    if value.get("schema") != NATIVE_SCIENTIFIC_REVIEW_SCHEMA:
        raise BenchmarkIntegrityError("Native scientific review schema is invalid.")
    if value.get("status") != NATIVE_SCIENTIFIC_REVIEW_STATUS:
        raise BenchmarkIntegrityError("Native scientific review status is invalid.")
    if value.get("decision") != "approved":
        raise BenchmarkIntegrityError(
            "Native scientific review requires decision='approved'."
        )
    _required_text(value.get("reviewer"), label="reviewer")
    _utc_timestamp(value.get("reviewed_at"))
    if value.get("review_scope") != NATIVE_SCIENTIFIC_REVIEW_SCOPE:
        raise BenchmarkIntegrityError("Native scientific review scope drifted.")
    _required_text(value.get("review_rationale"), label="review_rationale")

    lineage = value.get("lineage")
    boundary = value.get("scientific_boundary")
    if not isinstance(lineage, dict) or not isinstance(boundary, dict):
        raise BenchmarkIntegrityError("Native scientific review sections are missing.")
    _require_exact_keys(lineage, _LINEAGE_KEYS, label="lineage")
    _require_exact_keys(boundary, _BOUNDARY_KEYS, label="boundary")

    expected_lineage = _suite_lineage(suite)
    if lineage != expected_lineage:
        raise BenchmarkIntegrityError(
            "Native scientific review is not bound to the exact current suite lineage."
        )
    if boundary.get("scientific_review_completed") is not True:
        raise BenchmarkIntegrityError(
            "Native scientific review must record scientific_review_completed=true."
        )
    if boundary.get("approved_for_public_frozen_evidence") is not True:
        raise BenchmarkIntegrityError(
            "Native scientific review must approve public Frozen Evidence publication."
        )
    for field in _FALSE_BOUNDARY_KEYS:
        if boundary.get(field) is not False:
            raise BenchmarkIntegrityError(
                f"Native scientific review cannot promote {field}."
            )

    observed = value.get("review_fingerprint_sha256")
    if not _valid_sha256(observed) or observed != _review_fingerprint(value):
        raise BenchmarkIntegrityError("Native scientific review fingerprint drifted.")
    return value


def validate_native_scientific_review_approval(
    path: str | Path,
) -> dict[str, Any]:
    """Require an exact complete native suite plus a separate review approval."""
    root, review_path = _review_root(path)
    suite = validate_native_event_suite_manifest(root, verify_reports=True)
    if review_path.is_symlink() or not review_path.is_file():
        raise BenchmarkIntegrityError(
            "Native public Frozen Evidence requires native-scientific-review.json."
        )
    size = int(review_path.stat().st_size)
    if size <= 0 or size > _MAX_REVIEW_BYTES:
        raise BenchmarkIntegrityError(
            "Native scientific review file size is outside the allowed bound."
        )
    try:
        payload = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            "Native scientific review file is not valid UTF-8 JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "Native scientific review file must contain a JSON object."
        )
    return validate_native_scientific_review_record(payload, suite=suite)


def write_native_scientific_review_approval(
    path: str | Path,
    *,
    reviewer: str,
    reviewed_at: str,
    review_rationale: str,
    overwrite: bool = False,
) -> Path:
    """Write one explicit approval after verifying the complete native suite."""
    root, review_path = _review_root(path)
    if review_path.exists() and not overwrite:
        raise FileExistsError(
            f"Native scientific review approval already exists: {review_path}"
        )
    root.mkdir(parents=True, exist_ok=True)
    record = build_native_scientific_review_approval(
        root,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        review_rationale=review_rationale,
    )
    review_path.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    validate_native_scientific_review_approval(root)
    return review_path
