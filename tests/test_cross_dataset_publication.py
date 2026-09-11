from __future__ import annotations

import copy

import pandas as pd
import pytest

from gazeforge.benchmarks import (
    BenchmarkDatasetCard,
    benchmark_fingerprint,
    build_benchmark_report,
    freeze_benchmark_report,
)
from gazeforge.cross_dataset import CrossDatasetEventPrepared, CrossDatasetEventValidation
from gazeforge.cross_dataset_evidence import (
    CROSS_DATASET_BENCHMARK_NAME,
    CROSS_DATASET_VALIDATION_SCOPE,
    build_lund_hollywood2_cross_dataset_report,
    freeze_cross_dataset_frozen_report,
    validate_cross_dataset_frozen_report,
)
from gazeforge.cross_dataset_scientific_review import (
    write_cross_dataset_scientific_review_approval,
)
from gazeforge.dashboard import build_benchmark_dashboard, render_benchmark_dashboard_markdown
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.source_audit_lineage import SourceAuditLineageReceipt


def _lineage() -> SourceAuditLineageReceipt:
    return SourceAuditLineageReceipt(
        dataset_key="hollywood2em",
        audit_template_fingerprint_sha256="a" * 64,
        authorization_fingerprint_sha256="b" * 64,
        authorized_spec_fingerprint_sha256="c" * 64,
        audit_report_fingerprint_sha256="d" * 64,
        source_manifest_fingerprints_sha256={"source": "e" * 64},
        source_revision="test-revision",
    )


def _runner_outputs() -> tuple[
    CrossDatasetEventPrepared,
    CrossDatasetEventValidation,
    SourceAuditLineageReceipt,
]:
    lineage = _lineage()
    lineage_fingerprint = lineage.to_dict()["receipt_fingerprint_sha256"]
    dataset_reports = {
        "Hollywood2EM": {
            "source_sampling_rate_hz": 500.0,
            "target_sampling_rate_hz": 60.0,
            "sampling_origin_at_analysis": "resampled",
            "coordinate_source_unit": "pixels",
            "coordinate_unit_verified": True,
            "participant_identity_resolved": True,
            "source_audit_status": "verified",
            "source_audit_lineage_receipt_fingerprint_sha256": lineage_fingerprint,
            "source_audit_report_fingerprint_sha256": lineage.audit_report_fingerprint_sha256,
            "source_audit_spec_fingerprint_sha256": lineage.authorized_spec_fingerprint_sha256,
            "source_manifest_fingerprint_sha256": lineage.source_manifest_fingerprints_sha256[
                "source"
            ],
        },
        "Lund2013": {
            "source_sampling_rate_hz": 500.0,
            "target_sampling_rate_hz": 60.0,
            "sampling_origin_at_analysis": "resampled",
            "coordinate_source_unit": "pixels",
            "coordinate_unit_verified": True,
            "participant_identity_resolved": True,
            "source_audit_status": None,
            "source_audit_lineage_receipt_fingerprint_sha256": None,
            "source_audit_report_fingerprint_sha256": None,
            "source_audit_spec_fingerprint_sha256": None,
            "source_manifest_fingerprint_sha256": None,
        },
    }
    design = {
        "design": "harmonised_cross_dataset_event_benchmark",
        "dataset_ids": ["Hollywood2EM", "Lund2013"],
        "target_sampling_rate_hz": 60.0,
        "common_labels": ["fixation", "saccade", "pursuit"],
        "min_label_purity": 0.75,
        "ambiguous_label": "ambiguous",
        "require_resolved_participants": True,
        "require_verified_coordinates": True,
        "require_source_audits": True,
        "source_audit_lineage_policy": "required_for_external_audited_datasets",
        "require_all_common_labels": True,
        "participant_namespace_policy": "dataset_id::source_participant_id",
        "trial_namespace_policy": "dataset_id::source_trial_id",
        "validation_design": "leave_one_dataset_out",
        "models": ["RandomForest", "ContextMLP"],
        "random_state": 42,
        "context_radius_ms": 50.0,
        "rolling_window_ms": 80.0,
        "calibration_bins": 10,
        "event_min_iou": 0.5,
        "event_excluded_labels": ["ambiguous", "unlabelled", "undefined", "abstain"],
        "event_interval_convention": "half_open_[start,end)",
    }
    summary = pd.DataFrame(
        [
            {
                "model": model,
                "held_out_dataset": dataset,
                "n_test_rows": 100,
                "accuracy": 0.7,
                "balanced_accuracy": 0.68,
                "macro_f1": 0.67,
                "event_f1": 0.6,
                "event_mean_matched_iou": 0.7,
            }
            for model in ("RandomForest", "ContextMLP")
            for dataset in ("Hollywood2EM", "Lund2013")
        ]
    )
    prepared = CrossDatasetEventPrepared(
        data=pd.DataFrame(),
        dataset_reports=dataset_reports,
        design={key: value for key, value in design.items() if key not in {
            "validation_design",
            "models",
            "random_state",
            "context_radius_ms",
            "rolling_window_ms",
            "calibration_bins",
            "event_min_iou",
            "event_excluded_labels",
            "event_interval_convention",
        }},
    )
    validation_fingerprint = benchmark_fingerprint(
        {
            "design": design,
            "dataset_reports": dataset_reports,
            "summary": summary.to_dict(orient="records"),
        }
    )
    validation = CrossDatasetEventValidation(
        random_forest=None,  # type: ignore[arg-type]
        context_mlp=None,  # type: ignore[arg-type]
        summary=summary,
        design=design,
        report_fingerprint_sha256=validation_fingerprint,
    )
    return prepared, validation, lineage


def _report() -> dict:
    prepared, validation, lineage = _runner_outputs()
    return build_lund_hollywood2_cross_dataset_report(
        prepared,
        validation,
        hollywood2_lineage=lineage,
        benchmark_version="test-v1",
    )


def test_cross_dataset_report_binds_guarded_runner_and_hollywood_lineage() -> None:
    report = _report()
    validated = validate_cross_dataset_frozen_report(report)

    assert validated["benchmark"]["name"] == CROSS_DATASET_BENCHMARK_NAME
    assert validated["benchmark"]["validation_scope"] == CROSS_DATASET_VALIDATION_SCOPE
    assert validated["benchmark"]["sampling_origin"] == "resampled"
    assert validated["benchmark"]["reference_strength"] == "derived-human-reference"
    protocol = validated["protocol"]
    hollywood = protocol["dataset_reports"]["Hollywood2EM"]
    assert (
        protocol["hollywood2_source_audit_lineage"]["receipt_fingerprint_sha256"]
        == hollywood["source_audit_lineage_receipt_fingerprint_sha256"]
    )
    assert protocol["scientific_boundary"]["gp3_validity_claim_created"] is False
    assert protocol["scientific_boundary"]["source_rights_expanded"] is False


def test_cross_dataset_validator_rejects_lineage_tampering() -> None:
    report = copy.deepcopy(_report())
    report["protocol"]["dataset_reports"]["Hollywood2EM"][
        "source_audit_report_fingerprint_sha256"
    ] = "f" * 64
    body = {key: report[key] for key in ("benchmark", "model", "protocol", "metrics")}
    report["report_fingerprint_sha256"] = benchmark_fingerprint(body)

    with pytest.raises(BenchmarkIntegrityError, match="lineage receipt"):
        validate_cross_dataset_frozen_report(report)


def test_dashboard_rejects_cross_dataset_report_without_scientific_review(tmp_path) -> None:
    report_path = tmp_path / "cross.json"
    freeze_cross_dataset_frozen_report(_report(), report_path)

    with pytest.raises(BenchmarkIntegrityError, match="scientific-review"):
        build_benchmark_dashboard(tmp_path)


def test_dashboard_surfaces_only_exact_reviewed_cross_dataset_report(tmp_path) -> None:
    report_path = tmp_path / "cross.json"
    freeze_cross_dataset_frozen_report(_report(), report_path)
    review_path = write_cross_dataset_scientific_review_approval(
        report_path,
        reviewer="Method Reviewer",
        reviewed_at="2026-09-11T12:00:00+00:00",
        review_rationale="Reviewed source lineage, design, metrics, and claim boundaries.",
    )

    dashboard = build_benchmark_dashboard(tmp_path)
    assert len(dashboard.reports) == 1
    row = dashboard.table.iloc[0]
    assert row["scientific_review_reviewer"] == "Method Reviewer"
    assert row["scientific_review_scope"] == "cross-dataset-report-publication-review"

    review = pd.read_json(review_path, typ="series")
    review_fingerprint = str(review["review_fingerprint_sha256"])
    assert row["scientific_review_fingerprint_sha256"] == review_fingerprint
    markdown = render_benchmark_dashboard_markdown(dashboard)
    assert "Method Reviewer" in markdown
    assert review_fingerprint[:12] in markdown
    assert review_fingerprint not in markdown


def test_dashboard_rejects_copied_cross_dataset_report_path(tmp_path) -> None:
    original = tmp_path / "original.json"
    freeze_cross_dataset_frozen_report(_report(), original)
    write_cross_dataset_scientific_review_approval(
        original,
        reviewer="Method Reviewer",
        reviewed_at="2026-09-11T12:00:00+00:00",
        review_rationale="Reviewed exact report.",
    )
    copied = tmp_path / "copied.json"
    copied.write_bytes(original.read_bytes())
    original.unlink()

    with pytest.raises(BenchmarkIntegrityError, match="missing or non-regular report"):
        build_benchmark_dashboard(tmp_path)


def test_dashboard_rejects_generic_leave_one_dataset_out_bypass(tmp_path) -> None:
    card = BenchmarkDatasetCard(
        name="Lund2013-Hollywood2EM-manual-report",
        version="manual-v1",
        source="manual",
        license="unknown",
        task="cross-dataset event validation",
        sampling_rates_hz=[60.0],
        validation_scope="development",
        annotation_origin="expert-manual",
        sampling_origin="resampled",
        reference_strength="derived-human-reference",
    )
    report = build_benchmark_report(
        benchmark=card,
        model={"models": ["RandomForest", "ContextMLP"]},
        protocol={"validation_design": {"validation_design": "leave_one_dataset_out"}},
        metrics={"summary": []},
    )
    freeze_benchmark_report(report, tmp_path / "generic-cross.json")

    with pytest.raises(BenchmarkIntegrityError, match="review-gated Frozen Evidence schema"):
        build_benchmark_dashboard(tmp_path)
