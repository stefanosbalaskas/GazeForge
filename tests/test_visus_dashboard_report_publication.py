import json

import pytest

from gazeforge import dashboard
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError


def _frozen_report(
    *,
    name="VISUS-annotator_a",
    evaluation_type="visus-audited-model-human-dynamic-aoi",
    validation_scope="audited-source-model-human-dynamic-aoi",
):
    body = {
        "benchmark": {
            "name": name,
            "version": "1.0",
            "source": "audited VISUS source",
            "validation_scope": validation_scope,
            "annotation_origin": "human-manual",
            "sampling_origin": "native",
            "reference_strength": "human-reference",
            "sampling_rates_hz": [250.0],
        },
        "model": {"name": "test-model", "version": "1"},
        "protocol": {"evaluation_type": evaluation_type},
        "metrics": {"f1": 0.5},
    }
    return {
        **body,
        "report_fingerprint_sha256": benchmark_fingerprint(body),
    }


def _write(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _approved_suite(*, child_name, child_path, fingerprint):
    return {
        "suite": "visus-dynamic-aoi-validation-v1",
        "status": "complete",
        "report_count": 1,
        "reports": [
            {
                "name": child_name,
                "path": child_path,
                "report_fingerprint_sha256": fingerprint,
            }
        ],
        "suite_fingerprint_sha256": "a" * 64,
        "source": {"source_manifest_fingerprint_sha256": "b" * 64},
        "protocol": {
            "reference_stream_id": "annotator_a",
            "human_human_agreement_included": child_name == "human_human_agreement",
        },
    }


def test_dashboard_rejects_detached_visus_model_human_report(tmp_path):
    report = _frozen_report()
    _write(tmp_path / "model-human.json", report)

    with pytest.raises(BenchmarkIntegrityError, match="sibling VISUS suite manifest is missing"):
        dashboard.build_benchmark_dashboard(tmp_path)


def test_dashboard_accepts_exact_reviewed_model_human_suite_child(monkeypatch, tmp_path):
    report = _frozen_report()
    report_path = tmp_path / "model-human.json"
    _write(report_path, report)
    (tmp_path / dashboard._VISUS_SUITE_MANIFEST_NAME).write_text("{}\n", encoding="utf-8")
    summary = _approved_suite(
        child_name="model_human_validation",
        child_path="model-human.json",
        fingerprint=report["report_fingerprint_sha256"],
    )
    monkeypatch.setattr(dashboard, "_validate_visus_suite_for_dashboard", lambda path: summary)

    result = dashboard.build_benchmark_dashboard(tmp_path)

    assert len(result.reports) == 1
    assert result.table.loc[0, "benchmark"] == "VISUS-annotator_a"
    assert result.suite_table.loc[0, "suite"] == "visus-dynamic-aoi-validation-v1"


def test_dashboard_rejects_visus_child_fingerprint_not_in_reviewed_suite(monkeypatch, tmp_path):
    report = _frozen_report()
    report_path = tmp_path / "model-human.json"
    _write(report_path, report)
    (tmp_path / dashboard._VISUS_SUITE_MANIFEST_NAME).write_text("{}\n", encoding="utf-8")
    summary = _approved_suite(
        child_name="model_human_validation",
        child_path="model-human.json",
        fingerprint="f" * 64,
    )
    monkeypatch.setattr(dashboard, "_validate_visus_suite_for_dashboard", lambda path: summary)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exact scientifically reviewed suite child fingerprint",
    ):
        dashboard.build_benchmark_dashboard(tmp_path)


def test_dashboard_rejects_copied_visus_child_at_unapproved_path(monkeypatch, tmp_path):
    report = _frozen_report()
    copied_path = tmp_path / "copied-model-human.json"
    _write(copied_path, report)
    (tmp_path / dashboard._VISUS_SUITE_MANIFEST_NAME).write_text("{}\n", encoding="utf-8")
    summary = _approved_suite(
        child_name="model_human_validation",
        child_path="model-human.json",
        fingerprint=report["report_fingerprint_sha256"],
    )
    monkeypatch.setattr(dashboard, "_validate_visus_suite_for_dashboard", lambda path: summary)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exact scientifically reviewed suite child path",
    ):
        dashboard.build_benchmark_dashboard(tmp_path)


def test_dashboard_rejects_unknown_or_inconsistent_visus_report_schema(tmp_path):
    unknown = _frozen_report(
        evaluation_type="visus-future-unreviewed-result",
        validation_scope="future-unreviewed-result",
    )
    _write(tmp_path / "unknown.json", unknown)

    with pytest.raises(BenchmarkIntegrityError, match="known review-gated child schema"):
        dashboard.build_benchmark_dashboard(tmp_path)

    (tmp_path / "unknown.json").unlink()
    inconsistent = _frozen_report(
        evaluation_type="visus-audited-model-human-dynamic-aoi",
        validation_scope="audited-source-independent-human-dynamic-aoi-agreement",
    )
    _write(tmp_path / "inconsistent.json", inconsistent)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="evaluation type and validation scope disagree",
    ):
        dashboard.build_benchmark_dashboard(tmp_path)


def test_dashboard_accepts_exact_reviewed_human_human_suite_child(monkeypatch, tmp_path):
    report = _frozen_report(
        name="VISUS-annotator_a-vs-annotator_b",
        evaluation_type="visus-independent-human-dynamic-aoi-agreement",
        validation_scope="audited-source-independent-human-dynamic-aoi-agreement",
    )
    report_path = tmp_path / "human-human.json"
    _write(report_path, report)
    (tmp_path / dashboard._VISUS_SUITE_MANIFEST_NAME).write_text("{}\n", encoding="utf-8")
    summary = _approved_suite(
        child_name="human_human_agreement",
        child_path="human-human.json",
        fingerprint=report["report_fingerprint_sha256"],
    )
    monkeypatch.setattr(dashboard, "_validate_visus_suite_for_dashboard", lambda path: summary)

    dashboard._validate_visus_report_for_dashboard(report_path, report)


def test_dashboard_leaves_non_visus_frozen_reports_on_generic_integrity_path(tmp_path):
    report = _frozen_report(
        name="Generic-Benchmark",
        evaluation_type="generic-evaluation",
        validation_scope="generic-validation",
    )
    _write(tmp_path / "generic.json", report)

    result = dashboard.build_benchmark_dashboard(tmp_path)

    assert len(result.reports) == 1
    assert result.table.loc[0, "benchmark"] == "Generic-Benchmark"
