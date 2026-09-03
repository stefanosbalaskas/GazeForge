"""MkDocs hooks for evidence-aware GazeForge documentation builds."""

from __future__ import annotations

from pathlib import Path

from gazeforge.dashboard import build_benchmark_dashboard, render_benchmark_dashboard_markdown
from gazeforge.evidence_details import render_validated_report_detail_markdown


def _project_root(config) -> Path:
    config_path = getattr(config, "config_file_path", None)
    if config_path is None:
        config_path = config["config_file_path"]
    return Path(config_path).resolve().parent


def on_pre_build(config) -> None:
    """Regenerate the public frozen-evidence page from integrity-checked reports."""
    root = _project_root(config)
    dashboard = build_benchmark_dashboard(root / "validation")
    content = render_benchmark_dashboard_markdown(dashboard)
    if dashboard.reports:
        content += "\n## Validated report details\n\n"
        content += (
            "The tables below are generated directly from the same fingerprint-validated JSON "
            "reports listed above; no performance values are transcribed manually.\n\n"
        )
        for report in dashboard.reports:
            content += render_validated_report_detail_markdown(report)

    content += """

## What appears on this page

A JSON file is listed here only when it follows the GazeForge frozen benchmark-report schema and
its deterministic SHA-256 fingerprint recomputes successfully from the benchmark metadata, model
metadata, protocol, and metrics. Candidate protocols and configuration manifests are not treated as
performance evidence.

## Evidence interpretation

The table surfaces annotation origin, sampling origin, reference strength, model family, and
sampling rate so evidence strength remains visible alongside any future performance result.
Derived lower-rate evidence is therefore distinguishable from native-rate recordings, and
algorithmic/vendor labels cannot silently appear as human ground truth.

Detailed performance tables are generated only from reports that passed the same integrity check.
Unknown future report schemas remain visible in the frozen-report index without GazeForge guessing
which nested values should be presented as headline performance metrics.

## Current scientific rule

The absence of a row is meaningful: implemented benchmark infrastructure, adapters, candidate
datasets, and synthetic smoke tests do **not** become empirical validation merely because they
exist in the repository. See the [validation status](validation-status.md) and
[benchmark evidence](benchmark-evidence.md) pages for work that is implemented but not yet frozen
as empirical evidence.
"""
    (root / "docs" / "frozen-evidence.md").write_text(content, encoding="utf-8")
