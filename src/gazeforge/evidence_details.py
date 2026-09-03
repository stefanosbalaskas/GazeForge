"""Conservative Markdown details for already validated frozen benchmark reports."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _text(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (float, np.floating)):
        numeric = float(value)
        if not np.isfinite(numeric):
            return "—"
        if abs(numeric) >= 100:
            return f"{numeric:.1f}"
        return f"{numeric:.3f}"
    return str(value)


def _escape(value: Any) -> str:
    return _text(value).replace("\n", " ").replace("\r", " ").replace("|", "\\|")


def _table(records: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not records:
        return ""
    headers = [label for _, label in columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for record in records:
        lines.append(
            "| "
            + " | ".join(_escape(record.get(key)) for key, _ in columns)
            + " |"
        )
    return "\n".join(lines)


def _model_summary(metrics: dict[str, Any]) -> str:
    records = metrics.get("summary")
    if not isinstance(records, list) or not records:
        return ""
    if not all(isinstance(row, dict) and "model" in row for row in records):
        return ""
    columns = [
        ("model", "Model"),
        ("n_folds", "Folds"),
        ("accuracy_mean", "Accuracy"),
        ("balanced_accuracy_mean", "Balanced acc."),
        ("macro_f1_mean", "Macro-F1"),
        ("event_f1_mean", "Event F1"),
        ("event_mean_matched_iou_mean", "Event IoU"),
        ("multiclass_brier_score_mean", "Brier"),
        ("expected_calibration_error_mean", "ECE"),
    ]
    return "#### Overall held-out model performance\n\n" + _table(records, columns) + "\n\n"


def _paired_summary(metrics: dict[str, Any]) -> str:
    records = metrics.get("paired_model_difference_summary")
    if not isinstance(records, list) or not records:
        return ""
    preferred = {
        "accuracy",
        "macro_f1",
        "event_f1",
        "event_mean_matched_iou",
        "multiclass_brier_score",
        "expected_calibration_error",
    }
    filtered = [
        row
        for row in records
        if isinstance(row, dict) and str(row.get("metric")) in preferred
    ]
    if not filtered:
        return ""
    columns = [
        ("model_a", "Model A"),
        ("model_b", "Model B"),
        ("metric", "Metric"),
        ("n_paired_folds", "Paired folds"),
        ("mean_delta_a_minus_b", "Mean A−B"),
        ("mean_improvement_for_a", "Mean improvement A"),
        ("wins_model_a", "A wins"),
        ("ties", "Ties"),
        ("wins_model_b", "B wins"),
    ]
    note = (
        "Positive **Mean improvement A** always favours model A; raw **Mean A−B** keeps the "
        "original metric direction. These are descriptive matched-fold differences, not "
        "cross-validation significance tests.\n\n"
    )
    return "#### Matched-fold model differences\n\n" + note + _table(filtered, columns) + "\n\n"


def _stimulus_summary(metrics: dict[str, Any]) -> str:
    records = metrics.get("stimulus_type_summary")
    if not isinstance(records, list) or not records:
        return ""
    columns = [
        ("stratum", "Stimulus family"),
        ("model", "Model"),
        ("n_folds", "Folds"),
        ("n_test_rows_total", "Held-out rows"),
        ("n_test_groups_unique", "Participants"),
        ("accuracy_mean", "Accuracy"),
        ("macro_f1_mean", "Macro-F1"),
        ("event_f1_mean", "Event F1"),
        ("event_mean_matched_iou_mean", "Event IoU"),
    ]
    note = (
        "These are post-hoc summaries of the same held-out predictions used above; models were "
        "not refitted by stimulus family.\n\n"
    )
    return "#### Performance by stimulus family\n\n" + note + _table(records, columns) + "\n\n"


def _agreement_summary(metrics: dict[str, Any]) -> str:
    overall = metrics.get("overall")
    if not isinstance(overall, dict):
        return ""
    records = [
        {
            "scope": "overall",
            "n_aligned_samples": overall.get("n_aligned_samples"),
            "exact_agreement": overall.get("exact_agreement"),
            "cohen_kappa": overall.get("cohen_kappa"),
        }
    ]
    by_stimulus = metrics.get("by_stimulus_type")
    if isinstance(by_stimulus, dict):
        for stimulus, values in sorted(by_stimulus.items()):
            if not isinstance(values, dict):
                continue
            records.append(
                {
                    "scope": str(stimulus),
                    "n_aligned_samples": values.get("n_aligned_samples"),
                    "exact_agreement": values.get("exact_agreement"),
                    "cohen_kappa": values.get("cohen_kappa"),
                }
            )
    columns = [
        ("scope", "Scope"),
        ("n_aligned_samples", "Aligned samples"),
        ("exact_agreement", "Exact agreement"),
        ("cohen_kappa", "Cohen κ"),
    ]
    return "#### Human–human annotation agreement\n\n" + _table(records, columns) + "\n\n"


def _sensitivity_summary(metrics: dict[str, Any]) -> str:
    settings = metrics.get("settings")
    model_metrics = metrics.get("model_metrics")
    sections: list[str] = []
    if isinstance(settings, list) and settings:
        setting_columns = [
            ("target_sampling_rate_hz", "Rate Hz"),
            ("min_label_purity", "Min purity"),
            ("comparison_status", "Status"),
            ("ambiguous_fraction", "Ambiguous"),
            ("retained_fraction_of_target", "Retained"),
            ("retained_group_count", "Participants"),
        ]
        sections.extend(
            [
                "#### Sampling × label-purity settings\n\n",
                _table([row for row in settings if isinstance(row, dict)], setting_columns),
                "\n\n",
            ]
        )
    if isinstance(model_metrics, list) and model_metrics:
        metric_columns = [
            ("target_sampling_rate_hz", "Rate Hz"),
            ("min_label_purity", "Min purity"),
            ("model", "Model"),
            ("macro_f1_mean", "Macro-F1"),
            ("event_f1_mean", "Event F1"),
            ("event_mean_matched_iou_mean", "Event IoU"),
            ("ambiguous_fraction", "Ambiguous"),
            ("retained_fraction_of_target", "Retained"),
        ]
        sections.extend(
            [
                "#### Model sensitivity surface\n\n",
                _table(
                    [row for row in model_metrics if isinstance(row, dict)],
                    metric_columns,
                ),
                "\n\n",
            ]
        )
    return "".join(sections)


def render_validated_report_detail_markdown(report: dict[str, Any]) -> str:
    """Render scientific detail for a report already fingerprint-validated by the dashboard."""
    benchmark = report.get("benchmark")
    metrics = report.get("metrics")
    if not isinstance(benchmark, dict) or not isinstance(metrics, dict):
        return ""
    name = _escape(benchmark.get("name", "benchmark"))
    sampling_origin = _escape(benchmark.get("sampling_origin", "unknown"))
    reference_strength = _escape(benchmark.get("reference_strength", "unknown"))
    fingerprint = str(report.get("report_fingerprint_sha256", ""))[:12]
    sections = [
        f"### {name}\n\n",
        f"**Sampling:** {sampling_origin} · **Reference:** {reference_strength} · ",
        f"**Report:** `{fingerprint}`\n\n",
    ]
    for renderer in (
        _agreement_summary,
        _model_summary,
        _paired_summary,
        _stimulus_summary,
        _sensitivity_summary,
    ):
        rendered = renderer(metrics)
        if rendered:
            sections.append(rendered)
    if len(sections) == 3:
        sections.append(
            "This validated report has no specialised public detail renderer yet; its evidence "
            "metadata remains listed in the frozen-report index above.\n\n"
        )
    return "".join(sections)
