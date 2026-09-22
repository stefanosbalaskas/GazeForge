from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import gazeforge.visus_protocol_authority_transition as transition
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError


def _write(path: Path, payload: bytes = b"fixture\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _identity() -> dict[str, str]:
    return {
        "source_audit_report_fingerprint_sha256": "a" * 64,
        "source_audit_spec_fingerprint_sha256": "b" * 64,
        "source_manifest_fingerprint_sha256": "c" * 64,
    }


def _suite(
    tmp_path: Path,
    *,
    prefix: str,
    fingerprint: str = "d" * 64,
):
    root = tmp_path / prefix
    root.mkdir(parents=True, exist_ok=True)

    report = _write(
        root / "report.json",
        b'{"fixture": true}\n',
    )
    manifest = _write(
        root / "manifest.json",
        b'{"fixture": true}\n',
    )

    return SimpleNamespace(
        output_dir=root,
        report_paths={
            "report": report,
        },
        reports={"report": {"report_fingerprint_sha256": ("e" * 64)}},
        manifest_path=manifest,
        manifest={
            "source": {},
            "protocol": {},
        },
        suite_fingerprint_sha256=fingerprint,
    )


# ============================================================
# FILE INTEGRITY HELPERS
# ============================================================


def test_hash_regular_file_rejects_missing_file(
    tmp_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-symlink regular file",
    ):
        transition._hash_regular_file(
            tmp_path / "missing.bin",
            label="fixture",
        )


def test_hash_regular_file_success(
    tmp_path,
):
    path = _write(
        tmp_path / "payload.bin",
        b"abc",
    )

    observed = transition._hash_regular_file(
        path,
        label="fixture",
    )

    assert len(observed) == 64


def test_read_json_object_rejects_missing_file(
    tmp_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-symlink regular file",
    ):
        transition._read_json_object(
            tmp_path / "missing.json",
            label="fixture",
        )


def test_read_json_object_rejects_invalid_json(
    tmp_path,
):
    path = _write(
        tmp_path / "bad.json",
        b"{",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        transition._read_json_object(
            path,
            label="fixture",
        )


def test_read_json_object_requires_object(
    tmp_path,
):
    path = _write(
        tmp_path / "array.json",
        b"[]",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        transition._read_json_object(
            path,
            label="fixture",
        )


def test_read_json_object_success(
    tmp_path,
):
    path = _write(
        tmp_path / "object.json",
        b'{"x": 1}',
    )

    assert transition._read_json_object(
        path,
        label="fixture",
    ) == {"x": 1}


# ============================================================
# ORIGINAL SUITE MUST REMAIN UNBOUND
# ============================================================


def _validation_with_manifest(
    manifest,
):
    return SimpleNamespace(
        suite=SimpleNamespace(
            manifest=manifest,
        )
    )


@pytest.mark.parametrize(
    "manifest",
    [
        {
            "source": None,
            "protocol": {},
        },
        {
            "source": {},
            "protocol": None,
        },
    ],
)
def test_original_suite_requires_source_protocol_mappings(
    manifest,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="source/protocol structure is invalid",
    ):
        transition._assert_original_suite_unbound(_validation_with_manifest(manifest))


def test_original_suite_rejects_source_authority_binding():
    validation = _validation_with_manifest(
        {
            "source": {transition.AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: ("a" * 64)},
            "protocol": {},
        }
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="remain unbound",
    ):
        transition._assert_original_suite_unbound(validation)


@pytest.mark.parametrize(
    "protocol_value",
    [
        {
            transition._AUTHORITY_PROTOCOL_FLAG: True,
        },
        {transition.AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: ("a" * 64)},
    ],
)
def test_original_suite_rejects_protocol_authority_mutation(
    protocol_value,
):
    validation = _validation_with_manifest(
        {
            "source": {},
            "protocol": protocol_value,
        }
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="already authority-mutated",
    ):
        transition._assert_original_suite_unbound(validation)


# ============================================================
# CLONE ISOLATION
# ============================================================


def test_clone_rejects_existing_output(
    tmp_path,
):
    output = tmp_path / "already-exists"
    output.mkdir()

    validation = SimpleNamespace(
        suite=_suite(
            tmp_path,
            prefix="source-suite",
        )
    )

    with pytest.raises(
        FileExistsError,
    ):
        transition._clone_suite(
            validation,
            output,
        )


def test_clone_rejects_duplicate_child_filenames(
    tmp_path,
):
    first = _write(
        tmp_path / "a" / "same.json",
    )
    second = _write(
        tmp_path / "b" / "same.json",
    )
    manifest = _write(
        tmp_path / "manifest" / "manifest.json",
    )

    validation = SimpleNamespace(
        suite=SimpleNamespace(
            report_paths={
                "a": first,
                "b": second,
            },
            reports={
                "a": {},
                "b": {},
            },
            manifest_path=manifest,
            manifest={},
            suite_fingerprint_sha256=("a" * 64),
        )
    )

    output = tmp_path / "clone"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="filenames are not unique",
    ):
        transition._clone_suite(
            validation,
            output,
        )

    assert not output.exists()


def test_clone_rejects_manifest_child_filename_collision(
    tmp_path,
):
    child = _write(
        tmp_path / "child" / "manifest.json",
    )
    manifest = _write(
        tmp_path / "source" / "manifest.json",
    )

    validation = SimpleNamespace(
        suite=SimpleNamespace(
            report_paths={
                "child": child,
            },
            reports={
                "child": {},
            },
            manifest_path=manifest,
            manifest={},
            suite_fingerprint_sha256=("a" * 64),
        )
    )

    output = tmp_path / "clone"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="manifest filename collides",
    ):
        transition._clone_suite(
            validation,
            output,
        )

    assert not output.exists()


def test_clone_rejects_verified_fingerprint_mismatch_and_cleans_up(
    tmp_path,
    monkeypatch,
):
    validation = SimpleNamespace(
        suite=_suite(
            tmp_path,
            prefix="source-suite",
            fingerprint="a" * 64,
        )
    )

    monkeypatch.setattr(
        transition,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: {transition._SUITE_FINGERPRINT_FIELD: ("b" * 64)},
    )

    output = tmp_path / "clone"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not reproduce",
    ):
        transition._clone_suite(
            validation,
            output,
        )

    assert not output.exists()


# ============================================================
# PRE-AUTHORITY PROJECTION
# ============================================================


@pytest.mark.parametrize(
    ("source", "protocol"),
    [
        (None, {}),
        ({}, None),
    ],
)
def test_projection_requires_source_protocol_objects(
    source,
    protocol,
):
    manifest = {
        transition._SUITE_FINGERPRINT_FIELD: ("a" * 64),
        "source": source,
        "protocol": protocol,
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source/protocol structure is invalid",
    ):
        transition._pre_authority_projection_fingerprint(manifest)


# ============================================================
# CHILD REPORT LEDGER
# ============================================================


def test_child_ledger_requires_same_report_set(
    tmp_path,
):
    original = _suite(
        tmp_path,
        prefix="original",
    )
    authority = _suite(
        tmp_path,
        prefix="authority",
    )

    authority.report_paths = {"different": next(iter(authority.report_paths.values()))}

    with pytest.raises(
        BenchmarkIntegrityError,
        match="child-report set differs",
    ):
        transition._child_file_ledger(
            original,
            authority,
        )


def test_child_ledger_requires_same_filename(
    tmp_path,
):
    original = _suite(
        tmp_path,
        prefix="original",
    )
    authority = _suite(
        tmp_path,
        prefix="authority",
    )

    authority.report_paths["report"] = _write(
        authority.output_dir / "renamed.json",
        b'{"fixture": true}\n',
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="changed a child-report filename",
    ):
        transition._child_file_ledger(
            original,
            authority,
        )


def test_child_ledger_requires_report_object(
    tmp_path,
):
    original = _suite(
        tmp_path,
        prefix="original",
    )
    authority = _suite(
        tmp_path,
        prefix="authority",
    )

    original.reports["report"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="report object is missing",
    ):
        transition._child_file_ledger(
            original,
            authority,
        )


def test_child_ledger_requires_valid_report_fingerprint(
    tmp_path,
):
    original = _suite(
        tmp_path,
        prefix="original",
    )
    authority = _suite(
        tmp_path,
        prefix="authority",
    )

    original.reports["report"]["report_fingerprint_sha256"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="report fingerprint is invalid",
    ):
        transition._child_file_ledger(
            original,
            authority,
        )


# ============================================================
# AUTHORITY SUITE VALIDATION
# ============================================================


def _authority_validation():
    return SimpleNamespace(
        batch=SimpleNamespace(
            audit=object(),
        ),
        suite=SimpleNamespace(suite_fingerprint_sha256=("a" * 64)),
    )


def _authority_suite():
    return SimpleNamespace(
        manifest_path=Path("authority-manifest.json"),
        suite_fingerprint_sha256=("b" * 64),
    )


def _authority_manifest(
    *,
    suite_fp="b" * 64,
    source=None,
    protocol_value=None,
):
    certificate = "c" * 64

    if source is None:
        source = {transition.AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: (certificate)}

    if protocol_value is None:
        protocol_value = {
            transition._AUTHORITY_PROTOCOL_FLAG: True,
            transition.AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: (certificate),
        }

    return {
        transition._SUITE_FINGERPRINT_FIELD: (suite_fp),
        "source": source,
        "protocol": protocol_value,
        "reports": [],
    }


def _patch_authority_dependencies(
    monkeypatch,
    *,
    verified_fp="b" * 64,
    manifest=None,
    projection="a" * 64,
):
    if manifest is None:
        manifest = _authority_manifest()

    monkeypatch.setattr(
        transition,
        "source_authority_certificate_fingerprint",
        lambda *args, **kwargs: "c" * 64,
    )

    monkeypatch.setattr(
        transition,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda *args, **kwargs: {transition._SUITE_FINGERPRINT_FIELD: (verified_fp)},
    )

    monkeypatch.setattr(
        transition,
        "_read_json_object",
        lambda *args, **kwargs: copy.deepcopy(manifest),
    )

    monkeypatch.setattr(
        transition,
        "_pre_authority_projection_fingerprint",
        lambda value: projection,
    )


def test_verified_authority_suite_object_fingerprint_guard(
    monkeypatch,
):
    _patch_authority_dependencies(
        monkeypatch,
        verified_fp="9" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="object does not match",
    ):
        transition._verified_authority_suite(
            _authority_validation(),
            _authority_suite(),
        )


def test_verified_authority_suite_file_fingerprint_guard(
    monkeypatch,
):
    manifest = _authority_manifest(
        suite_fp="9" * 64,
    )

    _patch_authority_dependencies(
        monkeypatch,
        manifest=manifest,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file does not match",
    ):
        transition._verified_authority_suite(
            _authority_validation(),
            _authority_suite(),
        )


@pytest.mark.parametrize(
    ("source", "protocol_value"),
    [
        (None, {}),
        ({}, None),
    ],
)
def test_verified_authority_suite_requires_source_protocol(
    monkeypatch,
    source,
    protocol_value,
):
    manifest = _authority_manifest(
        source=source,
        protocol_value=protocol_value,
    )

    # _authority_manifest uses None as "use default",
    # so explicitly replace after construction.
    manifest["source"] = source
    manifest["protocol"] = protocol_value

    _patch_authority_dependencies(
        monkeypatch,
        manifest=manifest,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source/protocol sections are missing",
    ):
        transition._verified_authority_suite(
            _authority_validation(),
            _authority_suite(),
        )


def test_verified_authority_suite_requires_authority_flag(
    monkeypatch,
):
    manifest = _authority_manifest()

    manifest["protocol"][transition._AUTHORITY_PROTOCOL_FLAG] = False

    _patch_authority_dependencies(
        monkeypatch,
        manifest=manifest,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lacks the required authority declaration",
    ):
        transition._verified_authority_suite(
            _authority_validation(),
            _authority_suite(),
        )


def test_verified_authority_suite_requires_protocol_certificate_identity(
    monkeypatch,
):
    manifest = _authority_manifest()

    manifest["protocol"][transition.AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = "9" * 64

    _patch_authority_dependencies(
        monkeypatch,
        manifest=manifest,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="protocol/source certificate identities differ",
    ):
        transition._verified_authority_suite(
            _authority_validation(),
            _authority_suite(),
        )


def test_verified_authority_suite_requires_distinct_post_authority_identity(
    monkeypatch,
):
    validation = _authority_validation()

    authority = _authority_suite()
    authority.suite_fingerprint_sha256 = validation.suite.suite_fingerprint_sha256

    manifest = _authority_manifest(suite_fp=(authority.suite_fingerprint_sha256))

    _patch_authority_dependencies(
        monkeypatch,
        verified_fp=(authority.suite_fingerprint_sha256),
        manifest=manifest,
        projection=(validation.suite.suite_fingerprint_sha256),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="distinct post-authority suite identity",
    ):
        transition._verified_authority_suite(
            validation,
            authority,
        )


# ============================================================
# TRANSITION BODY LINEAGE GUARDS
# ============================================================


def _body_validation(
    tmp_path,
):
    binding_path = _write(
        tmp_path / "validation-binding.json",
        b'{"fixture": true}\n',
    )

    suite_manifest = _write(
        tmp_path / "original-suite.json",
        b'{"fixture": true}\n',
    )

    return SimpleNamespace(
        output_dir=tmp_path / "original-validation",
        binding_fingerprint_sha256=("d" * 64),
        binding={
            "binding_fingerprint_sha256": ("d" * 64),
            "source": _identity(),
            "protocol_fingerprint_sha256": ("e" * 64),
            "protocol_batch_fingerprint_sha256": ("f" * 64),
        },
        binding_path=binding_path,
        suite=SimpleNamespace(
            manifest_path=suite_manifest,
            suite_fingerprint_sha256=("a" * 64),
        ),
    )


def _body_authority_suite(
    output,
):
    manifest = _write(
        output / "authority-suite.json",
        b'{"fixture": true}\n',
    )

    return SimpleNamespace(
        output_dir=output,
        manifest_path=manifest,
        suite_fingerprint_sha256=("b" * 64),
    )


def _patch_body_dependencies(
    monkeypatch,
):
    monkeypatch.setattr(
        transition,
        "validate_visus_protocol_bound_validation_run",
        lambda value: value,
    )

    monkeypatch.setattr(
        transition,
        "_assert_original_suite_unbound",
        lambda value: None,
    )

    monkeypatch.setattr(
        transition,
        "_assert_separate_output",
        lambda value, output: None,
    )

    monkeypatch.setattr(
        transition,
        "_verified_authority_suite",
        lambda *args, **kwargs: (
            {
                "reports": [],
            },
            "c" * 64,
            "a" * 64,
        ),
    )

    monkeypatch.setattr(
        transition,
        "_child_file_ledger",
        lambda *args, **kwargs: [],
    )


def test_transition_body_requires_authority_suite_root(
    tmp_path,
    monkeypatch,
):
    _patch_body_dependencies(monkeypatch)

    validation = _body_validation(tmp_path)

    output = tmp_path / "expected-output"
    output.mkdir()

    authority = _body_authority_suite(tmp_path / "different-output")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not rooted",
    ):
        transition._transition_body(
            validation,
            authority,
            output,
        )


def test_transition_body_requires_manifest_inside_output(
    tmp_path,
    monkeypatch,
):
    _patch_body_dependencies(monkeypatch)

    validation = _body_validation(tmp_path)

    output = tmp_path / "expected-output"
    output.mkdir()

    authority = SimpleNamespace(
        output_dir=output,
        manifest_path=_write(
            tmp_path / "outside" / "authority-suite.json",
            b"fixture\n",
        ),
        suite_fingerprint_sha256=("b" * 64),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="manifest is outside",
    ):
        transition._transition_body(
            validation,
            authority,
            output,
        )


def test_transition_body_binding_object_identity_guard(
    tmp_path,
    monkeypatch,
):
    _patch_body_dependencies(monkeypatch)

    validation = _body_validation(tmp_path)

    validation.binding["binding_fingerprint_sha256"] = "9" * 64

    output = tmp_path / "output"
    output.mkdir()

    authority = _body_authority_suite(output)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="object/binding fingerprint identity drifted",
    ):
        transition._transition_body(
            validation,
            authority,
            output,
        )


def test_transition_body_requires_valid_binding_fingerprint(
    tmp_path,
    monkeypatch,
):
    _patch_body_dependencies(monkeypatch)

    validation = _body_validation(tmp_path)

    validation.binding_fingerprint_sha256 = "bad"
    validation.binding["binding_fingerprint_sha256"] = "bad"

    output = tmp_path / "output"
    output.mkdir()

    authority = _body_authority_suite(output)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="binding fingerprint is invalid",
    ):
        transition._transition_body(
            validation,
            authority,
            output,
        )


def test_transition_body_requires_source_identity(
    tmp_path,
    monkeypatch,
):
    _patch_body_dependencies(monkeypatch)

    validation = _body_validation(tmp_path)

    validation.binding["source"] = None

    output = tmp_path / "output"
    output.mkdir()

    authority = _body_authority_suite(output)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity is missing",
    ):
        transition._transition_body(
            validation,
            authority,
            output,
        )


# ============================================================
# RUNNER CLEANUP ON FAILURE
# ============================================================


def test_transition_runner_removes_clone_on_failure(
    tmp_path,
    monkeypatch,
):
    validation = SimpleNamespace(
        batch=SimpleNamespace(
            audit=object(),
        ),
        suite=SimpleNamespace(
            manifest={
                "source": {},
                "protocol": {},
            }
        ),
        output_dir=tmp_path / "original",
    )

    monkeypatch.setattr(
        transition,
        "validate_visus_protocol_bound_validation_run",
        lambda value: value,
    )

    monkeypatch.setattr(
        transition,
        "_assert_original_suite_unbound",
        lambda value: None,
    )

    monkeypatch.setattr(
        transition,
        "source_authority_certificate_fingerprint",
        lambda *args, **kwargs: "a" * 64,
    )

    monkeypatch.setattr(
        transition,
        "_assert_separate_output",
        lambda *args, **kwargs: None,
    )

    def fake_clone(value, output):
        output.mkdir(
            parents=True,
            exist_ok=False,
        )
        return object()

    monkeypatch.setattr(
        transition,
        "_clone_suite",
        fake_clone,
    )

    monkeypatch.setattr(
        transition,
        "bind_visus_suite_to_source_authority",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("forced authority failure")),
    )

    output = tmp_path / "transition-output"

    with pytest.raises(
        RuntimeError,
        match="forced authority failure",
    ):
        transition.run_visus_protocol_authority_transition(
            validation,
            output,
        )

    assert not output.exists()


# ============================================================
# FINAL TRANSITION VALIDATOR
# ============================================================


def _transition_body_record():
    return {
        "schema": transition._TRANSITION_SCHEMA,
        "status": ("verified-protocol-authority-transition"),
        "transition_semantics": {
            "original_protocol_validation_preserved": True,
            "authority_binding_applied_to_isolated_suite_clone": True,
            "only_suite_manifest_authority_fields_added": True,
            "child_report_bytes_unchanged": True,
            "authority_execution_provenance_required_separately": True,
        },
        "source_authority_certificate_consumed": True,
        "empirical_validation_authorized_by_transition": False,
        "empirical_performance_claim_created": False,
        "formal_preregistration_verified": False,
        "frozen_evidence_created": False,
        "raw_source_redistribution_action_authorized": False,
    }


def _resign_transition(
    value,
):
    body = {key: item for key, item in value.items() if key != "transition_fingerprint_sha256"}

    value["transition_fingerprint_sha256"] = benchmark_fingerprint(body)

    return value


def _transition_run(
    tmp_path,
    *,
    transition_value=None,
    filename=None,
    output_dir=None,
    object_fingerprint=None,
):
    if transition_value is None:
        transition_value = _resign_transition(_transition_body_record())

    if output_dir is None:
        output_dir = tmp_path / "transition"

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    if filename is None:
        filename = transition._TRANSITION_FILENAME

    transition_path = output_dir / filename

    transition_path.write_text(
        json.dumps(
            transition_value,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    fingerprint = (
        transition_value["transition_fingerprint_sha256"]
        if object_fingerprint is None
        else object_fingerprint
    )

    return transition.VisusProtocolAuthorityTransitionRun(
        validation=object(),
        authority_suite=object(),
        output_dir=output_dir,
        transition_path=transition_path,
        transition=transition_value,
        transition_fingerprint_sha256=(fingerprint),
    )


def _patch_transition_validator(
    monkeypatch,
    run,
):
    body = {
        key: value
        for key, value in run.transition.items()
        if key != "transition_fingerprint_sha256"
    }

    monkeypatch.setattr(
        transition,
        "_transition_body",
        lambda *args, **kwargs: copy.deepcopy(body),
    )


def test_transition_validator_type_guard():
    with pytest.raises(
        TypeError,
        match="VisusProtocolAuthorityTransitionRun",
    ):
        transition.validate_visus_protocol_authority_transition(object())


def test_transition_validator_filename_guard(
    tmp_path,
):
    run = _transition_run(
        tmp_path,
        filename="wrong.json",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="filename drifted",
    ):
        transition.validate_visus_protocol_authority_transition(run)


def test_transition_validator_parent_guard(
    tmp_path,
):
    run = _transition_run(
        tmp_path,
    )

    run.output_dir = tmp_path / "different-output"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="outside its output directory",
    ):
        transition.validate_visus_protocol_authority_transition(run)


def test_transition_validator_schema_guard(
    tmp_path,
):
    value = _transition_body_record()
    value["schema"] = "wrong"
    value = _resign_transition(value)

    run = _transition_run(
        tmp_path,
        transition_value=value,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="schema drifted",
    ):
        transition.validate_visus_protocol_authority_transition(run)


def test_transition_validator_status_guard(
    tmp_path,
):
    value = _transition_body_record()
    value["status"] = "wrong"
    value = _resign_transition(value)

    run = _transition_run(
        tmp_path,
        transition_value=value,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="status drifted",
    ):
        transition.validate_visus_protocol_authority_transition(run)


def test_transition_validator_fingerprint_guard(
    tmp_path,
):
    value = _transition_body_record()

    value["transition_fingerprint_sha256"] = "bad"

    run = _transition_run(
        tmp_path,
        transition_value=value,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint does not revalidate",
    ):
        transition.validate_visus_protocol_authority_transition(run)


def test_transition_validator_object_fingerprint_guard(
    tmp_path,
):
    run = _transition_run(
        tmp_path,
        object_fingerprint="9" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="object fingerprint drifted",
    ):
        transition.validate_visus_protocol_authority_transition(run)


def test_transition_validator_file_content_guard(
    tmp_path,
    monkeypatch,
):
    run = _transition_run(
        tmp_path,
    )

    _patch_transition_validator(
        monkeypatch,
        run,
    )

    run.transition_path.write_text(
        '{"different": true}\n',
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file/object content drifted",
    ):
        transition.validate_visus_protocol_authority_transition(run)


@pytest.mark.parametrize(
    "semantics",
    [
        None,
        {
            "original_protocol_validation_preserved": False,
            "authority_binding_applied_to_isolated_suite_clone": True,
            "only_suite_manifest_authority_fields_added": True,
            "child_report_bytes_unchanged": True,
            "authority_execution_provenance_required_separately": True,
        },
    ],
)
def test_transition_validator_semantics_guard(
    tmp_path,
    monkeypatch,
    semantics,
):
    value = _transition_body_record()
    value["transition_semantics"] = semantics
    value = _resign_transition(value)

    run = _transition_run(
        tmp_path,
        transition_value=value,
    )

    _patch_transition_validator(
        monkeypatch,
        run,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="semantics were weakened",
    ):
        transition.validate_visus_protocol_authority_transition(run)


def test_transition_validator_certificate_consumption_guard(
    tmp_path,
    monkeypatch,
):
    value = _transition_body_record()

    value["source_authority_certificate_consumed"] = False

    value = _resign_transition(value)

    run = _transition_run(
        tmp_path,
        transition_value=value,
    )

    _patch_transition_validator(
        monkeypatch,
        run,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lost its certificate-consumption status",
    ):
        transition.validate_visus_protocol_authority_transition(run)


@pytest.mark.parametrize(
    "field",
    [
        "empirical_validation_authorized_by_transition",
        "empirical_performance_claim_created",
        "formal_preregistration_verified",
        "frozen_evidence_created",
        "raw_source_redistribution_action_authorized",
    ],
)
def test_transition_validator_claim_promotion_guards(
    tmp_path,
    monkeypatch,
    field,
):
    value = _transition_body_record()

    value[field] = True

    value = _resign_transition(value)

    run = _transition_run(
        tmp_path,
        transition_value=value,
    )

    _patch_transition_validator(
        monkeypatch,
        run,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=f"cannot promote {field}",
    ):
        transition.validate_visus_protocol_authority_transition(run)


def test_transition_validator_success(
    tmp_path,
    monkeypatch,
):
    run = _transition_run(
        tmp_path,
    )

    _patch_transition_validator(
        monkeypatch,
        run,
    )

    assert transition.validate_visus_protocol_authority_transition(run) is run
