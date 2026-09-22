from __future__ import annotations

import json

import pytest
from test_visus_scientific_review import _bundle

from gazeforge import visus_scientific_review as review
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_authority_binding import (
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
)


def _mock_bundle(
    monkeypatch,
    bundle=None,
):
    value = _bundle() if bundle is None else bundle

    monkeypatch.setattr(
        review,
        "validate_visus_frozen_evidence_bundle",
        lambda path, protocol_validation_binding_path=None: value,
    )

    return value


def _valid_record(
    monkeypatch,
    tmp_path,
    *,
    bundle=None,
):
    value = _mock_bundle(
        monkeypatch,
        bundle,
    )

    record = review.build_visus_scientific_review_approval(
        tmp_path,
        reviewer="Scientific Reviewer",
        reviewed_at="2026-09-11T18:30:00Z",
        review_rationale=("Reviewed exact lineage for public Frozen Evidence."),
    )

    return record, value


def _resign(
    record,
):
    body = {key: value for key, value in record.items() if key != "review_fingerprint_sha256"}

    record["review_fingerprint_sha256"] = benchmark_fingerprint(body)

    return record


# ============================================================
# CLOSED-SCHEMA CONTRACT
# ============================================================


def test_exact_keys_reports_missing_and_extra():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="schema drifted",
    ) as exc:
        review._require_exact_keys(
            {
                "present": 1,
                "unexpected": 2,
            },
            frozenset(
                {
                    "present",
                    "required",
                }
            ),
            label="fixture",
        )

    message = str(exc.value)

    assert "required" in message
    assert "unexpected" in message


# ============================================================
# SHA-256 CONTRACT
# ============================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, False),
        (123, False),
        ("a" * 63, False),
        ("g" * 64, False),
        ("A" * 64, False),
        ("a" * 64, True),
    ],
)
def test_valid_sha256_contract(
    value,
    expected,
):
    assert review._valid_sha256(value) is expected


# ============================================================
# TEXT CONTRACTS
# ============================================================


def test_required_text_rejects_non_text():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be text",
    ):
        review._required_text(
            123,
            label="fixture",
        )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
    ],
)
def test_required_text_rejects_empty(
    value,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be non-empty",
    ):
        review._required_text(
            value,
            label="fixture",
        )


def test_required_text_rejects_excessive_length():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="too long",
    ):
        review._required_text(
            "x" * (review._MAX_TEXT_LENGTH + 1),
            label="fixture",
        )


# ============================================================
# UTC TIMESTAMP CONTRACT
# ============================================================


def test_utc_timestamp_rejects_invalid_iso_value():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="ISO-8601 timestamp",
    ):
        review._utc_timestamp("definitely-not-a-timestamp")


# ============================================================
# REVIEW PATH RESOLUTION
# ============================================================


def test_review_root_accepts_direct_review_filename(
    tmp_path,
):
    path = tmp_path / review.SCIENTIFIC_REVIEW_FILENAME

    root, resolved = review._review_root(path)

    assert root == tmp_path
    assert resolved == path


# ============================================================
# BUNDLE LINEAGE
# ============================================================


def test_bundle_lineage_requires_source_mapping():
    bundle = _bundle()
    bundle["source"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source identity is invalid",
    ):
        review._bundle_lineage(bundle)


@pytest.mark.parametrize(
    "authority",
    [
        None,
        "bad",
        "G" * 64,
        "A" * 64,
    ],
)
def test_bundle_lineage_requires_valid_authority_fingerprint(
    authority,
):
    bundle = _bundle()

    bundle["source"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] = authority

    with pytest.raises(
        BenchmarkIntegrityError,
        match="authority-certificate fingerprint is invalid",
    ):
        review._bundle_lineage(bundle)


# ============================================================
# BUILD-TIME SCIENTIFIC BOUNDARY GUARDS
# ============================================================


def test_build_rejects_self_promoted_review_completion(
    monkeypatch,
    tmp_path,
):
    bundle = _bundle()

    bundle["scientific_review_completed"] = True

    _mock_bundle(
        monkeypatch,
        bundle,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-promoted scientific review completion",
    ):
        review.build_visus_scientific_review_approval(
            tmp_path,
            reviewer="Scientific Reviewer",
            reviewed_at="2026-09-11T18:30:00Z",
            review_rationale="Reviewed.",
        )


def test_build_rejects_preexisting_empirical_claim(
    monkeypatch,
    tmp_path,
):
    bundle = _bundle()

    bundle["empirical_performance_claim_created"] = True

    _mock_bundle(
        monkeypatch,
        bundle,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="promoted an empirical-performance claim",
    ):
        review.build_visus_scientific_review_approval(
            tmp_path,
            reviewer="Scientific Reviewer",
            reviewed_at="2026-09-11T18:30:00Z",
            review_rationale="Reviewed.",
        )


def test_build_rejects_preexisting_preregistration_promotion(
    monkeypatch,
    tmp_path,
):
    bundle = _bundle()

    bundle["formal_preregistration_verified"] = True

    _mock_bundle(
        monkeypatch,
        bundle,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="promoted formal preregistration",
    ):
        review.build_visus_scientific_review_approval(
            tmp_path,
            reviewer="Scientific Reviewer",
            reviewed_at="2026-09-11T18:30:00Z",
            review_rationale="Reviewed.",
        )


# ============================================================
# TOP-LEVEL REVIEW RECORD GUARDS
# ============================================================


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "schema",
            "wrong-schema",
            "schema is invalid",
        ),
        (
            "status",
            "wrong-status",
            "status is invalid",
        ),
        (
            "decision",
            "rejected",
            "requires decision='approved'",
        ),
        (
            "review_scope",
            "wrong-scope",
            "scope drifted",
        ),
    ],
)
def test_record_top_level_guards(
    monkeypatch,
    tmp_path,
    field,
    value,
    message,
):
    record, bundle = _valid_record(
        monkeypatch,
        tmp_path,
    )

    record[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        review.validate_visus_scientific_review_record(
            record,
            bundle=bundle,
        )


# ============================================================
# SECTION SHAPE GUARDS
# ============================================================


@pytest.mark.parametrize(
    "field",
    [
        "lineage",
        "scientific_boundary",
    ],
)
def test_record_requires_lineage_and_boundary_sections(
    monkeypatch,
    tmp_path,
    field,
):
    record, bundle = _valid_record(
        monkeypatch,
        tmp_path,
    )

    record[field] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sections are missing",
    ):
        review.validate_visus_scientific_review_record(
            record,
            bundle=bundle,
        )


# ============================================================
# LINEAGE BOOLEAN GUARDS
# ============================================================


def test_record_requires_verified_protocol_lineage(
    monkeypatch,
    tmp_path,
):
    record, bundle = _valid_record(
        monkeypatch,
        tmp_path,
    )

    bundle["protocol_bound_lineage_verified"] = False

    record["lineage"]["protocol_bound_lineage_verified"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires verified protocol-bound lineage",
    ):
        review.validate_visus_scientific_review_record(
            record,
            bundle=bundle,
        )


def test_record_requires_scientific_review_eligibility(
    monkeypatch,
    tmp_path,
):
    record, bundle = _valid_record(
        monkeypatch,
        tmp_path,
    )

    bundle["frozen_evidence_eligible_for_scientific_review"] = False

    record["lineage"]["frozen_evidence_eligible_for_scientific_review"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires v3 scientific-review eligibility",
    ):
        review.validate_visus_scientific_review_record(
            record,
            bundle=bundle,
        )


# ============================================================
# LINEAGE FINGERPRINT GUARD
# ============================================================


@pytest.mark.parametrize(
    "field",
    [
        "suite_fingerprint_sha256",
        "pre_authority_suite_fingerprint_sha256",
        "execution_fingerprint_sha256",
        "transition_fingerprint_sha256",
        "protocol_validation_binding_fingerprint_sha256",
        "protocol_fingerprint_sha256",
        "protocol_batch_fingerprint_sha256",
    ],
)
def test_record_rejects_invalid_lineage_fingerprints(
    monkeypatch,
    tmp_path,
    field,
):
    record, bundle = _valid_record(
        monkeypatch,
        tmp_path,
    )

    bundle[field] = "bad"

    record["lineage"][field] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lineage fingerprint",
    ):
        review.validate_visus_scientific_review_record(
            record,
            bundle=bundle,
        )


# ============================================================
# LINEAGE CARDINALITY
# ============================================================


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "report_count",
            0,
        ),
        (
            "raw_execution_input_count",
            4,
        ),
        (
            "raw_execution_input_count",
            6,
        ),
    ],
)
def test_record_rejects_invalid_lineage_cardinality(
    monkeypatch,
    tmp_path,
    field,
    value,
):
    record, bundle = _valid_record(
        monkeypatch,
        tmp_path,
    )

    bundle[field] = value

    record["lineage"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lineage cardinality is inconsistent",
    ):
        review.validate_visus_scientific_review_record(
            record,
            bundle=bundle,
        )


# ============================================================
# REVIEW BOUNDARY BOOLEAN GUARDS
# ============================================================


def test_record_requires_review_completion_true(
    monkeypatch,
    tmp_path,
):
    record, bundle = _valid_record(
        monkeypatch,
        tmp_path,
    )

    record["scientific_boundary"]["scientific_review_completed"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="scientific_review_completed=true",
    ):
        review.validate_visus_scientific_review_record(
            record,
            bundle=bundle,
        )


def test_record_requires_public_frozen_evidence_approval_true(
    monkeypatch,
    tmp_path,
):
    record, bundle = _valid_record(
        monkeypatch,
        tmp_path,
    )

    record["scientific_boundary"]["approved_for_public_frozen_evidence"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="approve public Frozen Evidence publication",
    ):
        review.validate_visus_scientific_review_record(
            record,
            bundle=bundle,
        )


# ============================================================
# REVIEW FINGERPRINT
# ============================================================


def test_record_rejects_fingerprint_drift(
    monkeypatch,
    tmp_path,
):
    record, bundle = _valid_record(
        monkeypatch,
        tmp_path,
    )

    record["review_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint drifted",
    ):
        review.validate_visus_scientific_review_record(
            record,
            bundle=bundle,
        )


# ============================================================
# REVIEW FILE VALIDATION
# ============================================================


def test_review_file_rejects_zero_length(
    monkeypatch,
    tmp_path,
):
    _mock_bundle(monkeypatch)

    path = tmp_path / review.SCIENTIFIC_REVIEW_FILENAME

    path.write_bytes(b"")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file size is outside the allowed bound",
    ):
        review.validate_visus_scientific_review_approval(tmp_path)


def test_review_file_rejects_oversize_payload(
    monkeypatch,
    tmp_path,
):
    _mock_bundle(monkeypatch)

    path = tmp_path / review.SCIENTIFIC_REVIEW_FILENAME

    path.write_bytes(b"x" * (review._MAX_REVIEW_BYTES + 1))

    with pytest.raises(
        BenchmarkIntegrityError,
        match="file size is outside the allowed bound",
    ):
        review.validate_visus_scientific_review_approval(tmp_path)


def test_review_file_rejects_invalid_json(
    monkeypatch,
    tmp_path,
):
    _mock_bundle(monkeypatch)

    path = tmp_path / review.SCIENTIFIC_REVIEW_FILENAME

    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not valid UTF-8 JSON",
    ):
        review.validate_visus_scientific_review_approval(tmp_path)


def test_review_file_requires_json_object(
    monkeypatch,
    tmp_path,
):
    _mock_bundle(monkeypatch)

    path = tmp_path / review.SCIENTIFIC_REVIEW_FILENAME

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must contain a JSON object",
    ):
        review.validate_visus_scientific_review_approval(tmp_path)


# ============================================================
# DIRECT-FILENAME LOAD SUCCESS
# ============================================================


def test_review_validation_accepts_direct_filename(
    monkeypatch,
    tmp_path,
):
    bundle = _mock_bundle(monkeypatch)

    record = review.build_visus_scientific_review_approval(
        tmp_path,
        reviewer="Scientific Reviewer",
        reviewed_at="2026-09-11T18:30:00Z",
        review_rationale="Reviewed.",
    )

    path = tmp_path / review.SCIENTIFIC_REVIEW_FILENAME

    path.write_text(
        json.dumps(
            record,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    observed = review.validate_visus_scientific_review_approval(path)

    assert observed["review_fingerprint_sha256"] == record["review_fingerprint_sha256"]

    assert review._bundle_lineage(bundle) == observed["lineage"]
