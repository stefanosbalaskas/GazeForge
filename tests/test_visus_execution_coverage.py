from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from test_visus_execution import _raw_fixture, _run_from_raw, _snapshots

import gazeforge.visus_execution as execution
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError


@pytest.fixture(scope="module")
def baseline(tmp_path_factory):
    root = tmp_path_factory.mktemp("visus-execution-coverage")

    paths = _raw_fixture(root)
    snapshots = _snapshots(paths)
    audit, suite = _run_from_raw(paths)

    manifest = execution.build_visus_execution_provenance(
        audit,
        suite,
        snapshots,
    )

    verified_suite = execution.validate_visus_dynamic_aoi_suite_manifest(
        suite.manifest_path,
        verify_reports=True,
    )

    children = execution._load_suite_children(
        suite.manifest_path.parent,
        verified_suite,
    )

    return {
        "root": root,
        "paths": paths,
        "snapshots": snapshots,
        "audit": audit,
        "suite": suite,
        "manifest": manifest,
        "verified_suite": verified_suite,
        "children": children,
    }


def _resign_manifest(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    body = {key: value for key, value in manifest.items() if key != "execution_fingerprint_sha256"}

    manifest["execution_fingerprint_sha256"] = benchmark_fingerprint(body)

    return manifest


def _write_manifest(
    tmp_path: Path,
    manifest: dict[str, Any],
) -> Path:
    path = tmp_path / "visus-execution-provenance.json"

    path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return path


def _resign_audit(audit) -> None:
    body = {key: value for key, value in audit.report.items() if key != "report_fingerprint_sha256"}

    audit.report["report_fingerprint_sha256"] = benchmark_fingerprint(body)


def _ledger() -> dict[str, Any]:
    return {
        "stimulus_id": "S01",
        "n_timestamps": 3,
        "first_timestamp_ms": 0.0,
        "last_timestamp_ms": 80.0,
        "timestamp_grid_fingerprint_sha256": ("a" * 64),
    }


def _parsed_components():
    reference = {
        "input_table_fingerprint_sha256": ("a" * 64),
        "canonical_table_fingerprint_sha256": ("b" * 64),
    }

    prediction = {
        "input_table_fingerprint_sha256": ("c" * 64),
        "canonical_table_fingerprint_sha256": ("d" * 64),
    }

    protocol = {
        "timestamp_grids": [_ledger()],
        "timestamp_grid_basis": ("fixed external fixture grid"),
        "prediction_emission_grid_used": False,
    }

    return (
        reference,
        prediction,
        protocol,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("a" * 64, True),
        ("A" * 64, True),
        ("a" * 63, False),
        ("g" * 64, False),
        ("", False),
        (None, False),
        (123, False),
    ],
)
def test_valid_sha256_contract(
    value: Any,
    expected: bool,
) -> None:
    assert execution._valid_sha256(value) is expected


def test_sha256_file_success(
    tmp_path: Path,
) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"abc")

    assert execution._sha256(path) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_snapshot_file_success(
    tmp_path: Path,
) -> None:
    path = tmp_path / "input.csv"
    path.write_text(
        "x\n1\n",
        encoding="utf-8",
    )

    result = execution._snapshot_file(
        "human_aoi_table",
        path,
        semantic_fingerprint_sha256=("a" * 64),
    )

    assert result.role == "human_aoi_table"
    assert result.filename == "input.csv"
    assert result.bytes > 0
    assert len(result.sha256) == 64
    assert result.semantic_fingerprint_sha256 == "a" * 64


def test_snapshot_file_missing_guard(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        execution._snapshot_file(
            "fixture",
            tmp_path / "missing.txt",
        )


def test_snapshot_file_empty_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "empty.txt"
    path.write_bytes(b"")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-empty regular file",
    ):
        execution._snapshot_file(
            "fixture",
            path,
        )


def test_snapshot_file_semantic_fingerprint_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "input.txt"
    path.write_text(
        "x",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="invalid semantic fingerprint",
    ):
        execution._snapshot_file(
            "fixture",
            path,
            semantic_fingerprint_sha256="bad",
        )


def test_snapshot_file_symlink_guard_portable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "input.txt"
    path.write_text(
        "x",
        encoding="utf-8",
    )

    original = Path.is_symlink

    def fake_is_symlink(
        self: Path,
    ) -> bool:
        if self == path:
            return True
        return original(self)

    monkeypatch.setattr(
        Path,
        "is_symlink",
        fake_is_symlink,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="symbolic link",
    ):
        execution._snapshot_file(
            "fixture",
            path,
        )


def test_snapshot_source_spec_success(
    baseline,
) -> None:
    result = execution._snapshot_source_spec(baseline["paths"]["spec"])

    assert result.role == "source_audit_spec"

    assert execution._valid_sha256(result.semantic_fingerprint_sha256)


def test_snapshot_source_spec_detects_midread_change(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = execution.VisusExecutionInputSnapshot(
        role="source_audit_spec",
        filename="spec.json",
        sha256="a" * 64,
        bytes=10,
    )

    after = execution.VisusExecutionInputSnapshot(
        role="source_audit_spec",
        filename="spec.json",
        sha256="b" * 64,
        bytes=10,
    )

    snapshots = iter(
        [
            before,
            after,
        ]
    )

    monkeypatch.setattr(
        execution,
        "_snapshot_file",
        lambda *args, **kwargs: next(snapshots),
    )

    monkeypatch.setattr(
        execution,
        "load_visus_source_audit_spec",
        lambda path: baseline["audit"].spec,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="changed while",
    ):
        execution._snapshot_source_spec("unused.json")


def test_snapshot_all_inputs_roles(
    baseline,
) -> None:
    snapshots = execution.snapshot_visus_execution_inputs(
        source_audit_spec=baseline["paths"]["spec"],
        human_aoi_table=baseline["paths"]["human"],
        model_prediction_table=baseline["paths"]["prediction"],
        timestamp_grid_json=baseline["paths"]["grids"],
    )

    assert [item.role for item in snapshots] == list(execution._INPUT_ROLES)


def test_verify_inputs_unchanged_success(
    baseline,
) -> None:
    execution.verify_visus_execution_inputs_unchanged(
        baseline["snapshots"],
        source_audit_spec=baseline["paths"]["spec"],
        human_aoi_table=baseline["paths"]["human"],
        model_prediction_table=baseline["paths"]["prediction"],
        timestamp_grid_json=baseline["paths"]["grids"],
    )


def test_audit_identity_type_guard() -> None:
    with pytest.raises(
        TypeError,
        match="VisusSourceAuditRun",
    ):
        execution._audit_source_identity(object())


def test_audit_identity_status_guard(
    baseline,
) -> None:
    audit = copy.deepcopy(baseline["audit"])

    audit.report["status"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="verified source audit",
    ):
        execution._audit_source_identity(audit)


def test_audit_identity_report_fingerprint_guard(
    baseline,
) -> None:
    audit = copy.deepcopy(baseline["audit"])

    audit.report["report_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="invalid fingerprint",
    ):
        execution._audit_source_identity(audit)


def test_audit_identity_spec_fingerprint_guard(
    baseline,
) -> None:
    audit = copy.deepcopy(baseline["audit"])

    audit.report["spec_fingerprint_sha256"] = "0" * 64

    _resign_audit(audit)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="invalid spec fingerprint",
    ):
        execution._audit_source_identity(audit)


def test_audit_identity_manifest_fingerprint_guard(
    baseline,
) -> None:
    audit = copy.deepcopy(baseline["audit"])

    audit.report["inventory"]["manifest_fingerprint_sha256"] = "bad"

    _resign_audit(audit)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="incomplete source-manifest identity",
    ):
        execution._audit_source_identity(audit)


def test_audit_identity_success(
    baseline,
) -> None:
    result = execution._audit_source_identity(baseline["audit"])

    assert set(result) == set(execution._SOURCE_KEYS)


def test_input_rows_requires_tuple(
    baseline,
) -> None:
    with pytest.raises(
        TypeError,
        match="must be a tuple",
    ):
        execution._input_rows(list(baseline["snapshots"]))


def test_input_rows_requires_snapshot_objects(
    baseline,
) -> None:
    values = list(baseline["snapshots"])

    values[0] = object()

    with pytest.raises(
        TypeError,
        match="non-VisusExecutionInputSnapshot",
    ):
        execution._input_rows(tuple(values))


def test_input_rows_requires_exact_roles(
    baseline,
) -> None:
    values = list(baseline["snapshots"])

    values[1] = replace(
        values[1],
        role="source_audit_spec",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly one snapshot",
    ):
        execution._input_rows(tuple(values))


def test_input_rows_success(
    baseline,
) -> None:
    rows = execution._input_rows(baseline["snapshots"])

    assert [row["role"] for row in rows] == list(execution._INPUT_ROLES)


def test_load_suite_children_success(
    baseline,
) -> None:
    children = execution._load_suite_children(
        baseline["suite"].manifest_path.parent,
        baseline["verified_suite"],
    )

    assert "human_reference_intake" in children

    assert "model_prediction_intake" in children


def test_load_suite_children_requires_objects(
    tmp_path: Path,
) -> None:
    child = tmp_path / "child.json"

    child.write_text(
        "[]",
        encoding="utf-8",
    )

    summary = {
        "reports": [
            {
                "name": "child",
                "path": "child.json",
            }
        ]
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        execution._load_suite_children(
            tmp_path,
            summary,
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
    ],
)
def test_timestamp_ledgers_require_nonempty_list(
    value,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-empty timestamp-grid ledger",
    ):
        execution._validate_timestamp_grid_ledgers(value)


def test_timestamp_ledger_requires_object() -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="records must be objects",
    ):
        execution._validate_timestamp_grid_ledgers(
            [
                "bad",
            ]
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "stimulus_id",
            "",
        ),
        (
            "n_timestamps",
            0,
        ),
        (
            "n_timestamps",
            True,
        ),
        (
            "first_timestamp_ms",
            True,
        ),
        (
            "first_timestamp_ms",
            float("nan"),
        ),
        (
            "last_timestamp_ms",
            True,
        ),
        (
            "last_timestamp_ms",
            float("inf"),
        ),
        (
            "last_timestamp_ms",
            -1.0,
        ),
        (
            "timestamp_grid_fingerprint_sha256",
            "bad",
        ),
    ],
)
def test_timestamp_ledger_record_guards(
    field: str,
    value: Any,
) -> None:
    record = _ledger()
    record[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="invalid timestamp-grid ledger record",
    ):
        execution._validate_timestamp_grid_ledgers(
            [
                record,
            ]
        )


def test_timestamp_ledger_duplicate_stimulus_guard() -> None:
    record = _ledger()

    with pytest.raises(
        BenchmarkIntegrityError,
        match="invalid timestamp-grid ledger record",
    ):
        execution._validate_timestamp_grid_ledgers(
            [
                record,
                copy.deepcopy(record),
            ]
        )


def test_timestamp_ledgers_success() -> None:
    result = execution._validate_timestamp_grid_ledgers(
        [
            _ledger(),
        ]
    )

    assert result == [
        _ledger(),
    ]


def test_parsed_input_binding_success() -> None:
    reference, prediction, protocol = _parsed_components()

    result = execution._parsed_input_binding(
        reference,
        prediction,
        protocol,
    )

    assert result["prediction_emission_grid_used"] is False


@pytest.mark.parametrize(
    ("target", "field"),
    [
        (
            "reference",
            "input_table_fingerprint_sha256",
        ),
        (
            "reference",
            "canonical_table_fingerprint_sha256",
        ),
        (
            "prediction",
            "input_table_fingerprint_sha256",
        ),
        (
            "prediction",
            "canonical_table_fingerprint_sha256",
        ),
    ],
)
def test_parsed_input_fingerprint_guards(
    target: str,
    field: str,
) -> None:
    reference, prediction, protocol = _parsed_components()

    selected = reference if target == "reference" else prediction

    selected[field] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing canonical intake fingerprints",
    ):
        execution._parsed_input_binding(
            reference,
            prediction,
            protocol,
        )


def test_parsed_input_basis_guard() -> None:
    reference, prediction, protocol = _parsed_components()

    protocol["timestamp_grid_basis"] = " "

    with pytest.raises(
        BenchmarkIntegrityError,
        match="explicit timestamp-grid basis",
    ):
        execution._parsed_input_binding(
            reference,
            prediction,
            protocol,
        )


def test_parsed_input_prediction_grid_guard() -> None:
    reference, prediction, protocol = _parsed_components()

    protocol["prediction_emission_grid_used"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="prediction emissions",
    ):
        execution._parsed_input_binding(
            reference,
            prediction,
            protocol,
        )


def test_build_requires_suite_type(
    baseline,
) -> None:
    with pytest.raises(
        TypeError,
        match="VisusDynamicAOIValidationSuiteRun",
    ):
        execution.build_visus_execution_provenance(
            baseline["audit"],
            object(),
            baseline["snapshots"],
        )


def test_build_suite_fingerprint_guard(
    baseline,
) -> None:
    suite = copy.copy(baseline["suite"])

    suite.suite_fingerprint_sha256 = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="suite fingerprint",
    ):
        execution.build_visus_execution_provenance(
            baseline["audit"],
            suite,
            baseline["snapshots"],
        )


def test_build_source_identity_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = copy.deepcopy(baseline["verified_suite"])

    summary["source"]["source_manifest_fingerprint_sha256"] = "0" * 64

    monkeypatch.setattr(
        execution,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: summary,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity",
    ):
        execution.build_visus_execution_provenance(
            baseline["audit"],
            baseline["suite"],
            baseline["snapshots"],
        )


def test_build_source_spec_semantic_guard(
    baseline,
) -> None:
    values = list(baseline["snapshots"])

    values[0] = replace(
        values[0],
        semantic_fingerprint_sha256=("0" * 64),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not semantically match",
    ):
        execution.build_visus_execution_provenance(
            baseline["audit"],
            baseline["suite"],
            tuple(values),
        )


def test_build_requires_intake_children(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        execution,
        "_load_suite_children",
        lambda *args, **kwargs: {},
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="both verified intake reports",
    ):
        execution.build_visus_execution_provenance(
            baseline["audit"],
            baseline["suite"],
            baseline["snapshots"],
        )


def test_build_requires_protocol_dict(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = copy.deepcopy(baseline["verified_suite"])

    summary["protocol"] = []

    monkeypatch.setattr(
        execution,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: summary,
    )

    monkeypatch.setattr(
        execution,
        "_load_suite_children",
        lambda *args, **kwargs: copy.deepcopy(baseline["children"]),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="protocol must be a dictionary",
    ):
        execution.build_visus_execution_provenance(
            baseline["audit"],
            baseline["suite"],
            baseline["snapshots"],
        )


def test_execution_provenance_path(
    tmp_path: Path,
) -> None:
    assert (
        execution.visus_execution_provenance_path(tmp_path)
        == tmp_path / "visus-execution-provenance.json"
    )


def test_write_requires_dictionary(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        TypeError,
        match="dictionary",
    ):
        execution.write_visus_execution_provenance(
            [],
            tmp_path,
        )


def test_write_requires_valid_fingerprint(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint does not revalidate",
    ):
        execution.write_visus_execution_provenance(
            {"execution_fingerprint_sha256": ("0" * 64)},
            tmp_path,
        )


def test_write_success_existing_and_overwrite(
    baseline,
    tmp_path: Path,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    first = execution.write_visus_execution_provenance(
        manifest,
        tmp_path,
    )

    assert first.manifest_path.is_file()

    with pytest.raises(FileExistsError):
        execution.write_visus_execution_provenance(
            manifest,
            tmp_path,
        )

    second = execution.write_visus_execution_provenance(
        manifest,
        tmp_path,
        overwrite=True,
    )

    assert second.execution_fingerprint_sha256 == manifest["execution_fingerprint_sha256"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "schema",
            "wrong",
        ),
        (
            "status",
            "wrong",
        ),
    ],
)
def test_internal_manifest_identity_guards(
    baseline,
    field: str,
    value: Any,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="identity/status",
    ):
        execution._validate_internal_manifest(manifest)


def test_internal_manifest_scope_guard(
    baseline,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["provenance_scope"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="scope is invalid",
    ):
        execution._validate_internal_manifest(manifest)


def test_internal_manifest_source_guard(
    baseline,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["source"]["source_manifest_fingerprint_sha256"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity is invalid",
    ):
        execution._validate_internal_manifest(manifest)


def test_internal_manifest_raw_inventory_guard(
    baseline,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["raw_inputs"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="raw-input inventory",
    ):
        execution._validate_internal_manifest(manifest)


def test_internal_manifest_role_order_guard(
    baseline,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["raw_inputs"][0]["role"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="raw-input roles",
    ):
        execution._validate_internal_manifest(manifest)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "filename",
            "../bad.csv",
        ),
        (
            "sha256",
            "bad",
        ),
        (
            "bytes",
            0,
        ),
        (
            "bytes",
            True,
        ),
    ],
)
def test_internal_manifest_raw_row_guards(
    baseline,
    field: str,
    value: Any,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["raw_inputs"][1][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="invalid raw-input record",
    ):
        execution._validate_internal_manifest(manifest)


def test_internal_manifest_spec_semantic_guard(
    baseline,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["raw_inputs"][0]["semantic_fingerprint_sha256"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="semantic fingerprint is invalid",
    ):
        execution._validate_internal_manifest(manifest)


def test_internal_manifest_spec_binding_guard(
    baseline,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["raw_inputs"][0]["semantic_fingerprint_sha256"] = "f" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="semantic binding is inconsistent",
    ):
        execution._validate_internal_manifest(manifest)


def test_internal_manifest_only_spec_may_have_semantic_fp(
    baseline,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["raw_inputs"][1]["semantic_fingerprint_sha256"] = "a" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Only the source-audit JSON",
    ):
        execution._validate_internal_manifest(manifest)


def test_internal_manifest_parsed_mapping_guard(
    baseline,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["parsed_inputs"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="parsed-input binding is invalid",
    ):
        execution._validate_internal_manifest(manifest)


def test_internal_manifest_suite_mapping_guard(
    baseline,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["suite"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="suite binding is invalid",
    ):
        execution._validate_internal_manifest(manifest)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "manifest_filename",
            "../suite.json",
        ),
        (
            "suite_fingerprint_sha256",
            "bad",
        ),
        (
            "report_count",
            0,
        ),
        (
            "report_count",
            True,
        ),
        (
            "reports_verified",
            False,
        ),
    ],
)
def test_internal_manifest_suite_incomplete_guards(
    baseline,
    field: str,
    value: Any,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["suite"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="suite binding is incomplete",
    ):
        execution._validate_internal_manifest(manifest)


def test_internal_manifest_success(
    baseline,
) -> None:
    rows, suite = execution._validate_internal_manifest(copy.deepcopy(baseline["manifest"]))

    assert len(rows) == 4
    assert suite["reports_verified"] is True


def test_validate_missing_file(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        execution.validate_visus_execution_provenance(tmp_path / "missing.json")


def test_validate_invalid_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "visus-execution-provenance.json"

    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not valid JSON",
    ):
        execution.validate_visus_execution_provenance(path)


def test_validate_requires_json_object(
    tmp_path: Path,
) -> None:
    path = tmp_path / "visus-execution-provenance.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        execution.validate_visus_execution_provenance(path)


def test_validate_fingerprint_guard(
    baseline,
    tmp_path: Path,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["execution_fingerprint_sha256"] = "0" * 64

    path = _write_manifest(
        tmp_path,
        manifest,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint mismatch",
    ):
        execution.validate_visus_execution_provenance(path)


def test_validate_without_suite_success(
    baseline,
    tmp_path: Path,
) -> None:
    path = _write_manifest(
        tmp_path,
        copy.deepcopy(baseline["manifest"]),
    )

    result = execution.validate_visus_execution_provenance(
        path,
        verify_suite=False,
    )

    assert result["suite_verified"] is False
    assert result["input_count"] == 4


def _suite_validation_case(
    baseline,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate,
    *,
    match: str,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    path = _write_manifest(
        tmp_path,
        manifest,
    )

    summary = copy.deepcopy(baseline["verified_suite"])

    mutate(summary)

    monkeypatch.setattr(
        execution,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: summary,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        execution.validate_visus_execution_provenance(
            path,
            verify_suite=True,
        )


def test_validate_suite_fingerprint_guard(
    baseline,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _suite_validation_case(
        baseline,
        tmp_path,
        monkeypatch,
        lambda summary: summary.__setitem__(
            "suite_fingerprint_sha256",
            "0" * 64,
        ),
        match="provenance/suite fingerprint mismatch",
    )


def test_validate_suite_report_count_guard(
    baseline,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _suite_validation_case(
        baseline,
        tmp_path,
        monkeypatch,
        lambda summary: summary.__setitem__(
            "report_count",
            int(summary["report_count"]) + 1,
        ),
        match="report-count mismatch",
    )


def test_validate_suite_source_guard(
    baseline,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(summary):
        summary["source"]["source_manifest_fingerprint_sha256"] = "0" * 64

    _suite_validation_case(
        baseline,
        tmp_path,
        monkeypatch,
        mutate,
        match="suite source identity mismatch",
    )


def test_validate_suite_timestamp_grid_guard(
    baseline,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(summary):
        summary["protocol"]["timestamp_grids"] = []

    _suite_validation_case(
        baseline,
        tmp_path,
        monkeypatch,
        mutate,
        match="timestamp-grid fingerprints mismatch",
    )


def test_validate_suite_timestamp_basis_guard(
    baseline,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(summary):
        summary["protocol"]["timestamp_grid_basis"] = "wrong"

    _suite_validation_case(
        baseline,
        tmp_path,
        monkeypatch,
        mutate,
        match="timestamp-grid basis mismatch",
    )


def test_validate_suite_prediction_grid_guard(
    baseline,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(summary):
        summary["protocol"]["prediction_emission_grid_used"] = True

    _suite_validation_case(
        baseline,
        tmp_path,
        monkeypatch,
        mutate,
        match="prediction emissions as grid",
    )


def test_validate_requires_intake_children(
    baseline,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_manifest(
        tmp_path,
        copy.deepcopy(baseline["manifest"]),
    )

    monkeypatch.setattr(
        execution,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: copy.deepcopy(baseline["verified_suite"]),
    )

    monkeypatch.setattr(
        execution,
        "_load_suite_children",
        lambda *args, **kwargs: {},
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot recover verified intake children",
    ):
        execution.validate_visus_execution_provenance(
            path,
            verify_suite=True,
        )


def test_validate_parsed_binding_guard(
    baseline,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_manifest(
        tmp_path,
        copy.deepcopy(baseline["manifest"]),
    )

    children = copy.deepcopy(baseline["children"])

    children["human_reference_intake"]["input_table_fingerprint_sha256"] = "f" * 64

    monkeypatch.setattr(
        execution,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: copy.deepcopy(baseline["verified_suite"]),
    )

    monkeypatch.setattr(
        execution,
        "_load_suite_children",
        lambda *args, **kwargs: children,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="parsed-input binding does not match",
    ):
        execution.validate_visus_execution_provenance(
            path,
            verify_suite=True,
        )


def test_validate_directory_input_success(
    baseline,
    tmp_path: Path,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    _write_manifest(
        tmp_path,
        manifest,
    )

    result = execution.validate_visus_execution_provenance(
        tmp_path,
        verify_suite=False,
    )

    assert result["manifest_path"].endswith("visus-execution-provenance.json")


# === VISUS EXECUTION FINAL COVERAGE CLOSURE ===


def test_internal_manifest_non_object_raw_row_guard(
    baseline,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["raw_inputs"][1] = "bad-row"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-object raw-input record",
    ):
        execution._validate_internal_manifest(manifest)
