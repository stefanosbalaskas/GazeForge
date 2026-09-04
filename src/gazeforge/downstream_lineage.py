"""Fail-closed lineage gates for downstream benchmark preparation and validation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .gaze_in_wild_audit import GazeInWildSourceAuditRun
from .schema import GazeFrame
from .source_audit_lineage import SourceAuditLineageReceipt


def _normalise_fingerprints(values: Mapping[str, Any], *, field_name: str) -> dict[str, str]:
    if not isinstance(values, Mapping):
        raise TypeError(f"{field_name} must be a mapping.")
    normalized = {str(key): str(value).strip().lower() for key, value in values.items()}
    if any(len(value) != 64 for value in normalized.values()):
        raise BenchmarkIntegrityError(f"{field_name} contains an invalid SHA-256 fingerprint.")
    return normalized


def validate_source_audit_lineage_binding(
    lineage: SourceAuditLineageReceipt,
    *,
    dataset_key: str,
    audit_report_fingerprint_sha256: str,
    authorized_spec_fingerprint_sha256: str,
    source_manifest_fingerprints_sha256: Mapping[str, Any],
    source_revision: str,
) -> str:
    """Require one lineage receipt to match the exact audited source being consumed.

    This gate does not create or upgrade empirical evidence. It only prevents a downstream
    benchmark from accepting a verified source audit that has been detached from the exact
    lineage receipt created for that audit.
    """
    if not isinstance(lineage, SourceAuditLineageReceipt):
        raise TypeError("lineage must be a SourceAuditLineageReceipt instance.")
    key = str(dataset_key).strip().lower()
    if lineage.dataset_key != key:
        raise BenchmarkIntegrityError(
            "Source-audit lineage dataset does not match the downstream dataset."
        )
    report_fingerprint = str(audit_report_fingerprint_sha256).strip().lower()
    if lineage.audit_report_fingerprint_sha256 != report_fingerprint:
        raise BenchmarkIntegrityError(
            "Source-audit lineage report fingerprint does not match the audited source."
        )
    spec_fingerprint = str(authorized_spec_fingerprint_sha256).strip().lower()
    if lineage.authorized_spec_fingerprint_sha256 != spec_fingerprint:
        raise BenchmarkIntegrityError(
            "Source-audit lineage authorized-spec fingerprint does not match the audited source."
        )
    revision = str(source_revision).strip()
    if lineage.source_revision != revision:
        raise BenchmarkIntegrityError(
            "Source-audit lineage source revision does not match the audited source."
        )
    expected_manifests = _normalise_fingerprints(
        source_manifest_fingerprints_sha256,
        field_name="source_manifest_fingerprints_sha256",
    )
    if dict(lineage.source_manifest_fingerprints_sha256) != expected_manifests:
        raise BenchmarkIntegrityError(
            "Source-audit lineage manifest fingerprints do not match the audited source."
        )
    payload = lineage.to_dict()
    return str(payload["receipt_fingerprint_sha256"])


def validate_gaze_in_wild_audit_lineage(
    audit: GazeInWildSourceAuditRun,
    lineage: SourceAuditLineageReceipt,
) -> str:
    """Bind a Gaze-in-the-Wild audit run to its exact lineage receipt."""
    if not isinstance(audit, GazeInWildSourceAuditRun):
        raise TypeError("audit must be a GazeInWildSourceAuditRun instance.")
    label_inventory = audit.report.get("label_inventory", {})
    process_inventory = audit.report.get("process_inventory", {})
    return validate_source_audit_lineage_binding(
        lineage,
        dataset_key="gaze-in-the-wild",
        audit_report_fingerprint_sha256=audit.report.get("report_fingerprint_sha256", ""),
        authorized_spec_fingerprint_sha256=audit.report.get("spec_fingerprint_sha256", ""),
        source_manifest_fingerprints_sha256={
            "label": label_inventory.get("manifest_fingerprint_sha256", ""),
            "process": process_inventory.get("manifest_fingerprint_sha256", ""),
        },
        source_revision=audit.spec.source_revision,
    )


def validate_hollywood2_gaze_lineage(
    gaze: GazeFrame,
    lineage: SourceAuditLineageReceipt,
) -> str:
    """Bind an audited Hollywood2EM GazeFrame to its exact lineage receipt."""
    if not isinstance(gaze, GazeFrame):
        raise TypeError("gaze must be a GazeFrame instance.")
    return validate_source_audit_lineage_binding(
        lineage,
        dataset_key="hollywood2em",
        audit_report_fingerprint_sha256=gaze.metadata.get(
            "source_audit_report_fingerprint_sha256", ""
        ),
        authorized_spec_fingerprint_sha256=gaze.metadata.get(
            "source_audit_spec_fingerprint_sha256", ""
        ),
        source_manifest_fingerprints_sha256={
            "source": gaze.metadata.get("source_manifest_fingerprint_sha256", "")
        },
        source_revision=gaze.metadata.get("source_revision", ""),
    )
