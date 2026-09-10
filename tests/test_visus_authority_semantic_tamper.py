import copy
import json

import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_authoritative_source_common import certificate_fingerprint
from gazeforge.visus_authority_binding import (
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
    audit_visus_source_with_authority,
    source_authority_certificate_fingerprint,
)
from gazeforge.visus_authority_execution_strict import (
    AUTHORITY_CERTIFICATE_RECORD_FIELD,
    validate_visus_authority_execution_provenance,
)

from _visus_authority_fixture import (
    build_visus_authority_certificate,
    build_visus_authority_spec,
)


def _promote_and_refingerprint_certificate(certificate):
    value = copy.deepcopy(certificate)
    value["scientific_boundary"]["model_human_validation_created"] = True
    value["certificate_fingerprint_sha256"] = certificate_fingerprint(value)
    return value


def test_rehashed_bound_audit_cannot_hide_promoted_certificate_semantics(tmp_path):
    root = tmp_path / "source"
    spec = build_visus_authority_spec(root)
    certificate = build_visus_authority_certificate(spec)
    audit = audit_visus_source_with_authority(root, spec, certificate)

    promoted = _promote_and_refingerprint_certificate(certificate)
    report = copy.deepcopy(audit.report)
    section = report["source_authority"]
    section["certificate_record"] = promoted
    section["certificate_fingerprint_sha256"] = promoted[
        "certificate_fingerprint_sha256"
    ]
    report[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = promoted[
        "certificate_fingerprint_sha256"
    ]
    body = {
        key: value
        for key, value in report.items()
        if key != "report_fingerprint_sha256"
    }
    report["report_fingerprint_sha256"] = benchmark_fingerprint(body)
    audit.report = report

    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        source_authority_certificate_fingerprint(audit, required=True)


def test_rehashed_execution_manifest_cannot_hide_promoted_certificate_semantics(tmp_path):
    root = tmp_path / "source"
    spec = build_visus_authority_spec(root)
    certificate = build_visus_authority_certificate(spec)
    promoted = _promote_and_refingerprint_certificate(certificate)

    body = {
        "schema": "gazeforge-visus-execution-provenance-v2",
        "status": "complete",
        "provenance_scope": "exact-authority-and-raw-input-files-to-frozen-visus-suite",
        AUTHORITY_CERTIFICATE_RECORD_FIELD: promoted,
    }
    manifest = {
        **body,
        "execution_fingerprint_sha256": benchmark_fingerprint(body),
    }
    path = tmp_path / "visus-execution-provenance.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_visus_authority_execution_provenance(path, verify_suite=False)
