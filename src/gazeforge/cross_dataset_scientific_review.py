"""Explicit scientific-review approval for cross-dataset public Frozen Evidence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .cross_dataset_evidence import (
    CROSS_DATASET_EVIDENCE_SCHEMA,
    CROSS_DATASET_EXPECTED_DATASETS,
    load_cross_dataset_frozen_report,
    validate_cross_dataset_frozen_report,
)
from .exceptions import BenchmarkIntegrityError

CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME = "cross-dataset-scientific-review.json"
CROSS_DATASET_SCIENTIFIC_REVIEW_SCHEMA = "gazeforge-cross-dataset-scientific-review-v1"
CROSS_DATASET_SCIENTIFIC_REVIEW_STATUS = "approved-for-public-frozen-evidence"
CROSS_DATASET_SCIENTIFIC_REVIEW_SCOPE = "cross-dataset-report-publication-review"
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
        "report_file_name",
        "report_fingerprint_sha256",
        "cross_dataset_validation_fingerprint_sha256",
        "dataset_ids",
        "hollywood2_lineage_receipt_fingerprint_sha256",
        "hollywood2_audit_report_fingerprint_sha256",
        "hollywood2_source_manifest_fingerprint_sha256",
        "report_verified",
    }
)
_BOUNDARY = {
    "scientific_review_completed": True,
    "approved_for_public_frozen_evidence": True,
    "native_60hz_validity_claim_created": False,
    "gp3_validity_claim_created": False,
    "universal_cross_dataset_generalizability_claim_created": False,
    "human_reference_ground_truth_promoted": False,
    "source_rights_expanded": False,
    "raw_source_redistribution_authorized": False,
}


def _require_exact_keys(
    value: Mapping[str, Any], expected: frozenset[str], *, label: str
) -> None:
    observed = frozenset(value)
    if observed != expected:
        raise BenchmarkIntegrityError(
            f"Cross-dataset scientific-review {label} schema drifted; "
            f"missing={sorted(expected - observed)}, extra={sorted(observed - expected)}."
        )


def _valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _required_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        raise BenchmarkIntegrityError(
            f"Cross-dataset scientific review {label} must be text."
        )
    text = value.strip()
    if not text:
        raise BenchmarkIntegrityError(
            f"Cross-dataset scientific review {label} must be non-empty."
        )
    if len(text) > _MAX_TEXT_LENGTH:
        raise BenchmarkIntegrityError(
            f"Cross-dataset scientific review {label} is too long."
        )
    return text


def _utc_timestamp(value: Any) -> str:
    text = _required_text(value, label="reviewed_at")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BenchmarkIntegrityError(
            "Cross-dataset scientific review reviewed_at must be ISO-8601."
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise BenchmarkIntegrityError(
            "Cross-dataset scientific review reviewed_at must use explicit UTC."
        )
    return text


def _review_fingerprint(record: Mapping[str, Any]) -> str:
    return benchmark_fingerprint(
        {
            key: value
            for key, value in record.items()
            if key != "review_fingerprint_sha256"
        }
    )


def _safe_report_name(value: Any) -> str:
    name = _required_text(value, label="lineage.report_file_name")
    path = Path(name)
    if path.name != name or name in {".", ".."}:
        raise BenchmarkIntegrityError(
            "Cross-dataset scientific-review report_file_name must be a sibling basename."
        )
    return name


def _lineage_from_report(
    report_path: Path,
    report: Mapping[str, Any],
) -> dict[str, Any]:
    protocol = report.get("protocol")
    if not isinstance(protocol, Mapping):
        raise BenchmarkIntegrityError("Cross-dataset report protocol is invalid.")
    design = protocol.get("validation_design")
    reports = protocol.get("dataset_reports")
    if not isinstance(design, Mapping) or not isinstance(reports, Mapping):
        raise BenchmarkIntegrityError("Cross-dataset report provenance sections are invalid.")
    hollywood = reports.get("Hollywood2EM")
    if not isinstance(hollywood, Mapping):
        raise BenchmarkIntegrityError("Cross-dataset Hollywood2EM provenance is missing.")
    validation_fingerprint = protocol.get(
        "cross_dataset_validation_fingerprint_sha256"
    )
    report_fingerprint = report.get("report_fingerprint_sha256")
    for label, value in (
        ("report_fingerprint_sha256", report_fingerprint),
        ("cross_dataset_validation_fingerprint_sha256", validation_fingerprint),
        (
            "hollywood2_lineage_receipt_fingerprint_sha256",
            hollywood.get("source_audit_lineage_receipt_fingerprint_sha256"),
        ),
        (
            "hollywood2_audit_report_fingerprint_sha256",
            hollywood.get("source_audit_report_fingerprint_sha256"),
        ),
        (
            "hollywood2_source_manifest_fingerprint_sha256",
            hollywood.get("source_manifest_fingerprint_sha256"),
        ),
    ):
        if not _valid_sha256(value):
            raise BenchmarkIntegrityError(
                f"Cross-dataset scientific-review lineage {label} is invalid."
            )
    dataset_ids = design.get("dataset_ids")
    valid_dataset_ids = (
        isinstance(dataset_ids, list)
        and tuple(sorted(map(str, dataset_ids))) == CROSS_DATASET_EXPECTED_DATASETS
    )
    if not valid_dataset_ids:
        raise BenchmarkIntegrityError(
            "Cross-dataset scientific-review dataset identity drifted."
        )
    if protocol.get("evidence_schema") != CROSS_DATASET_EVIDENCE_SCHEMA:
        raise BenchmarkIntegrityError(
            "Cross-dataset scientific-review report schema drifted."
        )
    return {
        "report_file_name": report_path.name,
        "report_fingerprint_sha256": str(report_fingerprint),
        "cross_dataset_validation_fingerprint_sha256": str(validation_fingerprint),
        "dataset_ids": list(CROSS_DATASET_EXPECTED_DATASETS),
        "hollywood2_lineage_receipt_fingerprint_sha256": str(
            hollywood["source_audit_lineage_receipt_fingerprint_sha256"]
        ),
        "hollywood2_audit_report_fingerprint_sha256": str(
            hollywood["source_audit_report_fingerprint_sha256"]
        ),
        "hollywood2_source_manifest_fingerprint_sha256": str(
            hollywood["source_manifest_fingerprint_sha256"]
        ),
        "report_verified": True,
    }


def build_cross_dataset_scientific_review_approval(
    report_path: str | Path,
    *,
    reviewer: str,
    reviewed_at: str,
    review_rationale: str,
) -> dict[str, Any]:
    """Build an explicit approval bound to one exact cross-dataset report."""
    source = Path(report_path)
    report = load_cross_dataset_frozen_report(source)
    record: dict[str, Any] = {
        "schema": CROSS_DATASET_SCIENTIFIC_REVIEW_SCHEMA,
        "status": CROSS_DATASET_SCIENTIFIC_REVIEW_STATUS,
        "decision": "approved",
        "reviewer": _required_text(reviewer, label="reviewer"),
        "reviewed_at": _utc_timestamp(reviewed_at),
        "review_scope": CROSS_DATASET_SCIENTIFIC_REVIEW_SCOPE,
        "review_rationale": _required_text(
            review_rationale,
            label="review_rationale",
        ),
        "lineage": _lineage_from_report(source, report),
        "scientific_boundary": dict(_BOUNDARY),
    }
    record["review_fingerprint_sha256"] = _review_fingerprint(record)
    return validate_cross_dataset_scientific_review_record(
        record,
        report_path=source,
        report=report,
    )


def validate_cross_dataset_scientific_review_record(
    record: Mapping[str, Any],
    *,
    report_path: str | Path,
    report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate one closed-schema approval against the exact report bytes."""
    value = dict(record)
    _require_exact_keys(value, _REVIEW_KEYS, label="approval")
    if value.get("schema") != CROSS_DATASET_SCIENTIFIC_REVIEW_SCHEMA:
        raise BenchmarkIntegrityError("Cross-dataset scientific review schema is invalid.")
    if value.get("status") != CROSS_DATASET_SCIENTIFIC_REVIEW_STATUS:
        raise BenchmarkIntegrityError("Cross-dataset scientific review status is invalid.")
    if value.get("decision") != "approved":
        raise BenchmarkIntegrityError("Cross-dataset scientific review requires approval.")
    _required_text(value.get("reviewer"), label="reviewer")
    _utc_timestamp(value.get("reviewed_at"))
    if value.get("review_scope") != CROSS_DATASET_SCIENTIFIC_REVIEW_SCOPE:
        raise BenchmarkIntegrityError("Cross-dataset scientific review scope drifted.")
    _required_text(value.get("review_rationale"), label="review_rationale")

    lineage = value.get("lineage")
    if not isinstance(lineage, Mapping):
        raise BenchmarkIntegrityError("Cross-dataset scientific-review lineage is missing.")
    _require_exact_keys(lineage, _LINEAGE_KEYS, label="lineage")
    if value.get("scientific_boundary") != _BOUNDARY:
        raise BenchmarkIntegrityError(
            "Cross-dataset scientific-review claim boundary drifted."
        )

    source = Path(report_path)
    if report is None:
        current_report = load_cross_dataset_frozen_report(source)
    else:
        current_report = validate_cross_dataset_frozen_report(report)
    expected_lineage = _lineage_from_report(source, current_report)
    if dict(lineage) != expected_lineage:
        raise BenchmarkIntegrityError(
            "Cross-dataset scientific review is not bound to the exact current report lineage."
        )
    observed = value.get("review_fingerprint_sha256")
    if not _valid_sha256(observed) or observed != _review_fingerprint(value):
        raise BenchmarkIntegrityError(
            "Cross-dataset scientific review fingerprint drifted."
        )
    return value


def _approval_paths(path: str | Path) -> tuple[Path, Path]:
    source = Path(path)
    if source.name == CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME:
        return source.parent, source
    return source, source / CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME


def validate_cross_dataset_scientific_review_approval(
    path: str | Path,
) -> dict[str, Any]:
    """Require one exact report plus its separate scientific-review approval."""
    root, review_path = _approval_paths(path)
    if review_path.is_symlink() or not review_path.is_file():
        raise BenchmarkIntegrityError(
            "Cross-dataset public Frozen Evidence requires "
            "cross-dataset-scientific-review.json."
        )
    size = int(review_path.stat().st_size)
    if size <= 0 or size > _MAX_REVIEW_BYTES:
        raise BenchmarkIntegrityError(
            "Cross-dataset scientific review file size is outside the allowed bound."
        )
    try:
        payload = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            "Cross-dataset scientific review file is not valid UTF-8 JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "Cross-dataset scientific review file must contain an object."
        )
    lineage = payload.get("lineage")
    if not isinstance(lineage, Mapping):
        raise BenchmarkIntegrityError("Cross-dataset scientific-review lineage is missing.")
    report_name = _safe_report_name(lineage.get("report_file_name"))
    report_path = root / report_name
    if report_path.is_symlink() or not report_path.is_file():
        raise BenchmarkIntegrityError(
            "Cross-dataset scientific review references a missing or non-regular report."
        )
    report = load_cross_dataset_frozen_report(report_path)
    return validate_cross_dataset_scientific_review_record(
        payload,
        report_path=report_path,
        report=report,
    )


def write_cross_dataset_scientific_review_approval(
    report_path: str | Path,
    *,
    reviewer: str,
    reviewed_at: str,
    review_rationale: str,
    overwrite: bool = False,
) -> Path:
    """Write one manual approval after validating the exact frozen report."""
    source = Path(report_path)
    if source.is_symlink() or not source.is_file():
        raise BenchmarkIntegrityError(
            "Cross-dataset scientific review requires an existing regular report file."
        )
    review_path = source.parent / CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME
    if review_path.exists() and not overwrite:
        raise FileExistsError(
            f"Cross-dataset scientific review approval already exists: {review_path}"
        )
    record = build_cross_dataset_scientific_review_approval(
        source,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        review_rationale=review_rationale,
    )
    review_path.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    validate_cross_dataset_scientific_review_approval(source.parent)
    return review_path
