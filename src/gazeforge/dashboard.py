"""Integrity-checked data layer for benchmark dashboards and public evidence summaries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError

_REPORT_BODY_KEYS = ("benchmark", "model", "protocol", "metrics")
_REQUIRED_BENCHMARK_FIELDS = (
    "name",
    "version",
    "source",
    "validation_scope",
    "annotation_origin",
    "sampling_origin",
    "reference_strength",
)


@dataclass(slots=True)
class BenchmarkDashboard:
    """Validated benchmark reports plus a compact public evidence table."""

    reports: tuple[dict[str, Any], ...]
    table: pd.DataFrame
    source_files: tuple[str, ...]


def validate_frozen_benchmark_report(report: dict[str, Any]) -> str:
    """Validate report structure and recompute its deterministic SHA-256 fingerprint.

    The fingerprint is computed from the same four report-body objects used by
    :func:`gazeforge.benchmarks.build_benchmark_report`. Any later edit to benchmark metadata,
    protocol, model metadata, or metrics therefore invalidates the report.
    """
    if not isinstance(report, dict):
        raise BenchmarkIntegrityError("Benchmark report must be a JSON object.")
    missing = [key for key in (*_REPORT_BODY_KEYS, "report_fingerprint_sha256") if key not in report]
    if missing:
        raise BenchmarkIntegrityError(f"Benchmark report is missing required fields: {missing}")

    body = {key: report[key] for key in _REPORT_BODY_KEYS}
    expected = benchmark_fingerprint(body)
    observed = str(report["report_fingerprint_sha256"])
    if observed != expected:
        raise BenchmarkIntegrityError(
            "Benchmark report fingerprint mismatch; the frozen report has been modified or "
            "does not follow the GazeForge benchmark-report schema."
        )

    benchmark = report["benchmark"]
    if not isinstance(benchmark, dict):
        raise BenchmarkIntegrityError("Benchmark metadata must be a JSON object.")
    missing_metadata = [field for field in _REQUIRED_BENCHMARK_FIELDS if field not in benchmark]
    if missing_metadata:
        raise BenchmarkIntegrityError(
            f"Benchmark metadata is missing evidence fields: {missing_metadata}"
        )
    return expected


def load_frozen_benchmark_report(path: str | Path) -> dict[str, Any]:
    """Load and integrity-check one frozen benchmark JSON report."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkIntegrityError(f"Invalid benchmark JSON: {source}") from exc
    validate_frozen_benchmark_report(payload)
    return payload


def discover_frozen_benchmark_reports(
    root: str | Path,
    *,
    recursive: bool = True,
) -> tuple[Path, ...]:
    """Discover fingerprinted benchmark reports while ignoring protocol/config JSON files.

    JSON files without ``report_fingerprint_sha256`` are not treated as benchmark results. Files
    that do claim to be frozen reports are validated later and cannot silently bypass integrity
    checks.
    """
    directory = Path(root)
    if not directory.exists():
        raise FileNotFoundError(directory)
    candidates = sorted(directory.rglob("*.json") if recursive else directory.glob("*.json"))
    reports: list[Path] = []
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and "report_fingerprint_sha256" in payload:
            reports.append(path)
    return tuple(reports)


def _model_names(model_metadata: Any) -> str:
    if not isinstance(model_metadata, dict):
        return ""
    models = model_metadata.get("models")
    if isinstance(models, (list, tuple)):
        return ", ".join(str(value) for value in models)
    if models is not None:
        return str(models)
    for key in ("name", "model", "type"):
        if key in model_metadata:
            return str(model_metadata[key])
    return ""


def _dashboard_row(report: dict[str, Any], source_file: str) -> dict[str, Any]:
    benchmark = report["benchmark"]
    sampling_rates = benchmark.get("sampling_rates_hz", [])
    if isinstance(sampling_rates, (list, tuple)):
        rate_text = ", ".join(f"{float(value):g}" for value in sampling_rates)
    else:
        rate_text = str(sampling_rates)
    return {
        "benchmark": str(benchmark["name"]),
        "version": str(benchmark["version"]),
        "validation_scope": str(benchmark["validation_scope"]),
        "annotation_origin": str(benchmark["annotation_origin"]),
        "sampling_origin": str(benchmark["sampling_origin"]),
        "reference_strength": str(benchmark["reference_strength"]),
        "sampling_rates_hz": rate_text,
        "models": _model_names(report.get("model")),
        "source": str(benchmark["source"]),
        "report_fingerprint_sha256": str(report["report_fingerprint_sha256"]),
        "source_file": source_file,
    }


def build_benchmark_dashboard(
    root: str | Path,
    *,
    recursive: bool = True,
) -> BenchmarkDashboard:
    """Build an evidence table from integrity-checked frozen reports under ``root``.

    Duplicate report fingerprints are rejected so copied files cannot inflate the apparent number
    of independent validation results on a public dashboard.
    """
    paths = discover_frozen_benchmark_reports(root, recursive=recursive)
    reports: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    fingerprints: set[str] = set()

    for path in paths:
        report = load_frozen_benchmark_report(path)
        fingerprint = str(report["report_fingerprint_sha256"])
        if fingerprint in fingerprints:
            raise BenchmarkIntegrityError(
                f"Duplicate frozen benchmark fingerprint discovered: {fingerprint}"
            )
        fingerprints.add(fingerprint)
        reports.append(report)
        rows.append(_dashboard_row(report, str(path)))

    table = pd.DataFrame(rows)
    if not table.empty:
        table = table.sort_values(
            ["benchmark", "version", "report_fingerprint_sha256"],
            kind="stable",
        ).reset_index(drop=True)
    return BenchmarkDashboard(
        reports=tuple(reports),
        table=table,
        source_files=tuple(str(path) for path in paths),
    )


def render_benchmark_dashboard_markdown(dashboard: BenchmarkDashboard) -> str:
    """Render a conservative Markdown evidence index for the documentation website."""
    heading = "# Frozen benchmark evidence\n\n"
    if dashboard.table.empty:
        return (
            heading
            + "No integrity-checked frozen empirical benchmark reports are committed yet. "
            "Implemented benchmark infrastructure and candidate datasets are documented in the "
            "validation-status pages, but they are not displayed here as performance evidence.\n"
        )

    columns = [
        "benchmark",
        "version",
        "annotation_origin",
        "sampling_origin",
        "reference_strength",
        "sampling_rates_hz",
        "models",
        "report_fingerprint_sha256",
    ]
    public = dashboard.table.loc[:, columns].copy()
    public["report_fingerprint_sha256"] = public["report_fingerprint_sha256"].str.slice(0, 12)
    return (
        heading
        + "Only reports whose deterministic fingerprint recomputes successfully are listed.\n\n"
        + public.to_markdown(index=False)
        + "\n"
    )
