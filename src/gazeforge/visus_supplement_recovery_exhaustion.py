"""Fail-closed validation for the frozen VISUS 2021 supplement recovery checkpoint."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .visus_authoritative_source_recheck import (
    EXPECTED_RECORD_FINGERPRINT_SHA256 as SOURCE_RECHECK_FINGERPRINT,
)
from .visus_authoritative_source_recheck import validate_visus_authoritative_source_recheck

RECORD_TYPE = "visus-2021-supplement-recovery-exhaustion-evidence-v1"
STATUS = "reviewed-current-and-archived-public-surfaces-no-supplement-object-recovered"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "6e263fe3c8ec202e06cd6c819be622bbe1831202b94393e2bea205df25278761"
)
DEFAULT_SOURCE_RECHECK_PATH = Path(
    "validation/evidence/visus-source-recheck/"
    "visus-authoritative-source-recheck-2026-09-09.json"
)

_EXPECTED_SOURCE_BINDING = {
    "authoritative_source_recheck_record_fingerprint_sha256": SOURCE_RECHECK_FINGERPRINT,
    "sensors_article_doi": "10.3390/s21124143",
    "sensors_article_pmcid": "PMC8235043",
    "sensors_article_pmid": "34208736",
    "reconnaissance_branch": "feat/visus-pmc-supplement-probe",
    "reconnaissance_head_sha1": "347ba06dd802f9bd8b38aa2a6c770949702bc3ea",
    "workflow_name": "VISUS PMC supplement discovery",
    "workflow_run_id": 34497168884,
    "workflow_run_number": 7,
    "workflow_conclusion": "success",
    "artifact_id": 10160434617,
    "artifact_name": "visus-pmc-supplement-discovery",
    "artifact_digest_sha256": (
        "4545afdc8a37aee06b8415b68a7bc23614943fa6ac9dcbba774034fed3f7479d"
    ),
    "artifact_created_at_utc": "2026-09-10T15:44:20Z",
}

_EXPECTED_PROBE_BINDINGS = (
    (
        "visus_mdpi_static_attachment_probe.json",
        "78a8820f51e1efa711198cce5c60691973ab070e6bf6e1170baee69f111b5b14",
        "123b41809167d93a1e389e12a7ea947a5d290e0f79b6132f010b97accd77bc60",
    ),
    (
        "visus_mdpi_supplement_link_probe.json",
        "d4184c7ea7ee684e95094378319cf8baea2a0a35a15d5962206055921d013bad",
        "1e0422a792a03fdfe473c43961fdc5057387d5506f8be44b40d5f4a5cc127962",
    ),
    (
        "visus_pmc_supplement_discovery_probe.json",
        "e980119334a58ce924e65e4ae86a39c85fb9083f2a10950b60df912d6da7c4e6",
        "680a619da4d552ff42b60abe9f13e395d41bccd9fde2abd0678e1310f3dd940b",
    ),
    (
        "visus_pmc_xml_supplement_link_probe.json",
        "9dd3e755f60d31b27905211bd224f9a8fd1ec8ad88991272b11d03eaf4796f30",
        "1756e1c119e2c105600a3e0b4b7d30dfd1da8577e69bf300edc566f3144473d4",
    ),
    (
        "visus_wayback_archived_article_link_probe.json",
        "bc9490dd8356318e16e8fd130cb9a215df991fe5a920552191d716d2402c431a",
        "7d8702186c88e459ca65ea70ab1d62aad4a914956f927ba9d2d8059259b437c8",
    ),
    (
        "visus_wayback_attachment_history_probe.json",
        "f6cb8609436c592de5b70ecff63396fdd7a0772a31de08f3415fe38ad0fbd50d",
        "7dd03428e157dfdbbf54f113048c6c157eb8f88abafc3570d7948c3516dd442e",
    ),
)

_RECOVERY_FALSE_FIELDS = (
    "supplement_object_recovered",
    "supplement_url_resolved",
    "supplement_bytes_downloaded",
    "supplement_contents_inspected",
    "supplement_never_existed_conclusion",
    "all_possible_public_surfaces_exhaustively_proven_negative",
    "blind_url_guessing_authorized",
)

_SCIENTIFIC_FALSE_FIELDS = (
    "full_visus_authoritative_source_recovered",
    "visus_dataset_license_resolved",
    "analysis_use_rights_resolved",
    "raw_source_redistribution_rights_resolved",
    "source_audit_stage_authorized",
    "participant_stimulus_mapping_verified",
    "annotation_independence_verified",
    "human_human_validation_created",
    "model_human_validation_created",
    "cross_dataset_validation_created",
    "native_60hz_gp3_validity_created",
    "frozen_evidence_created",
    "raw_source_redistributed",
    "new_empirical_performance_claim_created",
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return the canonical SHA-256 excluding the self-fingerprint field."""
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(record_or_path: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path)
    try:
        payload = json.loads(Path(record_or_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load VISUS supplement-recovery evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "VISUS supplement-recovery evidence must contain one JSON object."
        )
    return payload


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(
            f"VISUS supplement-recovery field {key!r} must be an object."
        )
    return value


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(
            f"VISUS supplement recovery must not promote {label}."
        )


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(
            f"VISUS supplement recovery must preserve {label}."
        )


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(
            f"VISUS supplement-recovery {label} drifted."
        )


def _validate_source_binding(
    record: Mapping[str, Any],
    source_recheck_path: str | Path,
) -> None:
    recheck = validate_visus_authoritative_source_recheck(source_recheck_path)
    _equal(
        recheck["record_fingerprint_sha256"],
        SOURCE_RECHECK_FINGERPRINT,
        "authoritative-source recheck fingerprint",
    )
    binding = _mapping(record, "source_binding")
    _equal(dict(binding), _EXPECTED_SOURCE_BINDING, "source binding")


def _validate_probe_bindings(record: Mapping[str, Any]) -> None:
    rows = record.get("probe_bindings")
    if not isinstance(rows, list):
        raise BenchmarkIntegrityError(
            "VISUS supplement-recovery probe bindings must be a list."
        )
    observed = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise BenchmarkIntegrityError(
                "VISUS supplement-recovery probe binding must be an object."
            )
        _equal(
            set(row),
            {"filename", "raw_file_sha256", "probe_fingerprint_sha256"},
            "probe-binding schema",
        )
        observed.append(
            (
                str(row["filename"]),
                str(row["raw_file_sha256"]),
                str(row["probe_fingerprint_sha256"]),
            )
        )
    _equal(tuple(observed), _EXPECTED_PROBE_BINDINGS, "probe bindings")


def _validate_paper_statement(record: Mapping[str, Any]) -> None:
    paper = _mapping(record, "paper_statement")
    for key in (
        "supplementary_material_explicitly_stated",
        "extracted_ground_truth_events_stated",
        "predicted_events_stated",
        "coverage_each_scenario_and_participant_stated",
    ):
        _true(paper.get(key), key.replace("_", " "))
    _equal(paper.get("visus_participant_count"), 25, "paper participant count")
    _equal(paper.get("visus_scenario_count"), 11, "paper scenario count")
    _equal(paper.get("paper_article_license"), "CC BY 4.0", "paper license")
    _false(
        paper.get("paper_article_license_is_visus_dataset_license"),
        "the article license as a VISUS dataset license",
    )
    _false(
        paper.get("supplement_reuse_terms_resolved"),
        "supplement reuse terms",
    )


def _validate_surface_findings(record: Mapping[str, Any]) -> None:
    findings = _mapping(record, "reviewed_surface_findings")

    pmc = _mapping(findings, "pmc_oa_package")
    _equal(pmc.get("selected_version"), 1, "PMC package version")
    _equal(pmc.get("metadata_license_code"), "CC BY", "PMC metadata license code")
    _equal(
        pmc.get("supplement_candidate_article_object_count"),
        0,
        "PMC supplement article-object count",
    )
    _equal(
        pmc.get("supplement_candidate_media_url_count"),
        0,
        "PMC supplement media count",
    )
    _equal(pmc.get("exact_xml_bytes"), 243122, "PMC XML byte count")
    _equal(
        pmc.get("exact_xml_sha256"),
        "2aa36a03effd0ffca21a72cd610a0efe9825d35709c88c20f62db14933b96bc5",
        "PMC XML SHA-256",
    )
    _equal(
        pmc.get("exact_xml_custom_meta_has_supplement_value"),
        "no",
        "PMC supplement custom-meta value",
    )
    _false(
        pmc.get("pmc_package_absence_proves_supplement_never_existed"),
        "PMC package absence as non-existence evidence",
    )

    mdpi = _mapping(findings, "current_mdpi_routes")
    for key in ("article_http_status", "doi_s1_http_status", "article_s1_http_status"):
        _equal(mdpi.get(key), 403, f"current MDPI {key}")
    _equal(mdpi.get("candidate_link_count"), 0, "current MDPI candidate count")
    _equal(
        mdpi.get("resolved_binary_target_count"),
        0,
        "current MDPI resolved-binary count",
    )
    _false(
        mdpi.get("access_denial_is_absence_evidence"),
        "HTTP 403 as absence evidence",
    )

    static = _mapping(findings, "mdpi_static_attachment_candidates")
    _false(static.get("candidate_naming_authoritative"), "candidate filename authority")
    _equal(static.get("candidate_base"), "sensors-21-04143-s001", "candidate base")
    _equal(static.get("probe_count"), 12, "static candidate probe count")
    _true(static.get("all_head_status_404"), "twelve static-candidate 404 outcomes")
    _equal(static.get("resolved_candidate_count"), 0, "resolved static candidates")
    _false(
        static.get("candidate_404s_prove_original_filename"),
        "candidate 404s as original-filename evidence",
    )

    history = _mapping(findings, "wayback_article_namespace")
    _equal(history.get("query_count"), 2, "Wayback article-namespace query count")
    _equal(
        history.get("successful_query_count"),
        2,
        "Wayback successful article-namespace queries",
    )
    _equal(history.get("captures_per_query"), 5, "Wayback captures per query")
    _equal(
        history.get("historical_supplement_candidate_count"),
        0,
        "Wayback historical supplement candidates",
    )
    _false(
        history.get("ordinary_article_captures_are_supplement_evidence"),
        "ordinary archived article captures as supplement evidence",
    )

    static_history = _mapping(findings, "wayback_static_attachment_namespace")
    _equal(static_history.get("query_count"), 2, "Wayback static query count")
    _equal(static_history.get("timeout_count"), 2, "Wayback static timeout count")
    _equal(
        static_history.get("successful_query_count"),
        0,
        "Wayback static successful-query count",
    )
    _false(
        static_history.get("complete_negative_search_established"),
        "a complete negative Wayback static-attachment search",
    )

    archived = _mapping(findings, "wayback_archived_article")
    _equal(archived.get("html_2021_network_error"), "TimeoutError", "2021 HTML result")
    _equal(archived.get("xml_2022_http_status"), 200, "2022 XML HTTP status")
    _equal(archived.get("xml_2022_body_bytes"), 324681, "2022 XML byte count")
    _equal(
        archived.get("xml_2022_body_sha256"),
        "aa4fe316fadcc08c7b1369f475c1462af8f96fc53c477ff63434b236e571215d",
        "2022 XML SHA-256",
    )
    _true(archived.get("xml_2022_doi_marker_present"), "2022 XML DOI marker")
    _true(
        archived.get("xml_2022_supplement_text_marker_present"),
        "2022 XML supplement text marker",
    )
    _equal(
        archived.get("xml_2022_candidate_link_count"),
        0,
        "2022 XML candidate-link count",
    )
    _equal(
        archived.get("historical_supplement_link_count"),
        0,
        "archived supplement-link count",
    )
    _false(
        archived.get("both_archived_article_captures_successfully_inspected"),
        "successful inspection of both archived article captures",
    )


def _validate_boundaries(record: Mapping[str, Any]) -> None:
    recovery = _mapping(record, "recovery_boundary")
    _equal(set(recovery), set(_RECOVERY_FALSE_FIELDS), "recovery-boundary schema")
    for key in _RECOVERY_FALSE_FIELDS:
        _false(recovery.get(key), key.replace("_", " "))

    scientific = _mapping(record, "scientific_boundary")
    _equal(set(scientific), set(_SCIENTIFIC_FALSE_FIELDS), "scientific-boundary schema")
    for key in _SCIENTIFIC_FALSE_FIELDS:
        _false(scientific.get(key), key.replace("_", " "))


def _validate_remaining_routes(record: Mapping[str, Any]) -> None:
    routes = record.get("remaining_authoritative_resolution_routes")
    if not isinstance(routes, list) or len(routes) != 3:
        raise BenchmarkIntegrityError(
            "VISUS supplement recovery must preserve three authoritative routes."
        )
    _equal(
        [row.get("route") if isinstance(row, Mapping) else None for row in routes],
        [
            "publisher-or-archive-exact-object",
            "author-or-institutional-recovery",
            "authoritative-redeposit",
        ],
        "remaining authoritative routes",
    )
    for row in routes:
        if not isinstance(row, Mapping) or set(row) != {
            "route",
            "requirement",
            "promotion_condition",
        }:
            raise BenchmarkIntegrityError(
                "VISUS supplement-recovery route schema drifted."
            )
        if not str(row["requirement"]).strip() or not str(row["promotion_condition"]).strip():
            raise BenchmarkIntegrityError(
                "VISUS supplement-recovery route text must remain non-empty."
            )


def validate_visus_supplement_recovery_exhaustion(
    record_or_path: Mapping[str, Any] | str | Path,
    *,
    source_recheck_path: str | Path = DEFAULT_SOURCE_RECHECK_PATH,
) -> dict[str, Any]:
    """Validate the immutable VISUS 2021 supplement-recovery checkpoint."""
    record = _load(record_or_path)
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("checked_on"), "2026-09-10", "review date")
    _equal(record.get("status"), STATUS, "status")

    _validate_source_binding(record, source_recheck_path)
    _validate_probe_bindings(record)
    _validate_paper_statement(record)
    _validate_surface_findings(record)
    _validate_boundaries(record)
    _validate_remaining_routes(record)

    claim_limits = record.get("claim_limits")
    if not isinstance(claim_limits, list) or len(claim_limits) != 8:
        raise BenchmarkIntegrityError(
            "VISUS supplement recovery must preserve eight claim limits."
        )
    if any(not isinstance(item, str) or not item.strip() for item in claim_limits):
        raise BenchmarkIntegrityError(
            "VISUS supplement-recovery claim limits must be non-empty strings."
        )

    claimed = str(record.get("evidence_fingerprint_sha256", ""))
    _equal(claimed, EXPECTED_EVIDENCE_FINGERPRINT_SHA256, "evidence fingerprint")
    _equal(
        evidence_fingerprint(record),
        EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        "canonical evidence body",
    )
    return record
