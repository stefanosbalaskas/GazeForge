from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_explicit_crosswalk_certificate import (
    validate_certificate_record,
)
from gazeforge.hollywood2_explicit_crosswalk_intake import (
    CANDIDATE_RECORD_TYPE,
    CERTIFICATE_RECORD_TYPE,
    GIN_TOKENS,
    REVIEW_RECORD_TYPE,
    SOURCE_RECORD_TYPE,
    candidate_fingerprint,
    certificate_fingerprint,
    inspect_explicit_crosswalk_candidate,
    require_reviewed_explicit_crosswalk,
    review_fingerprint,
    validate_candidate_record,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _entries() -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for index, token in enumerate(GIN_TOKENS):
        values.append(
            {
                "gin_token": token,
                "original_subject_id": f"S{index + 1:02d}",
                "task_group": "active" if index < 12 else "free_viewing",
            }
        )
    return values


def _write_source_and_manifest(
    tmp_path: Path,
    *,
    entries: list[dict[str, str]] | None = None,
    authority: str = "original_distribution_metadata",
) -> tuple[Path, Path]:
    source = tmp_path / "authoritative-ledger.txt"
    source_bytes = (
        b"Synthetic test fixture representing an explicit authoritative mapping source.\n"
    )
    source.write_bytes(source_bytes)
    manifest = {
        "record_type": SOURCE_RECORD_TYPE,
        "source_reference": "synthetic-test-fixture://authoritative-ledger",
        "source_authority_claim": authority,
        "source_file_sha256": _sha256(source_bytes),
        "obtained_via_authorized_channel_affirmed": True,
        "mapping_entries": _entries() if entries is None else entries,
    }
    manifest_path = tmp_path / "crosswalk-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return source, manifest_path


def _review_dict(candidate: dict) -> dict:
    review = {
        "record_type": REVIEW_RECORD_TYPE,
        "decision": "approved",
        "candidate_fingerprint_sha256": candidate["candidate_fingerprint_sha256"],
        "reviewer": "Synthetic Reviewer",
        "reviewed_at": "2026-09-10T12:00:00+03:00",
        "source_authority_verified": True,
        "source_authority_evidence": "Synthetic authoritative-source evidence.",
        "mapping_explicit_in_source_verified": True,
        "mapping_explicitness_evidence": "Synthetic explicitness evidence.",
        "mapping_transcription_verified": True,
        "mapping_transcription_evidence": "Synthetic transcription evidence.",
        "task_group_semantics_verified": True,
        "task_group_semantics_evidence": "Synthetic task-group evidence.",
        "source_version_scope_verified": True,
        "source_version_scope_evidence": "Synthetic source-version evidence.",
        "rights_scope_promoted": False,
        "empirical_validation_created": False,
    }
    review["review_fingerprint_sha256"] = review_fingerprint(review)
    return review


def _write_review(tmp_path: Path, review: dict) -> Path:
    path = tmp_path / "crosswalk-review.json"
    path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _refingerprint_candidate(record: dict) -> dict:
    record["candidate_fingerprint_sha256"] = candidate_fingerprint(record)
    return record


def _refingerprint_review(record: dict) -> dict:
    record["review_fingerprint_sha256"] = review_fingerprint(record)
    return record


def _refingerprint_certificate(record: dict) -> dict:
    record["certificate_fingerprint_sha256"] = certificate_fingerprint(record)
    return record


def test_complete_candidate_is_non_promoting_and_private(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    validated = validate_candidate_record(candidate)

    assert validated["record_type"] == CANDIDATE_RECORD_TYPE
    assert validated["mapping_summary"]["entry_count"] == len(GIN_TOKENS)
    assert validated["mapping_summary"]["complete_gin_token_coverage"] is True
    assert validated["mapping_summary"]["one_to_one_subject_ids"] is True
    assert validated["mapping_summary"]["task_group_label_count"] == 2
    assert validated["review_boundary"]["participant_identity_mapping_verified"] is False
    assert validated["scientific_boundary"]["cross_dataset_validation_created"] is False

    serialized = json.dumps(validated)
    for entry in _entries():
        assert entry["original_subject_id"] not in serialized
    assert '"active"' not in serialized
    assert '"free_viewing"' not in serialized


def test_partial_candidate_is_allowed_but_not_complete(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path, entries=_entries()[:-1])
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    assert candidate["mapping_summary"]["entry_count"] == len(GIN_TOKENS) - 1
    assert candidate["mapping_summary"]["complete_gin_token_coverage"] is False


def test_unknown_token_is_rejected(tmp_path: Path) -> None:
    entries = _entries()
    entries[0]["gin_token"] = "007"
    source, manifest = _write_source_and_manifest(tmp_path, entries=entries)
    with pytest.raises(BenchmarkIntegrityError, match="unknown GIN token"):
        inspect_explicit_crosswalk_candidate(source, manifest)


def test_duplicate_token_is_rejected(tmp_path: Path) -> None:
    entries = _entries()
    entries[-1]["gin_token"] = entries[0]["gin_token"]
    source, manifest = _write_source_and_manifest(tmp_path, entries=entries)
    with pytest.raises(BenchmarkIntegrityError, match="duplicates GIN token"):
        inspect_explicit_crosswalk_candidate(source, manifest)


def test_source_sha_mismatch_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["source_file_sha256"] = "0" * 64
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="do not match"):
        inspect_explicit_crosswalk_candidate(source, manifest)


def test_unsupported_authority_claim_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path, authority="third_party_repack")
    with pytest.raises(BenchmarkIntegrityError, match="unsupported"):
        inspect_explicit_crosswalk_candidate(source, manifest)


def test_authorized_channel_affirmation_is_required(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["obtained_via_authorized_channel_affirmed"] = False
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="authorized-channel"):
        inspect_explicit_crosswalk_candidate(source, manifest)


def test_candidate_fingerprint_tamper_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    candidate["mapping_summary"]["entry_count"] -= 1
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint drifted"):
        validate_candidate_record(candidate)


def test_refingerprinted_candidate_mapping_promotion_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    candidate["review_boundary"]["participant_identity_mapping_verified"] = True
    _refingerprint_candidate(candidate)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_candidate_record(candidate)


def test_refingerprinted_candidate_scientific_promotion_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    candidate["scientific_boundary"]["participant_disjoint_model_validation_created"] = True
    _refingerprint_candidate(candidate)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_candidate_record(candidate)


def test_partial_candidate_cannot_be_review_promoted(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path, entries=_entries()[:-1])
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    review_path = _write_review(tmp_path, _review_dict(candidate))
    with pytest.raises(BenchmarkIntegrityError, match="complete canonical GIN-token coverage"):
        require_reviewed_explicit_crosswalk(source, manifest, candidate, review_path)


def test_duplicate_subject_ids_block_review_promotion(tmp_path: Path) -> None:
    entries = _entries()
    entries[-1]["original_subject_id"] = entries[0]["original_subject_id"]
    source, manifest = _write_source_and_manifest(tmp_path, entries=entries)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    assert candidate["mapping_summary"]["one_to_one_subject_ids"] is False
    review_path = _write_review(tmp_path, _review_dict(candidate))
    with pytest.raises(BenchmarkIntegrityError, match="one-to-one subject identifiers"):
        require_reviewed_explicit_crosswalk(source, manifest, candidate, review_path)


def test_candidate_must_replay_exact_local_source_and_manifest(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["source_reference"] = "synthetic-test-fixture://changed-reference"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    review_path = _write_review(tmp_path, _review_dict(candidate))
    with pytest.raises(BenchmarkIntegrityError, match="no longer matches"):
        require_reviewed_explicit_crosswalk(source, manifest, candidate, review_path)


def test_review_requires_explicit_approval(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    review = _review_dict(candidate)
    review["decision"] = "pending"
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match="decision='approved'"):
        require_reviewed_explicit_crosswalk(source, manifest, candidate, review_path)


def test_review_must_bind_exact_candidate(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    review = _review_dict(candidate)
    review["candidate_fingerprint_sha256"] = "0" * 64
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match="not bound"):
        require_reviewed_explicit_crosswalk(source, manifest, candidate, review_path)


def test_review_timestamp_requires_timezone(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    review = _review_dict(candidate)
    review["reviewed_at"] = "2026-09-10T12:00:00"
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match="timezone offset"):
        require_reviewed_explicit_crosswalk(source, manifest, candidate, review_path)


def test_review_requires_resolved_evidence(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    review = _review_dict(candidate)
    review["mapping_explicitness_evidence"] = "REVIEW_REQUIRED"
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match="mapping_explicitness_evidence"):
        require_reviewed_explicit_crosswalk(source, manifest, candidate, review_path)


def test_review_requires_all_verification_gates_true(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    review = _review_dict(candidate)
    review["source_version_scope_verified"] = False
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match="source_version_scope_verified=true"):
        require_reviewed_explicit_crosswalk(source, manifest, candidate, review_path)


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("rights_scope_promoted", "cannot promote dataset rights"),
        ("empirical_validation_created", "cannot create empirical validation"),
    ],
)
def test_review_cannot_promote_rights_or_empirical_validation(
    tmp_path: Path,
    field: str,
    message: str,
) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    review = _review_dict(candidate)
    review[field] = True
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match=message):
        require_reviewed_explicit_crosswalk(source, manifest, candidate, review_path)


def test_review_fingerprint_tamper_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    review = _review_dict(candidate)
    review["reviewer"] = "Changed Reviewer"
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match="review fingerprint drifted"):
        require_reviewed_explicit_crosswalk(source, manifest, candidate, review_path)


def test_approved_review_returns_private_certificate_and_in_memory_mapping(
    tmp_path: Path,
) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    review = _review_dict(candidate)
    review_path = _write_review(tmp_path, review)

    reviewed = require_reviewed_explicit_crosswalk(source, manifest, candidate, review_path)
    certificate = validate_certificate_record(reviewed.certificate)

    assert certificate["record_type"] == CERTIFICATE_RECORD_TYPE
    assert certificate["token_count"] == len(GIN_TOKENS)
    assert certificate["mapping_boundary"]["participant_identity_mapping_verified"] is True
    assert certificate["scientific_boundary"]["cross_dataset_validation_created"] is False
    assert reviewed.mapping[GIN_TOKENS[0]] == ("S01", "active")
    assert reviewed.mapping[GIN_TOKENS[-1]] == ("S16", "free_viewing")

    serialized = json.dumps(certificate)
    assert "S01" not in serialized
    assert "S16" not in serialized
    assert '"active"' not in serialized
    assert '"free_viewing"' not in serialized


def test_certificate_fingerprint_tamper_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    review_path = _write_review(tmp_path, _review_dict(candidate))
    certificate = require_reviewed_explicit_crosswalk(
        source,
        manifest,
        candidate,
        review_path,
    ).certificate
    certificate["token_count"] -= 1
    with pytest.raises(BenchmarkIntegrityError, match="token count drifted"):
        validate_certificate_record(certificate)


def test_refingerprinted_certificate_scientific_promotion_is_rejected(
    tmp_path: Path,
) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    review_path = _write_review(tmp_path, _review_dict(candidate))
    certificate = require_reviewed_explicit_crosswalk(
        source,
        manifest,
        candidate,
        review_path,
    ).certificate
    certificate["scientific_boundary"]["cross_dataset_validation_created"] = True
    _refingerprint_certificate(certificate)
    with pytest.raises(BenchmarkIntegrityError, match="scientific boundary drifted"):
        validate_certificate_record(certificate)


def test_refingerprinted_certificate_raw_mapping_leak_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_crosswalk_candidate(source, manifest)
    review_path = _write_review(tmp_path, _review_dict(candidate))
    certificate = require_reviewed_explicit_crosswalk(
        source,
        manifest,
        candidate,
        review_path,
    ).certificate
    certificate["mapping_entries"] = deepcopy(_entries())
    _refingerprint_certificate(certificate)
    with pytest.raises(BenchmarkIntegrityError, match="forbidden raw mapping fields"):
        validate_certificate_record(certificate)
