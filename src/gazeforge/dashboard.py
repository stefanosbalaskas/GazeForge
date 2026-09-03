"""Integrity-checked data layer for benchmark dashboards and public evidence summaries."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .lund_suite import validate_lund2013_suite_manifest
from .visus_suite import validate_visus_dynamic_aoi_suite_manifest

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
_LUND_SUITE_MANIFEST_NAME = "lund2013-suite-manifest.json"
_VISUS_SUITE_MANIFEST_NAME = "visus-dynamic-aoi-suite-manifest.json"


@dataclass(slots=True)
class BenchmarkDashboard:
    """Validated benchmark reports and verified report suites for public evidence."""

    reports: tuple[dict[str, Any], ...]
    table: pd.DataFrame
    source_files: tuple[str, ...]
    suites: tuple[dict[str, Any], ...] = ()
    suite_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    suite_source_files: tuple[str, ...] = ()


def validate_frozen_benchmark_report(report: dict[str, Any]) -> str:
    """Validate report structure and recompute its deterministic SHA-256 fingerprint.

    The fingerprint is computed from the same four report-body objects used by
    :func:`gazeforge.benchmarks.build_benchmark_report`. Any later edit to benchmark metadata,
    protocol, model metadata, or metrics therefore invalidates the report.
    """
    if not isinstance(report, dict):
        raise BenchmarkIntegrityError("Benchmark report must be a JSON object.")
    required = (*_REPORT_BODY_KEYS, "report_fingerprint_sha256")
    missing = [key for key in required if key not in report]
    if missing:
        raise BenchmarkIntegrityError(
            f"Benchmark report is missing required fields: {missing}"
        )

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
    missing_metadata = [
        field_name
        for field_name in _REQUIRED_BENCHMARK_FIELDS
        if field_name not in benchmark
    ]
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
    """Discover benchmark-schema reports while ignoring provenance/config JSON files.

    A deterministic ``report_fingerprint_sha256`` can also belong to audited intake or provenance
    reports. Those files are deliberately not treated as performance evidence unless they contain
    the complete benchmark/model/protocol/metrics report body.
    """
    directory = Path(root)
    if not directory.exists():
        raise FileNotFoundError(directory)
    candidates = sorted(
        directory.rglob("*.json") if recursive else directory.glob("*.json")
    )
    reports: list[Path] = []
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if "report_fingerprint_sha256" not in payload:
            continue
        if all(key in payload for key in _REPORT_BODY_KEYS):
            reports.append(path)
    return tuple(reports)


def _discover_named_suite_manifests(
    root: str | Path,
    manifest_name: str,
    *,
    recursive: bool,
) -> tuple[Path, ...]:
    directory = Path(root)
    if not directory.exists():
        raise FileNotFoundError(directory)
    if recursive:
        paths = sorted(directory.rglob(manifest_name))
    else:
        candidate = directory / manifest_name
        paths = [candidate] if candidate.is_file() else []
    return tuple(paths)


def discover_lund2013_suite_manifests(
    root: str | Path,
    *,
    recursive: bool = True,
) -> tuple[Path, ...]:
    """Discover Lund suite completion manifests without treating them as result rows."""
    return _discover_named_suite_manifests(
        root,
        _LUND_SUITE_MANIFEST_NAME,
        recursive=recursive,
    )


def discover_visus_dynamic_aoi_suite_manifests(
    root: str | Path,
    *,
    recursive: bool = True,
) -> tuple[Path, ...]:
    """Discover VISUS dynamic-AOI completion manifests for strict suite validation."""
    return _discover_named_suite_manifests(
        root,
        _VISUS_SUITE_MANIFEST_NAME,
        recursive=recursive,
    )


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


def _suite_source_fingerprint(summary: dict[str, Any]) -> str:
    source_manifest = summary.get("source_manifest")
    if isinstance(source_manifest, dict):
        return str(source_manifest.get("manifest_fingerprint_sha256", ""))
    source = summary.get("source")
    if isinstance(source, dict):
        return str(source.get("source_manifest_fingerprint_sha256", ""))
    return ""


def _suite_row(summary: dict[str, Any], source_file: str) -> dict[str, Any]:
    protocol = summary.get("protocol")
    target_rate = ""
    model = ""
    reference_stream = ""
    human_agreement = ""
    if isinstance(protocol, dict):
        if "target_sampling_rate_hz" in protocol:
            target_rate = f"{float(protocol['target_sampling_rate_hz']):g}"
        model_name = str(protocol.get("model_name", "")).strip()
        model_version = str(protocol.get("model_version", "")).strip()
        if model_name:
            model = model_name if not model_version else f"{model_name} {model_version}"
        reference_stream = str(protocol.get("reference_stream_id", ""))
        if "human_human_agreement_included" in protocol:
            human_agreement = str(
                bool(protocol["human_human_agreement_included"])
            ).lower()
    return {
        "suite": str(summary["suite"]),
        "status": str(summary["status"]),
        "report_count": int(summary["report_count"]),
        "target_sampling_rate_hz": target_rate,
        "model": model,
        "reference_stream_id": reference_stream,
        "human_human_agreement_included": human_agreement,
        "source_manifest_fingerprint_sha256": _suite_source_fingerprint(summary),
        "suite_fingerprint_sha256": str(summary["suite_fingerprint_sha256"]),
        "source_file": source_file,
    }


def _validated_suite_records(
    paths: tuple[Path, ...],
    validator: Callable[[str | Path], dict[str, Any]],
) -> list[tuple[Path, dict[str, Any]]]:
    return [(path, validator(path)) for path in paths]


def build_benchmark_dashboard(
    root: str | Path,
    *,
    recursive: bool = True,
) -> BenchmarkDashboard:
    """Build evidence tables from integrity-checked reports and complete suites under ``root``.

    Duplicate report and suite fingerprints are rejected so copied artifacts cannot inflate the
    apparent number of independent validation results or completed tranches on a public dashboard.
    Provenance-only JSON children are never promoted to performance-report rows.
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

    lund_paths = discover_lund2013_suite_manifests(root, recursive=recursive)
    visus_paths = discover_visus_dynamic_aoi_suite_manifests(
        root,
        recursive=recursive,
    )
    suite_records = [
        *_validated_suite_records(lund_paths, validate_lund2013_suite_manifest),
        *_validated_suite_records(
            visus_paths,
            validate_visus_dynamic_aoi_suite_manifest,
        ),
    ]
    suite_records.sort(key=lambda item: str(item[0]))

    suites: list[dict[str, Any]] = []
    suite_rows: list[dict[str, Any]] = []
    suite_files: list[str] = []
    suite_fingerprints: set[str] = set()
    for path, summary in suite_records:
        fingerprint = str(summary["suite_fingerprint_sha256"])
        if fingerprint in suite_fingerprints:
            raise BenchmarkIntegrityError(
                f"Duplicate verified suite fingerprint discovered: {fingerprint}"
            )
        suite_fingerprints.add(fingerprint)
        suites.append(summary)
        suite_rows.append(_suite_row(summary, str(path)))
        suite_files.append(str(path))

    suite_table = pd.DataFrame(suite_rows)
    if not suite_table.empty:
        suite_table = suite_table.sort_values(
            ["suite", "suite_fingerprint_sha256"],
            kind="stable",
        ).reset_index(drop=True)

    return BenchmarkDashboard(
        reports=tuple(reports),
        table=table,
        source_files=tuple(str(path) for path in paths),
        suites=tuple(suites),
        suite_table=suite_table,
        suite_source_files=tuple(suite_files),
    )


def _escape_markdown_cell(value: Any) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ")
    return text.replace("|", "\\|")


def _markdown_table(frame: pd.DataFrame) -> str:
    headers = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in frame.itertuples(index=False, name=None):
        lines.append(
            "| " + " | ".join(_escape_markdown_cell(value) for value in row) + " |"
        )
    return "\n".join(lines)


def render_benchmark_dashboard_markdown(dashboard: BenchmarkDashboard) -> str:
    """Render a conservative Markdown evidence index for the documentation website."""
    heading = "# Frozen benchmark evidence\n\n"
    if dashboard.table.empty and dashboard.suite_table.empty:
        return (
            heading
            + "No integrity-checked frozen empirical benchmark reports are committed yet. "
            "Implemented benchmark infrastructure and candidate datasets are documented in the "
            "validation-status pages, but they are not displayed here as performance evidence.\n"
        )

    sections = [heading]
    if not dashboard.suite_table.empty:
        suite_columns = [
            "suite",
            "status",
            "report_count",
            "target_sampling_rate_hz",
            "model",
            "reference_stream_id",
            "human_human_agreement_included",
            "source_manifest_fingerprint_sha256",
            "suite_fingerprint_sha256",
        ]
        public_suites = dashboard.suite_table.loc[:, suite_columns].copy()
        for column in (
            "source_manifest_fingerprint_sha256",
            "suite_fingerprint_sha256",
        ):
            public_suites[column] = public_suites[column].str.slice(0, 12)
        sections.extend(
            [
                "## Verified report suites\n\n",
                (
                    "A suite appears here only when its completion manifest and every "
                    "referenced child report verify successfully.\n\n"
                ),
                _markdown_table(public_suites),
                "\n\n",
            ]
        )

    if not dashboard.table.empty:
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
        public["report_fingerprint_sha256"] = public[
            "report_fingerprint_sha256"
        ].str.slice(0, 12)
        sections.extend(
            [
                "## Frozen reports\n\n",
                (
                    "Only reports whose deterministic fingerprint recomputes "
                    "successfully are listed.\n\n"
                ),
                _markdown_table(public),
                "\n",
            ]
        )
    return "".join(sections)
