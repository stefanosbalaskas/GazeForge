from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

import gazeforge.visus_authority_execution_strict as strict
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_authority_binding import (
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
)
from gazeforge.visus_execution import VisusExecutionProvenanceRun

FP = "a" * 64
OTHER_FP = "b" * 64


def _certificate(
    fingerprint: str = FP,
) -> dict[str, Any]:
    return {
        "certificate_fingerprint_sha256": fingerprint,
    }


def _manifest() -> dict[str, Any]:
    return {
        "schema": "gazeforge-visus-execution-provenance-v2",
        "status": "complete",
        "provenance_scope": ("exact-authority-and-raw-input-files-to-frozen-visus-suite"),
        "source": {
            AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: FP,
        },
        "raw_inputs": [
            {
                "role": "source_audit_spec",
                "semantic_fingerprint_sha256": "c" * 64,
            },
            {
                "role": "source_authority_certificate",
                "semantic_fingerprint_sha256": FP,
            },
            {
                "role": "human_aoi_table",
                "semantic_fingerprint_sha256": None,
            },
            {
                "role": "model_prediction_table",
                "semantic_fingerprint_sha256": None,
            },
            {
                "role": "timestamp_grid_json",
                "semantic_fingerprint_sha256": None,
            },
        ],
        strict.AUTHORITY_CERTIFICATE_RECORD_FIELD: _certificate(),
    }


def _signed_manifest() -> dict[str, Any]:
    manifest = _manifest()

    body = {key: value for key, value in manifest.items() if key != "execution_fingerprint_sha256"}

    manifest["execution_fingerprint_sha256"] = strict.benchmark_fingerprint(body)

    return manifest


def _patch_certificate_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def validate(raw):
        if not isinstance(raw, dict):
            raise BenchmarkIntegrityError("certificate fixture must be an object")

        return copy.deepcopy(raw)

    monkeypatch.setattr(
        strict,
        "validate_certificate_record",
        validate,
    )


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
    assert strict._valid_sha256(value) is expected


def test_read_manifest_missing_guard(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        strict._read_manifest(tmp_path / "missing.json")


def test_read_manifest_invalid_json_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "manifest.json"

    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not valid JSON",
    ):
        strict._read_manifest(path)


def test_read_manifest_requires_object(
    tmp_path: Path,
) -> None:
    path = tmp_path / "manifest.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        strict._read_manifest(path)


def test_read_manifest_file_success(
    tmp_path: Path,
) -> None:
    path = tmp_path / "custom.json"

    path.write_text(
        json.dumps({"a": 1}),
        encoding="utf-8",
    )

    observed_path, value = strict._read_manifest(path)

    assert observed_path == path
    assert value == {"a": 1}


def test_read_manifest_directory_success(
    tmp_path: Path,
) -> None:
    path = tmp_path / "visus-execution-provenance.json"

    path.write_text(
        json.dumps({"a": 1}),
        encoding="utf-8",
    )

    observed_path, value = strict._read_manifest(tmp_path)

    assert observed_path == path
    assert value == {"a": 1}


def test_embedded_certificate_missing_guard() -> None:
    manifest = _manifest()

    del manifest[strict.AUTHORITY_CERTIFICATE_RECORD_FIELD]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing the reviewed certificate record",
    ):
        strict._embedded_certificate(manifest)


def test_embedded_certificate_source_structure_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_certificate_validator(monkeypatch)

    manifest = _manifest()
    manifest["source"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source/input structure is invalid",
    ):
        strict._embedded_certificate(manifest)


def test_embedded_certificate_rows_structure_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_certificate_validator(monkeypatch)

    manifest = _manifest()
    manifest["raw_inputs"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source/input structure is invalid",
    ):
        strict._embedded_certificate(manifest)


def test_embedded_certificate_source_identity_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_certificate_validator(monkeypatch)

    manifest = _manifest()

    manifest["source"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = OTHER_FP

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not match the execution source identity",
    ):
        strict._embedded_certificate(manifest)


def test_embedded_certificate_requires_one_authority_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_certificate_validator(monkeypatch)

    manifest = _manifest()

    manifest["raw_inputs"] = [
        row for row in manifest["raw_inputs"] if row["role"] != strict._AUTHORITY_ROLE
    ]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires one authority-certificate raw input",
    ):
        strict._embedded_certificate(manifest)


def test_embedded_certificate_duplicate_authority_row_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_certificate_validator(monkeypatch)

    manifest = _manifest()

    manifest["raw_inputs"].append(copy.deepcopy(manifest["raw_inputs"][1]))

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires one authority-certificate raw input",
    ):
        strict._embedded_certificate(manifest)


def test_embedded_certificate_semantic_identity_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_certificate_validator(monkeypatch)

    manifest = _manifest()

    manifest["raw_inputs"][1]["semantic_fingerprint_sha256"] = OTHER_FP

    with pytest.raises(
        BenchmarkIntegrityError,
        match="raw-input semantic identity",
    ):
        strict._embedded_certificate(manifest)


def test_embedded_certificate_comprehension_nonmapping_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_certificate_validator(monkeypatch)

    manifest = _manifest()

    manifest["raw_inputs"].append("unrelated-non-object")

    certificate = strict._embedded_certificate(manifest)

    assert certificate["certificate_fingerprint_sha256"] == FP


def test_embedded_certificate_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_certificate_validator(monkeypatch)

    certificate = strict._embedded_certificate(_manifest())

    assert certificate == _certificate()


def test_build_rejects_existing_certificate_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _signed_manifest()

    monkeypatch.setattr(
        strict,
        "_build_transport_provenance",
        lambda *args, **kwargs: transport,
    )

    monkeypatch.setattr(
        strict,
        "source_authority_certificate_record",
        lambda *args, **kwargs: _certificate(),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="already contains a certificate record",
    ):
        strict.build_visus_authority_execution_provenance(
            object(),
            object(),
            tuple(),
        )


def test_build_certificate_dependency_must_resolve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _signed_manifest()

    transport.pop(
        strict.AUTHORITY_CERTIFICATE_RECORD_FIELD,
        None,
    )

    monkeypatch.setattr(
        strict,
        "_build_transport_provenance",
        lambda *args, **kwargs: transport,
    )

    monkeypatch.setattr(
        strict,
        "source_authority_certificate_record",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(AssertionError):
        strict.build_visus_authority_execution_provenance(
            object(),
            object(),
            tuple(),
        )


def test_build_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _signed_manifest()

    transport.pop(
        strict.AUTHORITY_CERTIFICATE_RECORD_FIELD,
        None,
    )

    monkeypatch.setattr(
        strict,
        "_build_transport_provenance",
        lambda *args, **kwargs: copy.deepcopy(transport),
    )

    monkeypatch.setattr(
        strict,
        "source_authority_certificate_record",
        lambda *args, **kwargs: _certificate(),
    )

    monkeypatch.setattr(
        strict,
        "_embedded_certificate",
        lambda manifest: _certificate(),
    )

    result = strict.build_visus_authority_execution_provenance(
        object(),
        object(),
        tuple(),
    )

    assert result[strict.AUTHORITY_CERTIFICATE_RECORD_FIELD] == _certificate()

    body = {key: value for key, value in result.items() if key != "execution_fingerprint_sha256"}

    assert result["execution_fingerprint_sha256"] == strict.benchmark_fingerprint(body)


def test_validate_fingerprint_guard(
    tmp_path: Path,
) -> None:
    manifest = _signed_manifest()

    manifest["execution_fingerprint_sha256"] = "0" * 64

    path = tmp_path / "manifest.json"

    path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint mismatch",
    ):
        strict.validate_visus_authority_execution_provenance(
            path,
            verify_suite=False,
        )


def test_validate_transport_certificate_identity_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _signed_manifest()

    path = tmp_path / "manifest.json"

    path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        strict,
        "_embedded_certificate",
        lambda value: _certificate(),
    )

    monkeypatch.setattr(
        strict,
        "_validate_transport_provenance",
        lambda *args, **kwargs: {
            AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: (OTHER_FP),
        },
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="certificate/transport identity mismatch",
    ):
        strict.validate_visus_authority_execution_provenance(
            path,
            verify_suite=False,
        )


def test_validate_success_and_verify_suite_forwarding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _signed_manifest()

    path = tmp_path / "manifest.json"

    path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    calls: list[bool] = []

    monkeypatch.setattr(
        strict,
        "_embedded_certificate",
        lambda value: _certificate(),
    )

    def transport(
        manifest_path,
        *,
        verify_suite=True,
    ):
        calls.append(verify_suite)

        return {
            "schema": ("gazeforge-visus-execution-provenance-v2"),
            "status": "complete",
            "input_count": 5,
            AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: FP,
        }

    monkeypatch.setattr(
        strict,
        "_validate_transport_provenance",
        transport,
    )

    result = strict.validate_visus_authority_execution_provenance(
        path,
        verify_suite=False,
    )

    assert calls == [False]

    assert result["authority_certificate_semantics_verified"] is True

    assert result[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] == FP


def test_write_requires_dictionary(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        TypeError,
        match="dictionary",
    ):
        strict.write_visus_authority_execution_provenance(
            [],
            tmp_path,
        )


def test_write_embedded_certificate_failure_propagates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(manifest):
        raise BenchmarkIntegrityError("bad embedded certificate")

    monkeypatch.setattr(
        strict,
        "_embedded_certificate",
        fail,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="bad embedded certificate",
    ):
        strict.write_visus_authority_execution_provenance(
            {},
            tmp_path,
        )


def test_write_success_and_revalidation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _signed_manifest()

    path = tmp_path / "visus-execution-provenance.json"

    run = VisusExecutionProvenanceRun(
        manifest_path=path,
        manifest=manifest,
        execution_fingerprint_sha256=(manifest["execution_fingerprint_sha256"]),
    )

    calls: list[tuple[str, Any]] = []

    monkeypatch.setattr(
        strict,
        "_embedded_certificate",
        lambda value: _certificate(),
    )

    def write_transport(
        value,
        output_dir,
        *,
        overwrite=False,
    ):
        calls.append(
            (
                "write",
                overwrite,
            )
        )

        return run

    def validate(
        value,
        *,
        verify_suite=True,
    ):
        calls.append(
            (
                "validate",
                verify_suite,
            )
        )

        return {
            "status": "complete",
        }

    monkeypatch.setattr(
        strict,
        "_write_transport_provenance",
        write_transport,
    )

    monkeypatch.setattr(
        strict,
        "validate_visus_authority_execution_provenance",
        validate,
    )

    observed = strict.write_visus_authority_execution_provenance(
        manifest,
        tmp_path,
        overwrite=True,
    )

    assert observed is run

    assert calls == [
        (
            "write",
            True,
        ),
        (
            "validate",
            True,
        ),
    ]
