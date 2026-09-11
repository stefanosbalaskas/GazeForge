"""Public Frozen Evidence publication gates layered over the lower-level dashboard API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .dashboard import (
    BenchmarkDashboard,
    build_benchmark_dashboard,
    discover_frozen_benchmark_reports,
    load_frozen_benchmark_report,
)
from .exceptions import BenchmarkIntegrityError

_GIW_BENCHMARK_PREFIX = "Gaze-in-the-Wild-"
_GIW_VALIDATION_SCOPE = (
    "lineage-bound-audited-source-participant-held-out-model-validation"
)
_GIW_DATASET_NAME = "Gaze-in-the-Wild"


def _gaze_in_wild_publication_signal(report: dict[str, Any]) -> bool:
    """Detect benchmark-schema reports that claim Gaze-in-the-Wild result lineage."""
    benchmark = report.get("benchmark")
    protocol = report.get("protocol")
    benchmark = benchmark if isinstance(benchmark, dict) else {}
    protocol = protocol if isinstance(protocol, dict) else {}
    preparation = protocol.get("preparation")
    preparation = preparation if isinstance(preparation, dict) else {}

    name = str(benchmark.get("name", ""))
    scope = str(benchmark.get("validation_scope", ""))
    dataset = str(preparation.get("dataset", ""))
    return (
        name.startswith(_GIW_BENCHMARK_PREFIX)
        or scope == _GIW_VALIDATION_SCOPE
        or dataset == _GIW_DATASET_NAME
    )


def validate_public_benchmark_report_families(
    root: str | Path,
    *,
    recursive: bool = True,
) -> None:
    """Fail closed on result families that lack a dedicated public-publication contract.

    Gaze-in-the-Wild currently has separately reviewed exact-distribution evidence records, but
    those records are deliberately not generic benchmark-schema dashboard rows. The lower-level
    model-validation API may also produce exploratory benchmark reports, including optional task
    stratification from a caller-supplied mapping. Until a dedicated publication contract binds
    such a report to the reviewed exact evidence lineage—and, for task sensitivity, to a reviewed
    authoritative file-to-task mapping—generic dashboard publication is forbidden.
    """
    for path in discover_frozen_benchmark_reports(root, recursive=recursive):
        report = load_frozen_benchmark_report(path)
        if _gaze_in_wild_publication_signal(report):
            raise BenchmarkIntegrityError(
                "Gaze-in-the-Wild benchmark result rows cannot use the generic public Frozen "
                "Evidence publication path. Public GIW performance evidence requires a "
                "dedicated reviewed publication contract bound to the exact evidence lineage; "
                "task-stratified evidence additionally requires an authoritative reviewed "
                "file-to-publication-task mapping."
            )


def build_public_benchmark_dashboard(
    root: str | Path,
    *,
    recursive: bool = True,
) -> BenchmarkDashboard:
    """Build the public dashboard only after family-specific publication preflight."""
    validate_public_benchmark_report_families(root, recursive=recursive)
    return build_benchmark_dashboard(root, recursive=recursive)
