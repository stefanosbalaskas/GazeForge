import json

import pytest

from gazeforge.benchmarks import (
    BenchmarkDatasetCard,
    benchmark_fingerprint,
    build_benchmark_report,
)
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.public_evidence import (
    build_public_benchmark_dashboard,
    validate_public_benchmark_report_families,
)


def _write(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _generic_report():
    card = BenchmarkDatasetCard(
        name="Independent-human-benchmark",
        version="1",
        source="external-test-source",
        license="test-only",
        task="eye-event classification",
        sampling_rates_hz=[60.0],
        validation_scope="external-empirical-benchmark",
        annotation_origin="expert-manual",
        sampling_origin="resampled",
        reference_strength="derived-human-reference",
    )
    return build_benchmark_report(
        benchmark=card,
        model={"models": ["RandomForest"]},
        protocol={"n_splits": 5},
        metrics={"summary": [{"model": "RandomForest", "macro_f1_mean": 0.5}]},
    )


def _gaze_in_wild_report(*, task_stratified: bool):
    card = BenchmarkDatasetCard(
        name="Gaze-in-the-Wild-labeller-5",
        version="fixture",
        source="audited-test-source",
        license="test-only",
        task="participant-held-out naturalistic eye-event classification",
        sampling_rates_hz=[60.0],
        validation_scope=(
            "lineage-bound-audited-source-participant-held-out-model-validation"
        ),
        annotation_origin="human-manual",
        sampling_origin="resampled",
        reference_strength="derived-human-reference",
    )
    task_mapping = (
        {
            "task_col": "task_label",
            "mapping_rows": 1,
            "mapping_fingerprint_sha256": "a" * 64,
            "mapping": [
                {
                    "participant_id": "P01",
                    "trial_id": "T1",
                    "task_label": "Tea_Making",
                }
            ],
            "task_labels": ["Tea_Making"],
            "task_labels_inferred_from_filenames": False,
        }
        if task_stratified
        else None
    )
    return build_benchmark_report(
        benchmark=card,
        model={"models": ["I-VT", "RandomForest", "ContextMLP"]},
        protocol={
            "preparation": {
                "dataset": "Gaze-in-the-Wild",
                "source_audit_lineage_receipt_fingerprint_sha256": "b" * 64,
                "task_mapping": task_mapping,
            },
            "task_sensitivity_design": (
                {"models_refit_by_stratum": False} if task_stratified else None
            ),
        },
        metrics={
            "summary": [{"model": "RandomForest", "macro_f1_mean": 0.5}],
            "task_summary": (
                [{"task_label": "Tea_Making", "macro_f1_mean": 0.4}]
                if task_stratified
                else []
            ),
            "task_fold_metrics": [],
        },
    )


def test_public_dashboard_preserves_unrelated_generic_reports(tmp_path):
    _write(tmp_path / "report.json", _generic_report())

    validate_public_benchmark_report_families(tmp_path)
    dashboard = build_public_benchmark_dashboard(tmp_path)

    assert len(dashboard.reports) == 1
    assert dashboard.table.iloc[0]["benchmark"] == "Independent-human-benchmark"


@pytest.mark.parametrize("task_stratified", [False, True])
def test_public_dashboard_rejects_generic_gaze_in_wild_benchmark_rows(
    tmp_path,
    task_stratified,
):
    _write(
        tmp_path / "gaze-in-wild-report.json",
        _gaze_in_wild_report(task_stratified=task_stratified),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot use the generic public Frozen Evidence publication path",
    ):
        build_public_benchmark_dashboard(tmp_path)


def test_public_dashboard_rejects_partial_gaze_in_wild_family_signal(tmp_path):
    report = _generic_report()
    report["benchmark"]["validation_scope"] = (
        "lineage-bound-audited-source-participant-held-out-model-validation"
    )
    body = {key: report[key] for key in ("benchmark", "model", "protocol", "metrics")}
    report["report_fingerprint_sha256"] = benchmark_fingerprint(body)
    _write(tmp_path / "partial-signal.json", report)

    with pytest.raises(BenchmarkIntegrityError, match="Gaze-in-the-Wild benchmark result rows"):
        build_public_benchmark_dashboard(tmp_path)
