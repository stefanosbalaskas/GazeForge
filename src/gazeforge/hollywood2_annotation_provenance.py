"""Validation for Hollywood2EM annotation-rights and participant-context evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

RECORD_TYPE = "hollywood2-annotation-provenance-evidence-v1"
STATUS = (
    "verified_author_open_source_declaration_and_upstream_subject_id_context_"
    "exact_terms_and_gin_mapping_unresolved"
)
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "a08510e43caca2a8e6d5c85e7b1ad41c9f312247cd9bd8367372f8ecad8aacab"
)
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


@dataclass(frozen=True, slots=True)
class Hollywood2AnnotationProvenanceEvidence:
    """Compact identity for the validated annotation-provenance record."""

    path: Path | None
    fingerprint_sha256: str
    author_open_source_declaration_verified: bool
    exact_license_identifier_verified: bool
    participant_identity_mapping_verified: bool


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return the canonical fingerprint excluding the stored fingerprint field."""

    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(
    record_or_path: Mapping[str, Any] | str | Path,
) -> tuple[dict[str, Any], Path | None]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path), None
    path = Path(record_or_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load Hollywood2 annotation provenance evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "Hollywood2 annotation provenance evidence must be a JSON object."
        )
    return payload, path


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(
            f"Hollywood2 annotation provenance field {key!r} is missing."
        )
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(
            f"Hollywood2 annotation provenance {label} drifted."
        )


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(
            f"Hollywood2 annotation provenance must preserve {label}."
        )


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(
            f"Hollywood2 annotation provenance must not promote {label}."
        )


def validate_hollywood2_annotation_provenance_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the frozen author declaration and participant-context evidence."""

    record, _ = _load(record_or_path)
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("checked_on"), "2026-09-05", "review date")

    scope = _mapping(record, "scope")
    _equal(
        scope.get("annotation_distribution"),
        "Agtzidis-Startsev-Dorr Hollywood2EM hand-labelled GIN repository",
        "annotation distribution",
    )
    _equal(
        scope.get("repository"),
        "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git",
        "repository URL",
    )
    _equal(scope.get("commit_sha1"), GIN_COMMIT, "GIN commit")

    declaration = _mapping(record, "author_declaration")
    _equal(declaration.get("author"), "Ioannis Agtzidis", "declaration author")
    _equal(
        declaration.get("title"),
        "Towards a better understanding of eye movements in natural contexts",
        "declaration source title",
    )
    _equal(
        declaration.get("institution"),
        "Technical University of Munich",
        "declaration institution",
    )
    _equal(declaration.get("year"), 2020, "declaration year")
    _equal(declaration.get("submitted_on"), "2020-06-15", "submission date")
    _equal(declaration.get("accepted_on"), "2020-09-08", "acceptance date")
    _equal(
        declaration.get("source_url"),
        "https://mediatum.ub.tum.de/doc/1538004/1538004.pdf",
        "declaration source URL",
    )
    _equal(declaration.get("chapter"), 4, "declaration chapter")
    _equal(declaration.get("chapter_page"), 27, "declaration chapter page")
    _equal(
        declaration.get("declaration_excerpt"),
        "All the data presented in this chapter are made publicly available "
        "with an open-source license.",
        "open-source declaration excerpt",
    )
    _equal(declaration.get("hollywood2_footnote_number"), 2, "Hollywood2 footnote")
    _equal(
        declaration.get("hollywood2_footnote_url"),
        "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em",
        "Hollywood2 footnote URL",
    )
    _true(
        declaration.get("declaration_applies_to_hollywood2em_by_explicit_footnote"),
        "explicit Hollywood2EM footnote binding",
    )
    _true(
        declaration.get("author_open_source_declaration_verified"),
        "author open-source declaration",
    )
    _false(
        declaration.get("exact_license_identifier_named_in_declaration"),
        "an exact license identifier from the declaration",
    )
    _false(
        declaration.get("exact_license_text_embedded_in_declaration"),
        "exact license text from the declaration",
    )
    _false(
        declaration.get("source_bytes_fingerprint_recovered"),
        "source-byte fingerprint recovery",
    )

    participant = _mapping(record, "upstream_participant_context")
    _equal(participant.get("author"), "Stefan Mathe", "participant-context author")
    _equal(participant.get("title"), "Actions in the Eye", "participant-context title")
    _equal(
        participant.get("institution"),
        "University of Toronto",
        "participant-context institution",
    )
    _equal(participant.get("year"), 2015, "participant-context year")
    _equal(
        participant.get("published_hollywood2_action_recognition_subject_count"),
        12,
        "action-recognition subject count",
    )
    _equal(
        participant.get("published_hollywood2_free_viewing_subject_count"),
        4,
        "free-viewing subject count",
    )
    _true(
        participant.get("original_public_dataset_declares_unique_subject_ids_within_groups"),
        "upstream unique-subject-ID semantics",
    )
    _equal(
        tuple(participant.get("gin_file_subject_tokens", [])),
        GIN_TOKENS,
        "GIN subject tokens",
    )
    _equal(participant.get("gin_file_subject_token_count"), 16, "GIN token count")
    _false(
        participant.get("gin_tokens_authoritatively_linked_to_original_unique_subject_ids"),
        "GIN-to-original subject-ID linkage",
    )
    _false(
        participant.get("participant_group_membership_by_gin_token_verified"),
        "participant group mapping",
    )
    _false(
        participant.get("participant_identity_mapping_verified"),
        "participant identity mapping",
    )
    _false(participant.get("mapping_inference_permitted"), "participant mapping inference")

    rights = _mapping(record, "rights_interpretation")
    _equal(rights.get("analysis_use_terms_status"), "unresolved", "analysis-use status")
    _equal(
        rights.get("raw_data_redistribution_terms_status"),
        "unresolved",
        "redistribution status",
    )
    _true(
        rights.get("author_open_source_declaration_verified"),
        "author open-source declaration in rights interpretation",
    )
    for key, label in (
        ("open_source_declaration_is_exact_license_text", "declaration as exact license text"),
        ("exact_license_identifier_verified", "exact license identifier"),
        ("repository_license_file_recovered", "repository license-file recovery"),
        ("dataset_specific_license_verified", "dataset-specific license verification"),
        ("article_cc_by_is_dataset_license", "article license as dataset license"),
        (
            "underlying_hollywood2_license_automatically_applies_to_annotation_repository",
            "automatic underlying-license inheritance",
        ),
        ("license_inference_permitted", "license inference"),
    ):
        _false(rights.get(key), label)

    boundary = _mapping(record, "scientific_boundary")
    _true(
        boundary.get("annotation_repository_author_open_source_declaration_verified"),
        "author declaration boundary",
    )
    _true(
        boundary.get("upstream_original_dataset_unique_subject_id_semantics_verified"),
        "upstream subject-ID semantics boundary",
    )
    for key, label in (
        ("annotation_repository_exact_license_identifier_verified", "exact license identifier"),
        ("annotation_repository_exact_license_text_recovered", "exact license text"),
        ("annotation_repository_rights_fully_resolved", "fully resolved annotation rights"),
        ("annotation_repository_redistribution_verified", "annotation redistribution"),
        (
            "gin_file_subject_token_to_original_subject_id_mapping_verified",
            "GIN token-to-subject mapping",
        ),
        ("participant_identity_mapping_verified", "participant identity mapping"),
        ("participant_disjoint_model_validation_created", "participant-disjoint validation"),
        ("cross_dataset_validation_created", "cross-dataset validation"),
        ("independent_human_human_agreement_created", "independent agreement"),
        ("frozen_evidence_performance_claim_created", "Frozen Evidence performance"),
    ):
        _false(boundary.get(key), label)

    limits = record.get("claim_limits")
    actions = record.get("next_required_actions")
    if not isinstance(limits, list) or not limits:
        raise BenchmarkIntegrityError(
            "Hollywood2 annotation provenance must preserve explicit claim limits."
        )
    if not isinstance(actions, list) or not actions:
        raise BenchmarkIntegrityError(
            "Hollywood2 annotation provenance must preserve next required actions."
        )

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    calculated = evidence_fingerprint(record)
    if stored != calculated:
        raise BenchmarkIntegrityError(
            "Hollywood2 annotation provenance self-fingerprint is invalid."
        )
    if stored != EXPECTED_EVIDENCE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError(
            "Hollywood2 annotation provenance immutable v1 fingerprint drifted."
        )
    return record


def load_hollywood2_annotation_provenance_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> Hollywood2AnnotationProvenanceEvidence:
    """Return a compact typed identity after full validation."""

    record, path = _load(record_or_path)
    validated = validate_hollywood2_annotation_provenance_evidence(record)
    rights = _mapping(validated, "rights_interpretation")
    participant = _mapping(validated, "upstream_participant_context")
    return Hollywood2AnnotationProvenanceEvidence(
        path=path,
        fingerprint_sha256=str(validated["evidence_fingerprint_sha256"]),
        author_open_source_declaration_verified=bool(
            rights["author_open_source_declaration_verified"]
        ),
        exact_license_identifier_verified=bool(
            rights["exact_license_identifier_verified"]
        ),
        participant_identity_mapping_verified=bool(
            participant["participant_identity_mapping_verified"]
        ),
    )
