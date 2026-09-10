"""Bind a structural VISUS source audit to a reviewed source-authority certificate."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .visus_audit import VisusSourceAuditRun, VisusSourceAuditSpec, audit_visus_source
from .visus_authoritative_source_certificate import validate_certificate_record

AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD = (
    "source_authority_certificate_fingerprint_sha256"
)
_AUTHORITY_SECTION = "source_authority"
_MAX_CERTIFICATE_BYTES = 2 * 1024**2


def _valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def load_visus_source_authority_certificate(path: str | Path) -> dict[str, Any]:
    """Load and validate one reviewed VISUS source-authority certificate JSON file."""
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise BenchmarkIntegrityError(
            "VISUS authority certificate must be a non-symlink regular file."
        )
    size = int(source.stat().st_size)
    if size <= 0 or size > _MAX_CERTIFICATE_BYTES:
        raise BenchmarkIntegrityError("VISUS authority certificate size is outside the allowed bound.")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            "VISUS authority certificate must be valid UTF-8 JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError("VISUS authority certificate must contain one JSON object.")
    return validate_certificate_record(payload)


def _verify_structural_audit(audit: VisusSourceAuditRun) -> None:
    if not isinstance(audit, VisusSourceAuditRun):
        raise TypeError("audit must be a VisusSourceAuditRun instance.")
    if audit.report.get("status") != "verified":
        raise BenchmarkIntegrityError("VISUS authority binding requires a verified source audit.")
    claimed = str(audit.report.get("report_fingerprint_sha256", ""))
    body = {
        key: value
        for key, value in audit.report.items()
        if key != "report_fingerprint_sha256"
    }
    if not _valid_sha256(claimed) or benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError(
            "VISUS authority binding received an invalid source-audit report fingerprint."
        )
    spec_fingerprint = str(audit.report.get("spec_fingerprint_sha256", ""))
    if (
        not _valid_sha256(spec_fingerprint)
        or benchmark_fingerprint(audit.spec.to_dict()) != spec_fingerprint
    ):
        raise BenchmarkIntegrityError(
            "VISUS authority binding received an invalid source-audit spec fingerprint."
        )


def _neutral_inventory_fingerprint(audit: VisusSourceAuditRun) -> str:
    """Reproduce the pre-review scaffold fingerprint without scientific role inference."""
    rows = [
        {
            "path": item.record.path,
            "sha256": item.record.sha256,
            "bytes": int(item.record.bytes),
            "role": "other",
        }
        for item in sorted(audit.files, key=lambda item: item.record.path)
    ]
    if not rows:
        raise BenchmarkIntegrityError("VISUS authority binding requires a non-empty source tree.")
    return benchmark_fingerprint(rows)


def validate_visus_source_authority_binding(
    audit: VisusSourceAuditRun,
    certificate: Mapping[str, Any],
) -> dict[str, Any]:
    """Cross-check a reviewed authority certificate against one exact structural audit."""
    _verify_structural_audit(audit)
    cert = validate_certificate_record(certificate)
    source = cert["source"]
    rights = cert["rights"]
    inventory = cert["inventory"]
    authority = cert["authority_boundary"]

    if str(audit.spec.source).strip() != str(source["source_reference"]).strip():
        raise BenchmarkIntegrityError(
            "VISUS source-audit source does not match the reviewed authority certificate."
        )
    if str(audit.spec.source_revision).strip() != str(source["source_revision"]).strip():
        raise BenchmarkIntegrityError(
            "VISUS source-audit revision does not match the reviewed authority certificate."
        )
    if str(audit.spec.license).strip() != str(rights["license_or_terms_identifier"]).strip():
        raise BenchmarkIntegrityError(
            "VISUS source-audit licence/terms identifier does not match the reviewed certificate."
        )
    if str(audit.spec.reuse_terms_source).strip() != str(rights["evidence_reference"]).strip():
        raise BenchmarkIntegrityError(
            "VISUS source-audit reuse-terms source does not match the reviewed rights evidence."
        )
    if audit.spec.reuse_terms_verified is not True or audit.spec.analysis_use_permitted is not True:
        raise BenchmarkIntegrityError(
            "VISUS authority-bound audit requires verified reuse terms and analysis permission."
        )
    if str(audit.spec.redistribution_status).strip().lower() != str(
        rights["redistribution_status"]
    ).strip().lower():
        raise BenchmarkIntegrityError(
            "VISUS source-audit redistribution status does not match the reviewed certificate."
        )

    if int(inventory["file_count"]) != len(audit.files):
        raise BenchmarkIntegrityError(
            "VISUS authority certificate file count does not match the structural audit."
        )
    neutral_fingerprint = _neutral_inventory_fingerprint(audit)
    if str(inventory["fingerprint_sha256"]) != neutral_fingerprint:
        raise BenchmarkIntegrityError(
            "VISUS authority certificate does not bind the exact audited source-tree inventory."
        )
    if int(inventory["published_participant_count"]) != int(
        audit.spec.published_participant_count
    ):
        raise BenchmarkIntegrityError(
            "VISUS authority certificate participant-count boundary does not match the audit."
        )
    if int(inventory["published_stimulus_count"]) != int(audit.spec.published_stimulus_count):
        raise BenchmarkIntegrityError(
            "VISUS authority certificate stimulus-count boundary does not match the audit."
        )
    if authority.get("source_audit_stage_authorized") is not True:
        raise BenchmarkIntegrityError(
            "VISUS authority certificate does not authorize entry into the source-audit stage."
        )

    return {
        "certificate_fingerprint_sha256": cert["certificate_fingerprint_sha256"],
        "candidate_fingerprint_sha256": cert["candidate_fingerprint_sha256"],
        "review_fingerprint_sha256": cert["review_fingerprint_sha256"],
        "source_artifact_sha256": source["artifact_sha256"],
        "rights_evidence_sha256": rights["evidence_sha256"],
        "neutral_inventory_fingerprint_sha256": neutral_fingerprint,
        "source_authority_verified": True,
        "analysis_use_permitted": True,
        "redistribution_status": rights["redistribution_status"],
        "source_audit_stage_authorized": True,
        "empirical_validation_authorized": False,
        "raw_source_redistribution_action_authorized": False,
    }


def source_authority_certificate_fingerprint(
    audit: VisusSourceAuditRun,
    *,
    required: bool = False,
) -> str | None:
    """Return the bound certificate fingerprint, validating the report-level binding."""
    section = audit.report.get(_AUTHORITY_SECTION)
    top_level = audit.report.get(AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD)
    if section is None and top_level is None:
        if required:
            raise BenchmarkIntegrityError(
                "VISUS empirical evidence requires an authority-bound source audit."
            )
        return None
    if not isinstance(section, Mapping):
        raise BenchmarkIntegrityError("VISUS source-audit authority binding is malformed.")
    nested = section.get("certificate_fingerprint_sha256")
    if not _valid_sha256(top_level) or nested != top_level:
        raise BenchmarkIntegrityError(
            "VISUS source-audit authority certificate fingerprint is inconsistent."
        )
    if section.get("source_audit_stage_authorized") is not True:
        raise BenchmarkIntegrityError("VISUS source-audit authority-stage authorization drifted.")
    if section.get("empirical_validation_authorized") is not False:
        raise BenchmarkIntegrityError(
            "VISUS source-authority binding cannot itself authorize empirical validation."
        )
    if section.get("raw_source_redistribution_action_authorized") is not False:
        raise BenchmarkIntegrityError(
            "VISUS source-authority binding cannot authorize raw-source redistribution."
        )
    return str(top_level)


def audit_visus_source_with_authority(
    root: str | Path,
    spec: VisusSourceAuditSpec,
    certificate: Mapping[str, Any],
) -> VisusSourceAuditRun:
    """Run the structural audit and cryptographically bind its exact tree to reviewed authority."""
    audit = audit_visus_source(root, spec)
    binding = validate_visus_source_authority_binding(audit, certificate)
    body = {
        key: value
        for key, value in audit.report.items()
        if key != "report_fingerprint_sha256"
    }
    if _AUTHORITY_SECTION in body or AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD in body:
        raise BenchmarkIntegrityError("VISUS source audit is already authority-bound.")
    body[_AUTHORITY_SECTION] = binding
    body[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = binding[
        "certificate_fingerprint_sha256"
    ]
    report = {**body, "report_fingerprint_sha256": benchmark_fingerprint(body)}
    bound = VisusSourceAuditRun(spec=audit.spec, files=audit.files, report=report)
    source_authority_certificate_fingerprint(bound, required=True)
    return bound
