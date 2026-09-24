from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import gazeforge.cross_dataset_scientific_review as review
import gazeforge.hollywood2_token_portability_evidence as portability
from gazeforge.exceptions import BenchmarkIntegrityError

PORTABILITY_EVIDENCE = Path(
    "validation/evidence/hollywood2/hollywood2-source-token-numeric-portability-evidence-v2.json"
)

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64


# ============================================================
# HOLLYWOOD2 PORTABILITY HELPERS
# ============================================================


def _portability_record():
    return json.loads(PORTABILITY_EVIDENCE.read_text(encoding="utf-8"))


def _bypass_portability_outer_fingerprint(
    monkeypatch,
):
    monkeypatch.setattr(
        portability,
        "portability_evidence_fingerprint",
        lambda record: portability.PORTABILITY_EVIDENCE_FINGERPRINT,
    )


def test_portability_fingerprint_ignores_stored_value():
    record = _portability_record()

    first = portability.portability_evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = "0" * 64

    assert portability.portability_evidence_fingerprint(record) == first


def test_portability_load_dict_is_copy():
    record = _portability_record()

    loaded = portability._load_record(record)

    assert loaded == record
    assert loaded is not record


def test_portability_load_path():
    loaded = portability._load_record(PORTABILITY_EVIDENCE)

    assert loaded["record_type"] == ("hollywood2-source-token-numeric-portability-evidence-v2")


# ============================================================
# V1/V2 METRIC EQUIVALENCE RECURSION
# ============================================================


def test_metric_equivalence_empty_dict():
    assert (
        portability.validate_hollywood2_v1_v2_metric_equivalence(
            {},
            {},
        )
        == 0.0
    )


def test_metric_equivalence_empty_list():
    assert (
        portability.validate_hollywood2_v1_v2_metric_equivalence(
            [],
            [],
        )
        == 0.0
    )


def test_metric_equivalence_nested_delta():
    observed = portability.validate_hollywood2_v1_v2_metric_equivalence(
        {
            "rows": [
                {
                    "score": 0.5,
                }
            ]
        },
        {
            "rows": [
                {
                    "score": (0.5 + 1e-15),
                }
            ]
        },
    )

    assert observed > 0.0


@pytest.mark.parametrize(
    "second",
    [
        [],
        {
            "other": 1.0,
        },
    ],
)
def test_metric_equivalence_dict_structure(
    second,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="structure drifted",
    ):
        portability.validate_hollywood2_v1_v2_metric_equivalence(
            {
                "metric": 1.0,
            },
            second,
        )


@pytest.mark.parametrize(
    "second",
    [
        {},
        [
            1,
            2,
        ],
    ],
)
def test_metric_equivalence_list_structure(
    second,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="list structure drifted",
    ):
        portability.validate_hollywood2_v1_v2_metric_equivalence(
            [
                1,
            ],
            second,
        )


def test_metric_equivalence_float_type():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="scalar type drifted",
    ):
        portability.validate_hollywood2_v1_v2_metric_equivalence(
            {
                "metric": 1.0,
            },
            {
                "metric": 1,
            },
        )


@pytest.mark.parametrize(
    (
        "first",
        "second",
    ),
    [
        (
            float("nan"),
            1.0,
        ),
        (
            1.0,
            float("inf"),
        ),
    ],
)
def test_metric_equivalence_nonfinite(
    first,
    second,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be finite",
    ):
        portability.validate_hollywood2_v1_v2_metric_equivalence(
            {
                "metric": first,
            },
            {
                "metric": second,
            },
        )


def test_metric_equivalence_excess_delta():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="exceeded portability bound",
    ):
        portability.validate_hollywood2_v1_v2_metric_equivalence(
            {
                "metric": 0.5,
            },
            {
                "metric": (0.5 + 2e-14),
            },
        )


@pytest.mark.parametrize(
    (
        "first",
        "second",
    ),
    [
        (
            1,
            2,
        ),
        (
            True,
            False,
        ),
        (
            "A",
            "B",
        ),
        (
            None,
            "None",
        ),
    ],
)
def test_metric_equivalence_nonfloat_drift(
    first,
    second,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-float metric value drifted",
    ):
        portability.validate_hollywood2_v1_v2_metric_equivalence(
            {
                "metric": first,
            },
            {
                "metric": second,
            },
        )


# ============================================================
# PORTABILITY EVIDENCE OUTER CONTRACT
# ============================================================


def test_portability_record_type():
    record = _portability_record()

    record["record_type"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="record type",
    ):
        portability.validate_hollywood2_source_token_portability_evidence(record)


def test_portability_status():
    record = _portability_record()

    record["status"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not verified",
    ):
        portability.validate_hollywood2_source_token_portability_evidence(record)


def test_portability_stored_fingerprint():
    record = _portability_record()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint is not reviewed",
    ):
        portability.validate_hollywood2_source_token_portability_evidence(record)


def test_portability_content_fingerprint():
    record = _portability_record()

    record["portability_observations"]["interpretation"] += " drift"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="content drifted",
    ):
        portability.validate_hollywood2_source_token_portability_evidence(record)


# ============================================================
# PORTABILITY DEEP MIGRATION CONTRACT
# ============================================================


def test_portability_migration_missing(
    monkeypatch,
):
    record = _portability_record()

    record["migration"] = None

    _bypass_portability_outer_fingerprint(monkeypatch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="migration metadata is missing",
    ):
        portability.validate_hollywood2_source_token_portability_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "from_contract",
        "to_contract",
    ],
)
def test_portability_contract_missing(
    monkeypatch,
    field,
):
    record = _portability_record()

    record["migration"][field] = None

    _bypass_portability_outer_fingerprint(monkeypatch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="contracts are missing",
    ):
        portability.validate_hollywood2_source_token_portability_evidence(record)


def test_portability_v1_contract_drift(
    monkeypatch,
):
    record = _portability_record()

    record["migration"]["from_contract"]["metric_float_decimal_places"] = 99

    _bypass_portability_outer_fingerprint(monkeypatch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="v1 numeric contract drifted",
    ):
        portability.validate_hollywood2_source_token_portability_evidence(record)


def test_portability_v2_contract_drift(
    monkeypatch,
):
    record = _portability_record()

    record["migration"]["to_contract"]["metric_float_decimal_places"] = 99

    _bypass_portability_outer_fingerprint(monkeypatch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="v2 numeric contract drifted",
    ):
        portability.validate_hollywood2_source_token_portability_evidence(record)


@pytest.mark.parametrize(
    (
        "side",
        "field",
        "message",
    ),
    [
        (
            "from_contract",
            ("frozen_summary_report_fingerprint_sha256"),
            "frozen-summary identity",
        ),
        (
            "from_contract",
            ("canonical_source_report_fingerprint_sha256"),
            "v1 report identity",
        ),
        (
            "from_contract",
            ("canonical_source_report_file_sha256"),
            "v1 report bytes",
        ),
        (
            "to_contract",
            ("canonical_source_report_fingerprint_sha256"),
            "v2 report identity",
        ),
        (
            "to_contract",
            ("canonical_source_report_file_sha256"),
            "v2 report bytes",
        ),
    ],
)
def test_portability_contract_lineage(
    monkeypatch,
    side,
    field,
    message,
):
    record = _portability_record()

    record["migration"][side][field] = "0" * 64

    _bypass_portability_outer_fingerprint(monkeypatch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        portability.validate_hollywood2_source_token_portability_evidence(record)


# ============================================================
# REVIEWED ARTIFACT CONTRACT
# ============================================================


def test_portability_reviewed_missing(
    monkeypatch,
):
    record = _portability_record()

    record["reviewed_source_verified_artifacts"] = None

    _bypass_portability_outer_fingerprint(monkeypatch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="reviewed source artifacts are missing",
    ):
        portability.validate_hollywood2_source_token_portability_evidence(record)


def test_portability_byte_replay_required(
    monkeypatch,
):
    record = _portability_record()

    record["reviewed_source_verified_artifacts"]["v2_recanonicalized_reports_byte_identical"] = (
        False
    )

    _bypass_portability_outer_fingerprint(monkeypatch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="byte-identical",
    ):
        portability.validate_hollywood2_source_token_portability_evidence(record)


@pytest.mark.parametrize(
    "label",
    [
        "pre_merge",
        "exact_merge",
    ],
)
def test_portability_reviewed_artifact_lineage(
    monkeypatch,
    label,
):
    record = _portability_record()

    record["reviewed_source_verified_artifacts"][label]["artifact_id"] += 1

    _bypass_portability_outer_fingerprint(monkeypatch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=(f"reviewed {label} artifact lineage drifted"),
    ):
        portability.validate_hollywood2_source_token_portability_evidence(record)


# ============================================================
# SCIENTIFIC BOUNDARY
# ============================================================


def test_portability_boundary_missing(
    monkeypatch,
):
    record = _portability_record()

    record["scientific_boundary"] = None

    _bypass_portability_outer_fingerprint(monkeypatch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="scientific boundary is missing",
    ):
        portability.validate_hollywood2_source_token_portability_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "scientific_metrics_reestimated",
        "model_configuration_changed",
        "fold_assignment_changed",
        "source_rows_changed",
        "participant_identity_mapping_verified",
        "participant_disjoint_validation_created",
        "participant_generalization_claim",
        "cross_dataset_validation_created",
        "rights_status_changed",
        "raw_source_redistributed_by_gazeforge",
        "v1_evidence_rewritten",
    ],
)
def test_portability_boundary_promotions(
    monkeypatch,
    field,
):
    record = _portability_record()

    record["scientific_boundary"][field] = True

    _bypass_portability_outer_fingerprint(monkeypatch)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot promote",
    ):
        portability.validate_hollywood2_source_token_portability_evidence(record)


def test_portability_deep_valid(
    monkeypatch,
):
    record = _portability_record()

    _bypass_portability_outer_fingerprint(monkeypatch)

    assert portability.validate_hollywood2_source_token_portability_evidence(record) == record


# ============================================================
# CROSS-DATASET REVIEW SYNTHETIC REPORT
# ============================================================


def _report():
    return {
        "report_fingerprint_sha256": SHA_A,
        "protocol": {
            "evidence_schema": (review.CROSS_DATASET_EVIDENCE_SCHEMA),
            ("cross_dataset_validation_fingerprint_sha256"): SHA_B,
            "validation_design": {
                "dataset_ids": [
                    "Lund2013",
                    "Hollywood2EM",
                ],
            },
            "dataset_reports": {
                "Hollywood2EM": {
                    ("source_audit_lineage_receipt_fingerprint_sha256"): SHA_C,
                    ("source_audit_report_fingerprint_sha256"): SHA_D,
                    ("source_manifest_fingerprint_sha256"): SHA_E,
                },
                "Lund2013": {},
            },
        },
    }


def _approval_record(
    report_path,
    *,
    report=None,
):
    if report is None:
        report = _report()

    record = {
        "schema": (review.CROSS_DATASET_SCIENTIFIC_REVIEW_SCHEMA),
        "status": (review.CROSS_DATASET_SCIENTIFIC_REVIEW_STATUS),
        "decision": "approved",
        "reviewer": "Reviewer",
        "reviewed_at": ("2026-09-24T09:00:00Z"),
        "review_scope": (review.CROSS_DATASET_SCIENTIFIC_REVIEW_SCOPE),
        "review_rationale": ("Reviewed exact frozen report and its bounded claim scope."),
        "lineage": (
            review._lineage_from_report(
                Path(report_path),
                report,
            )
        ),
        "scientific_boundary": dict(review._BOUNDARY),
    }

    record["review_fingerprint_sha256"] = review._review_fingerprint(record)

    return record


def _patch_report_validation(
    monkeypatch,
    report,
):
    monkeypatch.setattr(
        review,
        "load_cross_dataset_frozen_report",
        lambda path: copy.deepcopy(report),
    )

    monkeypatch.setattr(
        review,
        "validate_cross_dataset_frozen_report",
        lambda value: copy.deepcopy(dict(value)),
    )


# ============================================================
# CROSS-DATASET REVIEW HELPER CONTRACTS
# ============================================================


def test_review_exact_keys_valid():
    review._require_exact_keys(
        {
            "a": 1,
        },
        frozenset(
            {
                "a",
            }
        ),
        label="fixture",
    )


@pytest.mark.parametrize(
    "value",
    [
        {},
        {
            "a": 1,
            "b": 2,
        },
    ],
)
def test_review_exact_keys_invalid(
    value,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="schema drifted",
    ):
        review._require_exact_keys(
            value,
            frozenset(
                {
                    "a",
                }
            ),
            label="fixture",
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            SHA_A,
            True,
        ),
        (
            None,
            False,
        ),
        (
            "A" * 64,
            False,
        ),
        (
            "a" * 63,
            False,
        ),
        (
            "g" * 64,
            False,
        ),
    ],
)
def test_review_valid_sha(
    value,
    expected,
):
    assert review._valid_sha256(value) is expected


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (
            None,
            "must be text",
        ),
        (
            "",
            "must be non-empty",
        ),
        (
            " " * 10,
            "must be non-empty",
        ),
        (
            "x" * (review._MAX_TEXT_LENGTH + 1),
            "too long",
        ),
    ],
)
def test_review_required_text_rejects(
    value,
    message,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        review._required_text(
            value,
            label="fixture",
        )


def test_review_required_text_strips():
    assert (
        review._required_text(
            " value ",
            label="fixture",
        )
        == "value"
    )


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (
            "not-a-date",
            "ISO-8601",
        ),
        (
            "2026-09-24T09:00:00",
            "explicit UTC",
        ),
        (
            "2026-09-24T12:00:00+03:00",
            "explicit UTC",
        ),
    ],
)
def test_review_timestamp_rejects(
    value,
    message,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        review._utc_timestamp(value)


@pytest.mark.parametrize(
    "value",
    [
        "2026-09-24T09:00:00Z",
        "2026-09-24T09:00:00+00:00",
    ],
)
def test_review_timestamp_valid(
    value,
):
    assert review._utc_timestamp(value) == value


def test_review_fingerprint_ignores_stored():
    record = {
        "x": 1,
        "review_fingerprint_sha256": SHA_A,
    }

    first = review._review_fingerprint(record)

    record["review_fingerprint_sha256"] = SHA_B

    assert review._review_fingerprint(record) == first


@pytest.mark.parametrize(
    "value",
    [
        "../report.json",
        "folder/report.json",
        ".",
        "..",
    ],
)
def test_review_safe_report_name_rejects(
    value,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="sibling basename",
    ):
        review._safe_report_name(value)


def test_review_safe_report_name_valid():
    assert review._safe_report_name("report.json") == "report.json"


# ============================================================
# CROSS-DATASET LINEAGE EXTRACTION
# ============================================================


def test_review_lineage_protocol_invalid():
    report = _report()

    report["protocol"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="protocol is invalid",
    ):
        review._lineage_from_report(
            Path("report.json"),
            report,
        )


@pytest.mark.parametrize(
    "field",
    [
        "validation_design",
        "dataset_reports",
    ],
)
def test_review_lineage_provenance_invalid(
    field,
):
    report = _report()

    report["protocol"][field] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="provenance sections are invalid",
    ):
        review._lineage_from_report(
            Path("report.json"),
            report,
        )


def test_review_lineage_hollywood_missing():
    report = _report()

    report["protocol"]["dataset_reports"]["Hollywood2EM"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Hollywood2EM provenance is missing",
    ):
        review._lineage_from_report(
            Path("report.json"),
            report,
        )


@pytest.mark.parametrize(
    (
        "location",
        "field",
    ),
    [
        (
            "report",
            "report_fingerprint_sha256",
        ),
        (
            "protocol",
            ("cross_dataset_validation_fingerprint_sha256"),
        ),
        (
            "hollywood",
            ("source_audit_lineage_receipt_fingerprint_sha256"),
        ),
        (
            "hollywood",
            ("source_audit_report_fingerprint_sha256"),
        ),
        (
            "hollywood",
            ("source_manifest_fingerprint_sha256"),
        ),
    ],
)
def test_review_lineage_invalid_fingerprints(
    location,
    field,
):
    report = _report()

    if location == "report":
        report[field] = "BAD"
    elif location == "protocol":
        report["protocol"][field] = "BAD"
    else:
        report["protocol"]["dataset_reports"]["Hollywood2EM"][field] = "BAD"

    expected_message = {
        "source_audit_lineage_receipt_fingerprint_sha256": (
            "hollywood2_lineage_receipt_fingerprint_sha256"
        ),
        "source_audit_report_fingerprint_sha256": ("hollywood2_audit_report_fingerprint_sha256"),
    }.get(field, field)

    with pytest.raises(
        BenchmarkIntegrityError,
        match=expected_message,
    ):
        review._lineage_from_report(
            Path("report.json"),
            report,
        )


def test_review_lineage_dataset_identity():
    report = _report()

    report["protocol"]["validation_design"]["dataset_ids"] = [
        "Hollywood2EM",
    ]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="dataset identity drifted",
    ):
        review._lineage_from_report(
            Path("report.json"),
            report,
        )


def test_review_lineage_schema():
    report = _report()

    report["protocol"]["evidence_schema"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="report schema drifted",
    ):
        review._lineage_from_report(
            Path("report.json"),
            report,
        )


def test_review_lineage_success():
    result = review._lineage_from_report(
        Path("report.json"),
        _report(),
    )

    assert result["report_file_name"] == "report.json"

    assert result["dataset_ids"] == [
        "Hollywood2EM",
        "Lund2013",
    ]

    assert result["report_verified"] is True


# ============================================================
# BUILD SCIENTIFIC REVIEW
# ============================================================


def test_review_build_success(
    monkeypatch,
    tmp_path,
):
    report_path = tmp_path / "report.json"

    report_path.write_text(
        "{}",
        encoding="utf-8",
    )

    report_data = _report()

    _patch_report_validation(
        monkeypatch,
        report_data,
    )

    result = review.build_cross_dataset_scientific_review_approval(
        report_path,
        reviewer=" Reviewer ",
        reviewed_at=("2026-09-24T09:00:00Z"),
        review_rationale=(" Exact report reviewed. "),
    )

    assert result["decision"] == "approved"

    assert result["reviewer"] == "Reviewer"

    assert result["scientific_boundary"] == review._BOUNDARY


# ============================================================
# REVIEW RECORD VALIDATOR
# ============================================================


def _validated_record(
    monkeypatch,
    tmp_path,
):
    report_path = tmp_path / "report.json"

    report_path.write_text(
        "{}",
        encoding="utf-8",
    )

    report_data = _report()

    _patch_report_validation(
        monkeypatch,
        report_data,
    )

    record = _approval_record(
        report_path,
        report=report_data,
    )

    return (
        report_path,
        report_data,
        record,
    )


def test_review_record_extra_key(
    monkeypatch,
    tmp_path,
):
    report_path, report_data, record = _validated_record(
        monkeypatch,
        tmp_path,
    )

    record["extra"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="approval schema drifted",
    ):
        review.validate_cross_dataset_scientific_review_record(
            record,
            report_path=report_path,
            report=report_data,
        )


@pytest.mark.parametrize(
    (
        "field",
        "value",
        "message",
    ),
    [
        (
            "schema",
            "wrong",
            "schema is invalid",
        ),
        (
            "status",
            "wrong",
            "status is invalid",
        ),
        (
            "decision",
            "rejected",
            "requires approval",
        ),
        (
            "review_scope",
            "wrong",
            "scope drifted",
        ),
    ],
)
def test_review_record_identity_fields(
    monkeypatch,
    tmp_path,
    field,
    value,
    message,
):
    report_path, report_data, record = _validated_record(
        monkeypatch,
        tmp_path,
    )

    record[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        review.validate_cross_dataset_scientific_review_record(
            record,
            report_path=report_path,
            report=report_data,
        )


def test_review_record_reviewer(
    monkeypatch,
    tmp_path,
):
    report_path, report_data, record = _validated_record(
        monkeypatch,
        tmp_path,
    )

    record["reviewer"] = ""

    with pytest.raises(
        BenchmarkIntegrityError,
        match="reviewer must be non-empty",
    ):
        review.validate_cross_dataset_scientific_review_record(
            record,
            report_path=report_path,
            report=report_data,
        )


def test_review_record_timestamp(
    monkeypatch,
    tmp_path,
):
    report_path, report_data, record = _validated_record(
        monkeypatch,
        tmp_path,
    )

    record["reviewed_at"] = "2026-09-24"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="explicit UTC",
    ):
        review.validate_cross_dataset_scientific_review_record(
            record,
            report_path=report_path,
            report=report_data,
        )


def test_review_record_rationale(
    monkeypatch,
    tmp_path,
):
    report_path, report_data, record = _validated_record(
        monkeypatch,
        tmp_path,
    )

    record["review_rationale"] = ""

    with pytest.raises(
        BenchmarkIntegrityError,
        match="review_rationale must be non-empty",
    ):
        review.validate_cross_dataset_scientific_review_record(
            record,
            report_path=report_path,
            report=report_data,
        )


def test_review_record_lineage_missing(
    monkeypatch,
    tmp_path,
):
    report_path, report_data, record = _validated_record(
        monkeypatch,
        tmp_path,
    )

    record["lineage"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lineage is missing",
    ):
        review.validate_cross_dataset_scientific_review_record(
            record,
            report_path=report_path,
            report=report_data,
        )


def test_review_record_lineage_schema(
    monkeypatch,
    tmp_path,
):
    report_path, report_data, record = _validated_record(
        monkeypatch,
        tmp_path,
    )

    record["lineage"]["extra"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lineage schema drifted",
    ):
        review.validate_cross_dataset_scientific_review_record(
            record,
            report_path=report_path,
            report=report_data,
        )


def test_review_record_boundary(
    monkeypatch,
    tmp_path,
):
    report_path, report_data, record = _validated_record(
        monkeypatch,
        tmp_path,
    )

    record["scientific_boundary"]["native_60hz_validity_claim_created"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="claim boundary drifted",
    ):
        review.validate_cross_dataset_scientific_review_record(
            record,
            report_path=report_path,
            report=report_data,
        )


def test_review_record_lineage_mismatch(
    monkeypatch,
    tmp_path,
):
    report_path, report_data, record = _validated_record(
        monkeypatch,
        tmp_path,
    )

    record["lineage"]["report_fingerprint_sha256"] = "f" * 64

    record["review_fingerprint_sha256"] = review._review_fingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exact current report lineage",
    ):
        review.validate_cross_dataset_scientific_review_record(
            record,
            report_path=report_path,
            report=report_data,
        )


@pytest.mark.parametrize(
    "fingerprint",
    [
        "BAD",
        "0" * 64,
    ],
)
def test_review_record_fingerprint(
    monkeypatch,
    tmp_path,
    fingerprint,
):
    report_path, report_data, record = _validated_record(
        monkeypatch,
        tmp_path,
    )

    record["review_fingerprint_sha256"] = fingerprint

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint drifted",
    ):
        review.validate_cross_dataset_scientific_review_record(
            record,
            report_path=report_path,
            report=report_data,
        )


def test_review_record_report_none_branch(
    monkeypatch,
    tmp_path,
):
    report_path, _, record = _validated_record(
        monkeypatch,
        tmp_path,
    )

    result = review.validate_cross_dataset_scientific_review_record(
        record,
        report_path=report_path,
        report=None,
    )

    assert result["decision"] == "approved"


def test_review_record_report_provided_branch(
    monkeypatch,
    tmp_path,
):
    report_path, report_data, record = _validated_record(
        monkeypatch,
        tmp_path,
    )

    result = review.validate_cross_dataset_scientific_review_record(
        record,
        report_path=report_path,
        report=report_data,
    )

    assert result["review_fingerprint_sha256"] == record["review_fingerprint_sha256"]


# ============================================================
# APPROVAL PATHS
# ============================================================


def test_review_approval_paths_directory(
    tmp_path,
):
    root, path = review._approval_paths(tmp_path)

    assert root == tmp_path

    assert path.name == (review.CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME)


def test_review_approval_paths_file(
    tmp_path,
):
    source = tmp_path / review.CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME

    root, path = review._approval_paths(source)

    assert root == tmp_path
    assert path == source


# ============================================================
# APPROVAL FILE VALIDATION
# ============================================================


def test_review_approval_missing(
    tmp_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires cross-dataset-scientific-review",
    ):
        review.validate_cross_dataset_scientific_review_approval(tmp_path)


def test_review_approval_empty(
    tmp_path,
):
    path = tmp_path / review.CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME

    path.write_bytes(b"")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="size is outside",
    ):
        review.validate_cross_dataset_scientific_review_approval(tmp_path)


def test_review_approval_oversize(
    tmp_path,
):
    path = tmp_path / review.CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME

    path.write_bytes(b"x" * (review._MAX_REVIEW_BYTES + 1))

    with pytest.raises(
        BenchmarkIntegrityError,
        match="size is outside",
    ):
        review.validate_cross_dataset_scientific_review_approval(tmp_path)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            "{",
            "not valid UTF-8 JSON",
        ),
        (
            "[]",
            "must contain an object",
        ),
    ],
)
def test_review_approval_bad_payload(
    tmp_path,
    payload,
    message,
):
    path = tmp_path / review.CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME

    path.write_text(
        payload,
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        review.validate_cross_dataset_scientific_review_approval(tmp_path)


def test_review_approval_bad_utf8(
    tmp_path,
):
    path = tmp_path / review.CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME

    path.write_bytes(b"\xff\xfe")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="not valid UTF-8 JSON",
    ):
        review.validate_cross_dataset_scientific_review_approval(tmp_path)


def test_review_approval_lineage_missing(
    tmp_path,
):
    path = tmp_path / review.CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME

    path.write_text(
        json.dumps(
            {
                "lineage": None,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="lineage is missing",
    ):
        review.validate_cross_dataset_scientific_review_approval(tmp_path)


def test_review_approval_unsafe_report_name(
    tmp_path,
):
    path = tmp_path / review.CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME

    path.write_text(
        json.dumps(
            {
                "lineage": {
                    "report_file_name": "../report.json",
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="sibling basename",
    ):
        review.validate_cross_dataset_scientific_review_approval(tmp_path)


def test_review_approval_report_missing(
    tmp_path,
):
    path = tmp_path / review.CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME

    path.write_text(
        json.dumps(
            {
                "lineage": {
                    "report_file_name": "report.json",
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="missing or non-regular report",
    ):
        review.validate_cross_dataset_scientific_review_approval(tmp_path)


def test_review_approval_success(
    monkeypatch,
    tmp_path,
):
    report_path = tmp_path / "report.json"

    report_path.write_text(
        "{}",
        encoding="utf-8",
    )

    report_data = _report()

    _patch_report_validation(
        monkeypatch,
        report_data,
    )

    record = _approval_record(
        report_path,
        report=report_data,
    )

    review_path = tmp_path / review.CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME

    review_path.write_text(
        json.dumps(record),
        encoding="utf-8",
    )

    result = review.validate_cross_dataset_scientific_review_approval(tmp_path)

    assert result["decision"] == "approved"


def test_review_approval_explicit_file_success(
    monkeypatch,
    tmp_path,
):
    report_path = tmp_path / "report.json"

    report_path.write_text(
        "{}",
        encoding="utf-8",
    )

    report_data = _report()

    _patch_report_validation(
        monkeypatch,
        report_data,
    )

    record = _approval_record(
        report_path,
        report=report_data,
    )

    review_path = tmp_path / review.CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME

    review_path.write_text(
        json.dumps(record),
        encoding="utf-8",
    )

    result = review.validate_cross_dataset_scientific_review_approval(review_path)

    assert result["review_scope"] == (review.CROSS_DATASET_SCIENTIFIC_REVIEW_SCOPE)


# ============================================================
# APPROVAL WRITER
# ============================================================


def test_review_writer_missing_report(
    tmp_path,
):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="existing regular report file",
    ):
        review.write_cross_dataset_scientific_review_approval(
            tmp_path / "missing.json",
            reviewer="Reviewer",
            reviewed_at=("2026-09-24T09:00:00Z"),
            review_rationale="Reviewed.",
        )


def test_review_writer_existing(
    monkeypatch,
    tmp_path,
):
    report_path = tmp_path / "report.json"

    report_path.write_text(
        "{}",
        encoding="utf-8",
    )

    existing = tmp_path / review.CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME

    existing.write_text(
        "{}",
        encoding="utf-8",
    )

    _patch_report_validation(
        monkeypatch,
        _report(),
    )

    with pytest.raises(
        FileExistsError,
    ):
        review.write_cross_dataset_scientific_review_approval(
            report_path,
            reviewer="Reviewer",
            reviewed_at=("2026-09-24T09:00:00Z"),
            review_rationale="Reviewed.",
        )


def test_review_writer_success(
    monkeypatch,
    tmp_path,
):
    report_path = tmp_path / "report.json"

    report_path.write_text(
        "{}",
        encoding="utf-8",
    )

    report_data = _report()

    _patch_report_validation(
        monkeypatch,
        report_data,
    )

    written = review.write_cross_dataset_scientific_review_approval(
        report_path,
        reviewer="Reviewer",
        reviewed_at=("2026-09-24T09:00:00Z"),
        review_rationale=("Exact frozen report reviewed."),
    )

    assert written.is_file()

    result = review.validate_cross_dataset_scientific_review_approval(tmp_path)

    assert result["decision"] == "approved"


def test_review_writer_overwrite(
    monkeypatch,
    tmp_path,
):
    report_path = tmp_path / "report.json"

    report_path.write_text(
        "{}",
        encoding="utf-8",
    )

    review_path = tmp_path / review.CROSS_DATASET_SCIENTIFIC_REVIEW_FILENAME

    review_path.write_text(
        "{}",
        encoding="utf-8",
    )

    report_data = _report()

    _patch_report_validation(
        monkeypatch,
        report_data,
    )

    written = review.write_cross_dataset_scientific_review_approval(
        report_path,
        reviewer="Reviewer",
        reviewed_at=("2026-09-24T09:00:00Z"),
        review_rationale=("Exact frozen report reviewed."),
        overwrite=True,
    )

    assert written == review_path
