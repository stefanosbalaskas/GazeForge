import copy
import json

import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_audit import audit_visus_source
from gazeforge.visus_authoritative_source_common import certificate_fingerprint
from gazeforge.visus_authority_binding import (
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
    audit_visus_source_with_authority,
    load_visus_source_authority_certificate,
    source_authority_certificate_fingerprint,
    validate_visus_source_authority_binding,
)

from _visus_authority_fixture import (
    build_visus_authority_certificate,
    build_visus_authority_spec,
    write_visus_authority_certificate,
)


def _refingerprint_certificate(certificate):
    value = copy.deepcopy(certificate)
    value["certificate_fingerprint_sha256"] = certificate_fingerprint(value)
    return value


def test_authority_binding_promotes_only_source_authority_into_structural_audit(tmp_path):
    root = tmp_path / "source"
    spec = build_visus_authority_spec(root)
    certificate = build_visus_authority_certificate(spec)

    unbound = audit_visus_source(root, spec)
    with pytest.raises(BenchmarkIntegrityError, match="authority-bound"):
        source_authority_certificate_fingerprint(unbound, required=True)

    bound = audit_visus_source_with_authority(root, spec, certificate)
    fingerprint = source_authority_certificate_fingerprint(bound, required=True)

    assert fingerprint == certificate["certificate_fingerprint_sha256"]
    assert bound.report[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] == fingerprint
    assert bound.report["source_authority"]["source_authority_verified"] is True
    assert bound.report["source_authority"]["empirical_validation_authorized"] is False
    assert bound.report["source_authority"]["raw_source_redistribution_action_authorized"] is False
    assert bound.report["report_fingerprint_sha256"] != unbound.report["report_fingerprint_sha256"]

    body = {
        key: value
        for key, value in bound.report.items()
        if key != "report_fingerprint_sha256"
    }
    assert benchmark_fingerprint(body) == bound.report["report_fingerprint_sha256"]


def test_authority_binding_rejects_source_identity_drift_even_after_refingerprinting(tmp_path):
    root = tmp_path / "source"
    spec = build_visus_authority_spec(root)
    certificate = build_visus_authority_certificate(spec)
    altered = copy.deepcopy(certificate)
    altered["source"]["source_revision"] = "different-revision"
    altered = _refingerprint_certificate(altered)

    audit = audit_visus_source(root, spec)
    with pytest.raises(BenchmarkIntegrityError, match="revision"):
        validate_visus_source_authority_binding(audit, altered)


def test_authority_binding_rejects_exact_inventory_drift_even_after_refingerprinting(tmp_path):
    root = tmp_path / "source"
    spec = build_visus_authority_spec(root)
    certificate = build_visus_authority_certificate(spec)
    altered = copy.deepcopy(certificate)
    altered["inventory"]["fingerprint_sha256"] = "f" * 64
    altered = _refingerprint_certificate(altered)

    audit = audit_visus_source(root, spec)
    with pytest.raises(BenchmarkIntegrityError, match="exact audited source-tree inventory"):
        validate_visus_source_authority_binding(audit, altered)


def test_authority_binding_rejects_rights_scope_drift_even_after_refingerprinting(tmp_path):
    root = tmp_path / "source"
    spec = build_visus_authority_spec(root)
    certificate = build_visus_authority_certificate(spec)
    altered = copy.deepcopy(certificate)
    altered["rights"]["redistribution_status"] = "not_stated"
    altered = _refingerprint_certificate(altered)

    audit = audit_visus_source(root, spec)
    with pytest.raises(BenchmarkIntegrityError, match="redistribution status"):
        validate_visus_source_authority_binding(audit, altered)


def test_authority_binding_rejects_certificate_scientific_promotion(tmp_path):
    root = tmp_path / "source"
    spec = build_visus_authority_spec(root)
    certificate = build_visus_authority_certificate(spec)
    altered = copy.deepcopy(certificate)
    altered["scientific_boundary"]["model_human_validation_created"] = True
    altered = _refingerprint_certificate(altered)

    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        audit_visus_source_with_authority(root, spec, altered)


def test_authority_certificate_loader_revalidates_exact_json(tmp_path):
    root = tmp_path / "source"
    spec = build_visus_authority_spec(root)
    certificate = build_visus_authority_certificate(spec)
    path = write_visus_authority_certificate(
        tmp_path / "visus-source-authority-certificate.json",
        certificate,
    )

    loaded = load_visus_source_authority_certificate(path)
    assert loaded == certificate

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["rights"]["analysis_use_permitted"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError):
        load_visus_source_authority_certificate(path)
