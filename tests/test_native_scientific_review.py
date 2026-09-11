import json

import pytest

from gazeforge import native_scientific_review as review
from gazeforge.exceptions import BenchmarkIntegrityError


def _suite(*, suite_fingerprint: str = "a" * 64) -> dict:
    return {
        "suite": "native-event-validation-v1",
        "status": "complete",
        "report_count": 3,
        "reports": [
            {
                "name": "human_agreement",
                "path": "native-human-agreement.json",
                "report_fingerprint_sha256": "1" * 64,
            },
            {
                "name": "primary_annotator_model",
                "path": "native-primary-model.json",
                "report_fingerprint_sha256": "2" * 64,
            },
            {
                "name": "annotator_sensitivity_model",
                "path": "native-annotator-sensitivity-model.json",
                "report_fingerprint_sha256": "3" * 64,
            },
        ],
        "source": {
            "data_file_name": "native.csv",
            "data_file_sha256": "b" * 64,
            "spec_file_name": "native-spec.json",
            "spec_fingerprint_sha256": "c" * 64,
        },
        "protocol": {"primary_annotator": "A", "sensitivity_annotator": "B"},
        "suite_fingerprint_sha256": suite_fingerprint,
        "reports_verified": True,
        "manifest_path": "native-event-suite-manifest.json",
    }


def test_build_native_review_requires_explicit_manual_decision(monkeypatch, tmp_path):
    monkeypatch.setattr(
        review,
        "validate_native_event_suite_manifest",
        lambda path, verify_reports=True: _suite(),
    )

    record = review.build_native_scientific_review_approval(
        tmp_path,
        reviewer="Scientific Reviewer",
        reviewed_at="2026-09-11T18:30:00Z",
        review_rationale="Reviewed the complete native suite and publication boundary.",
    )

    assert record["schema"] == review.NATIVE_SCIENTIFIC_REVIEW_SCHEMA
    assert record["decision"] == "approved"
    assert record["review_scope"] == review.NATIVE_SCIENTIFIC_REVIEW_SCOPE
    assert record["lineage"]["suite_fingerprint_sha256"] == "a" * 64
    assert record["lineage"]["data_file_sha256"] == "b" * 64
    assert record["lineage"]["spec_fingerprint_sha256"] == "c" * 64
    assert record["lineage"]["report_count"] == 3
    boundary = record["scientific_boundary"]
    assert boundary["scientific_review_completed"] is True
    assert boundary["approved_for_public_frozen_evidence"] is True
    assert boundary["cross_device_generalizability_claim_created"] is False
    assert boundary["gp3_general_validity_claim_created"] is False
    assert boundary["human_reference_ground_truth_promoted"] is False
    assert boundary["source_rights_expanded"] is False
    assert boundary["raw_source_redistribution_authorized"] is False
    assert boundary["universal_performance_validity_claim_created"] is False
    assert len(record["review_fingerprint_sha256"]) == 64


def test_native_review_rejects_non_utc_timestamp(monkeypatch, tmp_path):
    monkeypatch.setattr(
        review,
        "validate_native_event_suite_manifest",
        lambda path, verify_reports=True: _suite(),
    )

    with pytest.raises(BenchmarkIntegrityError, match="explicit UTC offset"):
        review.build_native_scientific_review_approval(
            tmp_path,
            reviewer="Scientific Reviewer",
            reviewed_at="2026-09-11T18:30:00+03:00",
            review_rationale="Reviewed.",
        )


def test_native_review_fails_closed_when_suite_lineage_changes(monkeypatch, tmp_path):
    current = _suite()
    monkeypatch.setattr(
        review,
        "validate_native_event_suite_manifest",
        lambda path, verify_reports=True: current,
    )
    record = review.build_native_scientific_review_approval(
        tmp_path,
        reviewer="Scientific Reviewer",
        reviewed_at="2026-09-11T18:30:00Z",
        review_rationale="Reviewed.",
    )

    changed = _suite(suite_fingerprint="d" * 64)
    with pytest.raises(BenchmarkIntegrityError, match="exact current suite lineage"):
        review.validate_native_scientific_review_record(record, suite=changed)


def test_native_review_rejects_tampering(monkeypatch, tmp_path):
    monkeypatch.setattr(
        review,
        "validate_native_event_suite_manifest",
        lambda path, verify_reports=True: _suite(),
    )
    record = review.build_native_scientific_review_approval(
        tmp_path,
        reviewer="Scientific Reviewer",
        reviewed_at="2026-09-11T18:30:00Z",
        review_rationale="Reviewed.",
    )
    record["review_rationale"] = "Changed after approval."

    with pytest.raises(BenchmarkIntegrityError, match="fingerprint drifted"):
        review.validate_native_scientific_review_record(record, suite=_suite())


def test_write_and_validate_native_review_approval(monkeypatch, tmp_path):
    monkeypatch.setattr(
        review,
        "validate_native_event_suite_manifest",
        lambda path, verify_reports=True: _suite(),
    )

    review_path = review.write_native_scientific_review_approval(
        tmp_path,
        reviewer="Scientific Reviewer",
        reviewed_at="2026-09-11T18:30:00Z",
        review_rationale="Reviewed the complete native suite.",
    )
    assert review_path.name == review.NATIVE_SCIENTIFIC_REVIEW_FILENAME
    payload = json.loads(review_path.read_text(encoding="utf-8"))
    assert review.validate_native_scientific_review_approval(tmp_path) == payload

    with pytest.raises(FileExistsError):
        review.write_native_scientific_review_approval(
            tmp_path,
            reviewer="Scientific Reviewer",
            reviewed_at="2026-09-11T18:30:00Z",
            review_rationale="Reviewed again.",
        )


def test_native_review_requires_review_file(monkeypatch, tmp_path):
    monkeypatch.setattr(
        review,
        "validate_native_event_suite_manifest",
        lambda path, verify_reports=True: _suite(),
    )

    with pytest.raises(BenchmarkIntegrityError, match="requires native-scientific-review"):
        review.validate_native_scientific_review_approval(tmp_path)
