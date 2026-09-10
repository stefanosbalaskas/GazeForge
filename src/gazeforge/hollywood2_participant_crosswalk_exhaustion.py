"""Fail-closed validation for Hollywood2 participant-crosswalk exhaustion evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "hollywood2-participant-crosswalk-exhaustion-evidence-v1"
STATUS = "reviewed-public-authoritative-surfaces-exhausted-no-gin-participant-crosswalk"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "5900a3515243f92ea374a0dc5d1d80e6c95d64b1dc6fa7b4f698df85488eaafa"
)
GIN_REPOSITORY = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git"
GIN_HEAD = "870fa6d6209c9085260918d61433a0a2c70fd497"
GIN_TOKENS = (
    "001",
    "002",
    "003",
    "004",
    "005",
    "006",
    "008",
    "010",
    "011",
    "012",
    "013",
    "014",
    "015",
    "017",
    "018",
    "019",
)
MISSING_NUMERIC_TOKENS = ("007", "009", "016")

_EXPECTED_SOURCE_BINDING = {
    "gin_repository": GIN_REPOSITORY,
    "gin_pinned_commit_sha1": GIN_HEAD,
    "gin_history_evidence_fingerprint_sha256": (
        "c7d2f477a66feca3676482ffdabff2b0778196db99e48b86104fe86d0f5bfae1"
    ),
    "original_subject_metadata_evidence_fingerprint_sha256": (
        "ba7813dd4f87c4a20ee75f3a9e537e329bca74c519b7bc65a5ba5e5095dd8a5c"
    ),
    "participant_cardinality_evidence_fingerprint_sha256": (
        "c27b11f9d38d29aa09f0971a1a8189d5e82e444bde4f10dd585ce153c683ca10"
    ),
    "participant_ledger_intake_governance_fingerprint_sha256": (
        "b47cc0acea2ded577d140d38ca97ad71ce414d82a41b2675e5cac6fc2dc9135b"
    ),
    "original_description_url": "https://vision.imar.ro/eyetracking/description.php",
    "original_license_url": "https://vision.imar.ro/eyetracking/license.php",
    "original_archive_filename": "gaze_hollywood2.zip",
    "arxiv_identifier": "arXiv:1312.7570v1",
    "arxiv_url": "https://arxiv.org/abs/1312.7570",
    "final_article_doi": "10.1109/TPAMI.2014.2366154",
    "final_article_pmid": "26352449",
    "hollywood2em_article_doi": "10.16910/jemr.13.4.5",
    "hollywood2em_article_url": "https://bop.unibe.ch/JEMR/article/view/JEMR.13.4.5",
    "secondary_parser_repository": (
        "https://github.com/r-zemblys/EM-event-detection-evaluation"
    ),
    "secondary_parser_commit_sha1": "7a968b34485ee83b3afee050a5d9b3c1e6d48d88",
    "secondary_parser_path": "misc/data_parsers/tum.py",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return the evidence SHA-256 excluding its self-fingerprint field."""
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
            f"Could not load Hollywood2 crosswalk-exhaustion evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk-exhaustion evidence must be a JSON object."
        )
    return payload


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(
            f"Hollywood2 crosswalk-exhaustion field {key!r} is missing."
        )
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(
            f"Hollywood2 crosswalk-exhaustion {label} drifted."
        )


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(
            f"Hollywood2 crosswalk-exhaustion must preserve {label}."
        )


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(
            f"Hollywood2 crosswalk-exhaustion must not promote {label}."
        )


def validate_hollywood2_participant_crosswalk_exhaustion(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Strictly validate the immutable public-crosswalk exhaustion record."""
    record = _load(record_or_path)
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("checked_on"), "2026-09-10", "review date")

    binding = _mapping(record, "source_binding")
    for key, expected in _EXPECTED_SOURCE_BINDING.items():
        _equal(binding.get(key), expected, f"source binding {key}")

    tokens = _mapping(record, "gin_filename_token_context")
    _equal(tuple(tokens.get("stable_three_digit_tokens", [])), GIN_TOKENS, "token ledger")
    _equal(
        tuple(tokens.get("absent_numbers_within_001_to_019", [])),
        MISSING_NUMERIC_TOKENS,
        "missing numeric tokens",
    )
    _equal(tokens.get("token_count"), 16, "token count")
    _true(
        tokens.get("token_count_matches_earlier_public_subject_count"),
        "16-to-16 count match",
    )
    _true(
        tokens.get("numeric_hole_count_matches_16_to_19_publication_delta"),
        "three-hole cardinality coincidence",
    )
    _false(
        tokens.get("token_count_match_is_crosswalk_evidence"),
        "count-only crosswalk evidence",
    )
    _false(
        tokens.get("numeric_hole_match_is_crosswalk_evidence"),
        "numeric-hole crosswalk evidence",
    )

    findings = _mapping(record, "reviewed_surface_findings")
    original = _mapping(findings, "original_public_distribution")
    _equal(original.get("subject_count"), 16, "original subject count")
    _equal(original.get("active_subject_count"), 12, "active subject count")
    _equal(original.get("free_viewing_subject_count"), 4, "free-viewing subject count")
    _true(original.get("included_readme_referenced"), "included README reference")
    for key in (
        "public_subject_ledger_exposed_on_description_page",
        "gin_filename_token_mapping_exposed",
        "task_group_membership_by_gin_token_exposed",
    ):
        _false(original.get(key), key)

    access = _mapping(findings, "original_access_and_rights")
    _true(
        access.get("academic_use_license_page_public"),
        "public academic-use license page",
    )
    _true(
        access.get("archive_access_requires_normal_institutional_access"),
        "normal institutional access requirement",
    )
    for key in (
        "login_or_license_gate_bypassed",
        "archive_download_performed_by_this_audit",
        "raw_gaze_inspected_by_this_audit",
    ):
        _false(access.get(key), key)

    lineage = _mapping(findings, "publication_lineage")
    _equal(
        lineage.get("arxiv_v1_reports_subject_count"),
        16,
        "arXiv-v1 subject count",
    )
    _equal(
        lineage.get("final_article_reports_subject_count"),
        19,
        "final-article subject count",
    )
    _true(
        lineage.get("cardinality_drift_already_frozen_elsewhere"),
        "separate cardinality evidence",
    )
    _false(
        lineage.get("publication_cardinality_resolves_token_identity"),
        "cardinality-based identity",
    )
    _false(
        lineage.get("free_viewing_ordinal_labels_resolve_gin_tokens"),
        "ordinal-label identity",
    )

    article = _mapping(findings, "hollywood2em_article")
    _equal(article.get("annotated_clip_count"), 56, "Hollywood2EM annotated clip count")
    _equal(article.get("observer_count"), 16, "Hollywood2EM observer count")
    _true(article.get("links_canonical_gin_dataset"), "Hollywood2EM GIN link")
    _false(
        article.get("explicit_filename_token_to_original_subject_id_crosswalk_recovered"),
        "article participant crosswalk",
    )
    _false(
        article.get("explicit_filename_token_to_task_group_crosswalk_recovered"),
        "article task-group crosswalk",
    )

    history = _mapping(findings, "canonical_gin_history")
    _equal(history.get("reachable_commit_count"), 7, "GIN history commit count")
    _equal(history.get("readme_unique_version_count"), 3, "GIN README version count")
    _false(
        history.get("participant_or_identity_keyword_ever_present_in_readme_history"),
        "historical README participant mapping",
    )
    _true(
        history.get("token_set_stable_from_ground_truth_move_commit"),
        "stable GIN token syntax",
    )
    _false(
        history.get("history_links_tokens_to_original_subject_ids"),
        "historical token crosswalk",
    )

    secondary = _mapping(findings, "secondary_public_implementation")
    _true(secondary.get("parser_reviewed"), "secondary parser review")
    _true(secondary.get("preserves_hollywood2em_paths"), "secondary path preservation")
    for key in (
        "interprets_filename_prefix_as_participant_id",
        "interprets_filename_prefix_as_task_group",
        "authoritative_for_original_participant_identity",
    ):
        _false(secondary.get(key), key)

    crosswalk = _mapping(record, "crosswalk_boundary")
    for key in (
        "gin_tokens_are_original_participant_ids",
        "gin_token_to_original_subject_id_verified",
        "gin_token_to_task_group_verified",
        "participant_identity_mapping_verified",
        "missing_numeric_tokens_identify_additional_subjects",
        "missing_numeric_tokens_define_task_group",
        "ordinal_free_view_labels_map_to_gin_tokens",
        "earlier_16_subject_count_defines_gin_token_identity",
        "final_19_subject_count_defines_gin_token_identity",
        "secondary_parser_is_authoritative_identity_evidence",
    ):
        _false(crosswalk.get(key), key)

    scientific = _mapping(record, "scientific_boundary")
    for key in (
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "frozen_evidence_performance_claim_created",
        "native_60hz_gp3_validity_created",
        "new_empirical_performance_claim_created",
        "rights_scope_promoted_by_crosswalk_audit",
        "raw_gaze_redistributed",
    ):
        _false(scientific.get(key), key)

    routes = record.get("remaining_authoritative_resolution_routes")
    observed_routes = [
        item.get("route") for item in routes if isinstance(item, Mapping)
    ] if isinstance(routes, list) else []
    expected_routes = [
        "authorized-original-archive-metadata",
        "author-or-institution-explicit-crosswalk",
        "author-supplied-reviewed-ledger",
    ]
    if observed_routes != expected_routes:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk-exhaustion resolution routes drifted."
        )

    limits = record.get("claim_limits")
    if not isinstance(limits, list) or len(limits) != 6:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk-exhaustion claim limits drifted."
        )

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    calculated = evidence_fingerprint(record)
    if stored != calculated:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk-exhaustion self-fingerprint is invalid."
        )
    if stored != EXPECTED_EVIDENCE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError(
            "Hollywood2 crosswalk-exhaustion immutable fingerprint drifted."
        )
    return record
