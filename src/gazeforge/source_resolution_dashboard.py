"""Public governance dashboard for benchmark source-resolution checkpoints."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .source_resolution import (
    validate_source_resolution_record,
    validate_source_resolution_records,
)
from .source_resolution_discovery import discover_source_resolution_paths
from .source_resolution_lock import validate_source_resolution_bundle_lock

_TABLE_HEADER = (
    "| Dataset | Checked | Resolution status | Analysis use | Raw redistribution | "
    "Audit ready | Empirical evidence | Record fingerprint |"
)
_TABLE_SEPARATOR = "| --- | --- | --- | --- | --- | --- | --- | --- |"


@dataclass(frozen=True, slots=True)
class SourceResolutionDashboard:
    """Integrity-checked source-resolution records prepared for public status reporting."""

    records: tuple[dict[str, Any], ...]
    rows: tuple[dict[str, str], ...]
    source_files: tuple[str, ...]
    bundle_fingerprint_sha256: str
    reviewed_snapshot: bool = False
    reviewed_on: str | None = None
    lock_fingerprint_sha256: str | None = None
    lock_source_file: str | None = None


def _dashboard_row(summary: dict[str, Any], source_file: str) -> dict[str, str]:
    rights = summary.get("rights")
    if not isinstance(rights, dict):
        raise BenchmarkIntegrityError(
            "Validated source-resolution summary is missing the common rights object."
        )
    return {
        "dataset": str(summary["dataset"]),
        "dataset_key": str(summary["dataset_key"]),
        "checked_on": str(summary["checked_on"]),
        "status": str(summary["status"]),
        "analysis_use_terms_status": str(rights["analysis_use_terms_status"]),
        "raw_data_redistribution_terms_status": str(
            rights["raw_data_redistribution_terms_status"]
        ),
        "source_audit_ready": str(bool(summary["source_audit_ready"])).lower(),
        "empirical_evidence_created": str(
            bool(summary["empirical_evidence_created"])
        ).lower(),
        "record_fingerprint_sha256": str(summary["record_fingerprint_sha256"]),
        "source_file": source_file,
    }


def build_source_resolution_dashboard(
    root: str | Path,
    *,
    lock_path: str | Path | None = None,
) -> SourceResolutionDashboard:
    """Discover and validate source-resolution checkpoints and an optional reviewed lock.

    Supplying ``lock_path`` upgrades only the dashboard's governance-integrity statement: the live
    checkpoint bundle must exactly match the separately frozen reviewed snapshot. It does not
    itself upgrade source authority, rights, source-audit readiness, or empirical status.
    """
    directory = Path(root)
    paths = discover_source_resolution_paths(directory)
    bundle = validate_source_resolution_records(paths)

    source_by_dataset: dict[str, str] = {}
    for path in paths:
        summary = validate_source_resolution_record(path)
        dataset_key = str(summary["dataset_key"])
        if dataset_key in source_by_dataset:
            raise BenchmarkIntegrityError(
                f"Duplicate source-resolution checkpoint discovered for {dataset_key!r}."
            )
        try:
            source_by_dataset[dataset_key] = str(path.relative_to(directory))
        except ValueError:
            source_by_dataset[dataset_key] = str(path)

    records = tuple(dict(record) for record in bundle["records"])
    rows = tuple(
        _dashboard_row(record, source_by_dataset[str(record["dataset_key"])])
        for record in records
    )

    reviewed_snapshot = False
    reviewed_on: str | None = None
    lock_fingerprint: str | None = None
    lock_source_file: str | None = None
    if lock_path is not None:
        lock_source = Path(lock_path)
        lock = validate_source_resolution_bundle_lock(lock_source, directory)
        if str(lock["bundle_fingerprint_sha256"]) != str(bundle["bundle_fingerprint_sha256"]):
            raise BenchmarkIntegrityError(
                "Reviewed source-resolution lock does not identify the dashboard bundle."
            )
        reviewed_snapshot = True
        reviewed_on = str(lock["reviewed_on"])
        lock_fingerprint = str(lock["lock_fingerprint_sha256"])
        lock_source_file = str(lock_source)

    return SourceResolutionDashboard(
        records=records,
        rows=rows,
        source_files=tuple(row["source_file"] for row in rows),
        bundle_fingerprint_sha256=str(bundle["bundle_fingerprint_sha256"]),
        reviewed_snapshot=reviewed_snapshot,
        reviewed_on=reviewed_on,
        lock_fingerprint_sha256=lock_fingerprint,
        lock_source_file=lock_source_file,
    )


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_source_resolution_dashboard_markdown(
    dashboard: SourceResolutionDashboard,
) -> str:
    """Render governance status without conflating it with performance evidence."""
    lines = [
        "# Source-resolution status",
        "",
        "!!! warning \"Governance status, not performance evidence\"",
        "    This page reports integrity-checked source-resolution checkpoints. A row may",
        "    reference separately frozen empirical source evidence when that evidence has",
        "    actually been created, but the dashboard itself does **not** establish model",
        "    performance, human-human reliability, analysis rights, redistribution rights,",
        "    source-audit readiness, or Frozen Evidence publication.",
        "",
        "The table is generated from the committed `source-resolution-status-v1` JSON records and",
        "their dataset-specific validators. Values are not transcribed by hand.",
        "",
        _TABLE_HEADER,
        _TABLE_SEPARATOR,
    ]
    for row in dashboard.rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_cell(row["dataset"]),
                    _escape_cell(row["checked_on"]),
                    f"`{_escape_cell(row['status'])}`",
                    _escape_cell(row["analysis_use_terms_status"]),
                    _escape_cell(row["raw_data_redistribution_terms_status"]),
                    _escape_cell(row["source_audit_ready"]),
                    _escape_cell(row["empirical_evidence_created"]),
                    f"`{row['record_fingerprint_sha256'][:12]}…`",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Bundle identity",
            "",
            "The complete currently discovered checkpoint set has deterministic validation-bundle",
            "fingerprint:",
            "",
            f"`{dashboard.bundle_fingerprint_sha256}`",
            "",
            "Changing any validated checkpoint changes this bundle identity. Duplicate datasets,",
            "malformed governed files, unsupported datasets, or unsupported evidence-state",
            "transitions fail before this page is generated.",
            "",
        ]
    )

    if dashboard.reviewed_snapshot:
        if dashboard.reviewed_on is None or dashboard.lock_fingerprint_sha256 is None:
            raise BenchmarkIntegrityError(
                "Reviewed source-resolution dashboard is missing reviewed lock metadata."
            )
        lines.extend(
            [
                "## Reviewed governance snapshot",
                "",
                "The live validation bundle exactly matches the separately frozen reviewed",
                f"source-resolution snapshot dated **{dashboard.reviewed_on}**.",
                "",
                "Reviewed lock fingerprint:",
                "",
                f"`{dashboard.lock_fingerprint_sha256}`",
                "",
                "This lock confirms only that the public status page matches the checkpoint",
                "contents intentionally reviewed for repository governance. It does **not**",
                "authorize source-status upgrades, source-audit readiness, empirical evidence,",
                "dataset analysis or redistribution rights, or Frozen Evidence publication.",
                "A checkpoint may point to empirical evidence only when that evidence is",
                "independently frozen and validated outside the governance lock.",
                "",
            ]
        )

    lines.extend(
        [
            "## Scientific boundary",
            "",
            "Source resolution and source evidence do not automatically imply source-audit",
            "readiness or benchmark performance. The Frozen Evidence layer remains a separate",
            "publication gate for validated performance results. A source-resolution row must",
            "never be interpreted as benchmark accuracy, independent human reliability, GP3",
            "validity, or permission to redistribute raw data unless those claims are separately",
            "supported and frozen.",
            "",
        ]
    )
    return "\n".join(lines)
