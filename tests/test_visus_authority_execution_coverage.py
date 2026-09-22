from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from test_visus_authority_execution import _authority_snapshots, _fixture

import gazeforge.visus_authority_execution as authority
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_authority_binding import (
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
)
from gazeforge.visus_execution import VisusExecutionInputSnapshot


@pytest.fixture(scope="module")
def baseline(tmp_path_factory):
    root = tmp_path_factory.mktemp("visus-authority-execution-coverage")
    paths = _fixture(root)
    snapshots = _authority_snapshots(paths)

    manifest = authority.build_visus_authority_execution_provenance(
        paths["audit"],
        paths["suite"],
        snapshots,
    )

    verified_suite = authority.validate_visus_dynamic_aoi_suite_manifest(
        paths["suite"].manifest_path,
        verify_reports=True,
    )

    children = authority._load_suite_children(
        paths["suite"].manifest_path.parent,
        verified_suite,
    )

    return {
        "root": root,
        "paths": paths,
        "snapshots": snapshots,
        "manifest": manifest,
        "verified_suite": verified_suite,
        "children": children,
        "certificate_fingerprint": paths["audit"].report[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD],
    }


def _resign(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    body = {key: value for key, value in manifest.items() if key != "execution_fingerprint_sha256"}

    manifest["execution_fingerprint_sha256"] = benchmark_fingerprint(body)

    return manifest


def _write(
    tmp_path: Path,
    manifest: Any,
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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("a" * 64, True),
        ("0" * 64, True),
        ("A" * 64, False),
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
    assert authority._valid_sha256(value) is expected


def test_hash_regular_file_success(
    tmp_path: Path,
) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"abc")

    result = authority._hash_regular_file(
        "fixture",
        path,
        semantic_fingerprint_sha256=("a" * 64),
    )

    assert result.role == "fixture"
    assert result.filename == "payload.bin"
    assert result.bytes == 3
    assert len(result.sha256) == 64
    assert result.semantic_fingerprint_sha256 == "a" * 64


def test_hash_regular_file_missing_guard(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-symlink regular file",
    ):
        authority._hash_regular_file(
            "fixture",
            tmp_path / "missing.bin",
        )


def test_hash_regular_file_symlink_guard_portable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"abc")

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
        match="non-symlink regular file",
    ):
        authority._hash_regular_file(
            "fixture",
            path,
        )


def test_hash_regular_file_empty_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-empty regular file",
    ):
        authority._hash_regular_file(
            "fixture",
            path,
        )


def test_hash_authority_size_bound(
    tmp_path: Path,
) -> None:
    path = tmp_path / "certificate.json"

    path.write_bytes(b"x" * (authority._MAX_AUTHORITY_CERTIFICATE_BYTES + 1))

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exceeds the allowed size bound",
    ):
        authority._hash_regular_file(
            authority._AUTHORITY_ROLE,
            path,
        )


def test_hash_regular_file_semantic_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"x")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="invalid semantic fingerprint",
    ):
        authority._hash_regular_file(
            "fixture",
            path,
            semantic_fingerprint_sha256="BAD",
        )


def test_snapshot_authority_certificate_success(
    baseline,
) -> None:
    result = authority._snapshot_authority_certificate(baseline["paths"]["certificate"])

    assert result.role == authority._AUTHORITY_ROLE

    assert result.semantic_fingerprint_sha256 == baseline["certificate_fingerprint"]


def test_snapshot_authority_detects_midread_change(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = VisusExecutionInputSnapshot(
        role=authority._AUTHORITY_ROLE,
        filename="certificate.json",
        sha256="a" * 64,
        bytes=100,
    )

    after = VisusExecutionInputSnapshot(
        role=authority._AUTHORITY_ROLE,
        filename="certificate.json",
        sha256="b" * 64,
        bytes=100,
    )

    values = iter(
        [
            before,
            after,
        ]
    )

    monkeypatch.setattr(
        authority,
        "_hash_regular_file",
        lambda *args, **kwargs: next(values),
    )

    monkeypatch.setattr(
        authority,
        "load_visus_source_authority_certificate",
        lambda path: {"certificate_fingerprint_sha256": (baseline["certificate_fingerprint"])},
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="changed while",
    ):
        authority._snapshot_authority_certificate("unused.json")


def test_snapshot_authority_execution_roles(
    baseline,
) -> None:
    snapshots = authority.snapshot_visus_authority_execution_inputs(
        source_audit_spec=baseline["paths"]["spec"],
        source_authority_certificate=baseline["paths"]["certificate"],
        human_aoi_table=baseline["paths"]["human"],
        model_prediction_table=baseline["paths"]["prediction"],
        timestamp_grid_json=baseline["paths"]["grid"],
    )

    assert tuple(item.role for item in snapshots) == authority._INPUT_ROLES


def test_verify_authority_inputs_unchanged_success(
    baseline,
) -> None:
    authority.verify_visus_authority_execution_inputs_unchanged(
        baseline["snapshots"],
        source_audit_spec=baseline["paths"]["spec"],
        source_authority_certificate=baseline["paths"]["certificate"],
        human_aoi_table=baseline["paths"]["human"],
        model_prediction_table=baseline["paths"]["prediction"],
        timestamp_grid_json=baseline["paths"]["grid"],
    )


@pytest.mark.parametrize(
    ("case", "match"),
    [
        (
            "source",
            "source and protocol objects",
        ),
        (
            "protocol",
            "source and protocol objects",
        ),
        (
            "fingerprint",
            "missing a valid",
        ),
        (
            "bound",
            "does not declare",
        ),
        (
            "inconsistent",
            "inconsistent across source and protocol",
        ),
    ],
)
def test_suite_authority_fingerprint_guards(
    baseline,
    case: str,
    match: str,
) -> None:
    manifest = copy.deepcopy(baseline["paths"]["suite"].manifest)

    if case == "source":
        manifest["source"] = None

    elif case == "protocol":
        manifest["protocol"] = None

    elif case == "fingerprint":
        manifest["source"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = "BAD"

    elif case == "bound":
        manifest["protocol"]["source_authority_certificate_bound"] = False

    elif case == "inconsistent":
        manifest["protocol"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = "f" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        authority._suite_authority_fingerprint(manifest)


def test_suite_authority_fingerprint_success(
    baseline,
) -> None:
    assert (
        authority._suite_authority_fingerprint(baseline["paths"]["suite"])
        == baseline["certificate_fingerprint"]
    )


def test_bind_suite_requires_suite_type(
    baseline,
) -> None:
    with pytest.raises(
        TypeError,
        match="VisusDynamicAOIValidationSuiteRun",
    ):
        authority.bind_visus_suite_to_source_authority(
            baseline["paths"]["audit"],
            object(),
        )


def test_bind_suite_verified_object_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = copy.deepcopy(baseline["verified_suite"])

    summary["suite_fingerprint_sha256"] = "0" * 64

    monkeypatch.setattr(
        authority,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: summary,
    )

    suite = copy.copy(baseline["paths"]["suite"])

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not match its verified",
    ):
        authority.bind_visus_suite_to_source_authority(
            baseline["paths"]["audit"],
            suite,
        )


def test_bind_suite_source_audit_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = copy.deepcopy(baseline["verified_suite"])

    summary["source"]["source_audit_report_fingerprint_sha256"] = "0" * 64

    monkeypatch.setattr(
        authority,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: summary,
    )

    suite = copy.copy(baseline["paths"]["suite"])

    with pytest.raises(
        BenchmarkIntegrityError,
        match="different source audit",
    ):
        authority.bind_visus_suite_to_source_authority(
            baseline["paths"]["audit"],
            suite,
        )


def test_bind_suite_structure_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = copy.deepcopy(baseline["verified_suite"])

    monkeypatch.setattr(
        authority,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: summary,
    )

    suite = copy.copy(baseline["paths"]["suite"])

    suite.manifest = copy.deepcopy(suite.manifest)

    suite.manifest["source"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source/protocol structure",
    ):
        authority.bind_visus_suite_to_source_authority(
            baseline["paths"]["audit"],
            suite,
        )


def test_bind_suite_conflicting_existing_certificate_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = copy.deepcopy(baseline["verified_suite"])

    monkeypatch.setattr(
        authority,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: summary,
    )

    suite = copy.copy(baseline["paths"]["suite"])

    suite.manifest = copy.deepcopy(suite.manifest)

    suite.manifest["source"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = "f" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="different authority-certificate",
    ):
        authority.bind_visus_suite_to_source_authority(
            baseline["paths"]["audit"],
            suite,
        )


def test_authority_snapshot_type_guard() -> None:
    with pytest.raises(
        TypeError,
        match="tuple of VisusExecutionInputSnapshot",
    ):
        authority._authority_snapshot([])


def test_authority_snapshot_item_type_guard(
    baseline,
) -> None:
    values = list(baseline["snapshots"])

    values[1] = object()

    with pytest.raises(
        TypeError,
        match="tuple of VisusExecutionInputSnapshot",
    ):
        authority._authority_snapshot(tuple(values))


def test_authority_snapshot_role_guard(
    baseline,
) -> None:
    values = list(baseline["snapshots"])

    values[1] = VisusExecutionInputSnapshot(
        role="wrong",
        filename="x",
        sha256="a" * 64,
        bytes=1,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly five governed input roles",
    ):
        authority._authority_snapshot(tuple(values))


def test_authority_snapshot_success(
    baseline,
) -> None:
    result = authority._authority_snapshot(baseline["snapshots"])

    assert result.role == authority._AUTHORITY_ROLE


def test_base_snapshots_success(
    baseline,
) -> None:
    base = authority._base_snapshots(baseline["snapshots"])

    assert tuple(item.role for item in base) == authority._BASE_INPUT_ROLES


def test_build_authority_semantic_guard(
    baseline,
) -> None:
    values = list(baseline["snapshots"])

    values[1] = VisusExecutionInputSnapshot(
        role=authority._AUTHORITY_ROLE,
        filename=values[1].filename,
        sha256=values[1].sha256,
        bytes=values[1].bytes,
        semantic_fingerprint_sha256=("f" * 64),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not semantically match",
    ):
        authority.build_visus_authority_execution_provenance(
            baseline["paths"]["audit"],
            baseline["paths"]["suite"],
            tuple(values),
        )


def test_build_authority_suite_certificate_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        authority,
        "_suite_authority_fingerprint",
        lambda suite: "f" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not match the bound source audit",
    ):
        authority.build_visus_authority_execution_provenance(
            baseline["paths"]["audit"],
            baseline["paths"]["suite"],
            baseline["snapshots"],
        )


def test_build_authority_base_source_structure_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        authority,
        "_build_v1_execution_provenance",
        lambda *args, **kwargs: {
            "schema": "gazeforge-visus-execution-provenance-v1",
            "status": "complete",
            "provenance_scope": ("exact-raw-input-files-to-frozen-visus-suite"),
            "source": None,
            "raw_inputs": [],
        },
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity is invalid",
    ):
        authority.build_visus_authority_execution_provenance(
            baseline["paths"]["audit"],
            baseline["paths"]["suite"],
            baseline["snapshots"],
        )


def test_base_projection_success(
    baseline,
) -> None:
    projected = authority._base_projection(copy.deepcopy(baseline["manifest"]))

    assert projected["schema"] == authority._V1_EXECUTION_SCHEMA

    assert projected["provenance_scope"] == authority._V1_EXECUTION_SCOPE

    assert len(projected["raw_inputs"]) == 4

    assert all(row["role"] != authority._AUTHORITY_ROLE for row in projected["raw_inputs"])


def test_base_projection_source_guard(
    baseline,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["source"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity is invalid",
    ):
        authority._base_projection(manifest)


def test_base_projection_raw_inventory_guard(
    baseline,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["raw_inputs"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="raw-input inventory is invalid",
    ):
        authority._base_projection(manifest)


def test_validate_authority_row_count_guard(
    baseline,
) -> None:
    rows = copy.deepcopy(baseline["manifest"]["raw_inputs"])

    rows.pop()

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly five raw inputs",
    ):
        authority._validate_authority_row(
            rows,
            source=baseline["manifest"]["source"],
        )


def test_validate_authority_row_role_guard(
    baseline,
) -> None:
    rows = copy.deepcopy(baseline["manifest"]["raw_inputs"])

    rows[1]["role"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="raw-input roles are invalid",
    ):
        authority._validate_authority_row(
            rows,
            source=baseline["manifest"]["source"],
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "filename",
            "../certificate.json",
        ),
        (
            "sha256",
            "BAD",
        ),
        (
            "bytes",
            0,
        ),
        (
            "bytes",
            True,
        ),
        (
            "bytes",
            authority._MAX_AUTHORITY_CERTIFICATE_BYTES + 1,
        ),
        (
            "semantic_fingerprint_sha256",
            "BAD",
        ),
    ],
)
def test_validate_authority_row_field_guards(
    baseline,
    field: str,
    value: Any,
) -> None:
    rows = copy.deepcopy(baseline["manifest"]["raw_inputs"])

    rows[1][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="raw-input record is incomplete",
    ):
        authority._validate_authority_row(
            rows,
            source=baseline["manifest"]["source"],
        )


def test_validate_authority_row_semantic_binding_guard(
    baseline,
) -> None:
    rows = copy.deepcopy(baseline["manifest"]["raw_inputs"])

    rows[1]["semantic_fingerprint_sha256"] = "f" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not match source identity",
    ):
        authority._validate_authority_row(
            rows,
            source=baseline["manifest"]["source"],
        )


def test_validate_authority_row_extra_semantic_guard(
    baseline,
) -> None:
    rows = copy.deepcopy(baseline["manifest"]["raw_inputs"])

    rows[2]["semantic_fingerprint_sha256"] = "a" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Only the source-audit JSON and authority certificate",
    ):
        authority._validate_authority_row(
            rows,
            source=baseline["manifest"]["source"],
        )


def test_validate_authority_row_success(
    baseline,
) -> None:
    rows = copy.deepcopy(baseline["manifest"]["raw_inputs"])

    assert (
        authority._validate_authority_row(
            rows,
            source=baseline["manifest"]["source"],
        )
        == rows
    )


def test_validate_suite_binding_skip_success(
    baseline,
) -> None:
    authority._validate_suite_binding(
        baseline["paths"]["suite"].manifest_path,
        baseline["manifest"],
        verify_suite=False,
    )


def _suite_case(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
    mutate,
    *,
    match: str,
) -> None:
    summary = copy.deepcopy(baseline["verified_suite"])

    mutate(summary)

    monkeypatch.setattr(
        authority,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: summary,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        authority._validate_suite_binding(
            baseline["paths"]["suite"].manifest_path,
            baseline["manifest"],
            verify_suite=True,
        )


def test_suite_binding_fingerprint_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _suite_case(
        baseline,
        monkeypatch,
        lambda summary: summary.__setitem__(
            "suite_fingerprint_sha256",
            "0" * 64,
        ),
        match="suite fingerprint mismatch",
    )


def test_suite_binding_report_count_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _suite_case(
        baseline,
        monkeypatch,
        lambda summary: summary.__setitem__(
            "report_count",
            int(summary["report_count"]) + 1,
        ),
        match="report-count mismatch",
    )


def test_suite_binding_source_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(summary):
        summary["source"]["source_manifest_fingerprint_sha256"] = "0" * 64

    _suite_case(
        baseline,
        monkeypatch,
        mutate,
        match="suite source identity mismatch",
    )


def test_suite_binding_certificate_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(summary):
        summary["source"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = "f" * 64

    _suite_case(
        baseline,
        monkeypatch,
        mutate,
        match="certificate identity mismatch",
    )


def test_suite_binding_protocol_mapping_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _suite_case(
        baseline,
        monkeypatch,
        lambda summary: summary.__setitem__(
            "protocol",
            None,
        ),
        match="protocol must be a dictionary",
    )


def test_suite_binding_protocol_bound_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(summary):
        summary["protocol"]["source_authority_certificate_bound"] = False

    _suite_case(
        baseline,
        monkeypatch,
        mutate,
        match="lacks the required authority-bound",
    )


def test_suite_binding_protocol_certificate_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(summary):
        summary["protocol"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = "f" * 64

    _suite_case(
        baseline,
        monkeypatch,
        mutate,
        match="protocol/source fingerprint mismatch",
    )


def test_suite_binding_children_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        authority,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: copy.deepcopy(baseline["verified_suite"]),
    )

    monkeypatch.setattr(
        authority,
        "_load_suite_children",
        lambda *args, **kwargs: {},
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot recover verified intake children",
    ):
        authority._validate_suite_binding(
            baseline["paths"]["suite"].manifest_path,
            baseline["manifest"],
            verify_suite=True,
        )


def test_suite_binding_parsed_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    children = copy.deepcopy(baseline["children"])

    children["human_reference_intake"]["input_table_fingerprint_sha256"] = "f" * 64

    monkeypatch.setattr(
        authority,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: copy.deepcopy(baseline["verified_suite"]),
    )

    monkeypatch.setattr(
        authority,
        "_load_suite_children",
        lambda *args, **kwargs: children,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="parsed-input binding does not match",
    ):
        authority._validate_suite_binding(
            baseline["paths"]["suite"].manifest_path,
            baseline["manifest"],
            verify_suite=True,
        )


def test_validate_missing_file(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        authority.validate_visus_authority_execution_provenance(tmp_path / "missing.json")


def test_validate_invalid_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad.json"

    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not valid JSON",
    ):
        authority.validate_visus_authority_execution_provenance(path)


def test_validate_non_object(
    tmp_path: Path,
) -> None:
    path = tmp_path / "array.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        authority.validate_visus_authority_execution_provenance(path)


def test_validate_fingerprint_guard(
    baseline,
    tmp_path: Path,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["execution_fingerprint_sha256"] = "0" * 64

    path = _write(
        tmp_path,
        manifest,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint mismatch",
    ):
        authority.validate_visus_authority_execution_provenance(
            path,
            verify_suite=False,
        )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "schema",
            "wrong",
            "provenance v2",
        ),
        (
            "status",
            "wrong",
            "status is invalid",
        ),
        (
            "provenance_scope",
            "wrong",
            "scope is invalid",
        ),
    ],
)
def test_validate_top_level_guards(
    baseline,
    tmp_path: Path,
    field: str,
    value: Any,
    match: str,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest[field] = value
    _resign(manifest)

    path = _write(
        tmp_path,
        manifest,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        authority.validate_visus_authority_execution_provenance(
            path,
            verify_suite=False,
        )


def test_validate_source_mapping_guard(
    baseline,
    tmp_path: Path,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["source"] = None
    _resign(manifest)

    path = _write(
        tmp_path,
        manifest,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity is invalid",
    ):
        authority.validate_visus_authority_execution_provenance(
            path,
            verify_suite=False,
        )


def test_validate_source_fingerprint_guard(
    baseline,
    tmp_path: Path,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["source"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = "BAD"

    _resign(manifest)

    path = _write(
        tmp_path,
        manifest,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source fingerprints are incomplete",
    ):
        authority.validate_visus_authority_execution_provenance(
            path,
            verify_suite=False,
        )


def test_validate_without_suite_success(
    baseline,
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path,
        copy.deepcopy(baseline["manifest"]),
    )

    result = authority.validate_visus_authority_execution_provenance(
        path,
        verify_suite=False,
    )

    assert result["input_count"] == 5
    assert result["suite_verified"] is False
    assert result[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] == baseline["certificate_fingerprint"]


def test_validate_directory_input_without_suite(
    baseline,
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        copy.deepcopy(baseline["manifest"]),
    )

    result = authority.validate_visus_authority_execution_provenance(
        tmp_path,
        verify_suite=False,
    )

    assert result["manifest_path"].endswith("visus-execution-provenance.json")


def test_write_requires_dict(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        TypeError,
        match="dictionary",
    ):
        authority.write_visus_authority_execution_provenance(
            [],
            tmp_path,
        )


def test_write_revalidation_guard(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not revalidate",
    ):
        authority.write_visus_authority_execution_provenance(
            {
                "schema": (authority._EXECUTION_SCHEMA),
                "execution_fingerprint_sha256": ("0" * 64),
            },
            tmp_path,
        )


def test_write_existing_guard(
    baseline,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    target = authority.visus_execution_provenance_path(tmp_path)

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    target.write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(FileExistsError):
        authority.write_visus_authority_execution_provenance(
            manifest,
            tmp_path,
        )


def test_write_success_with_revalidation_hook(
    baseline,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    calls: list[tuple[Path, bool]] = []

    def fake_validate(
        path,
        *,
        verify_suite=True,
    ):
        calls.append(
            (
                Path(path),
                verify_suite,
            )
        )

        return {
            "status": "complete",
        }

    monkeypatch.setattr(
        authority,
        "validate_visus_authority_execution_provenance",
        fake_validate,
    )

    run = authority.write_visus_authority_execution_provenance(
        manifest,
        tmp_path,
    )

    assert run.manifest_path.is_file()
    assert calls == [
        (
            run.manifest_path,
            True,
        )
    ]

    second = authority.write_visus_authority_execution_provenance(
        manifest,
        tmp_path,
        overwrite=True,
    )

    assert second.manifest_path == run.manifest_path


# === VISUS AUTHORITY EXECUTION FINAL COVERAGE CLOSURE ===


def test_bind_suite_post_seal_revalidation_guard(
    baseline,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite = copy.copy(baseline["paths"]["suite"])

    suite.manifest = copy.deepcopy(suite.manifest)

    suite.manifest_path = tmp_path / "suite-manifest.json"

    suite.manifest_path.write_text(
        json.dumps(
            suite.manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    first = copy.deepcopy(baseline["verified_suite"])

    first["suite_fingerprint_sha256"] = suite.suite_fingerprint_sha256

    first["source"]["source_audit_report_fingerprint_sha256"] = baseline["paths"]["audit"].report[
        "report_fingerprint_sha256"
    ]

    second = copy.deepcopy(first)

    second["suite_fingerprint_sha256"] = "0" * 64

    responses = iter(
        [
            first,
            second,
        ]
    )

    monkeypatch.setattr(
        authority,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: next(responses),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="did not revalidate after sealing",
    ):
        authority.bind_visus_suite_to_source_authority(
            baseline["paths"]["audit"],
            suite,
        )


def test_validate_authority_row_non_object_authority_guard(
    baseline,
) -> None:
    rows = copy.deepcopy(baseline["manifest"]["raw_inputs"])

    rows[1] = "bad-authority-row"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="authority-certificate raw-input record is invalid",
    ):
        authority._validate_authority_row(
            rows,
            source=baseline["manifest"]["source"],
        )


def test_validate_authority_row_non_object_analysis_input_guard(
    baseline,
) -> None:
    rows = copy.deepcopy(baseline["manifest"]["raw_inputs"])

    rows[2] = "bad-analysis-row"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-object raw-input record",
    ):
        authority._validate_authority_row(
            rows,
            source=baseline["manifest"]["source"],
        )


def test_validate_suite_binding_requires_suite_object(
    baseline,
) -> None:
    manifest = copy.deepcopy(baseline["manifest"])

    manifest["suite"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="suite binding is invalid",
    ):
        authority._validate_suite_binding(
            baseline["paths"]["suite"].manifest_path,
            manifest,
            verify_suite=True,
        )
