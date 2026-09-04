"""Public non-empirical status dashboard for benchmark source-resolution checkpoints."""

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


def build_source_resolution_dashboard(root: str | Path) -> SourceResolutionDashboard:
    """Discover, validate, and prepare every source-resolution checkpoint under ``root``."""
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
    return SourceResolutionDashboard(
        records=records,
        rows=rows,
        source_files=tuple(row["source_file"] for row in rows),
        bundle_fingerprint_sha256=str(bundle["bundle_fingerprint_sha256"]),
    )


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_source_resolution_dashboard_markdown(
    dashboard: SourceResolutionDashboard,
) -> str:
    """Render an explicitly non-empirical Markdown status page from validated checkpoints."""
    lines = [
        "# Source-resolution status",
        "",
        "!!! warning \"Non-empirical governance status\"",
        "    This page reports validated source-resolution checkpoints only. Passing a checkpoint",
        "    does **not** mean that the external dataset has been obtained, source-audited, licensed",
        "    for analysis or redistribution, or used to create model-performance or human-agreement",
        "    evidence.",
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
            "## Scientific boundary",
            "",
            "Source resolution precedes source audit. The Frozen Evidence layer remains a separate",
            "publication gate and is the only public dashboard intended to surface validated",
            "performance evidence. A source-resolution row must never be interpreted as benchmark",
            "accuracy, human reliability, GP3 validity, or permission to redistribute raw data.",
            "",
        ]
    )
    return "\n".join(lines)
