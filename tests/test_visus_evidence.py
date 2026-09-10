import json

import pytest

from gazeforge import visus_evidence
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_authority_binding import AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD


def _touch_manifests(root):
    root.mkdir(parents=True)
    (root / "visus-dynamic-aoi-suite-manifest.json").write_text(
        json.dumps({"placeholder": True}), encoding="utf-8"
    )
    (root / "visus-execution-provenance.json").write_text(
        json.dumps({"placeholder": True}), encoding="utf-8"
    )


def _suite_summary():
    authority = "e" * 64
    return {
        "suite": "visus-dynamic-aoi-validation-v1",
        "status": "complete",
        "report_count": 3,
        "suite_fingerprint_sha256": "a" * 64,
        "source": {
            "source_audit_report_fingerprint_sha256": "b" * 64,
            "source_audit_spec_fingerprint_sha256": "c" * 64,
            "source_manifest_fingerprint_sha256": "d" * 64,
            AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: authority,
        },
        "protocol": {
            "reference_stream_id": "annotator_a",
            "prediction_emission_grid_used": False,
            "human_human_agreement_included": False,
            "source_authority_certificate_bound": True,
            AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: authority,
        },
    }


def _execution_summary():
    return {
        "schema": "gazeforge-visus-execution-provenance-v2",
        "status": "complete",
        "input_count": 5,
        "suite_fingerprint_sha256": "a" * 64,
        "execution_fingerprint_sha256": "f" * 64,
        AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: "e" * 64,
        "authority_certificate_semantics_verified": True,
        "suite_verified": True,
    }


def test_frozen_evidence_bundle_requires_both_manifests(tmp_path):
    root = tmp_path / "bundle"
    root.mkdir()
    (root / "visus-dynamic-aoi-suite-manifest.json").write_text("{}", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="raw-execution provenance"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_bundle_cross_checks_suite_and_authority_execution(
    monkeypatch,
    tmp_path,
):
    root = tmp_path / "bundle"
    _touch_manifests(root)
    monkeypatch.setattr(
        visus_evidence,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda path, verify_reports=True: _suite_summary(),
    )
    monkeypatch.setattr(
        visus_evidence,
        "validate_visus_authority_execution_provenance",
        lambda path, verify_suite=True: _execution_summary(),
    )

    summary = visus_evidence.validate_visus_frozen_evidence_bundle(root)
    assert summary["status"] == "verified-authority-bound-bundle"
    assert summary["bundle"] == "visus-frozen-evidence-v2"
    assert summary["frozen_evidence_eligible_for_scientific_review"] is True
    assert summary["raw_execution_input_count"] == 5
    assert summary["suite_fingerprint_sha256"] == "a" * 64
    assert summary["execution_fingerprint_sha256"] == "f" * 64
    assert summary["protocol"]["prediction_emission_grid_used"] is False
    assert summary["source"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] == "e" * 64

    typed = visus_evidence.load_visus_frozen_evidence_bundle(
        root / "visus-execution-provenance.json"
    )
    assert typed.root == root
    assert typed.report_count == 3
    assert typed.source_manifest_fingerprint_sha256 == "d" * 64
    assert typed.source_authority_certificate_fingerprint_sha256 == "e" * 64


def test_frozen_evidence_bundle_rejects_cross_manifest_mismatch(monkeypatch, tmp_path):
    root = tmp_path / "bundle"
    _touch_manifests(root)
    execution = _execution_summary()
    execution["suite_fingerprint_sha256"] = "0" * 64
    monkeypatch.setattr(
        visus_evidence,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda path, verify_reports=True: _suite_summary(),
    )
    monkeypatch.setattr(
        visus_evidence,
        "validate_visus_authority_execution_provenance",
        lambda path, verify_suite=True: execution,
    )

    with pytest.raises(BenchmarkIntegrityError, match="fingerprints disagree"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_bundle_rejects_legacy_four_raw_inputs(monkeypatch, tmp_path):
    root = tmp_path / "bundle"
    _touch_manifests(root)
    execution = _execution_summary()
    execution["input_count"] = 4
    monkeypatch.setattr(
        visus_evidence,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda path, verify_reports=True: _suite_summary(),
    )
    monkeypatch.setattr(
        visus_evidence,
        "validate_visus_authority_execution_provenance",
        lambda path, verify_suite=True: execution,
    )

    with pytest.raises(BenchmarkIntegrityError, match="exactly five raw inputs"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_bundle_rejects_missing_suite_authority_binding(monkeypatch, tmp_path):
    root = tmp_path / "bundle"
    _touch_manifests(root)
    suite = _suite_summary()
    suite["protocol"]["source_authority_certificate_bound"] = False
    monkeypatch.setattr(
        visus_evidence,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda path, verify_reports=True: suite,
    )
    monkeypatch.setattr(
        visus_evidence,
        "validate_visus_authority_execution_provenance",
        lambda path, verify_suite=True: _execution_summary(),
    )

    with pytest.raises(BenchmarkIntegrityError, match="not sealed"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_bundle_rejects_authority_fingerprint_mismatch(monkeypatch, tmp_path):
    root = tmp_path / "bundle"
    _touch_manifests(root)
    execution = _execution_summary()
    execution[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = "0" * 64
    monkeypatch.setattr(
        visus_evidence,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda path, verify_reports=True: _suite_summary(),
    )
    monkeypatch.setattr(
        visus_evidence,
        "validate_visus_authority_execution_provenance",
        lambda path, verify_suite=True: execution,
    )

    with pytest.raises(BenchmarkIntegrityError, match="authority fingerprints disagree"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_bundle_rejects_unverified_certificate_semantics(monkeypatch, tmp_path):
    root = tmp_path / "bundle"
    _touch_manifests(root)
    execution = _execution_summary()
    execution["authority_certificate_semantics_verified"] = False
    monkeypatch.setattr(
        visus_evidence,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda path, verify_reports=True: _suite_summary(),
    )
    monkeypatch.setattr(
        visus_evidence,
        "validate_visus_authority_execution_provenance",
        lambda path, verify_suite=True: execution,
    )

    with pytest.raises(BenchmarkIntegrityError, match="did not revalidate"):
        visus_evidence.validate_visus_frozen_evidence_bundle(root)


def test_frozen_evidence_bundle_rejects_unrelated_file_path(tmp_path):
    unrelated = tmp_path / "something.json"
    unrelated.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="suite directory"):
        visus_evidence.validate_visus_frozen_evidence_bundle(unrelated)
