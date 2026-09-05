"""Fail-closed validation for Hollywood2 author-level rights and mapping assertions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "hollywood2-author-rights-mapping-assertions-v1"
STATUS = "verified-author-assertions-exact-license-and-id-list-unresolved"
EXPECTED_FINGERPRINT = "cc890d995ce6ae9d55e4e989937bfee2c6e10eb98ed71ac10456424ff38c4462"
GIN_COMMIT = "870fa6d6209c9085260918d61433a0a2c70fd497"
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


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return SHA-256 after excluding the self-fingerprint field."""

    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(record_or_path: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path)
    path = Path(record_or_path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(f"Could not load Hollywood2 author assertions: {exc}") from exc
    if not isinstance(value, dict):
        raise BenchmarkIntegrityError("Hollywood2 author assertions must be a JSON object.")
    return value


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"Hollywood2 author-assertion field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"Hollywood2 author-assertion {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"Hollywood2 author assertions must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"Hollywood2 author assertions must not promote {label}.")


def validate_hollywood2_author_assertions(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the conservative author-assertion evidence contract."""

    record = _load(record_or_path)
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("checked_on"), "2026-09-05", "review date")

    sources = _mapping(record, "sources")
    agtzidis = _mapping(sources, "agtzidis_thesis")
    _equal(agtzidis.get("author"), "Ioannis Agtzidis", "Agtzidis author")
    _equal(
        agtzidis.get("title"),
        "Towards a better understanding of eye movements in natural contexts",
        "Agtzidis thesis title",
    )
    _equal(agtzidis.get("source_class"), "author-doctoral-thesis", "Agtzidis source class")
    _true(agtzidis.get("indexed_text_reviewed"), "Agtzidis indexed-text review")
    _true(agtzidis.get("assertion_applies_to_hollywood2em"), "Hollywood2EM footnote binding")
    _false(agtzidis.get("source_bytes_frozen_by_gazeforge"), "thesis-byte freezing")

    mathe = _mapping(sources, "mathe_thesis")
    _equal(mathe.get("author"), "Stefan Mathe", "Mathe author")
    _equal(mathe.get("title"), "Actions in the Eye", "Mathe thesis title")
    _equal(mathe.get("source_class"), "author-doctoral-thesis", "Mathe source class")
    _true(mathe.get("indexed_text_reviewed"), "Mathe indexed-text review")
    _true(mathe.get("cross_task_groups_disjoint"), "cross-task group disjointness")
    _equal(
        mathe.get("hollywood2_group_counts"),
        {"action_recognition": 12, "context_recognition": 4, "free_viewing": 4},
        "Hollywood2 task-group counts",
    )
    _false(mathe.get("source_bytes_frozen_by_gazeforge"), "Mathe thesis-byte freezing")

    gin = _mapping(record, "gin_repository_state")
    _equal(gin.get("commit_sha1"), GIN_COMMIT, "GIN commit")
    _equal(tuple(gin.get("file_subject_tokens", [])), GIN_TOKENS, "GIN subject tokens")
    _equal(gin.get("file_subject_token_count"), 16, "GIN token count")
    _false(gin.get("repository_license_file_recovered"), "GIN licence-file recovery")

    rights = _mapping(record, "rights_interpretation")
    _true(rights.get("author_open_source_license_assertion_verified"), "author licence assertion")
    _equal(rights.get("author_assertion_source"), "agtzidis_thesis", "licence assertion source")
    _equal(
        rights.get("analysis_use_terms_status"),
        "author_open_source_assertion_verified_exact_terms_unresolved",
        "GIN analysis-use state",
    )
    _equal(
        rights.get("raw_annotation_redistribution_terms_status"),
        "unresolved",
        "GIN redistribution state",
    )
    for key, label in (
        ("exact_license_identifier_verified", "exact licence identifier"),
        ("exact_license_text_recovered", "exact licence text"),
        ("repository_license_file_recovered", "repository licence file"),
        ("article_cc_by_is_dataset_license", "article licence as dataset licence"),
        (
            "underlying_hollywood2_license_automatically_applies_to_gin",
            "automatic underlying-licence inheritance",
        ),
        ("license_inference_permitted", "licence inference"),
    ):
        _false(rights.get(key), label)

    participant = _mapping(record, "participant_mapping_interpretation")
    _true(
        participant.get("author_public_dataset_subject_ids_within_groups_assertion_verified"),
        "author subject-ID-structure assertion",
    )
    _equal(participant.get("author_assertion_source"), "mathe_thesis", "mapping assertion source")
    _equal(participant.get("published_hollywood2_action_recognition_count"), 12, "active count")
    _equal(participant.get("published_hollywood2_free_viewing_count"), 4, "free-viewing count")
    _equal(participant.get("published_hollywood2_context_recognition_count"), 4, "context count")
    _true(participant.get("published_cross_task_groups_disjoint"), "cross-task disjointness")
    _true(
        participant.get("gin_token_count_matches_hollywood2em_observer_count"),
        "token-count corroboration",
    )
    for key, label in (
        ("exact_original_subject_id_list_recovered", "exact original ID list"),
        ("gin_tokens_verified_as_original_public_dataset_subject_ids", "GIN token semantics"),
        ("gin_token_to_task_group_mapping_verified", "token-to-task mapping"),
        ("participant_identity_mapping_verified", "participant identity mapping"),
        ("participant_disjoint_split_authorized", "participant-disjoint split authorization"),
        ("mapping_inference_permitted", "mapping inference"),
    ):
        _false(participant.get(key), label)

    boundary = _mapping(record, "scientific_boundary")
    _true(boundary.get("author_open_source_license_assertion_created"), "licence assertion evidence")
    _true(
        boundary.get("author_public_dataset_subject_id_structure_assertion_created"),
        "subject-ID-structure evidence",
    )
    for key, label in (
        ("exact_gin_license_resolved", "exact GIN licence resolution"),
        ("gin_annotation_redistribution_resolved", "GIN redistribution resolution"),
        ("exact_original_subject_id_list_recovered", "original subject-ID list recovery"),
        ("gin_subject_token_semantics_verified", "GIN subject-token semantics"),
        ("participant_group_membership_by_token_verified", "participant-group mapping"),
        ("participant_identity_mapping_verified", "participant identity mapping"),
        ("participant_disjoint_model_validation_created", "participant-disjoint validation"),
        ("cross_dataset_validation_created", "cross-dataset validation"),
        ("independent_human_human_agreement_created", "independent human-human agreement"),
        ("frozen_evidence_performance_claim_created", "performance Frozen Evidence"),
    ):
        _false(boundary.get(key), label)

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    calculated = evidence_fingerprint(record)
    if stored != calculated:
        raise BenchmarkIntegrityError("Hollywood2 author-assertion self-fingerprint is invalid.")
    if stored != EXPECTED_FINGERPRINT:
        raise BenchmarkIntegrityError("Hollywood2 author-assertion immutable v1 fingerprint drifted.")
    return record
