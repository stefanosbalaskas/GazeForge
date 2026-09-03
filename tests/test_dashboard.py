import json

import pytest

import gazeforge
from gazeforge.benchmarks import (
    BenchmarkDatasetCard,
    benchmark_fingerprint,
    build_benchmark_report,
)
from gazeforge.dashboard import (
    build_benchmark_dashboard,
    discover_frozen_benchmark_reports,
    load_frozen_benchmark_report,
    render_benchmark_dashboard_markdown,
    validate_frozen_benchmark_report,
)
from gazeforge.exceptions import BenchmarkIntegrityError


def _report():
    card = BenchmarkDatasetCard(
        name="Example-human-benchmark",
        version="1.0",
        source="external-test-source",
        license="test-only",
        task="eye-event classification",
        sampling_rates_hz=[500.0, 60.0],
        participant_count=10,
        split_unit="participant_id",
        validation_scope="external-empirical-benchmark",
        annotation_origin="expert-manual",
        sampling_origin="resampled",
        reference_strength="derived-human-reference",
        human_annotator_count=2,
    )
    return build_benchmark_report(
        benchmark=card,
        model={"models": ["I-VT", "RandomForest", "ContextMLP"]},
        protocol={"n_splits": 5},
        metrics={"summary": [{"model": "RandomForest", "accuracy": 0.8}]},
    )


def _write(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def test_dashboard_public_api_is_exposed():
    assert callable(gazeforge.build_benchmark_dashboard)
    assert callable(gazeforge.validate_frozen_benchmark_report)
    assert issubclass(gazeforge.BenchmarkIntegrityError, ValueError)


def test_valid_report_recomputes_fingerprint():
    report = _report()
    assert validate_frozen_benchmark_report(report) == report["report_fingerprint_sha256"]


def test_tampered_report_is_rejected(tmp_path):
    report = _report()
    report["metrics"]["summary"][0]["accuracy"] = 0.99
    path = tmp_path / "tampered.json"
    _write(path, report)
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint mismatch"):
        load_frozen_benchmark_report(path)


def test_protocol_json_is_not_discovered_as_performance_evidence(tmp_path):
    _write(tmp_path / "protocol.json", {"benchmark": "candidate", "status": "planned"})
    _write(tmp_path / "report.json", _report())
    assert [path.name for path in discover_frozen_benchmark_reports(tmp_path)] == ["report.json"]


def test_dashboard_rejects_duplicate_frozen_report(tmp_path):
    report = _report()
    _write(tmp_path / "report-a.json", report)
    _write(tmp_path / "report-b.json", report)
    with pytest.raises(BenchmarkIntegrityError, match="Duplicate frozen benchmark fingerprint"):
        build_benchmark_dashboard(tmp_path)


def test_dashboard_table_surfaces_evidence_strength_and_models(tmp_path):
    report = _report()
    _write(tmp_path / "report.json", report)
    dashboard = build_benchmark_dashboard(tmp_path)
    assert len(dashboard.reports) == 1
    row = dashboard.table.iloc[0]
    assert row["benchmark"] == "Example-human-benchmark"
    assert row["annotation_origin"] == "expert-manual"
    assert row["sampling_origin"] == "resampled"
    assert row["reference_strength"] == "derived-human-reference"
    assert row["models"] == "I-VT, RandomForest, ContextMLP"


def test_empty_dashboard_markdown_never_claims_performance(tmp_path):
    dashboard = build_benchmark_dashboard(tmp_path)
    markdown = render_benchmark_dashboard_markdown(dashboard)
    assert "No integrity-checked frozen empirical benchmark reports" in markdown
    assert "performance evidence" in markdown


def test_dashboard_markdown_uses_short_fingerprint_without_optional_dependency(tmp_path):
    report = _report()
    _write(tmp_path / "report.json", report)
    markdown = render_benchmark_dashboard_markdown(build_benchmark_dashboard(tmp_path))
    assert "Example-human-benchmark" in markdown
    assert report["report_fingerprint_sha256"][:12] in markdown
    assert report["report_fingerprint_sha256"] not in markdown


def test_missing_evidence_metadata_is_rejected():
    report = _report()
    report["benchmark"].pop("reference_strength")
    body = {key: report[key] for key in ("benchmark", "model", "protocol", "metrics")}
    report["report_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(BenchmarkIntegrityError, match="evidence fields"):
        validate_frozen_benchmark_report(report)
