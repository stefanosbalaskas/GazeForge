import json

import pandas as pd
import pytest

from gazeforge import dashboard
from gazeforge import visus_scientific_review as review
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_authority_binding import AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD


def _bundle():
    return {
        "bundle": "visus-frozen-evidence-v3",
        "status": "verified-protocol-authority-bound-bundle",
        "frozen_evidence_eligible_for_scientific_review": True,
        "scientific_review_completed": False,
        "empirical_performance_claim_created": False,
        "formal_preregistration_verified": False,
        "protocol_bound_lineage_verified": True,
        "suite_fingerprint_sha256": "a" * 64,
        "pre_authority_suite_fingerprint_sha256": "b" * 64,
        "execution_fingerprint_sha256": "c" * 64,
        "transition_fingerprint_sha256": "d" * 64,
        "protocol_validation_binding_fingerprint_sha256": "e" * 64,
        "protocol_fingerprint_sha256": "1" * 64,
        "protocol_batch_fingerprint_sha256": "2" * 64,
        "report_count": 3,
        "raw_execution_input_count": 5,
        "source": {
            AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD: "3" * 64,
        },
    }


def _suite():
    return {
        "suite": "visus-dynamic-aoi-validation-v1",
        "status": "complete",
        "report_count": 3,
        "suite_fingerprint_sha256": "a" * 64,
        "source": {"source_manifest_fingerprint_sha256": "4" * 64},
        "protocol": {
            "reference_stream_id": "annotator_a",
            "human_human_agreement_included": False,
        },
    }


def _mock_bundle(monkeypatch, payload=None):
    value = _bundle() if payload is None else payload
    monkeypatch.setattr(
        review,
        "validate_visus_frozen_evidence_bundle",
        lambda path, protocol_validation_binding_path=None: value,
    )


def _resign(record):
    body = {key: value for key, value in record.items() if key != "review_fingerprint_sha256"}
    record["review_fingerprint_sha256"] = benchmark_fingerprint(body)
    return record


def test_scientific_review_builds_explicit_closed_schema_approval(monkeypatch, tmp_path):
    _mock_bundle(monkeypatch)

    record = review.build_visus_scientific_review_approval(
        tmp_path,
        reviewer="Scientific Reviewer",
        reviewed_at="2026-09-11T18:30:00Z",
        review_rationale="Reviewed the exact frozen lineage and approved public indexing.",
    )

    assert record["schema"] == review.SCIENTIFIC_REVIEW_SCHEMA
    assert record["status"] == review.SCIENTIFIC_REVIEW_STATUS
    assert record["decision"] == "approved"
    assert record["review_scope"] == review.SCIENTIFIC_REVIEW_SCOPE
    assert record["lineage"]["suite_fingerprint_sha256"] == "a" * 64
    assert record["scientific_boundary"]["scientific_review_completed"] is True
    assert record["scientific_boundary"]["approved_for_public_frozen_evidence"] is True
    for field in review._FALSE_BOUNDARY_KEYS:
        assert record["scientific_boundary"][field] is False


def test_scientific_review_requires_explicit_utc_timestamp(monkeypatch, tmp_path):
    _mock_bundle(monkeypatch)

    with pytest.raises(BenchmarkIntegrityError, match="explicit UTC offset"):
        review.build_visus_scientific_review_approval(
            tmp_path,
            reviewer="Scientific Reviewer",
            reviewed_at="2026-09-11T18:30:00+03:00",
            review_rationale="Reviewed.",
        )


def test_scientific_review_refuses_noneligible_v3_bundle(monkeypatch, tmp_path):
    bundle = _bundle()
    bundle["frozen_evidence_eligible_for_scientific_review"] = False
    _mock_bundle(monkeypatch, bundle)

    with pytest.raises(BenchmarkIntegrityError, match="not review-eligible"):
        review.build_visus_scientific_review_approval(
            tmp_path,
            reviewer="Scientific Reviewer",
            reviewed_at="2026-09-11T18:30:00Z",
            review_rationale="Reviewed.",
        )


def test_scientific_review_write_and_reload_revalidates_exact_lineage(monkeypatch, tmp_path):
    _mock_bundle(monkeypatch)

    path = review.write_visus_scientific_review_approval(
        tmp_path,
        reviewer="Scientific Reviewer",
        reviewed_at="2026-09-11T18:30:00+00:00",
        review_rationale="Exact lineage reviewed for public Frozen Evidence indexing.",
    )
    validated = review.validate_visus_scientific_review_approval(tmp_path)

    assert path == tmp_path / review.SCIENTIFIC_REVIEW_FILENAME
    assert validated["review_fingerprint_sha256"]
    assert validated["lineage"]["raw_execution_input_count"] == 5


def test_scientific_review_missing_file_fails_closed(monkeypatch, tmp_path):
    _mock_bundle(monkeypatch)

    with pytest.raises(BenchmarkIntegrityError, match="requires visus-scientific-review.json"):
        review.validate_visus_scientific_review_approval(tmp_path)


def test_scientific_review_rejects_resigned_claim_promotion(monkeypatch, tmp_path):
    _mock_bundle(monkeypatch)
    record = review.build_visus_scientific_review_approval(
        tmp_path,
        reviewer="Scientific Reviewer",
        reviewed_at="2026-09-11T18:30:00Z",
        review_rationale="Reviewed.",
    )
    record["scientific_boundary"]["empirical_performance_claim_created"] = True
    _resign(record)
    (tmp_path / review.SCIENTIFIC_REVIEW_FILENAME).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="cannot promote"):
        review.validate_visus_scientific_review_approval(tmp_path)


def test_scientific_review_rejects_resigned_lineage_drift(monkeypatch, tmp_path):
    _mock_bundle(monkeypatch)
    record = review.build_visus_scientific_review_approval(
        tmp_path,
        reviewer="Scientific Reviewer",
        reviewed_at="2026-09-11T18:30:00Z",
        review_rationale="Reviewed.",
    )
    record["lineage"]["suite_fingerprint_sha256"] = "f" * 64
    _resign(record)
    (tmp_path / review.SCIENTIFIC_REVIEW_FILENAME).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="exact current v3 evidence lineage"):
        review.validate_visus_scientific_review_approval(tmp_path)


def test_scientific_review_write_protects_existing_approval(monkeypatch, tmp_path):
    _mock_bundle(monkeypatch)
    review.write_visus_scientific_review_approval(
        tmp_path,
        reviewer="Scientific Reviewer",
        reviewed_at="2026-09-11T18:30:00Z",
        review_rationale="Reviewed.",
    )

    with pytest.raises(FileExistsError):
        review.write_visus_scientific_review_approval(
            tmp_path,
            reviewer="Scientific Reviewer",
            reviewed_at="2026-09-11T18:31:00Z",
            review_rationale="Second review.",
        )


def test_dashboard_requires_separate_scientific_review_approval(monkeypatch, tmp_path):
    suite_path = tmp_path / "visus-dynamic-aoi-suite-manifest.json"
    suite_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        dashboard,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda path, verify_reports=True: _suite(),
    )
    monkeypatch.setattr(
        dashboard,
        "validate_visus_scientific_review_approval",
        lambda path: (_ for _ in ()).throw(
            BenchmarkIntegrityError("VISUS public Frozen Evidence requires review approval.")
        ),
    )

    with pytest.raises(BenchmarkIntegrityError, match="requires review approval"):
        dashboard._validate_visus_suite_for_dashboard(suite_path)


def test_dashboard_accepts_only_approval_bound_to_exact_suite(monkeypatch, tmp_path):
    suite_path = tmp_path / "visus-dynamic-aoi-suite-manifest.json"
    suite_path.write_text("{}\n", encoding="utf-8")
    approval = {
        "reviewer": "Scientific Reviewer",
        "reviewed_at": "2026-09-11T18:30:00Z",
        "review_scope": review.SCIENTIFIC_REVIEW_SCOPE,
        "review_fingerprint_sha256": "5" * 64,
        "lineage": {
            "suite_fingerprint_sha256": "a" * 64,
            "report_count": 3,
        },
        "scientific_boundary": {
            "scientific_review_completed": True,
            "approved_for_public_frozen_evidence": True,
        },
    }
    monkeypatch.setattr(
        dashboard,
        "validate_visus_dynamic_aoi_suite_manifest",
        lambda path, verify_reports=True: _suite(),
    )
    monkeypatch.setattr(
        dashboard,
        "validate_visus_scientific_review_approval",
        lambda path: approval,
    )

    validated = dashboard._validate_visus_suite_for_dashboard(suite_path)
    assert validated["scientific_review"] == {
        "reviewer": "Scientific Reviewer",
        "reviewed_at": "2026-09-11T18:30:00Z",
        "review_scope": review.SCIENTIFIC_REVIEW_SCOPE,
        "review_fingerprint_sha256": "5" * 64,
    }

    row = dashboard._suite_row(validated, str(suite_path))
    assert row["scientific_review_reviewer"] == "Scientific Reviewer"
    assert row["scientific_reviewed_at"] == "2026-09-11T18:30:00Z"
    assert row["scientific_review_scope"] == review.SCIENTIFIC_REVIEW_SCOPE
    assert row["scientific_review_fingerprint_sha256"] == "5" * 64

    evidence_dashboard = dashboard.BenchmarkDashboard(
        reports=(),
        table=pd.DataFrame(),
        source_files=(),
        suites=(validated,),
        suite_table=pd.DataFrame([row]),
        suite_source_files=(str(suite_path),),
    )
    markdown = dashboard.render_benchmark_dashboard_markdown(evidence_dashboard)
    assert "Scientific Reviewer" in markdown
    assert "2026-09-11T18:30:00Z" in markdown
    assert review.SCIENTIFIC_REVIEW_SCOPE in markdown
    assert ("5" * 12) in markdown
    assert ("5" * 64) not in markdown

    approval["lineage"]["suite_fingerprint_sha256"] = "f" * 64
    with pytest.raises(BenchmarkIntegrityError, match="fingerprints disagree"):
        dashboard._validate_visus_suite_for_dashboard(suite_path)
