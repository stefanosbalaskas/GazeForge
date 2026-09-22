from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

import gazeforge.visus_authority_binding as binding
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_audit import (
    VisusSourceAuditRun,
    audit_visus_source,
)
from gazeforge.visus_authority_binding import (
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
    AUTHORITY_CERTIFICATE_RECORD_FIELD,
)

from _visus_authority_fixture import (
    build_visus_authority_certificate,
    build_visus_authority_spec,
    write_visus_authority_certificate,
)


@pytest.fixture(scope="module")
def baseline(tmp_path_factory):
    root = tmp_path_factory.mktemp("visus-authority-binding-coverage")

    source = root / "source"
    spec = build_visus_authority_spec(source)
    certificate = build_visus_authority_certificate(spec)

    certificate_path = write_visus_authority_certificate(
        root / "visus-source-authority-certificate.json",
        certificate,
    )

    unbound = audit_visus_source(
        source,
        spec,
    )

    bound = binding.audit_visus_source_with_authority(
        source,
        spec,
        certificate,
    )

    return {
        "root": root,
        "source": source,
        "spec": spec,
        "certificate": certificate,
        "certificate_path": certificate_path,
        "unbound": unbound,
        "bound": bound,
    }


def _resign_audit(
    audit: VisusSourceAuditRun,
) -> None:
    body = {key: value for key, value in audit.report.items() if key != "report_fingerprint_sha256"}

    audit.report["report_fingerprint_sha256"] = benchmark_fingerprint(body)


def _identity_certificate_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        binding,
        "validate_certificate_record",
        lambda certificate: copy.deepcopy(dict(certificate)),
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
    assert binding._valid_sha256(value) is expected


def test_load_certificate_success(
    baseline,
) -> None:
    loaded = binding.load_visus_source_authority_certificate(baseline["certificate_path"])

    assert loaded == baseline["certificate"]


def test_load_certificate_missing_guard(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-symlink regular file",
    ):
        binding.load_visus_source_authority_certificate(tmp_path / "missing.json")


def test_load_certificate_symlink_guard_portable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "certificate.json"

    path.write_text(
        "{}",
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
        match="non-symlink regular file",
    ):
        binding.load_visus_source_authority_certificate(path)


def test_load_certificate_empty_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "certificate.json"
    path.write_bytes(b"")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="size is outside",
    ):
        binding.load_visus_source_authority_certificate(path)


def test_load_certificate_size_bound(
    tmp_path: Path,
) -> None:
    path = tmp_path / "certificate.json"

    path.write_bytes(b"x" * (binding._MAX_CERTIFICATE_BYTES + 1))

    with pytest.raises(
        BenchmarkIntegrityError,
        match="size is outside",
    ):
        binding.load_visus_source_authority_certificate(path)


def test_load_certificate_invalid_json_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "certificate.json"

    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        binding.load_visus_source_authority_certificate(path)


def test_load_certificate_invalid_utf8_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "certificate.json"
    path.write_bytes(b"\xff\xfe")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        binding.load_visus_source_authority_certificate(path)


def test_load_certificate_requires_object(
    tmp_path: Path,
) -> None:
    path = tmp_path / "certificate.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        binding.load_visus_source_authority_certificate(path)


def test_verify_structural_audit_type_guard() -> None:
    with pytest.raises(
        TypeError,
        match="VisusSourceAuditRun",
    ):
        binding._verify_structural_audit(object())


def test_verify_structural_audit_status_guard(
    baseline,
) -> None:
    audit = copy.deepcopy(baseline["unbound"])

    audit.report["status"] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="verified source audit",
    ):
        binding._verify_structural_audit(audit)


def test_verify_structural_audit_report_fingerprint_guard(
    baseline,
) -> None:
    audit = copy.deepcopy(baseline["unbound"])

    audit.report["report_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="invalid source-audit report fingerprint",
    ):
        binding._verify_structural_audit(audit)


def test_verify_structural_audit_spec_fingerprint_guard(
    baseline,
) -> None:
    audit = copy.deepcopy(baseline["unbound"])

    audit.report["spec_fingerprint_sha256"] = "0" * 64

    _resign_audit(audit)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="invalid source-audit spec fingerprint",
    ):
        binding._verify_structural_audit(audit)


def test_verify_structural_audit_success(
    baseline,
) -> None:
    binding._verify_structural_audit(baseline["unbound"])


def test_neutral_inventory_fingerprint_success(
    baseline,
) -> None:
    fingerprint = binding._neutral_inventory_fingerprint(baseline["unbound"])

    assert binding._valid_sha256(fingerprint)


def test_neutral_inventory_fingerprint_empty_guard(
    baseline,
) -> None:
    audit = VisusSourceAuditRun(
        spec=baseline["unbound"].spec,
        files=[],
        report=copy.deepcopy(baseline["unbound"].report),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-empty source tree",
    ):
        binding._neutral_inventory_fingerprint(audit)


@pytest.mark.parametrize(
    ("case", "match"),
    [
        (
            "source",
            "source does not match",
        ),
        (
            "revision",
            "revision does not match",
        ),
        (
            "license",
            "licence/terms identifier",
        ),
        (
            "reuse_source",
            "reuse-terms source",
        ),
        (
            "reuse_verified",
            "verified reuse terms",
        ),
        (
            "analysis_permission",
            "verified reuse terms",
        ),
        (
            "redistribution",
            "redistribution status",
        ),
        (
            "file_count",
            "file count",
        ),
        (
            "inventory_fingerprint",
            "exact audited source-tree inventory",
        ),
        (
            "participant_count",
            "participant-count boundary",
        ),
        (
            "stimulus_count",
            "stimulus-count boundary",
        ),
        (
            "audit_authorized",
            "does not authorize entry",
        ),
    ],
)
def test_validate_binding_contract_guards(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    match: str,
) -> None:
    _identity_certificate_validator(monkeypatch)

    audit = copy.deepcopy(baseline["unbound"])

    certificate = copy.deepcopy(baseline["certificate"])

    if case == "source":
        certificate["source"]["source_reference"] = "wrong"

    elif case == "revision":
        certificate["source"]["source_revision"] = "wrong"

    elif case == "license":
        certificate["rights"]["license_or_terms_identifier"] = "wrong"

    elif case == "reuse_source":
        certificate["rights"]["evidence_reference"] = "wrong"

    elif case == "reuse_verified":
        audit.spec.reuse_terms_verified = False

    elif case == "analysis_permission":
        audit.spec.analysis_use_permitted = False

    elif case == "redistribution":
        certificate["rights"]["redistribution_status"] = "wrong"

    elif case == "file_count":
        certificate["inventory"]["file_count"] += 1

    elif case == "inventory_fingerprint":
        certificate["inventory"]["fingerprint_sha256"] = "f" * 64

    elif case == "participant_count":
        certificate["inventory"]["published_participant_count"] += 1

    elif case == "stimulus_count":
        certificate["inventory"]["published_stimulus_count"] += 1

    elif case == "audit_authorized":
        certificate["authority_boundary"]["source_audit_stage_authorized"] = False

    if case in {
        "reuse_verified",
        "analysis_permission",
    }:
        audit.report["spec_fingerprint_sha256"] = benchmark_fingerprint(audit.spec.to_dict())

        _resign_audit(audit)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        binding.validate_visus_source_authority_binding(
            audit,
            certificate,
        )


def test_validate_binding_success(
    baseline,
) -> None:
    result = binding.validate_visus_source_authority_binding(
        baseline["unbound"],
        baseline["certificate"],
    )

    assert result["source_authority_verified"] is True

    assert result["analysis_use_permitted"] is True

    assert result["empirical_validation_authorized"] is False

    assert result["raw_source_redistribution_action_authorized"] is False

    assert result[AUTHORITY_CERTIFICATE_RECORD_FIELD] == baseline["certificate"]


def test_authority_section_unbound_optional(
    baseline,
) -> None:
    assert (
        binding._authority_section(
            baseline["unbound"],
            required=False,
        )
        is None
    )


def test_authority_section_unbound_required(
    baseline,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires an authority-bound source audit",
    ):
        binding._authority_section(
            baseline["unbound"],
            required=True,
        )


def test_authority_section_malformed_guard(
    baseline,
) -> None:
    audit = copy.deepcopy(baseline["bound"])

    audit.report[binding._AUTHORITY_SECTION] = None

    _resign_audit(audit)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="authority binding is malformed",
    ):
        binding._authority_section(
            audit,
            required=True,
        )


def test_authority_section_invalid_top_level_fingerprint(
    baseline,
) -> None:
    audit = copy.deepcopy(baseline["bound"])

    audit.report[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = "BAD"

    _resign_audit(audit)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint is invalid",
    ):
        binding._authority_section(
            audit,
            required=True,
        )


def test_authority_section_inconsistent_fingerprint(
    baseline,
) -> None:
    audit = copy.deepcopy(baseline["bound"])

    audit.report[binding._AUTHORITY_SECTION]["certificate_fingerprint_sha256"] = "f" * 64

    _resign_audit(audit)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint is inconsistent",
    ):
        binding._authority_section(
            audit,
            required=True,
        )


def test_authority_section_success(
    baseline,
) -> None:
    section = binding._authority_section(
        baseline["bound"],
        required=True,
    )

    assert section is not None


def test_certificate_record_unbound_optional(
    baseline,
) -> None:
    assert (
        binding.source_authority_certificate_record(
            baseline["unbound"],
            required=False,
        )
        is None
    )


def test_certificate_record_missing_guard(
    baseline,
) -> None:
    audit = copy.deepcopy(baseline["bound"])

    del audit.report[binding._AUTHORITY_SECTION][AUTHORITY_CERTIFICATE_RECORD_FIELD]

    _resign_audit(audit)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing the reviewed certificate record",
    ):
        binding.source_authority_certificate_record(
            audit,
            required=True,
        )


def test_certificate_record_fingerprint_mismatch(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    certificate = copy.deepcopy(baseline["certificate"])

    certificate["certificate_fingerprint_sha256"] = "f" * 64

    monkeypatch.setattr(
        binding,
        "validate_certificate_record",
        lambda record: certificate,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="does not match the source-audit fingerprint",
    ):
        binding.source_authority_certificate_record(
            baseline["bound"],
            required=True,
        )


@pytest.mark.parametrize(
    "field",
    [
        "candidate_fingerprint_sha256",
        "review_fingerprint_sha256",
        "source_artifact_sha256",
        "rights_evidence_sha256",
        "neutral_inventory_fingerprint_sha256",
        "redistribution_status",
    ],
)
def test_certificate_record_summary_drift_guards(
    baseline,
    field: str,
) -> None:
    audit = copy.deepcopy(baseline["bound"])

    section = audit.report[binding._AUTHORITY_SECTION]

    current = section[field]

    if isinstance(current, str):
        section[field] = "different" if len(current) != 64 else "f" * 64
    else:
        section[field] = "different"

    _resign_audit(audit)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="summary drifted",
    ):
        binding.source_authority_certificate_record(
            audit,
            required=True,
        )


def test_certificate_record_success(
    baseline,
) -> None:
    certificate = binding.source_authority_certificate_record(
        baseline["bound"],
        required=True,
    )

    assert certificate == baseline["certificate"]


def test_certificate_fingerprint_unbound_optional(
    baseline,
) -> None:
    assert (
        binding.source_authority_certificate_fingerprint(
            baseline["unbound"],
            required=False,
        )
        is None
    )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "source_audit_stage_authorized",
            False,
            "authority-stage authorization drifted",
        ),
        (
            "empirical_validation_authorized",
            True,
            "cannot itself authorize empirical validation",
        ),
        (
            "raw_source_redistribution_action_authorized",
            True,
            "cannot authorize raw-source redistribution",
        ),
    ],
)
def test_certificate_fingerprint_boundary_guards(
    baseline,
    field: str,
    value: bool,
    match: str,
) -> None:
    audit = copy.deepcopy(baseline["bound"])

    audit.report[binding._AUTHORITY_SECTION][field] = value

    _resign_audit(audit)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        binding.source_authority_certificate_fingerprint(
            audit,
            required=True,
        )


def test_certificate_fingerprint_success(
    baseline,
) -> None:
    result = binding.source_authority_certificate_fingerprint(
        baseline["bound"],
        required=True,
    )

    assert result == baseline["certificate"]["certificate_fingerprint_sha256"]


def test_audit_with_authority_already_bound_guard(
    baseline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        binding,
        "audit_visus_source",
        lambda root, spec: copy.deepcopy(baseline["bound"]),
    )

    monkeypatch.setattr(
        binding,
        "validate_visus_source_authority_binding",
        lambda audit, certificate: copy.deepcopy(
            baseline["bound"].report[binding._AUTHORITY_SECTION]
        ),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="already authority-bound",
    ):
        binding.audit_visus_source_with_authority(
            baseline["source"],
            baseline["spec"],
            baseline["certificate"],
        )


def test_audit_with_authority_success(
    baseline,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"

    spec = build_visus_authority_spec(source)

    certificate = build_visus_authority_certificate(spec)

    audit = binding.audit_visus_source_with_authority(
        source,
        spec,
        certificate,
    )

    assert (
        audit.report[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD]
        == certificate["certificate_fingerprint_sha256"]
    )

    assert (
        binding.source_authority_certificate_fingerprint(
            audit,
            required=True,
        )
        == certificate["certificate_fingerprint_sha256"]
    )
