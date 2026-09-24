from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

import gazeforge.dashboard as dashboard
import gazeforge.gaze_in_wild_explicit_task_mapping_intake as mapping
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError

# ============================================================
# SHARED
# ============================================================


def _write_json(
    path: Path,
    payload,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


# ============================================================
# DASHBOARD REPORT FIXTURES
# ============================================================


def _report(
    *,
    name="Fixture",
    scope="external-empirical-benchmark",
    protocol=None,
    model=None,
    sampling_rates=(60.0,),
):
    if protocol is None:
        protocol = {
            "n_splits": 2,
        }

    if model is None:
        model = {
            "models": [
                "A",
                "B",
            ]
        }

    benchmark = {
        "name": name,
        "version": "1.0",
        "source": "synthetic-test",
        "validation_scope": scope,
        "annotation_origin": "human",
        "sampling_origin": "native",
        "reference_strength": "human-reference",
        "sampling_rates_hz": sampling_rates,
    }

    body = {
        "benchmark": benchmark,
        "model": model,
        "protocol": protocol,
        "metrics": {
            "accuracy": 0.8,
        },
    }

    return {
        **body,
        "report_fingerprint_sha256": (benchmark_fingerprint(body)),
    }


def _cross_report():
    return _report(
        name=(dashboard.CROSS_DATASET_BENCHMARK_NAME),
        scope=(dashboard.CROSS_DATASET_VALIDATION_SCOPE),
        protocol={
            "evidence_schema": (dashboard.CROSS_DATASET_EVIDENCE_SCHEMA),
            "validation_design": {
                "validation_design": ("leave_one_dataset_out"),
            },
        },
    )


# ============================================================
# DASHBOARD REPORT VALIDATION
# ============================================================


def test_dashboard_report_must_be_dict():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="JSON object",
    ):
        dashboard.validate_frozen_benchmark_report([])


def test_dashboard_report_required_fields():
    report = _report()
    report.pop("metrics")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing required fields",
    ):
        dashboard.validate_frozen_benchmark_report(report)


def test_dashboard_report_benchmark_object():
    report = _report()
    report["benchmark"] = "bad"

    body = {key: report[key] for key in dashboard._REPORT_BODY_KEYS}
    report["report_fingerprint_sha256"] = benchmark_fingerprint(body)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="metadata must be a JSON object",
    ):
        dashboard.validate_frozen_benchmark_report(report)


def test_dashboard_load_missing(
    tmp_path,
):
    with pytest.raises(
        FileNotFoundError,
    ):
        dashboard.load_frozen_benchmark_report(tmp_path / "missing.json")


def test_dashboard_load_bad_json(
    tmp_path,
):
    path = tmp_path / "bad.json"
    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Invalid benchmark JSON",
    ):
        dashboard.load_frozen_benchmark_report(path)


def test_dashboard_load_valid(
    tmp_path,
):
    report = _report()

    path = tmp_path / "report.json"
    _write_json(
        path,
        report,
    )

    loaded = dashboard.load_frozen_benchmark_report(path)

    assert loaded["report_fingerprint_sha256"] == report["report_fingerprint_sha256"]

    expected_benchmark = dict(report["benchmark"])

    if isinstance(
        expected_benchmark.get("sampling_rates_hz"),
        tuple,
    ):
        expected_benchmark["sampling_rates_hz"] = list(expected_benchmark["sampling_rates_hz"])

    assert loaded["benchmark"] == expected_benchmark

    assert loaded["model"] == report["model"]

    assert loaded["protocol"] == report["protocol"]

    assert loaded["metrics"] == report["metrics"]


# ============================================================
# DASHBOARD DISCOVERY
# ============================================================


def test_dashboard_discovery_missing_root(
    tmp_path,
):
    with pytest.raises(
        FileNotFoundError,
    ):
        dashboard.discover_frozen_benchmark_reports(tmp_path / "missing")


def test_dashboard_discovery_nonrecursive(
    tmp_path,
):
    root_report = tmp_path / "root.json"
    nested = tmp_path / "nested"
    nested.mkdir()

    nested_report = nested / "nested.json"

    _write_json(
        root_report,
        _report(name="Root"),
    )
    _write_json(
        nested_report,
        _report(name="Nested"),
    )

    found = dashboard.discover_frozen_benchmark_reports(
        tmp_path,
        recursive=False,
    )

    assert found == (root_report,)


def test_dashboard_discovery_skips_invalid_json(
    tmp_path,
):
    (tmp_path / "bad.json").write_text(
        "{",
        encoding="utf-8",
    )

    assert dashboard.discover_frozen_benchmark_reports(tmp_path) == ()


def test_dashboard_discovery_skips_nonobject(
    tmp_path,
):
    _write_json(
        tmp_path / "array.json",
        [
            1,
            2,
        ],
    )

    assert dashboard.discover_frozen_benchmark_reports(tmp_path) == ()


def test_dashboard_discovery_skips_fp_only(
    tmp_path,
):
    _write_json(
        tmp_path / "fp.json",
        {"report_fingerprint_sha256": ("a" * 64)},
    )

    assert dashboard.discover_frozen_benchmark_reports(tmp_path) == ()


def test_dashboard_named_manifest_missing_root(
    tmp_path,
):
    with pytest.raises(
        FileNotFoundError,
    ):
        dashboard._discover_named_suite_manifests(
            tmp_path / "missing",
            "manifest.json",
            recursive=True,
        )


def test_dashboard_named_manifest_recursive(
    tmp_path,
):
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)

    path = nested / "manifest.json"
    path.write_text(
        "{}",
        encoding="utf-8",
    )

    assert dashboard._discover_named_suite_manifests(
        tmp_path,
        "manifest.json",
        recursive=True,
    ) == (path,)


def test_dashboard_named_manifest_nonrecursive_absent(
    tmp_path,
):
    assert (
        dashboard._discover_named_suite_manifests(
            tmp_path,
            "manifest.json",
            recursive=False,
        )
        == ()
    )


def test_dashboard_named_manifest_nonrecursive_present(
    tmp_path,
):
    path = tmp_path / "manifest.json"
    path.write_text(
        "{}",
        encoding="utf-8",
    )

    assert dashboard._discover_named_suite_manifests(
        tmp_path,
        "manifest.json",
        recursive=False,
    ) == (path,)


def test_dashboard_lund_manifest_wrapper(
    tmp_path,
):
    path = tmp_path / dashboard._LUND_SUITE_MANIFEST_NAME

    path.write_text(
        "{}",
        encoding="utf-8",
    )

    assert dashboard.discover_lund2013_suite_manifests(
        tmp_path,
        recursive=False,
    ) == (path,)


def test_dashboard_native_manifest_wrapper(
    tmp_path,
):
    path = tmp_path / dashboard._NATIVE_SUITE_MANIFEST_NAME

    path.write_text(
        "{}",
        encoding="utf-8",
    )

    assert dashboard.discover_native_event_suite_manifests(
        tmp_path,
        recursive=False,
    ) == (path,)


# ============================================================
# DASHBOARD ROW HELPERS
# ============================================================


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        (
            None,
            "",
        ),
        (
            [],
            "",
        ),
        (
            {
                "models": [
                    "A",
                    "B",
                ]
            },
            "A, B",
        ),
        (
            {"models": "A"},
            "A",
        ),
        (
            {"name": "A"},
            "A",
        ),
        (
            {"model": "B"},
            "B",
        ),
        (
            {"type": "C"},
            "C",
        ),
        (
            {"other": 1},
            "",
        ),
    ],
)
def test_dashboard_model_names(
    model,
    expected,
):
    assert dashboard._model_names(model) == expected


def test_dashboard_row_scalar_sampling():
    report = _report(
        model={"name": "M"},
        sampling_rates=60.0,
    )

    row = dashboard._dashboard_row(
        report,
        "report.json",
    )

    assert row["sampling_rates_hz"] == "60.0"

    assert row["models"] == "M"


def test_dashboard_row_review():
    report = _report()

    row = dashboard._dashboard_row(
        report,
        "report.json",
        scientific_review={
            "reviewer": "Reviewer",
            "reviewed_at": "2026-09-24T12:00:00Z",
            "review_scope": "scope",
            "review_fingerprint_sha256": ("a" * 64),
        },
    )

    assert row["scientific_review_reviewer"] == "Reviewer"


@pytest.mark.parametrize(
    ("summary", "expected"),
    [
        (
            {"source_manifest": {"manifest_fingerprint_sha256": ("a" * 64)}},
            "a" * 64,
        ),
        (
            {"source": {("source_manifest_fingerprint_sha256"): ("b" * 64)}},
            "b" * 64,
        ),
        (
            {},
            "",
        ),
    ],
)
def test_dashboard_suite_source_fp(
    summary,
    expected,
):
    assert dashboard._suite_source_fingerprint(summary) == expected


def test_dashboard_suite_row_full():
    summary = {
        "suite": "Suite",
        "status": "complete",
        "report_count": 2,
        "suite_fingerprint_sha256": ("a" * 64),
        "source_manifest": {"manifest_fingerprint_sha256": ("b" * 64)},
        "protocol": {
            "target_sampling_rate_hz": 60.0,
            "model_name": "Model",
            "model_version": "1.2",
            "reference_stream_id": "ref",
            "human_human_agreement_included": True,
        },
        "scientific_review": {
            "reviewer": "R",
            "reviewed_at": "2026",
            "review_scope": "scope",
            "review_fingerprint_sha256": ("c" * 64),
        },
    }

    row = dashboard._suite_row(
        summary,
        "suite.json",
    )

    assert row["target_sampling_rate_hz"] == "60"

    assert row["model"] == "Model 1.2"

    assert row["human_human_agreement_included"] == "true"

    assert row["scientific_review_reviewer"] == "R"


def test_dashboard_suite_row_minimal():
    summary = {
        "suite": "Suite",
        "status": "complete",
        "report_count": 0,
        "suite_fingerprint_sha256": ("a" * 64),
    }

    row = dashboard._suite_row(
        summary,
        "suite.json",
    )

    assert row["model"] == ""
    assert row["scientific_review_reviewer"] == ""


def test_dashboard_validated_suite_records(
    tmp_path,
):
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"

    seen = []

    result = dashboard._validated_suite_records(
        (
            first,
            second,
        ),
        lambda path: seen.append(path) or {"path": str(path)},
    )

    assert seen == [
        first,
        second,
    ]

    assert len(result) == 2


# ============================================================
# CROSS-DATASET SIGNAL + REVIEW GATES
# ============================================================


def test_dashboard_cross_signal_false():
    assert not (dashboard._cross_dataset_dashboard_signal(_report()))


def test_dashboard_cross_signal_true():
    assert dashboard._cross_dataset_dashboard_signal(_cross_report())


@pytest.mark.parametrize(
    "mutator",
    [
        lambda report: report["benchmark"].update({"validation_scope": "wrong"}),
        lambda report: report["protocol"].update({"evidence_schema": "wrong"}),
        lambda report: report["protocol"].update({"validation_design": {}}),
    ],
)
def test_dashboard_partial_cross_signal(
    mutator,
):
    report = _cross_report()
    mutator(report)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not match",
    ):
        dashboard._cross_dataset_dashboard_signal(report)


def _cross_approval(
    path: Path,
    report,
    *,
    reviewed=True,
    approved=True,
):
    return {
        "lineage": {
            "report_file_name": (path.name),
            ("report_fingerprint_sha256"): report["report_fingerprint_sha256"],
        },
        "scientific_boundary": {
            "scientific_review_completed": (reviewed),
            ("approved_for_public_frozen_evidence"): approved,
        },
        "reviewer": "R",
        "reviewed_at": "2026",
        "review_scope": "scope",
        "review_fingerprint_sha256": ("a" * 64),
    }


def test_dashboard_cross_validate_non_cross(
    tmp_path,
):
    assert (
        dashboard._validate_cross_dataset_report_for_dashboard(
            tmp_path / "r.json",
            _report(),
        )
        is None
    )


def test_dashboard_cross_validate_success(
    monkeypatch,
    tmp_path,
):
    report = _cross_report()
    path = tmp_path / "r.json"

    monkeypatch.setattr(
        dashboard,
        "validate_cross_dataset_frozen_report",
        lambda value: value,
    )

    monkeypatch.setattr(
        dashboard,
        ("validate_cross_dataset_scientific_review_approval"),
        lambda root: _cross_approval(
            path,
            report,
        ),
    )

    approval = dashboard._validate_cross_dataset_report_for_dashboard(
        path,
        report,
    )

    assert approval["reviewer"] == "R"


@pytest.mark.parametrize(
    (
        "approval",
        "message",
    ),
    [
        (
            {
                "lineage": [],
                "scientific_boundary": {},
            },
            "sections are invalid",
        ),
        (
            {
                "lineage": {
                    "report_file_name": "other.json",
                    ("report_fingerprint_sha256"): "x",
                },
                "scientific_boundary": {
                    ("scientific_review_completed"): True,
                    ("approved_for_public_frozen_evidence"): True,
                },
            },
            "exact scientifically reviewed file",
        ),
    ],
)
def test_dashboard_cross_validate_failures(
    monkeypatch,
    tmp_path,
    approval,
    message,
):
    report = _cross_report()
    path = tmp_path / "r.json"

    monkeypatch.setattr(
        dashboard,
        "validate_cross_dataset_frozen_report",
        lambda value: value,
    )

    monkeypatch.setattr(
        dashboard,
        ("validate_cross_dataset_scientific_review_approval"),
        lambda root: approval,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        dashboard._validate_cross_dataset_report_for_dashboard(
            path,
            report,
        )


def test_dashboard_cross_fp_failure(
    monkeypatch,
    tmp_path,
):
    report = _cross_report()
    path = tmp_path / "r.json"

    approval = _cross_approval(
        path,
        report,
    )

    approval["lineage"]["report_fingerprint_sha256"] = "0" * 64

    monkeypatch.setattr(
        dashboard,
        "validate_cross_dataset_frozen_report",
        lambda value: value,
    )

    monkeypatch.setattr(
        dashboard,
        ("validate_cross_dataset_scientific_review_approval"),
        lambda root: approval,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exact reviewed fingerprint",
    ):
        dashboard._validate_cross_dataset_report_for_dashboard(
            path,
            report,
        )


@pytest.mark.parametrize(
    (
        "reviewed",
        "approved",
        "message",
    ),
    [
        (
            False,
            True,
            "completed scientific review",
        ),
        (
            True,
            False,
            "explicit Frozen Evidence approval",
        ),
    ],
)
def test_dashboard_cross_boundary_failures(
    monkeypatch,
    tmp_path,
    reviewed,
    approved,
    message,
):
    report = _cross_report()
    path = tmp_path / "r.json"

    approval = _cross_approval(
        path,
        report,
        reviewed=reviewed,
        approved=approved,
    )

    monkeypatch.setattr(
        dashboard,
        "validate_cross_dataset_frozen_report",
        lambda value: value,
    )

    monkeypatch.setattr(
        dashboard,
        ("validate_cross_dataset_scientific_review_approval"),
        lambda root: approval,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        dashboard._validate_cross_dataset_report_for_dashboard(
            path,
            report,
        )


# ============================================================
# NATIVE SUITE + REPORT GATES
# ============================================================


def _native_summary():
    return {
        "suite": "native",
        "status": "complete",
        "suite_fingerprint_sha256": ("a" * 64),
        "report_count": 2,
        "source": {
            "data_file_name": "data.csv",
            "data_file_sha256": ("b" * 64),
            "spec_file_name": "spec.json",
            "spec_fingerprint_sha256": ("c" * 64),
        },
        "reports": [],
    }


def _native_approval():
    return {
        "lineage": {
            "suite_fingerprint_sha256": ("a" * 64),
            "report_count": 2,
            "data_file_name": "data.csv",
            "data_file_sha256": ("b" * 64),
            "spec_file_name": "spec.json",
            "spec_fingerprint_sha256": ("c" * 64),
        },
        "scientific_boundary": {
            "scientific_review_completed": True,
            ("approved_for_public_frozen_evidence"): True,
        },
        "reviewer": "R",
        "reviewed_at": "2026",
        "review_scope": "scope",
        "review_fingerprint_sha256": ("d" * 64),
    }


def _patch_native(
    monkeypatch,
    *,
    summary=None,
    approval=None,
):
    if summary is None:
        summary = _native_summary()

    if approval is None:
        approval = _native_approval()

    monkeypatch.setattr(
        dashboard,
        "validate_native_event_suite_manifest",
        lambda path, verify_reports=True: summary,
    )

    monkeypatch.setattr(
        dashboard,
        ("validate_native_scientific_review_approval"),
        lambda root: approval,
    )


def test_dashboard_native_suite_success(
    monkeypatch,
    tmp_path,
):
    _patch_native(monkeypatch)

    result = dashboard._validate_native_suite_for_dashboard(tmp_path / "suite.json")

    assert result["scientific_review"]["reviewer"] == "R"


def test_dashboard_native_lineage_invalid(
    monkeypatch,
    tmp_path,
):
    approval = _native_approval()
    approval["lineage"] = []

    _patch_native(
        monkeypatch,
        approval=approval,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lineage is invalid",
    ):
        dashboard._validate_native_suite_for_dashboard(tmp_path / "suite.json")


def test_dashboard_native_source_invalid(
    monkeypatch,
    tmp_path,
):
    summary = _native_summary()
    summary["source"] = None

    _patch_native(
        monkeypatch,
        summary=summary,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity is invalid",
    ):
        dashboard._validate_native_suite_for_dashboard(tmp_path / "suite.json")


def test_dashboard_native_lineage_mismatch(
    monkeypatch,
    tmp_path,
):
    approval = _native_approval()

    approval["lineage"]["report_count"] = 99

    _patch_native(
        monkeypatch,
        approval=approval,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="report_count disagree",
    ):
        dashboard._validate_native_suite_for_dashboard(tmp_path / "suite.json")


def test_dashboard_native_boundary_invalid(
    monkeypatch,
    tmp_path,
):
    approval = _native_approval()

    approval["scientific_boundary"] = []

    _patch_native(
        monkeypatch,
        approval=approval,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="boundary is invalid",
    ):
        dashboard._validate_native_suite_for_dashboard(tmp_path / "suite.json")


@pytest.mark.parametrize(
    (
        "field",
        "message",
    ),
    [
        (
            ("scientific_review_completed"),
            "completed scientific review",
        ),
        (
            ("approved_for_public_frozen_evidence"),
            "explicit Frozen Evidence approval",
        ),
    ],
)
def test_dashboard_native_boundary_false(
    monkeypatch,
    tmp_path,
    field,
    message,
):
    approval = _native_approval()

    approval["scientific_boundary"][field] = False

    _patch_native(
        monkeypatch,
        approval=approval,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        dashboard._validate_native_suite_for_dashboard(tmp_path / "suite.json")


def _native_report(
    scope,
    *,
    native_intake=None,
):
    report = _report(
        scope=scope,
    )

    if native_intake is not None:
        report["protocol"]["native_intake"] = native_intake

    return report


def test_dashboard_native_child_none():
    report = _native_report("other")

    assert dashboard._native_dashboard_child_names(report) is None


def test_dashboard_native_model_child():
    report = _native_report(
        dashboard._NATIVE_MODEL_SCOPE,
        native_intake={"source": "test"},
    )

    assert dashboard._native_dashboard_child_names(report) == dashboard._NATIVE_MODEL_CHILDREN


def test_dashboard_native_model_missing_intake():
    report = _native_report(
        dashboard._NATIVE_MODEL_SCOPE,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing native_intake",
    ):
        dashboard._native_dashboard_child_names(report)


def test_dashboard_native_agreement_child():
    report = _native_report(
        dashboard._NATIVE_AGREEMENT_SCOPE,
    )

    assert dashboard._native_dashboard_child_names(report) == frozenset({"human_agreement"})


def test_dashboard_native_agreement_has_intake():
    report = _native_report(
        dashboard._NATIVE_AGREEMENT_SCOPE,
        native_intake={"source": "test"},
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="model-only native_intake",
    ):
        dashboard._native_dashboard_child_names(report)


def test_dashboard_native_intake_wrong_scope():
    report = _native_report(
        "other",
        native_intake={"source": "test"},
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="disagrees with validation scope",
    ):
        dashboard._native_dashboard_child_names(report)


def test_dashboard_native_report_missing_suite(
    tmp_path,
):
    report = _native_report(
        dashboard._NATIVE_MODEL_SCOPE,
        native_intake={"source": "test"},
    )

    path = tmp_path / "report.json"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="suite manifest is missing",
    ):
        dashboard._validate_native_report_for_dashboard(
            path,
            report,
        )


def test_dashboard_native_report_non_native(
    tmp_path,
):
    dashboard._validate_native_report_for_dashboard(
        tmp_path / "r.json",
        _report(),
    )


def test_dashboard_native_inventory_invalid(
    monkeypatch,
    tmp_path,
):
    report = _native_report(
        dashboard._NATIVE_MODEL_SCOPE,
        native_intake={"source": "test"},
    )

    path = tmp_path / "report.json"
    suite = tmp_path / dashboard._NATIVE_SUITE_MANIFEST_NAME

    suite.write_text(
        "{}",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        dashboard,
        "_validate_native_suite_for_dashboard",
        lambda value: {"reports": None},
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="inventory is invalid",
    ):
        dashboard._validate_native_report_for_dashboard(
            path,
            report,
        )


def test_dashboard_native_membership_success(
    monkeypatch,
    tmp_path,
):
    report = _native_report(
        dashboard._NATIVE_MODEL_SCOPE,
        native_intake={"source": "test"},
    )

    path = tmp_path / "report.json"
    path.write_text(
        "{}",
        encoding="utf-8",
    )

    suite = tmp_path / dashboard._NATIVE_SUITE_MANIFEST_NAME

    suite.write_text(
        "{}",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        dashboard,
        "_validate_native_suite_for_dashboard",
        lambda value: {
            "reports": [
                "bad",
                {
                    "name": ("primary_annotator_model"),
                    ("report_fingerprint_sha256"): report["report_fingerprint_sha256"],
                    "path": "report.json",
                },
            ]
        },
    )

    dashboard._validate_native_report_for_dashboard(
        path,
        report,
    )


def test_dashboard_native_membership_missing(
    monkeypatch,
    tmp_path,
):
    report = _native_report(
        dashboard._NATIVE_MODEL_SCOPE,
        native_intake={"source": "test"},
    )

    path = tmp_path / "report.json"

    suite = tmp_path / dashboard._NATIVE_SUITE_MANIFEST_NAME

    suite.write_text(
        "{}",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        dashboard,
        "_validate_native_suite_for_dashboard",
        lambda value: {"reports": []},
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly one",
    ):
        dashboard._validate_native_report_for_dashboard(
            path,
            report,
        )


# ============================================================
# VISUS GATES
# ============================================================


def _visus_summary():
    return {
        "suite": "visus",
        "status": "complete",
        "suite_fingerprint_sha256": ("a" * 64),
        "report_count": 2,
        "reports": [],
    }


def _visus_approval():
    return {
        "lineage": {
            "suite_fingerprint_sha256": ("a" * 64),
            "report_count": 2,
        },
        "scientific_boundary": {
            "scientific_review_completed": True,
            ("approved_for_public_frozen_evidence"): True,
        },
        "reviewer": "R",
        "reviewed_at": "2026",
        "review_scope": "scope",
        "review_fingerprint_sha256": ("b" * 64),
    }


def _patch_visus(
    monkeypatch,
    *,
    summary=None,
    approval=None,
):
    if summary is None:
        summary = _visus_summary()

    if approval is None:
        approval = _visus_approval()

    monkeypatch.setattr(
        dashboard,
        ("validate_visus_dynamic_aoi_suite_manifest"),
        lambda path, verify_reports=True: summary,
    )

    monkeypatch.setattr(
        dashboard,
        ("validate_visus_scientific_review_approval"),
        lambda root: approval,
    )


def test_dashboard_visus_suite_success(
    monkeypatch,
    tmp_path,
):
    _patch_visus(monkeypatch)

    result = dashboard._validate_visus_suite_for_dashboard(tmp_path / "suite.json")

    assert result["scientific_review"]["reviewer"] == "R"


def test_dashboard_visus_lineage_invalid(
    monkeypatch,
    tmp_path,
):
    approval = _visus_approval()
    approval["lineage"] = []

    _patch_visus(
        monkeypatch,
        approval=approval,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lineage is invalid",
    ):
        dashboard._validate_visus_suite_for_dashboard(tmp_path / "suite.json")


def test_dashboard_visus_fp_mismatch(
    monkeypatch,
    tmp_path,
):
    approval = _visus_approval()

    approval["lineage"]["suite_fingerprint_sha256"] = "0" * 64

    _patch_visus(
        monkeypatch,
        approval=approval,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprints disagree",
    ):
        dashboard._validate_visus_suite_for_dashboard(tmp_path / "suite.json")


def test_dashboard_visus_count_mismatch(
    monkeypatch,
    tmp_path,
):
    approval = _visus_approval()

    approval["lineage"]["report_count"] = 3

    _patch_visus(
        monkeypatch,
        approval=approval,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="report counts disagree",
    ):
        dashboard._validate_visus_suite_for_dashboard(tmp_path / "suite.json")


def test_dashboard_visus_boundary_invalid(
    monkeypatch,
    tmp_path,
):
    approval = _visus_approval()

    approval["scientific_boundary"] = []

    _patch_visus(
        monkeypatch,
        approval=approval,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="boundary is invalid",
    ):
        dashboard._validate_visus_suite_for_dashboard(tmp_path / "suite.json")


@pytest.mark.parametrize(
    (
        "field",
        "message",
    ),
    [
        (
            ("scientific_review_completed"),
            "completed scientific review",
        ),
        (
            ("approved_for_public_frozen_evidence"),
            "explicit Frozen Evidence approval",
        ),
    ],
)
def test_dashboard_visus_boundary_false(
    monkeypatch,
    tmp_path,
    field,
    message,
):
    approval = _visus_approval()

    approval["scientific_boundary"][field] = False

    _patch_visus(
        monkeypatch,
        approval=approval,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        dashboard._validate_visus_suite_for_dashboard(tmp_path / "suite.json")


def _visus_report(
    *,
    name="VISUS-fixture",
    evaluation_type=("visus-audited-model-human-dynamic-aoi"),
    scope=("audited-source-model-human-dynamic-aoi"),
):
    return _report(
        name=name,
        scope=scope,
        protocol={"evaluation_type": (evaluation_type)},
    )


def test_dashboard_visus_child_none():
    assert dashboard._visus_dashboard_child_name(_report()) is None


def test_dashboard_visus_child_model():
    assert dashboard._visus_dashboard_child_name(_visus_report()) == "model_human_validation"


def test_dashboard_visus_child_human():
    assert (
        dashboard._visus_dashboard_child_name(
            _visus_report(
                evaluation_type=("visus-independent-human-dynamic-aoi-agreement"),
                scope=("audited-source-independent-human-dynamic-aoi-agreement"),
            )
        )
        == "human_human_agreement"
    )


def test_dashboard_visus_unknown_schema():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="known review-gated child schema",
    ):
        dashboard._visus_dashboard_child_name(
            _visus_report(
                evaluation_type="unknown",
            )
        )


def test_dashboard_visus_scope_mismatch():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="validation scope disagree",
    ):
        dashboard._visus_dashboard_child_name(
            _visus_report(scope=("audited-source-independent-human-dynamic-aoi-agreement"))
        )


def test_dashboard_visus_report_missing_suite(
    tmp_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="suite manifest is missing",
    ):
        dashboard._validate_visus_report_for_dashboard(
            tmp_path / "r.json",
            _visus_report(),
        )


def test_dashboard_visus_inventory_invalid(
    monkeypatch,
    tmp_path,
):
    report = _visus_report()

    path = tmp_path / "report.json"

    suite = tmp_path / dashboard._VISUS_SUITE_MANIFEST_NAME

    suite.write_text(
        "{}",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        dashboard,
        "_validate_visus_suite_for_dashboard",
        lambda value: {"reports": None},
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="inventory is invalid",
    ):
        dashboard._validate_visus_report_for_dashboard(
            path,
            report,
        )


def test_dashboard_visus_member_count(
    monkeypatch,
    tmp_path,
):
    report = _visus_report()

    suite = tmp_path / dashboard._VISUS_SUITE_MANIFEST_NAME

    suite.write_text(
        "{}",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        dashboard,
        "_validate_visus_suite_for_dashboard",
        lambda value: {"reports": []},
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly one approved suite child",
    ):
        dashboard._validate_visus_report_for_dashboard(
            tmp_path / "r.json",
            report,
        )


def test_dashboard_visus_member_fp(
    monkeypatch,
    tmp_path,
):
    report = _visus_report()

    suite = tmp_path / dashboard._VISUS_SUITE_MANIFEST_NAME

    suite.write_text(
        "{}",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        dashboard,
        "_validate_visus_suite_for_dashboard",
        lambda value: {
            "reports": [
                {
                    "name": ("model_human_validation"),
                    ("report_fingerprint_sha256"): "0" * 64,
                    "path": "r.json",
                }
            ]
        },
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exact scientifically reviewed",
    ):
        dashboard._validate_visus_report_for_dashboard(
            tmp_path / "r.json",
            report,
        )


def test_dashboard_visus_member_path_missing(
    monkeypatch,
    tmp_path,
):
    report = _visus_report()

    suite = tmp_path / dashboard._VISUS_SUITE_MANIFEST_NAME

    suite.write_text(
        "{}",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        dashboard,
        "_validate_visus_suite_for_dashboard",
        lambda value: {
            "reports": [
                {
                    "name": ("model_human_validation"),
                    ("report_fingerprint_sha256"): report["report_fingerprint_sha256"],
                    "path": "",
                }
            ]
        },
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="child path is missing",
    ):
        dashboard._validate_visus_report_for_dashboard(
            tmp_path / "r.json",
            report,
        )


def test_dashboard_visus_member_path_mismatch(
    monkeypatch,
    tmp_path,
):
    report = _visus_report()

    suite = tmp_path / dashboard._VISUS_SUITE_MANIFEST_NAME

    suite.write_text(
        "{}",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        dashboard,
        "_validate_visus_suite_for_dashboard",
        lambda value: {
            "reports": [
                {
                    "name": ("model_human_validation"),
                    ("report_fingerprint_sha256"): report["report_fingerprint_sha256"],
                    "path": "other.json",
                }
            ]
        },
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exact scientifically reviewed suite child path",
    ):
        dashboard._validate_visus_report_for_dashboard(
            tmp_path / "r.json",
            report,
        )


def test_dashboard_visus_member_success(
    monkeypatch,
    tmp_path,
):
    report = _visus_report()

    path = tmp_path / "r.json"
    path.write_text(
        "{}",
        encoding="utf-8",
    )

    suite = tmp_path / dashboard._VISUS_SUITE_MANIFEST_NAME

    suite.write_text(
        "{}",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        dashboard,
        "_validate_visus_suite_for_dashboard",
        lambda value: {
            "reports": [
                {
                    "name": ("model_human_validation"),
                    ("report_fingerprint_sha256"): report["report_fingerprint_sha256"],
                    "path": "r.json",
                }
            ]
        },
    )

    dashboard._validate_visus_report_for_dashboard(
        path,
        report,
    )


# ============================================================
# DASHBOARD MARKDOWN HELPERS
# ============================================================


def test_dashboard_escape_markdown():
    assert dashboard._escape_markdown_cell("a|b\nc\rd") == "a\\|b c d"


def test_dashboard_markdown_table():
    frame = pd.DataFrame(
        {
            "a": [
                "x|y",
            ],
            "b": [
                1,
            ],
        }
    )

    rendered = dashboard._markdown_table(frame)

    assert "x\\|y" in rendered


def test_dashboard_markdown_suite_review():
    suite_table = pd.DataFrame(
        [
            dashboard._suite_row(
                {
                    "suite": "Suite",
                    "status": "complete",
                    "report_count": 1,
                    ("suite_fingerprint_sha256"): "a" * 64,
                    "scientific_review": {
                        "reviewer": "R",
                        "reviewed_at": "2026",
                        "review_scope": "scope",
                        ("review_fingerprint_sha256"): "b" * 64,
                    },
                },
                "suite.json",
            )
        ]
    )

    value = dashboard.BenchmarkDashboard(
        reports=(),
        table=pd.DataFrame(),
        source_files=(),
        suites=({"x": 1},),
        suite_table=suite_table,
        suite_source_files=("suite.json",),
    )

    rendered = dashboard.render_benchmark_dashboard_markdown(value)

    assert "Verified report suites" in rendered
    assert "scientific_review_reviewer" in rendered
    assert ("a" * 12) in rendered
    assert ("b" * 12) in rendered


def test_dashboard_markdown_report_review():
    report = _report()

    row = dashboard._dashboard_row(
        report,
        "r.json",
        scientific_review={
            "reviewer": "R",
            "reviewed_at": "2026",
            "review_scope": "scope",
            "review_fingerprint_sha256": ("b" * 64),
        },
    )

    value = dashboard.BenchmarkDashboard(
        reports=(report,),
        table=pd.DataFrame(
            [
                row,
            ]
        ),
        source_files=("r.json",),
    )

    rendered = dashboard.render_benchmark_dashboard_markdown(value)

    assert "Frozen reports" in rendered
    assert "scientific_review_reviewer" in rendered
    assert ("b" * 12) in rendered


# ============================================================
# EXPLICIT TASK MAPPING FIXTURES
# ============================================================


def _mapping_entries(
    count=4,
):
    return [
        {
            "trial_index": index,
            "task_label": task,
        }
        for index, task in zip(
            mapping.TRIAL_INDICES[:count],
            mapping.EXPECTED_TASKS[:count],
            strict=True,
        )
    ]


def _mapping_files(
    tmp_path,
    *,
    count=4,
):
    source = tmp_path / "mapping-source.txt"

    source.write_bytes(b"explicit mapping source")

    manifest = {
        "record_type": (mapping.SOURCE_RECORD_TYPE),
        "source_reference": ("synthetic-test-source"),
        "source_authority_claim": ("author_statement"),
        "source_file_sha256": (hashlib.sha256(source.read_bytes()).hexdigest()),
        ("obtained_via_authorized_channel_affirmed"): True,
        "mapping_entries": (_mapping_entries(count)),
    }

    manifest_path = tmp_path / "mapping-manifest.json"

    _write_json(
        manifest_path,
        manifest,
    )

    return (
        source,
        manifest_path,
        manifest,
    )


def _candidate(
    tmp_path,
    *,
    count=4,
):
    source, manifest, _ = _mapping_files(
        tmp_path,
        count=count,
    )

    candidate = mapping.inspect_explicit_task_mapping_candidate(
        source,
        manifest,
    )

    return (
        source,
        manifest,
        candidate,
    )


def _recandidate_fp(
    candidate,
):
    candidate["candidate_fingerprint_sha256"] = mapping.candidate_fingerprint(candidate)


# ============================================================
# MAPPING PURE HELPERS
# ============================================================


def test_mapping_canonical_bytes():
    assert mapping._canonical_bytes(
        {
            "b": 2,
            "a": 1,
        }
    ) == mapping._canonical_bytes(
        {
            "a": 1,
            "b": 2,
        }
    )


@pytest.mark.parametrize(
    (
        "function",
        "field",
    ),
    [
        (
            mapping.candidate_fingerprint,
            "candidate_fingerprint_sha256",
        ),
        (
            mapping.review_fingerprint,
            "review_fingerprint_sha256",
        ),
        (
            mapping.certificate_fingerprint,
            "certificate_fingerprint_sha256",
        ),
    ],
)
def test_mapping_fingerprint_ignores_stored(
    function,
    field,
):
    value = {
        "x": 1,
        field: "a",
    }

    first = function(value)

    value[field] = "b"

    assert function(value) == first


def test_mapping_exact_keys_success():
    mapping._require_exact_keys(
        {
            "a": 1,
            "b": 2,
        },
        {
            "a",
            "b",
        },
        label="fixture",
    )


def test_mapping_exact_keys_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="schema drifted",
    ):
        mapping._require_exact_keys(
            {
                "a": 1,
                "extra": 2,
            },
            {
                "a",
                "b",
            },
            label="fixture",
        )


def test_mapping_sha256_bytes():
    assert mapping._sha256_bytes(b"abc") == hashlib.sha256(b"abc").hexdigest()


@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "empty",
        "large",
    ],
)
def test_mapping_read_bounded(
    tmp_path,
    kind,
):
    path = tmp_path / "x"

    if kind == "empty":
        path.write_bytes(b"")
    elif kind == "large":
        path.write_bytes(b"ab")

    with pytest.raises(
        BenchmarkIntegrityError,
        match=("not a regular file" if kind == "missing" else "size is outside"),
    ):
        mapping._read_bounded(
            path,
            max_bytes=1,
            label="fixture",
        )


def test_mapping_read_bounded_success(
    tmp_path,
):
    path = tmp_path / "x"
    path.write_bytes(b"a")

    assert (
        mapping._read_bounded(
            path,
            max_bytes=1,
            label="fixture",
        )
        == b"a"
    )


@pytest.mark.parametrize(
    (
        "raw",
        "message",
    ),
    [
        (
            b"\xff",
            "valid UTF-8 JSON",
        ),
        (
            b"{",
            "valid UTF-8 JSON",
        ),
        (
            b"[]",
            "one JSON object",
        ),
    ],
)
def test_mapping_load_json_bytes(
    raw,
    message,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        mapping._load_json_bytes(
            raw,
            label="fixture",
        )


def test_mapping_load_json_success():
    assert mapping._load_json_bytes(
        b'{"x": 1}',
        label="fixture",
    ) == {
        "x": 1,
    }


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        " ",
        "unknown",
        "TODO",
        "__unresolved__",
    ],
)
def test_mapping_resolved_text_rejects(
    value,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires resolved",
    ):
        mapping._resolved_text(
            value,
            label="fixture",
        )


def test_mapping_resolved_text_too_long():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="text-size guardrail",
    ):
        mapping._resolved_text(
            "x" * (mapping.MAX_TEXT_FIELD_LENGTH + 1),
            label="fixture",
        )


def test_mapping_resolved_text_valid():
    assert (
        mapping._resolved_text(
            " value ",
            label="fixture",
        )
        == "value"
    )


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "A" * 64,
        "g" * 64,
        "a" * 63,
    ],
)
def test_mapping_sha_guard(
    value,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="lowercase SHA-256",
    ):
        mapping._sha256(
            value,
            label="fixture",
        )


def test_mapping_sha_valid():
    assert (
        mapping._sha256(
            "a" * 64,
            label="fixture",
        )
        == "a" * 64
    )


@pytest.mark.parametrize(
    "value",
    [
        True,
        None,
        "abc",
        1.5,
        "1.5",
        5,
    ],
)
def test_mapping_trial_index_invalid(
    value,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="trial_index|unknown TrIdx",
    ):
        mapping._trial_index(value)


@pytest.mark.parametrize(
    (
        "value",
        "expected",
    ),
    [
        (
            1,
            1,
        ),
        (
            "2",
            2,
        ),
        (
            3.0,
            3,
        ),
    ],
)
def test_mapping_trial_index_valid(
    value,
    expected,
):
    assert mapping._trial_index(value) == expected


# ============================================================
# SOURCE MANIFEST FAIL-CLOSED BRANCHES
# ============================================================


def _manifest_for_bytes(
    raw=b"source",
):
    return {
        "record_type": (mapping.SOURCE_RECORD_TYPE),
        "source_reference": "ref",
        "source_authority_claim": ("author_statement"),
        "source_file_sha256": (hashlib.sha256(raw).hexdigest()),
        ("obtained_via_authorized_channel_affirmed"): True,
        "mapping_entries": (_mapping_entries()),
    }


def test_mapping_manifest_record_type():
    raw = b"source"
    manifest = _manifest_for_bytes(raw)
    manifest["record_type"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record type drifted",
    ):
        mapping._validate_manifest(
            manifest,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_mapping_manifest_source_reference():
    raw = b"source"
    manifest = _manifest_for_bytes(raw)
    manifest["source_reference"] = "review_required"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires resolved",
    ):
        mapping._validate_manifest(
            manifest,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_mapping_manifest_authority():
    raw = b"source"
    manifest = _manifest_for_bytes(raw)
    manifest["source_authority_claim"] = "secondary"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="unsupported",
    ):
        mapping._validate_manifest(
            manifest,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_mapping_manifest_sha_format():
    raw = b"source"
    manifest = _manifest_for_bytes(raw)
    manifest["source_file_sha256"] = "BAD"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lowercase SHA-256",
    ):
        mapping._validate_manifest(
            manifest,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


@pytest.mark.parametrize(
    "entries",
    [
        None,
        [],
    ],
)
def test_mapping_manifest_entries_required(
    entries,
):
    raw = b"source"
    manifest = _manifest_for_bytes(raw)
    manifest["mapping_entries"] = entries

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires mapping_entries",
    ):
        mapping._validate_manifest(
            manifest,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_mapping_manifest_too_many():
    raw = b"source"
    manifest = _manifest_for_bytes(raw)

    manifest["mapping_entries"] = _mapping_entries() + [
        {
            "trial_index": 1,
            "task_label": (mapping.EXPECTED_TASKS[0]),
        }
    ]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="too many TrIdx",
    ):
        mapping._validate_manifest(
            manifest,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_mapping_manifest_entry_object():
    raw = b"source"
    manifest = _manifest_for_bytes(raw)

    manifest["mapping_entries"][0] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be JSON objects",
    ):
        mapping._validate_manifest(
            manifest,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


def test_mapping_manifest_task_unresolved():
    raw = b"source"
    manifest = _manifest_for_bytes(raw)

    manifest["mapping_entries"][0]["task_label"] = "unknown"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires resolved",
    ):
        mapping._validate_manifest(
            manifest,
            source_sha256=(hashlib.sha256(raw).hexdigest()),
        )


# ============================================================
# CANDIDATE DEEP CONTRACTS
# ============================================================


def test_mapping_candidate_valid(
    tmp_path,
):
    _, _, candidate = _candidate(tmp_path)

    assert mapping.validate_candidate_record(candidate) == candidate


@pytest.mark.parametrize(
    (
        "field",
        "value",
        "message",
    ),
    [
        (
            "record_type",
            "bad",
            "record type drifted",
        ),
        (
            "status",
            "bad",
            "status drifted",
        ),
        (
            ("authoritative_task_mapping_exhaustion_fingerprint_sha256"),
            "0" * 64,
            "exhaustion binding drifted",
        ),
    ],
)
def test_mapping_candidate_identity(
    tmp_path,
    field,
    value,
    message,
):
    _, _, candidate = _candidate(tmp_path)

    candidate[field] = value

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        mapping.validate_candidate_record(candidate)


def test_mapping_candidate_sections(
    tmp_path,
):
    _, _, candidate = _candidate(tmp_path)

    candidate["mapping_summary"] = None

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sections are missing",
    ):
        mapping.validate_candidate_record(candidate)


@pytest.mark.parametrize(
    "section",
    [
        "source",
        "manifest",
        "mapping_summary",
        "review_boundary",
        "scientific_boundary",
    ],
)
def test_mapping_candidate_section_schema(
    tmp_path,
    section,
):
    _, _, candidate = _candidate(tmp_path)

    candidate[section]["extra"] = True

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="schema drifted",
    ):
        mapping.validate_candidate_record(candidate)


def test_mapping_candidate_authority(
    tmp_path,
):
    _, _, candidate = _candidate(tmp_path)

    candidate["source"]["source_authority_claim"] = "bad"

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="authority class drifted",
    ):
        mapping.validate_candidate_record(candidate)


def test_mapping_candidate_authorization(
    tmp_path,
):
    _, _, candidate = _candidate(tmp_path)

    candidate["source"]["authorized_channel_affirmed"] = False

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="authorization drifted",
    ):
        mapping.validate_candidate_record(candidate)


@pytest.mark.parametrize(
    (
        "section",
        "field",
    ),
    [
        (
            "source",
            "sha256",
        ),
        (
            "manifest",
            "sha256",
        ),
    ],
)
def test_mapping_candidate_sha(
    tmp_path,
    section,
    field,
):
    _, _, candidate = _candidate(tmp_path)

    candidate[section][field] = "bad"

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lowercase SHA-256",
    ):
        mapping.validate_candidate_record(candidate)


def test_mapping_candidate_indices_missing(
    tmp_path,
):
    _, _, candidate = _candidate(tmp_path)

    candidate["mapping_summary"]["trial_indices_present"] = None

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="ledger is missing",
    ):
        mapping.validate_candidate_record(candidate)


@pytest.mark.parametrize(
    "indices",
    [
        [
            1,
            2,
            5,
        ],
        [
            1,
            True,
        ],
    ],
)
def test_mapping_candidate_indices_invalid(
    tmp_path,
    indices,
):
    _, _, candidate = _candidate(tmp_path)

    candidate["mapping_summary"]["trial_indices_present"] = indices

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="coverage is invalid|ledger drifted",
    ):
        mapping.validate_candidate_record(candidate)


def test_mapping_candidate_indices_unsorted(
    tmp_path,
):
    _, _, candidate = _candidate(tmp_path)

    candidate["mapping_summary"]["trial_indices_present"] = [
        2,
        1,
        3,
        4,
    ]

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="ledger drifted",
    ):
        mapping.validate_candidate_record(candidate)


def test_mapping_candidate_entry_count(
    tmp_path,
):
    _, _, candidate = _candidate(tmp_path)

    candidate["mapping_summary"]["entry_count"] = 3

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="entry count drifted",
    ):
        mapping.validate_candidate_record(candidate)


@pytest.mark.parametrize(
    "task_count",
    [
        None,
        0,
        5,
        True,
    ],
)
def test_mapping_candidate_task_count_invalid(
    tmp_path,
    task_count,
):
    _, _, candidate = _candidate(tmp_path)

    candidate["mapping_summary"]["publication_task_count"] = task_count

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="task count is invalid|task count drifted from entries",
    ):
        mapping.validate_candidate_record(candidate)


def test_mapping_candidate_task_count_drift(
    tmp_path,
):
    _, _, candidate = _candidate(tmp_path)

    candidate["mapping_summary"]["publication_task_count"] = 3

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted from entries",
    ):
        mapping.validate_candidate_record(candidate)


@pytest.mark.parametrize(
    (
        "field",
        "value",
        "message",
    ),
    [
        (
            "complete_trial_index_coverage",
            False,
            "TrIdx completeness drifted",
        ),
        (
            "complete_publication_task_coverage",
            False,
            "task completeness drifted",
        ),
        (
            "complete_one_to_one_mapping",
            False,
            "one-to-one completeness drifted",
        ),
        (
            "tridx4_present_in_transcription",
            False,
            "TrIdx 4 presence drifted",
        ),
    ],
)
def test_mapping_candidate_completeness(
    tmp_path,
    field,
    value,
    message,
):
    _, _, candidate = _candidate(tmp_path)

    candidate["mapping_summary"][field] = value

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        mapping.validate_candidate_record(candidate)


def test_mapping_candidate_mapping_sha(
    tmp_path,
):
    _, _, candidate = _candidate(tmp_path)

    candidate["mapping_summary"]["mapping_fingerprint_sha256"] = "bad"

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lowercase SHA-256",
    ):
        mapping.validate_candidate_record(candidate)


def test_mapping_candidate_raw_mapping_leak(
    tmp_path,
):
    _, _, candidate = _candidate(tmp_path)

    candidate["mapping_summary"]["raw_task_mapping_copied_to_candidate_record"] = True

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="leaked the raw mapping",
    ):
        mapping.validate_candidate_record(candidate)


def test_mapping_candidate_manual_review_gate(
    tmp_path,
):
    _, _, candidate = _candidate(tmp_path)

    candidate["review_boundary"]["manual_review_required"] = False

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="manual-review gate was relaxed",
    ):
        mapping.validate_candidate_record(candidate)


@pytest.mark.parametrize(
    "field",
    sorted(mapping._SCIENTIFIC_BOUNDARY_KEYS),
)
def test_mapping_candidate_scientific_promotions(
    tmp_path,
    field,
):
    _, _, candidate = _candidate(tmp_path)

    candidate["scientific_boundary"][field] = True

    _recandidate_fp(candidate)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        mapping.validate_candidate_record(candidate)


# ============================================================
# REVIEW TIMESTAMP
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        "not-a-date",
        "2026-09-24",
        "2026-09-24T12:00:00",
    ],
)
def test_mapping_review_timestamp_invalid(
    value,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="ISO-8601|timezone offset",
    ):
        mapping._validate_review_timestamp(value)


@pytest.mark.parametrize(
    "value",
    [
        "2026-09-24T12:00:00Z",
        "2026-09-24T12:00:00+03:00",
    ],
)
def test_mapping_review_timestamp_valid(
    value,
):
    assert mapping._validate_review_timestamp(value) == value
