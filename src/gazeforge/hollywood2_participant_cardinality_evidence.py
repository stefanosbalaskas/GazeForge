"""Fail-closed validation for Hollywood2 participant-cardinality evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "hollywood2-participant-cardinality-evidence-v1"
STATUS = (
    "reviewed-publication-lineage-cardinality-drift-unresolved-no-participant-crosswalk"
)
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "c27b11f9d38d29aa09f0971a1a8189d5e82e444bde4f10dd585ce153c683ca10"
)
EXPECTED_ORIGINAL_SUBJECT_EVIDENCE_FINGERPRINT = (
    "ba7813dd4f87c4a20ee75f3a9e537e329bca74c519b7bc65a5ba5e5095dd8a5c"
)
EXPECTED_GROUND_TRUTH_EVIDENCE_FINGERPRINT = (
    "d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea"
)
EXPECTED_TOKENS = (
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
EXPECTED_ABSENT_TOKENS = ("007", "009", "016")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Recompute the evidence SHA-256 excluding its self-fingerprint field."""

    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(value: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    try:
        payload = json.loads(Path(value).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load Hollywood2 participant-cardinality evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "Hollywood2 participant-cardinality evidence must be a JSON object."
        )
    return payload


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(
            f"Hollywood2 participant-cardinality section {key!r} is missing."
        )
    return value


def _eq(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(
            f"Hollywood2 participant-cardinality {label} drifted."
        )


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(
            f"Hollywood2 participant-cardinality must preserve {label}."
        )


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(
            f"Hollywood2 participant-cardinality must not promote {label}."
        )


def validate_hollywood2_participant_cardinality_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate immutable cardinality drift evidence and all non-promotion gates."""

    record = _load(record_or_path)
    _eq(record.get("record_type"), RECORD_TYPE, "record type")
    _eq(record.get("status"), STATUS, "status")
    _eq(record.get("checked_on"), "2026-09-10", "review date")

    source = _mapping(record, "source_binding")
    _eq(source.get("arxiv_id"), "1312.7570v1", "arXiv identity")
    _eq(source.get("arxiv_submitted_on"), "2013-12-29", "arXiv date")
    _eq(
        source.get("arxiv_url"),
        "https://arxiv.org/abs/1312.7570v1",
        "arXiv URL",
    )
    _eq(
        source.get("final_article_doi"),
        "10.1109/TPAMI.2014.2366154",
        "final DOI",
    )
    _eq(source.get("final_article_pubmed_id"), "26352449", "PubMed identity")
    _eq(
        source.get("original_subject_metadata_evidence_fingerprint_sha256"),
        EXPECTED_ORIGINAL_SUBJECT_EVIDENCE_FINGERPRINT,
        "original-subject evidence binding",
    )
    _eq(
        source.get("authoritative_ground_truth_evidence_fingerprint_sha256"),
        EXPECTED_GROUND_TRUTH_EVIDENCE_FINGERPRINT,
        "ground-truth evidence binding",
    )

    surfaces = _mapping(record, "reviewed_cardinality_surfaces")
    original = _mapping(surfaces, "frozen_original_distribution")
    _eq(original.get("subject_count"), 16, "original subject count")
    _eq(original.get("active_action_recognition_subject_count"), 12, "active count")
    _eq(original.get("free_viewing_subject_count"), 4, "free-viewing count")
    _eq(
        original.get("scene_context_subject_count_recovered_from_this_surface"),
        None,
        "original context-group availability",
    )
    _false(original.get("subject_id_ledger_recovered"), "subject ledger recovery")

    arxiv = _mapping(surfaces, "author_arxiv_v1")
    _eq(arxiv.get("reported_frames"), 497107, "arXiv frame count")
    _eq(arxiv.get("reported_subject_count"), 16, "arXiv subject count")
    _eq(arxiv.get("human_subjects_total"), 16, "arXiv human-subject total")
    _eq(arxiv.get("active_action_recognition_subject_count"), 12, "arXiv active count")
    _eq(arxiv.get("free_viewing_subject_count"), 4, "arXiv free-viewing count")
    _false(
        arxiv.get("scene_context_recognition_present_in_reviewed_v1"),
        "scene-context presence in reviewed v1",
    )

    final = _mapping(surfaces, "final_pami_article_abstract")
    _eq(final.get("reported_frames"), 497107, "final frame count")
    _eq(final.get("reported_subject_count"), 19, "final subject count")
    _true(final.get("visual_action_recognition_present"), "final action-recognition scope")
    _true(final.get("scene_context_recognition_present"), "final scene-context scope")
    _true(final.get("free_viewing_present"), "final free-viewing scope")
    _false(final.get("participant_identity_ledger_exposed_in_abstract"), "abstract ledger")

    assessment = _mapping(record, "cardinality_assessment")
    _eq(assessment.get("earlier_author_surface_subject_count"), 16, "earlier count")
    _eq(assessment.get("final_article_surface_subject_count"), 19, "final count")
    _eq(assessment.get("observed_subject_count_delta"), 3, "count delta")
    _true(
        assessment.get("publication_lineage_cardinality_drift_observed"),
        "publication-lineage drift",
    )
    _true(
        assessment.get("dataset_or_task_scope_expansion_is_plausible"),
        "plausible scope expansion",
    )
    for key in (
        "exact_version_relationship_resolved",
        "exact_added_or_removed_subject_identities_resolved",
        "automatic_cardinality_reconciliation_permitted",
        "current_16_subject_distribution_may_be_equated_to_all_final_19_subjects",
    ):
        _false(assessment.get(key), key)

    token = _mapping(record, "gin_token_context")
    _eq(token.get("token_count"), 16, "GIN token count")
    _eq(tuple(token.get("stable_three_digit_tokens", [])), EXPECTED_TOKENS, "GIN tokens")
    _eq(
        tuple(token.get("absent_numbers_within_001_to_019", [])),
        EXPECTED_ABSENT_TOKENS,
        "GIN numeric holes",
    )
    _true(token.get("token_count_matches_16_subject_surface"), "count coincidence")
    _true(
        token.get("three_missing_numbers_match_observed_16_to_19_delta"),
        "numeric-hole cardinality coincidence",
    )
    for key in (
        "token_count_match_is_mapping_evidence",
        "numeric_hole_count_is_mapping_or_group_evidence",
        "tokens_are_verified_original_subject_ids",
    ):
        _false(token.get(key), key)

    forbidden = _mapping(record, "forbidden_inferences")
    for key, value in forbidden.items():
        _false(value, key)

    mapping = _mapping(record, "mapping_boundary")
    for key, value in mapping.items():
        _false(value, key)

    rights = _mapping(record, "rights_boundary")
    for key, value in rights.items():
        _false(value, key)

    scientific = _mapping(record, "scientific_boundary")
    for key, value in scientific.items():
        _false(value, key)

    stored = record.get("evidence_fingerprint_sha256")
    _eq(stored, evidence_fingerprint(record), "self-fingerprint")
    _eq(stored, EXPECTED_EVIDENCE_FINGERPRINT_SHA256, "immutable fingerprint")
    return record
