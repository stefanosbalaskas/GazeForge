from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import gazeforge.visus_supplement_recovery_exhaustion as recovery
from gazeforge.exceptions import BenchmarkIntegrityError

EVIDENCE = Path(
    "validation/evidence/visus-source-recheck/"
    "visus-2021-supplement-recovery-exhaustion-evidence-v1.json"
)


def _record() -> dict[str, Any]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _refingerprint(
    record: dict[str, Any],
) -> dict[str, Any]:
    record["evidence_fingerprint_sha256"] = recovery.evidence_fingerprint(record)
    return record


def test_canonical_bytes_are_deterministic() -> None:
    left = {
        "b": 2,
        "a": 1,
    }

    right = {
        "a": 1,
        "b": 2,
    }

    assert recovery._canonical_bytes(left) == recovery._canonical_bytes(right)


def test_evidence_fingerprint_ignores_self_field() -> None:
    record = {
        "a": 1,
    }

    first = recovery.evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = "0" * 64

    second = recovery.evidence_fingerprint(record)

    assert first == second


def test_load_mapping_returns_copy() -> None:
    source = {
        "a": 1,
    }

    loaded = recovery._load(source)

    assert loaded == source
    assert loaded is not source


def test_load_missing_file_guard(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        recovery._load(tmp_path / "missing.json")


def test_load_invalid_json_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad.json"

    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        recovery._load(path)


def test_load_non_object_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "array.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must contain one JSON object",
    ):
        recovery._load(path)


def test_mapping_helper_success_and_failure() -> None:
    value = {
        "nested": {
            "a": 1,
        }
    }

    assert recovery._mapping(
        value,
        "nested",
    ) == {
        "a": 1,
    }

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        recovery._mapping(
            {
                "nested": None,
            },
            "nested",
        )


def test_boolean_and_equality_helpers() -> None:
    recovery._false(
        False,
        "fixture",
    )

    recovery._true(
        True,
        "fixture",
    )

    recovery._equal(
        1,
        1,
        "fixture",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        recovery._false(
            True,
            "fixture",
        )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        recovery._true(
            False,
            "fixture",
        )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        recovery._equal(
            1,
            2,
            "fixture",
        )


def test_source_binding_success() -> None:
    recovery._validate_source_binding(
        _record(),
        recovery.DEFAULT_SOURCE_RECHECK_PATH,
    )


def test_source_recheck_fingerprint_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        recovery,
        "validate_visus_authoritative_source_recheck",
        lambda path: {"record_fingerprint_sha256": ("0" * 64)},
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="authoritative-source recheck fingerprint",
    ):
        recovery._validate_source_binding(
            _record(),
            recovery.DEFAULT_SOURCE_RECHECK_PATH,
        )


def test_source_binding_mapping_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _record()

    record["source_binding"] = None

    monkeypatch.setattr(
        recovery,
        "validate_visus_authoritative_source_recheck",
        lambda path: {"record_fingerprint_sha256": (recovery.SOURCE_RECHECK_FINGERPRINT)},
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        recovery._validate_source_binding(
            record,
            recovery.DEFAULT_SOURCE_RECHECK_PATH,
        )


def test_probe_bindings_success() -> None:
    recovery._validate_probe_bindings(_record())


def test_probe_bindings_requires_list() -> None:
    record = _record()

    record["probe_bindings"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a list",
    ):
        recovery._validate_probe_bindings(record)


def test_probe_binding_row_requires_mapping() -> None:
    record = _record()

    record["probe_bindings"][0] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        recovery._validate_probe_bindings(record)


def test_probe_binding_schema_guard() -> None:
    record = _record()

    record["probe_bindings"][0]["extra"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="probe-binding schema",
    ):
        recovery._validate_probe_bindings(record)


def test_probe_binding_final_identity_guard() -> None:
    record = _record()

    record["probe_bindings"][0]["filename"] = "wrong.json"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="probe bindings",
    ):
        recovery._validate_probe_bindings(record)


def test_paper_statement_success() -> None:
    recovery._validate_paper_statement(_record())


def test_paper_statement_mapping_guard() -> None:
    record = _record()

    record["paper_statement"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        recovery._validate_paper_statement(record)


@pytest.mark.parametrize(
    "field",
    [
        "supplementary_material_explicitly_stated",
        "extracted_ground_truth_events_stated",
        "predicted_events_stated",
        "coverage_each_scenario_and_participant_stated",
    ],
)
def test_paper_required_true_fields(
    field: str,
) -> None:
    record = _record()

    record["paper_statement"][field] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        recovery._validate_paper_statement(record)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "visus_participant_count",
            24,
            "participant count",
        ),
        (
            "visus_scenario_count",
            10,
            "scenario count",
        ),
        (
            "paper_article_license",
            "wrong",
            "paper license",
        ),
    ],
)
def test_paper_exact_fields(
    field: str,
    value: Any,
    match: str,
) -> None:
    record = _record()

    record["paper_statement"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        recovery._validate_paper_statement(record)


def test_paper_dataset_license_boundary() -> None:
    record = _record()

    record["paper_statement"]["paper_article_license_is_visus_dataset_license"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        recovery._validate_paper_statement(record)


def test_paper_supplement_reuse_boundary() -> None:
    record = _record()

    record["paper_statement"]["supplement_reuse_terms_resolved"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        recovery._validate_paper_statement(record)


def test_surface_findings_success() -> None:
    recovery._validate_surface_findings(_record())


def test_surface_findings_root_mapping_guard() -> None:
    record = _record()

    record["reviewed_surface_findings"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        recovery._validate_surface_findings(record)


@pytest.mark.parametrize(
    "section",
    [
        "pmc_oa_package",
        "current_mdpi_routes",
        "mdpi_static_attachment_candidates",
        "wayback_article_namespace",
        "wayback_static_attachment_namespace",
        "wayback_archived_article",
    ],
)
def test_surface_subsection_mapping_guards(
    section: str,
) -> None:
    record = _record()

    record["reviewed_surface_findings"][section] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        recovery._validate_surface_findings(record)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        (
            "pmc_oa_package",
            "selected_version",
            2,
        ),
        (
            "pmc_oa_package",
            "exact_xml_bytes",
            1,
        ),
        (
            "current_mdpi_routes",
            "article_http_status",
            200,
        ),
        (
            "current_mdpi_routes",
            "candidate_link_count",
            1,
        ),
        (
            "mdpi_static_attachment_candidates",
            "candidate_base",
            "wrong",
        ),
        (
            "mdpi_static_attachment_candidates",
            "probe_count",
            11,
        ),
        (
            "wayback_article_namespace",
            "query_count",
            1,
        ),
        (
            "wayback_article_namespace",
            "captures_per_query",
            4,
        ),
        (
            "wayback_static_attachment_namespace",
            "timeout_count",
            1,
        ),
        (
            "wayback_static_attachment_namespace",
            "successful_query_count",
            1,
        ),
        (
            "wayback_archived_article",
            "xml_2022_http_status",
            404,
        ),
        (
            "wayback_archived_article",
            "historical_supplement_link_count",
            1,
        ),
    ],
)
def test_surface_exact_value_guards(
    section: str,
    field: str,
    value: Any,
) -> None:
    record = _record()

    record["reviewed_surface_findings"][section][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        recovery._validate_surface_findings(record)


@pytest.mark.parametrize(
    ("section", "field"),
    [
        (
            "pmc_oa_package",
            "pmc_package_absence_proves_supplement_never_existed",
        ),
        (
            "current_mdpi_routes",
            "access_denial_is_absence_evidence",
        ),
        (
            "mdpi_static_attachment_candidates",
            "candidate_naming_authoritative",
        ),
        (
            "mdpi_static_attachment_candidates",
            "candidate_404s_prove_original_filename",
        ),
        (
            "wayback_article_namespace",
            "ordinary_article_captures_are_supplement_evidence",
        ),
        (
            "wayback_static_attachment_namespace",
            "complete_negative_search_established",
        ),
        (
            "wayback_archived_article",
            "both_archived_article_captures_successfully_inspected",
        ),
    ],
)
def test_surface_false_boundaries(
    section: str,
    field: str,
) -> None:
    record = _record()

    record["reviewed_surface_findings"][section][field] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        recovery._validate_surface_findings(record)


@pytest.mark.parametrize(
    ("section", "field"),
    [
        (
            "mdpi_static_attachment_candidates",
            "all_head_status_404",
        ),
        (
            "wayback_archived_article",
            "xml_2022_doi_marker_present",
        ),
        (
            "wayback_archived_article",
            "xml_2022_supplement_text_marker_present",
        ),
    ],
)
def test_surface_true_boundaries(
    section: str,
    field: str,
) -> None:
    record = _record()

    record["reviewed_surface_findings"][section][field] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        recovery._validate_surface_findings(record)


def test_boundaries_success() -> None:
    recovery._validate_boundaries(_record())


@pytest.mark.parametrize(
    "section",
    [
        "recovery_boundary",
        "scientific_boundary",
    ],
)
def test_boundary_mapping_guards(
    section: str,
) -> None:
    record = _record()

    record[section] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        recovery._validate_boundaries(record)


@pytest.mark.parametrize(
    ("section", "extra"),
    [
        (
            "recovery_boundary",
            "extra_recovery",
        ),
        (
            "scientific_boundary",
            "extra_science",
        ),
    ],
)
def test_boundary_schema_guards(
    section: str,
    extra: str,
) -> None:
    record = _record()

    record[section][extra] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="schema",
    ):
        recovery._validate_boundaries(record)


def test_remaining_routes_success() -> None:
    recovery._validate_remaining_routes(_record())


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        [
            {},
        ],
    ],
)
def test_remaining_routes_count_guard(
    value: Any,
) -> None:
    record = _record()

    record["remaining_authoritative_resolution_routes"] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="three authoritative routes",
    ):
        recovery._validate_remaining_routes(record)


def test_remaining_routes_identity_guard() -> None:
    record = _record()

    record["remaining_authoritative_resolution_routes"][0]["route"] = "wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="remaining authoritative routes",
    ):
        recovery._validate_remaining_routes(record)


def test_remaining_route_non_mapping_hits_identity_guard() -> None:
    record = _record()

    record["remaining_authoritative_resolution_routes"][0] = "bad-row"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="remaining authoritative routes",
    ):
        recovery._validate_remaining_routes(record)


def test_remaining_route_schema_guard() -> None:
    record = _record()

    row = record["remaining_authoritative_resolution_routes"][0]

    row["extra"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="route schema drifted",
    ):
        recovery._validate_remaining_routes(record)


@pytest.mark.parametrize(
    "field",
    [
        "requirement",
        "promotion_condition",
    ],
)
def test_remaining_route_text_guard(
    field: str,
) -> None:
    record = _record()

    record["remaining_authoritative_resolution_routes"][0][field] = " "

    with pytest.raises(
        BenchmarkIntegrityError,
        match="route text must remain non-empty",
    ):
        recovery._validate_remaining_routes(record)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "record_type",
            "wrong",
            "record type",
        ),
        (
            "checked_on",
            "2026-01-01",
            "review date",
        ),
        (
            "status",
            "wrong",
            "status",
        ),
    ],
)
def test_top_level_identity_guards(
    field: str,
    value: Any,
    match: str,
) -> None:
    record = _record()

    record[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        recovery.validate_visus_supplement_recovery_exhaustion(record)


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        ["only one"],
    ],
)
def test_claim_limits_count_guard(
    value: Any,
) -> None:
    record = _record()

    record["claim_limits"] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="eight claim limits",
    ):
        recovery.validate_visus_supplement_recovery_exhaustion(record)


@pytest.mark.parametrize(
    "bad_item",
    [
        "",
        " ",
        123,
        None,
    ],
)
def test_claim_limits_content_guard(
    bad_item: Any,
) -> None:
    record = _record()

    record["claim_limits"][0] = bad_item

    with pytest.raises(
        BenchmarkIntegrityError,
        match="non-empty strings",
    ):
        recovery.validate_visus_supplement_recovery_exhaustion(record)


def test_claimed_fingerprint_guard() -> None:
    record = _record()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="evidence fingerprint",
    ):
        recovery.validate_visus_supplement_recovery_exhaustion(record)


def test_canonical_body_fingerprint_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _record()

    monkeypatch.setattr(
        recovery,
        "EXPECTED_EVIDENCE_FINGERPRINT_SHA256",
        "0" * 64,
    )

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="canonical evidence body",
    ):
        recovery.validate_visus_supplement_recovery_exhaustion(record)


def test_full_validator_mapping_success() -> None:
    record = _record()

    result = recovery.validate_visus_supplement_recovery_exhaustion(record)

    assert result is not record
    assert result == record


def test_full_validator_path_success() -> None:
    result = recovery.validate_visus_supplement_recovery_exhaustion(EVIDENCE)

    assert result["record_type"] == recovery.RECORD_TYPE
