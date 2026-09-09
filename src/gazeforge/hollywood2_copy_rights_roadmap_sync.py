"""Fail-closed roadmap synchronization for Hollywood2EM copy and rights evidence.

This module records a narrow administrative split: the canonical GIN hand-labelled
Hollywood2EM ground-truth source identity is already audited, while exact reuse terms
and participant identity mapping remain unresolved. It creates no new empirical claim.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .hollywood2_author_license_evidence import validate_hollywood2_author_license_evidence
from .hollywood2_evidence import validate_hollywood2_authoritative_evidence
from .hollywood2_history_evidence import validate_hollywood2_gin_history_evidence
from .hollywood2_original_subject_metadata_evidence import (
    validate_hollywood2_original_subject_evidence,
)

RECORD_TYPE = "hollywood2-copy-rights-roadmap-sync-evidence-v1"
STATUS = "verified-roadmap-split-copy-identity-complete-rights-unresolved"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "948b4a3511217ea8a25be55c86495ee17af40ed5fa0598baf1cec283fab2e526"
)
GIN_REPOSITORY = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git"
GIN_COMMIT_SHA1 = "870fa6d6209c9085260918d61433a0a2c70fd497"
SOURCE_LEDGER_FINGERPRINT_SHA256 = (
    "51dd0883cf5b7966a4caea94fb9ac97e43bee6cf716423f26f268810041d3030"
)
AUTHORITATIVE_EVIDENCE_FINGERPRINT_SHA256 = (
    "d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea"
)
HISTORY_EVIDENCE_FINGERPRINT_SHA256 = (
    "c7d2f477a66feca3676482ffdabff2b0778196db99e48b86104fe86d0f5bfae1"
)
AUTHOR_LICENSE_EVIDENCE_FINGERPRINT_SHA256 = (
    "b01da719afe18f4eb0103a17d6e8c85f3750ba299050f8026063a9ebb55b1b2e"
)
ORIGINAL_SUBJECT_EVIDENCE_FINGERPRINT_SHA256 = (
    "ba7813dd4f87c4a20ee75f3a9e537e329bca74c519b7bc65a5ba5e5095dd8a5c"
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return the record SHA-256 without its self-fingerprint field."""
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
            f"Could not load Hollywood2 copy-rights roadmap evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "Hollywood2 copy-rights roadmap evidence must be one JSON object."
        )
    return payload


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(
            f"Hollywood2 copy-rights roadmap field {key!r} is missing."
        )
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"Hollywood2 copy-rights roadmap {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(
            f"Hollywood2 copy-rights roadmap must preserve {label}."
        )


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(
            f"Hollywood2 copy-rights roadmap must not promote {label}."
        )


def _validate_copy_identity(copy: Mapping[str, Any]) -> None:
    _equal(copy.get("repository"), GIN_REPOSITORY, "canonical repository")
    _equal(copy.get("pinned_commit_sha1"), GIN_COMMIT_SHA1, "canonical commit")
    _equal(copy.get("ground_truth_file_count"), 697, "ground-truth file count")
    _equal(copy.get("ground_truth_total_bytes"), 137328178, "ground-truth byte count")
    _equal(copy.get("ground_truth_total_samples"), 3871580, "ground-truth sample count")
    _equal(copy.get("clip_count"), 56, "clip count")
    _equal(copy.get("file_subject_token_count"), 16, "source-token count")
    _equal(
        copy.get("source_identity_ledger_fingerprint_sha256"),
        SOURCE_LEDGER_FINGERPRINT_SHA256,
        "source-identity ledger fingerprint",
    )
    _true(
        copy.get("authoritative_ground_truth_copy_identity_audited"),
        "authoritative source-identity audit",
    )
    _false(copy.get("source_bytes_redistributed_by_gazeforge"), "source-byte redistribution")


def _validate_rights_boundary(rights: Mapping[str, Any]) -> None:
    _true(rights.get("author_open_source_declaration_verified"), "author declaration")
    for key, label in (
        ("exact_annotation_repository_license_identifier_verified", "exact licence identifier"),
        ("exact_annotation_repository_license_text_verified", "exact licence text"),
        ("analysis_use_terms_resolved", "analysis-use terms"),
        ("raw_annotation_redistribution_terms_resolved", "redistribution terms"),
        ("article_cc_by_promoted_to_dataset_license", "article CC BY as dataset licence"),
        ("original_hollywood2_terms_promoted_to_gin_terms", "original-source rights inheritance"),
    ):
        _false(rights.get(key), label)


def _validate_identity_boundary(identity: Mapping[str, Any]) -> None:
    _true(identity.get("file_subject_tokens_recovered"), "source-token recovery")
    _equal(identity.get("file_subject_token_count"), 16, "source-token count")
    _false(identity.get("participant_identity_mapping_verified"), "participant identity mapping")
    _false(identity.get("participant_group_mapping_verified"), "participant group mapping")


def _validate_roadmap(roadmap: Mapping[str, Any]) -> None:
    _true(
        roadmap.get("authoritative_copy_source_identity_component_satisfied"),
        "authoritative copy/source-identity roadmap component",
    )
    for key, label in (
        ("current_reuse_terms_component_satisfied", "current reuse-terms component"),
        ("participant_identity_mapping_component_satisfied", "participant mapping component"),
        ("lund_hollywood2_cross_dataset_component_satisfied", "cross-dataset component"),
    ):
        _false(roadmap.get(key), label)


def _validate_scientific_boundary(boundary: Mapping[str, Any]) -> None:
    for key, label in (
        ("new_empirical_performance_claim_created", "new empirical performance"),
        ("participant_disjoint_hollywood2_validation_created", "participant-disjoint validation"),
        ("cross_dataset_validation_created", "cross-dataset validation"),
        ("redistribution_authorized", "redistribution authorization"),
    ):
        _false(boundary.get(key), label)


def validate_hollywood2_copy_rights_roadmap_sync(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the immutable Hollywood2EM copy/rights roadmap split record."""
    record = _load(record_or_path)
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("status"), STATUS, "status")
    _equal(record.get("checked_on"), "2026-09-09", "review date")

    upstream = _mapping(record, "upstream_evidence")
    expected_upstream = {
        "authoritative_ground_truth_evidence_fingerprint_sha256": (
            AUTHORITATIVE_EVIDENCE_FINGERPRINT_SHA256
        ),
        "gin_history_evidence_fingerprint_sha256": HISTORY_EVIDENCE_FINGERPRINT_SHA256,
        "author_license_statement_evidence_fingerprint_sha256": (
            AUTHOR_LICENSE_EVIDENCE_FINGERPRINT_SHA256
        ),
        "original_subject_metadata_evidence_fingerprint_sha256": (
            ORIGINAL_SUBJECT_EVIDENCE_FINGERPRINT_SHA256
        ),
    }
    for key, expected in expected_upstream.items():
        _equal(upstream.get(key), expected, f"upstream evidence {key}")

    _validate_copy_identity(_mapping(record, "canonical_copy_identity"))
    _validate_rights_boundary(_mapping(record, "rights_boundary"))
    _validate_identity_boundary(_mapping(record, "identity_boundary"))
    _validate_roadmap(_mapping(record, "roadmap"))
    _validate_scientific_boundary(_mapping(record, "scientific_boundary"))

    interpretation = record.get("interpretation")
    if not isinstance(interpretation, list) or len(interpretation) != 4:
        raise BenchmarkIntegrityError(
            "Hollywood2 copy-rights roadmap must retain four interpretation statements."
        )

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    _equal(stored, evidence_fingerprint(record), "self-fingerprint")
    _equal(stored, EXPECTED_EVIDENCE_FINGERPRINT_SHA256, "immutable fingerprint")
    return record


def validate_hollywood2_copy_rights_roadmap_sync_with_upstreams(
    record_or_path: Mapping[str, Any] | str | Path,
    *,
    authoritative_evidence_path: str | Path,
    history_evidence_path: str | Path,
    author_license_evidence_path: str | Path,
    original_subject_evidence_path: str | Path,
) -> dict[str, Any]:
    """Validate the roadmap split and every reviewed upstream evidence record."""
    record = validate_hollywood2_copy_rights_roadmap_sync(record_or_path)
    upstream = _mapping(record, "upstream_evidence")

    authoritative = validate_hollywood2_authoritative_evidence(authoritative_evidence_path)
    history = validate_hollywood2_gin_history_evidence(history_evidence_path)
    author_license = validate_hollywood2_author_license_evidence(author_license_evidence_path)
    original_subject = validate_hollywood2_original_subject_evidence(original_subject_evidence_path)

    pairs = (
        (
            authoritative,
            "authoritative_ground_truth_evidence_fingerprint_sha256",
        ),
        (history, "gin_history_evidence_fingerprint_sha256"),
        (author_license, "author_license_statement_evidence_fingerprint_sha256"),
        (original_subject, "original_subject_metadata_evidence_fingerprint_sha256"),
    )
    for upstream_record, key in pairs:
        _equal(
            upstream_record.get("evidence_fingerprint_sha256"),
            upstream.get(key),
            f"revalidated upstream {key}",
        )
    return record
