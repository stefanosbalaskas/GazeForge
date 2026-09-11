from pathlib import Path

import pytest

from gazeforge import dashboard
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError


def _report(*, scope: str, native_intake: bool, token: str) -> dict:
    protocol = {"evaluation_type": "native-test"}
    if native_intake:
        protocol["native_intake"] = {
            "source_file_name": "native.csv",
            "source_file_sha256": "b" * 64,
            "spec_fingerprint_sha256": "c" * 64,
        }
    body = {
        "benchmark": {
            "name": f"Native-{token}",
            "version": "1",
            "source": "synthetic-test",
            "validation_scope": scope,
            "annotation_origin": "expert-human",
            "sampling_origin": "native",
            "reference_strength": "human-reference",
            "sampling_rates_hz": [60.0],
        },
        "model": {"name": "test-model"},
        "protocol": protocol,
        "metrics": {"accuracy": 0.5},
    }
    return {**body, "report_fingerprint_sha256": benchmark_fingerprint(body)}


def _summary(path: Path, reports: list[dict]) -> dict:
    return {
        "suite": "native-event-validation-v1",
        "status": "complete",
        "report_count": 3,
        "reports": reports,
        "source": {
            "data_file_name": "native.csv",
            "data_file_sha256": "b" * 64,
            "spec_file_name": "native-spec.json",
            "spec_fingerprint_sha256": "c" * 64,
        },
        "protocol": {},
        "suite_fingerprint_sha256": "a" * 64,
        "reports_verified": True,
        "manifest_path": str(path),
    }


def _member(name: str, path: str, report: dict) -> dict:
    return {
        "name": name,
        "path": path,
        "report_fingerprint_sha256": report["report_fingerprint_sha256"],
    }


def test_detached_native_model_report_requires_sibling_reviewed_suite(tmp_path):
    report = _report(
        scope=dashboard._NATIVE_MODEL_SCOPE,
        native_intake=True,
        token="detached",
    )
    report_path = tmp_path / "native-primary-model.json"

    with pytest.raises(BenchmarkIntegrityError, match="sibling native suite manifest"):
        dashboard._validate_native_report_for_dashboard(report_path, report)


def test_exact_reviewed_native_primary_model_child_passes(monkeypatch, tmp_path):
    report = _report(
        scope=dashboard._NATIVE_MODEL_SCOPE,
        native_intake=True,
        token="primary",
    )
    report_path = tmp_path / "native-primary-model.json"
    suite_path = tmp_path / dashboard._NATIVE_SUITE_MANIFEST_NAME
    suite_path.write_text("{}\n", encoding="utf-8")
    summary = _summary(
        suite_path,
        [
            _member("primary_annotator_model", report_path.name, report),
            {
                "name": "annotator_sensitivity_model",
                "path": "native-annotator-sensitivity-model.json",
                "report_fingerprint_sha256": "2" * 64,
            },
            {
                "name": "human_agreement",
                "path": "native-human-agreement.json",
                "report_fingerprint_sha256": "3" * 64,
            },
        ],
    )
    monkeypatch.setattr(
        dashboard,
        "_validate_native_suite_for_dashboard",
        lambda path: summary,
    )

    dashboard._validate_native_report_for_dashboard(report_path, report)


def test_exact_reviewed_native_sensitivity_model_child_passes(monkeypatch, tmp_path):
    report = _report(
        scope=dashboard._NATIVE_MODEL_SCOPE,
        native_intake=True,
        token="sensitivity",
    )
    report_path = tmp_path / "native-annotator-sensitivity-model.json"
    suite_path = tmp_path / dashboard._NATIVE_SUITE_MANIFEST_NAME
    suite_path.write_text("{}\n", encoding="utf-8")
    summary = _summary(
        suite_path,
        [
            {
                "name": "primary_annotator_model",
                "path": "native-primary-model.json",
                "report_fingerprint_sha256": "1" * 64,
            },
            _member("annotator_sensitivity_model", report_path.name, report),
            {
                "name": "human_agreement",
                "path": "native-human-agreement.json",
                "report_fingerprint_sha256": "3" * 64,
            },
        ],
    )
    monkeypatch.setattr(
        dashboard,
        "_validate_native_suite_for_dashboard",
        lambda path: summary,
    )

    dashboard._validate_native_report_for_dashboard(report_path, report)


def test_exact_reviewed_native_human_agreement_child_passes(monkeypatch, tmp_path):
    report = _report(
        scope=dashboard._NATIVE_AGREEMENT_SCOPE,
        native_intake=False,
        token="agreement",
    )
    report_path = tmp_path / "native-human-agreement.json"
    suite_path = tmp_path / dashboard._NATIVE_SUITE_MANIFEST_NAME
    suite_path.write_text("{}\n", encoding="utf-8")
    summary = _summary(
        suite_path,
        [
            {
                "name": "primary_annotator_model",
                "path": "native-primary-model.json",
                "report_fingerprint_sha256": "1" * 64,
            },
            {
                "name": "annotator_sensitivity_model",
                "path": "native-annotator-sensitivity-model.json",
                "report_fingerprint_sha256": "2" * 64,
            },
            _member("human_agreement", report_path.name, report),
        ],
    )
    monkeypatch.setattr(
        dashboard,
        "_validate_native_suite_for_dashboard",
        lambda path: summary,
    )

    dashboard._validate_native_report_for_dashboard(report_path, report)


def test_native_child_copy_or_fingerprint_drift_fails_closed(monkeypatch, tmp_path):
    report = _report(
        scope=dashboard._NATIVE_MODEL_SCOPE,
        native_intake=True,
        token="copy",
    )
    suite_path = tmp_path / dashboard._NATIVE_SUITE_MANIFEST_NAME
    suite_path.write_text("{}\n", encoding="utf-8")
    summary = _summary(
        suite_path,
        [
            _member("primary_annotator_model", "native-primary-model.json", report),
            {
                "name": "annotator_sensitivity_model",
                "path": "native-annotator-sensitivity-model.json",
                "report_fingerprint_sha256": "2" * 64,
            },
            {
                "name": "human_agreement",
                "path": "native-human-agreement.json",
                "report_fingerprint_sha256": "3" * 64,
            },
        ],
    )
    monkeypatch.setattr(
        dashboard,
        "_validate_native_suite_for_dashboard",
        lambda path: summary,
    )

    with pytest.raises(BenchmarkIntegrityError, match="exactly one"):
        dashboard._validate_native_report_for_dashboard(tmp_path / "copied.json", report)

    changed = dict(report)
    changed["report_fingerprint_sha256"] = "f" * 64
    with pytest.raises(BenchmarkIntegrityError, match="exactly one"):
        dashboard._validate_native_report_for_dashboard(
            tmp_path / "native-primary-model.json",
            changed,
        )


def test_native_provenance_scope_mismatch_fails_closed(tmp_path):
    report = _report(
        scope="generic-external-validation",
        native_intake=True,
        token="mismatch",
    )
    with pytest.raises(BenchmarkIntegrityError, match="disagrees with validation scope"):
        dashboard._validate_native_report_for_dashboard(tmp_path / "report.json", report)


def test_generic_non_native_report_keeps_existing_publication_path(tmp_path):
    report = _report(
        scope="generic-external-validation",
        native_intake=False,
        token="generic",
    )
    dashboard._validate_native_report_for_dashboard(tmp_path / "generic.json", report)


def test_native_suite_dashboard_requires_and_surfaces_exact_review(monkeypatch, tmp_path):
    suite_path = tmp_path / dashboard._NATIVE_SUITE_MANIFEST_NAME
    suite_path.write_text("{}\n", encoding="utf-8")
    summary = _summary(suite_path, [])
    approval = {
        "reviewer": "Scientific Reviewer",
        "reviewed_at": "2026-09-11T18:30:00Z",
        "review_scope": "native-event-suite-publication-review",
        "review_fingerprint_sha256": "5" * 64,
        "lineage": {
            "suite": "native-event-validation-v1",
            "suite_fingerprint_sha256": "a" * 64,
            "report_count": 3,
            "data_file_name": "native.csv",
            "data_file_sha256": "b" * 64,
            "spec_file_name": "native-spec.json",
            "spec_fingerprint_sha256": "c" * 64,
            "reports_verified": True,
        },
        "scientific_boundary": {
            "scientific_review_completed": True,
            "approved_for_public_frozen_evidence": True,
        },
    }
    monkeypatch.setattr(
        dashboard,
        "validate_native_scientific_review_approval",
        lambda path: approval,
    )
    monkeypatch.setattr(
        dashboard,
        "validate_native_event_suite_manifest",
        lambda path, verify_reports=True: summary,
    )

    validated = dashboard._validate_native_suite_for_dashboard(suite_path)
    assert validated["scientific_review"] == {
        "reviewer": "Scientific Reviewer",
        "reviewed_at": "2026-09-11T18:30:00Z",
        "review_scope": "native-event-suite-publication-review",
        "review_fingerprint_sha256": "5" * 64,
    }
