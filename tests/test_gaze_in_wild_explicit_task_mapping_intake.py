from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_authoritative_task_mapping_exhaustion import EXPECTED_TASKS
from gazeforge.gaze_in_wild_explicit_task_mapping_certificate import (
    validate_certificate_record,
)
from gazeforge.gaze_in_wild_explicit_task_mapping_intake import (
    CANDIDATE_RECORD_TYPE,
    CERTIFICATE_RECORD_TYPE,
    REVIEW_RECORD_TYPE,
    SOURCE_RECORD_TYPE,
    TASK_MAPPING_EXHAUSTION_FINGERPRINT,
    TRIAL_INDICES,
    candidate_fingerprint,
    certificate_fingerprint,
    inspect_explicit_task_mapping_candidate,
    require_reviewed_explicit_task_mapping,
    review_fingerprint,
    validate_candidate_record,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _entries() -> list[dict[str, object]]:
    return [
        {"trial_index": index, "task_label": task}
        for index, task in zip(TRIAL_INDICES, EXPECTED_TASKS, strict=True)
    ]


def _write_source_and_manifest(
    tmp_path: Path,
    *,
    entries: list[dict[str, object]] | None = None,
    authority: str = "author_statement",
) -> tuple[Path, Path]:
    source = tmp_path / "authoritative-task-ledger.txt"
    source_bytes = (
        b"Synthetic test fixture representing an explicit authoritative TrIdx mapping.\n"
    )
    source.write_bytes(source_bytes)
    manifest = {
        "record_type": SOURCE_RECORD_TYPE,
        "source_reference": "synthetic-test-fixture://authoritative-task-ledger",
        "source_authority_claim": authority,
        "source_file_sha256": _sha256(source_bytes),
        "obtained_via_authorized_channel_affirmed": True,
        "mapping_entries": _entries() if entries is None else entries,
    }
    manifest_path = tmp_path / "task-mapping-manifest.json"
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
        "source_authority_evidence": "Synthetic authority evidence.",
        "mapping_explicit_in_source_verified": True,
        "mapping_explicitness_evidence": "Synthetic explicit lookup evidence.",
        "mapping_transcription_verified": True,
        "mapping_transcription_evidence": "Synthetic transcription evidence.",
        "publication_task_semantics_verified": True,
        "publication_task_semantics_evidence": "Synthetic publication-task evidence.",
        "source_version_scope_verified": True,
        "source_version_scope_evidence": "Synthetic source-version evidence.",
        "tridx4_explicit_in_source_verified": True,
        "tridx4_explicitness_evidence": "Synthetic source explicitly states TrIdx 4.",
        "no_elimination_or_order_inference_used_verified": True,
        "no_elimination_or_order_inference_evidence": (
            "Synthetic lookup was transcribed directly; no order/elimination inference."
        ),
        "rights_scope_promoted": False,
        "empirical_validation_created": False,
        "quarantine_exit_authorized": False,
    }
    review["review_fingerprint_sha256"] = review_fingerprint(review)
    return review


def _write_review(tmp_path: Path, review: dict) -> Path:
    path = tmp_path / "task-mapping-review.json"
    path.write_text(
        json.dumps(review, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
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


def _certificate(tmp_path: Path) -> tuple[dict, dict[int, str]]:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    review_path = _write_review(tmp_path, _review_dict(candidate))
    reviewed = require_reviewed_explicit_task_mapping(
        source,
        manifest,
        candidate,
        review_path,
    )
    return reviewed.certificate, reviewed.mapping


def test_complete_candidate_is_non_promoting_and_mapping_private(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    validated = validate_candidate_record(candidate)

    assert validated["record_type"] == CANDIDATE_RECORD_TYPE
    assert validated["authoritative_task_mapping_exhaustion_fingerprint_sha256"] == (
        TASK_MAPPING_EXHAUSTION_FINGERPRINT
    )
    assert validated["mapping_summary"]["entry_count"] == 4
    assert validated["mapping_summary"]["complete_trial_index_coverage"] is True
    assert validated["mapping_summary"]["complete_publication_task_coverage"] is True
    assert validated["mapping_summary"]["complete_one_to_one_mapping"] is True
    assert validated["mapping_summary"]["tridx4_present_in_transcription"] is True
    assert validated["review_boundary"]["authoritative_trial_task_mapping_verified"] is False
    assert validated["scientific_boundary"]["task_stratified_validation_created"] is False

    serialized = json.dumps(validated)
    assert '"mapping_entries"' not in serialized
    assert '"trial_index": 4' not in serialized
    assert '"task_label": "Tea_Making"' not in serialized


def test_partial_secondary_style_candidate_is_allowed_but_not_promoted(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path, entries=_entries()[:3])
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)

    assert candidate["mapping_summary"]["trial_indices_present"] == [1, 2, 3]
    assert candidate["mapping_summary"]["complete_trial_index_coverage"] is False
    assert candidate["mapping_summary"]["complete_publication_task_coverage"] is False
    assert candidate["mapping_summary"]["complete_one_to_one_mapping"] is False
    assert candidate["mapping_summary"]["tridx4_present_in_transcription"] is False
    assert candidate["review_boundary"]["mapping_explicit_in_source_verified"] is False


def test_unknown_tridx_is_rejected(tmp_path: Path) -> None:
    entries = _entries()
    entries[0]["trial_index"] = 5
    source, manifest = _write_source_and_manifest(tmp_path, entries=entries)
    with pytest.raises(BenchmarkIntegrityError, match="unknown TrIdx"):
        inspect_explicit_task_mapping_candidate(source, manifest)


def test_boolean_tridx_is_rejected(tmp_path: Path) -> None:
    entries = _entries()
    entries[0]["trial_index"] = True
    source, manifest = _write_source_and_manifest(tmp_path, entries=entries)
    with pytest.raises(BenchmarkIntegrityError, match="trial_index must be an integer"):
        inspect_explicit_task_mapping_candidate(source, manifest)


def test_duplicate_tridx_is_rejected(tmp_path: Path) -> None:
    entries = _entries()
    entries[-1]["trial_index"] = 1
    source, manifest = _write_source_and_manifest(tmp_path, entries=entries)
    with pytest.raises(BenchmarkIntegrityError, match="duplicates TrIdx"):
        inspect_explicit_task_mapping_candidate(source, manifest)


def test_unknown_publication_task_is_rejected(tmp_path: Path) -> None:
    entries = _entries()
    entries[-1]["task_label"] = "Unknown_Task"
    source, manifest = _write_source_and_manifest(tmp_path, entries=entries)
    with pytest.raises(BenchmarkIntegrityError, match="unknown publication task"):
        inspect_explicit_task_mapping_candidate(source, manifest)


def test_duplicate_publication_task_is_rejected(tmp_path: Path) -> None:
    entries = _entries()
    entries[-1]["task_label"] = entries[0]["task_label"]
    source, manifest = _write_source_and_manifest(tmp_path, entries=entries)
    with pytest.raises(BenchmarkIntegrityError, match="duplicates publication task"):
        inspect_explicit_task_mapping_candidate(source, manifest)


def test_source_sha_mismatch_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["source_file_sha256"] = "0" * 64
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="do not match"):
        inspect_explicit_task_mapping_candidate(source, manifest)


def test_secondary_repack_authority_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(
        tmp_path,
        authority="secondary_repack",
    )
    with pytest.raises(BenchmarkIntegrityError, match="unsupported"):
        inspect_explicit_task_mapping_candidate(source, manifest)


@pytest.mark.parametrize(
    "authority",
    [
        "author_statement",
        "first_party_repository_record",
        "original_distribution_metadata",
        "publication_supplement",
    ],
)
def test_supported_authority_classes_are_syntactically_accepted(
    tmp_path: Path,
    authority: str,
) -> None:
    source, manifest = _write_source_and_manifest(tmp_path, authority=authority)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    assert candidate["source"]["source_authority_claim"] == authority
    assert candidate["review_boundary"]["source_authority_verified"] is False


def test_authorized_channel_affirmation_is_required(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["obtained_via_authorized_channel_affirmed"] = False
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="authorized-channel"):
        inspect_explicit_task_mapping_candidate(source, manifest)


def test_candidate_fingerprint_tamper_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    candidate["mapping_summary"]["entry_count"] = 3
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint drifted"):
        validate_candidate_record(candidate)


def test_refingerprinted_candidate_mapping_promotion_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    candidate["review_boundary"]["complete_trial_task_mapping_verified"] = True
    _refingerprint_candidate(candidate)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_candidate_record(candidate)


def test_refingerprinted_candidate_scientific_promotion_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    candidate["scientific_boundary"]["task_stratified_validation_created"] = True
    _refingerprint_candidate(candidate)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_candidate_record(candidate)


def test_refingerprinted_candidate_count_drift_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path, entries=_entries()[:3])
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    candidate["mapping_summary"]["publication_task_count"] = 4
    _refingerprint_candidate(candidate)
    with pytest.raises(BenchmarkIntegrityError, match="task count"):
        validate_candidate_record(candidate)


def test_partial_candidate_cannot_be_review_promoted(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path, entries=_entries()[:3])
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    review_path = _write_review(tmp_path, _review_dict(candidate))
    with pytest.raises(BenchmarkIntegrityError, match="complete TrIdx 1..4 coverage"):
        require_reviewed_explicit_task_mapping(source, manifest, candidate, review_path)


def test_candidate_must_replay_exact_local_source_and_manifest(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["source_reference"] = "synthetic-test-fixture://changed-reference"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    review_path = _write_review(tmp_path, _review_dict(candidate))
    with pytest.raises(BenchmarkIntegrityError, match="no longer matches"):
        require_reviewed_explicit_task_mapping(source, manifest, candidate, review_path)


def test_review_requires_explicit_approval(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    review = _review_dict(candidate)
    review["decision"] = "pending"
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match="decision='approved'"):
        require_reviewed_explicit_task_mapping(source, manifest, candidate, review_path)


def test_review_must_bind_exact_candidate(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    review = _review_dict(candidate)
    review["candidate_fingerprint_sha256"] = "0" * 64
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match="not bound"):
        require_reviewed_explicit_task_mapping(source, manifest, candidate, review_path)


def test_review_timestamp_requires_timezone(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    review = _review_dict(candidate)
    review["reviewed_at"] = "2026-09-10T12:00:00"
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match="timezone offset"):
        require_reviewed_explicit_task_mapping(source, manifest, candidate, review_path)


def test_review_requires_resolved_tridx4_evidence(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    review = _review_dict(candidate)
    review["tridx4_explicitness_evidence"] = "REVIEW_REQUIRED"
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match="tridx4_explicitness_evidence"):
        require_reviewed_explicit_task_mapping(source, manifest, candidate, review_path)


@pytest.mark.parametrize(
    "field",
    [
        "source_authority_verified",
        "mapping_explicit_in_source_verified",
        "mapping_transcription_verified",
        "publication_task_semantics_verified",
        "source_version_scope_verified",
        "tridx4_explicit_in_source_verified",
        "no_elimination_or_order_inference_used_verified",
    ],
)
def test_review_requires_every_verification_gate(
    tmp_path: Path,
    field: str,
) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    review = _review_dict(candidate)
    review[field] = False
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match=f"{field}=true"):
        require_reviewed_explicit_task_mapping(source, manifest, candidate, review_path)


def test_tridx4_cannot_be_approved_by_elimination(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    review = _review_dict(candidate)
    review["tridx4_explicit_in_source_verified"] = False
    review["tridx4_explicitness_evidence"] = (
        "Tea_Making was the only remaining publication task."
    )
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(
        BenchmarkIntegrityError,
        match="tridx4_explicit_in_source_verified=true",
    ):
        require_reviewed_explicit_task_mapping(source, manifest, candidate, review_path)


def test_publication_or_directory_order_inference_cannot_be_approved(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    review = _review_dict(candidate)
    review["no_elimination_or_order_inference_used_verified"] = False
    review["no_elimination_or_order_inference_evidence"] = (
        "Mapping followed publication task order."
    )
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(
        BenchmarkIntegrityError,
        match="no_elimination_or_order_inference_used_verified=true",
    ):
        require_reviewed_explicit_task_mapping(source, manifest, candidate, review_path)


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("rights_scope_promoted", "cannot promote dataset rights"),
        ("empirical_validation_created", "cannot create empirical validation"),
        ("quarantine_exit_authorized", "cannot authorize quarantine exit"),
    ],
)
def test_review_cannot_promote_unrelated_boundaries(
    tmp_path: Path,
    field: str,
    message: str,
) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    review = _review_dict(candidate)
    review[field] = True
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match=message):
        require_reviewed_explicit_task_mapping(source, manifest, candidate, review_path)


def test_review_fingerprint_tamper_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    review = _review_dict(candidate)
    review["reviewer"] = "Changed Reviewer"
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match="review fingerprint drifted"):
        require_reviewed_explicit_task_mapping(source, manifest, candidate, review_path)


def test_approved_review_returns_mapping_and_non_empirical_certificate(
    tmp_path: Path,
) -> None:
    certificate, mapping = _certificate(tmp_path)
    validated = validate_certificate_record(certificate)

    assert validated["record_type"] == CERTIFICATE_RECORD_TYPE
    assert validated["trial_index_count"] == 4
    assert validated["mapping_boundary"]["authoritative_trial_task_mapping_verified"] is True
    assert validated["mapping_boundary"]["tridx4_explicit_in_source_verified"] is True
    assert validated["mapping_boundary"]["tridx4_tea_making_inferred_by_elimination"] is False
    assert validated["scientific_boundary"]["task_stratified_validation_created"] is False
    assert validated["scientific_boundary"]["cross_dataset_validation_created"] is False
    assert mapping == dict(zip(TRIAL_INDICES, EXPECTED_TASKS, strict=True))

    serialized = json.dumps(validated)
    assert '"mapping_entries"' not in serialized
    assert '"trial_task_mapping"' not in serialized
    assert '"4": "Tea_Making"' not in serialized


def test_certificate_fingerprint_tamper_is_rejected(tmp_path: Path) -> None:
    certificate, _ = _certificate(tmp_path)
    certificate["trial_index_count"] = 3
    with pytest.raises(BenchmarkIntegrityError, match="trial-index count drifted"):
        validate_certificate_record(certificate)


def test_refingerprinted_certificate_mapping_promotion_is_rejected(tmp_path: Path) -> None:
    certificate, _ = _certificate(tmp_path)
    certificate["mapping_boundary"]["tridx4_tea_making_inferred_by_elimination"] = True
    _refingerprint_certificate(certificate)
    with pytest.raises(BenchmarkIntegrityError, match="mapping boundary drifted"):
        validate_certificate_record(certificate)


def test_refingerprinted_certificate_scientific_promotion_is_rejected(
    tmp_path: Path,
) -> None:
    certificate, _ = _certificate(tmp_path)
    certificate["scientific_boundary"]["task_stratified_validation_created"] = True
    _refingerprint_certificate(certificate)
    with pytest.raises(BenchmarkIntegrityError, match="scientific boundary drifted"):
        validate_certificate_record(certificate)


def test_refingerprinted_certificate_exhaustion_binding_drift_is_rejected(
    tmp_path: Path,
) -> None:
    certificate, _ = _certificate(tmp_path)
    certificate["authoritative_task_mapping_exhaustion_fingerprint_sha256"] = "0" * 64
    _refingerprint_certificate(certificate)
    with pytest.raises(BenchmarkIntegrityError, match="exhaustion binding drifted"):
        validate_certificate_record(certificate)


def test_certificate_rejects_raw_mapping_field_even_when_refingerprinted(
    tmp_path: Path,
) -> None:
    certificate, _ = _certificate(tmp_path)
    certificate["mapping_entries"] = _entries()
    _refingerprint_certificate(certificate)
    with pytest.raises(BenchmarkIntegrityError, match="forbidden raw mapping fields"):
        validate_certificate_record(certificate)


def test_certificate_validator_accepts_json_path(tmp_path: Path) -> None:
    certificate, _ = _certificate(tmp_path)
    path = tmp_path / "certificate.json"
    path.write_text(json.dumps(certificate), encoding="utf-8")
    loaded = validate_certificate_record(path)
    assert loaded["certificate_fingerprint_sha256"] == (
        certificate["certificate_fingerprint_sha256"]
    )


def test_deepcopy_of_valid_candidate_remains_valid(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    assert validate_candidate_record(deepcopy(candidate)) == candidate


def test_refingerprinted_candidate_extra_claim_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    candidate["task_stratified_validation_authorized"] = True
    _refingerprint_candidate(candidate)
    with pytest.raises(BenchmarkIntegrityError, match="candidate top-level schema drifted"):
        validate_candidate_record(candidate)


def test_refingerprinted_review_extra_claim_is_rejected(tmp_path: Path) -> None:
    source, manifest = _write_source_and_manifest(tmp_path)
    candidate = inspect_explicit_task_mapping_candidate(source, manifest)
    review = _review_dict(candidate)
    review["tridx4_tea_making_inferred_by_elimination"] = True
    _refingerprint_review(review)
    review_path = _write_review(tmp_path, review)
    with pytest.raises(BenchmarkIntegrityError, match="review schema drifted"):
        require_reviewed_explicit_task_mapping(source, manifest, candidate, review_path)


def test_refingerprinted_certificate_extra_claim_is_rejected(tmp_path: Path) -> None:
    certificate, _ = _certificate(tmp_path)
    certificate["cross_dataset_validation_created"] = True
    _refingerprint_certificate(certificate)
    with pytest.raises(BenchmarkIntegrityError, match="certificate schema drifted"):
        validate_certificate_record(certificate)
