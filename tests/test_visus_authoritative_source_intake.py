from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_authoritative_source_certificate import (
    require_reviewed_visus_source_authority,
    validate_certificate_record,
)
from gazeforge.visus_authoritative_source_common import (
    CANDIDATE_RECORD_TYPE,
    CERTIFICATE_RECORD_TYPE,
    REVIEW_RECORD_TYPE,
    SOURCE_RECORD_TYPE,
    candidate_fingerprint,
    certificate_fingerprint,
    review_fingerprint,
)
from gazeforge.visus_authoritative_source_intake import (
    inspect_visus_authoritative_source_candidate,
    validate_candidate_record,
)
from gazeforge.visus_scaffold import build_visus_source_audit_scaffold


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "candidate-visus"
    root.mkdir()
    (root / "asset-a.dat").write_bytes(b"candidate asset A\n")
    nested = root / "nested"
    nested.mkdir()
    (nested / "asset-b.dat").write_bytes(b"candidate asset B\n")

    source = tmp_path / "visus-source-package.bin"
    source_bytes = b"synthetic authoritative source artifact for tests\n"
    source.write_bytes(source_bytes)

    rights = tmp_path / "rights-evidence.txt"
    rights_bytes = b"synthetic rights evidence used only for tests\n"
    rights.write_bytes(rights_bytes)

    scaffold = build_visus_source_audit_scaffold(root)
    manifest = tmp_path / "source-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "record_type": SOURCE_RECORD_TYPE,
                "source_reference": "synthetic-test://authoritative-visus",
                "source_revision": "synthetic-revision-1",
                "source_authority_claim": "institutional_repository",
                "source_artifact_sha256": _sha256(source_bytes),
                "rights_evidence_reference": "synthetic-test://rights",
                "rights_evidence_sha256": _sha256(rights_bytes),
                "inventory_fingerprint_sha256": scaffold.inventory_fingerprint_sha256,
                "file_count": scaffold.file_count,
                "obtained_via_authorized_channel_affirmed": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return root, source, rights, manifest


def _review(candidate: dict, *, redistribution: str = "prohibited") -> dict:
    value = {
        "record_type": REVIEW_RECORD_TYPE,
        "decision": "approved",
        "candidate_fingerprint_sha256": candidate["candidate_fingerprint_sha256"],
        "reviewer": "Synthetic Reviewer",
        "reviewed_at": "2026-09-10T12:30:00+03:00",
        "source_authority_verified": True,
        "source_authority_evidence": "Synthetic authority evidence.",
        "current_authoritative_distribution_identity_verified": True,
        "current_distribution_identity_evidence": "Synthetic current-distribution evidence.",
        "source_artifact_matches_authoritative_distribution_verified": True,
        "source_artifact_match_evidence": "Synthetic package identity evidence.",
        "extracted_tree_matches_source_artifact_verified": True,
        "extracted_tree_match_evidence": "Synthetic extraction evidence.",
        "rights_evidence_authoritative_verified": True,
        "rights_evidence_authority_evidence": "Synthetic rights-source evidence.",
        "analysis_use_permitted_verified": True,
        "analysis_use_evidence": "Synthetic analysis-permission evidence.",
        "redistribution_status_verified": redistribution,
        "redistribution_evidence": "Synthetic redistribution-scope evidence.",
        "license_or_terms_identifier": "Synthetic Research Terms v1",
        "rights_scope_limited_to_reviewed_source": True,
        "participant_mapping_verified": False,
        "stimulus_mapping_verified": False,
        "coordinate_basis_verified": False,
        "timestamp_basis_verified": False,
        "independent_annotation_streams_verified": False,
        "empirical_validation_created": False,
        "raw_source_redistributed": False,
    }
    value["review_fingerprint_sha256"] = review_fingerprint(value)
    return value


def _write_review(tmp_path: Path, review: dict) -> Path:
    path = tmp_path / "source-review.json"
    path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _candidate(tmp_path: Path) -> tuple[tuple[Path, Path, Path, Path], dict]:
    inputs = _make_inputs(tmp_path)
    candidate = inspect_visus_authoritative_source_candidate(*inputs)
    return inputs, candidate


def _refingerprint_candidate(record: dict) -> dict:
    record["candidate_fingerprint_sha256"] = candidate_fingerprint(record)
    return record


def _refingerprint_review(record: dict) -> dict:
    record["review_fingerprint_sha256"] = review_fingerprint(record)
    return record


def _refingerprint_certificate(record: dict) -> dict:
    record["certificate_fingerprint_sha256"] = certificate_fingerprint(record)
    return record


def test_candidate_is_exact_and_non_promoting(tmp_path: Path) -> None:
    _, candidate = _candidate(tmp_path)
    validated = validate_candidate_record(candidate)
    assert validated["record_type"] == CANDIDATE_RECORD_TYPE
    assert validated["inventory"]["file_count"] == 2
    assert validated["inventory"]["published_participant_count"] == 25
    assert validated["inventory"]["published_stimulus_count"] == 11
    assert validated["review_boundary"]["source_audit_stage_authorized"] is False
    assert all(value is False for value in validated["scientific_boundary"].values())
    assert "synthetic rights evidence used only for tests" not in json.dumps(validated)


def test_manifest_source_hash_mismatch_rejected(tmp_path: Path) -> None:
    root, source, rights, manifest = _make_inputs(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["source_artifact_sha256"] = "0" * 64
    manifest.write_text(json.dumps(payload))
    with pytest.raises(BenchmarkIntegrityError, match="source artifact bytes"):
        inspect_visus_authoritative_source_candidate(root, source, rights, manifest)


def test_manifest_rights_hash_mismatch_rejected(tmp_path: Path) -> None:
    root, source, rights, manifest = _make_inputs(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["rights_evidence_sha256"] = "0" * 64
    manifest.write_text(json.dumps(payload))
    with pytest.raises(BenchmarkIntegrityError, match="rights evidence bytes"):
        inspect_visus_authoritative_source_candidate(root, source, rights, manifest)


def test_manifest_inventory_mismatch_rejected(tmp_path: Path) -> None:
    root, source, rights, manifest = _make_inputs(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["inventory_fingerprint_sha256"] = "0" * 64
    manifest.write_text(json.dumps(payload))
    with pytest.raises(BenchmarkIntegrityError, match="source-tree inventory"):
        inspect_visus_authoritative_source_candidate(root, source, rights, manifest)


def test_manifest_file_count_mismatch_rejected(tmp_path: Path) -> None:
    root, source, rights, manifest = _make_inputs(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["file_count"] = 3
    manifest.write_text(json.dumps(payload))
    with pytest.raises(BenchmarkIntegrityError, match="file count"):
        inspect_visus_authoritative_source_candidate(root, source, rights, manifest)


def test_manifest_closed_schema_rejects_extra_claim(tmp_path: Path) -> None:
    root, source, rights, manifest = _make_inputs(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["empirical_ready"] = True
    manifest.write_text(json.dumps(payload))
    with pytest.raises(BenchmarkIntegrityError, match="source manifest schema drifted"):
        inspect_visus_authoritative_source_candidate(root, source, rights, manifest)


def test_unsupported_authority_rejected(tmp_path: Path) -> None:
    root, source, rights, manifest = _make_inputs(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["source_authority_claim"] = "third_party_repack"
    manifest.write_text(json.dumps(payload))
    with pytest.raises(BenchmarkIntegrityError, match="unsupported"):
        inspect_visus_authoritative_source_candidate(root, source, rights, manifest)


def test_authorized_channel_affirmation_required(tmp_path: Path) -> None:
    root, source, rights, manifest = _make_inputs(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["obtained_via_authorized_channel_affirmed"] = False
    manifest.write_text(json.dumps(payload))
    with pytest.raises(BenchmarkIntegrityError, match="authorized-channel"):
        inspect_visus_authoritative_source_candidate(root, source, rights, manifest)


def test_evidence_files_must_be_outside_source_tree(tmp_path: Path) -> None:
    root, source, rights, manifest = _make_inputs(tmp_path)
    copied = root / "source-package.bin"
    copied.write_bytes(source.read_bytes())
    with pytest.raises(BenchmarkIntegrityError, match="outside the inventoried source tree"):
        inspect_visus_authoritative_source_candidate(root, copied, rights, manifest)


def test_candidate_fingerprint_tamper_rejected(tmp_path: Path) -> None:
    _, candidate = _candidate(tmp_path)
    candidate["inventory"]["file_count"] = 3
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint drifted"):
        validate_candidate_record(candidate)


def test_refingerprinted_candidate_extra_field_rejected(tmp_path: Path) -> None:
    _, candidate = _candidate(tmp_path)
    candidate["empirical_ready"] = True
    _refingerprint_candidate(candidate)
    with pytest.raises(BenchmarkIntegrityError, match="candidate schema drifted"):
        validate_candidate_record(candidate)


def test_refingerprinted_candidate_nested_promotion_rejected(tmp_path: Path) -> None:
    _, candidate = _candidate(tmp_path)
    candidate["review_boundary"]["source_authority_verified"] = True
    _refingerprint_candidate(candidate)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_candidate_record(candidate)


def test_refingerprinted_candidate_nested_extra_field_rejected(tmp_path: Path) -> None:
    _, candidate = _candidate(tmp_path)
    candidate["inventory"]["full_visus_recovered"] = True
    _refingerprint_candidate(candidate)
    with pytest.raises(BenchmarkIntegrityError, match="candidate inventory schema drifted"):
        validate_candidate_record(candidate)


def test_source_mutation_blocks_review_replay(tmp_path: Path) -> None:
    inputs, candidate = _candidate(tmp_path)
    root, source, rights, manifest = inputs
    source.write_bytes(source.read_bytes() + b"mutation")
    review_path = _write_review(tmp_path, _review(candidate))
    with pytest.raises(BenchmarkIntegrityError):
        require_reviewed_visus_source_authority(
            root, source, rights, manifest, candidate, review_path
        )


def test_tree_mutation_blocks_review_replay(tmp_path: Path) -> None:
    inputs, candidate = _candidate(tmp_path)
    root, source, rights, manifest = inputs
    (root / "asset-a.dat").write_bytes(b"changed\n")
    review_path = _write_review(tmp_path, _review(candidate))
    with pytest.raises(BenchmarkIntegrityError):
        require_reviewed_visus_source_authority(
            root, source, rights, manifest, candidate, review_path
        )


def test_review_requires_approval(tmp_path: Path) -> None:
    inputs, candidate = _candidate(tmp_path)
    review = _review(candidate)
    review["decision"] = "pending"
    _refingerprint_review(review)
    with pytest.raises(BenchmarkIntegrityError, match="decision='approved'"):
        require_reviewed_visus_source_authority(
            *inputs, candidate, _write_review(tmp_path, review)
        )


def test_review_must_bind_exact_candidate(tmp_path: Path) -> None:
    inputs, candidate = _candidate(tmp_path)
    review = _review(candidate)
    review["candidate_fingerprint_sha256"] = "0" * 64
    _refingerprint_review(review)
    with pytest.raises(BenchmarkIntegrityError, match="not bound"):
        require_reviewed_visus_source_authority(
            *inputs, candidate, _write_review(tmp_path, review)
        )


def test_review_timestamp_requires_timezone(tmp_path: Path) -> None:
    inputs, candidate = _candidate(tmp_path)
    review = _review(candidate)
    review["reviewed_at"] = "2026-09-10T12:30:00"
    _refingerprint_review(review)
    with pytest.raises(BenchmarkIntegrityError, match="timezone offset"):
        require_reviewed_visus_source_authority(
            *inputs, candidate, _write_review(tmp_path, review)
        )


def test_review_requires_resolved_evidence(tmp_path: Path) -> None:
    inputs, candidate = _candidate(tmp_path)
    review = _review(candidate)
    review["analysis_use_evidence"] = "REVIEW_REQUIRED"
    _refingerprint_review(review)
    with pytest.raises(BenchmarkIntegrityError, match="analysis_use_evidence"):
        require_reviewed_visus_source_authority(
            *inputs, candidate, _write_review(tmp_path, review)
        )


@pytest.mark.parametrize(
    "field",
    [
        "source_authority_verified",
        "current_authoritative_distribution_identity_verified",
        "source_artifact_matches_authoritative_distribution_verified",
        "extracted_tree_matches_source_artifact_verified",
        "rights_evidence_authoritative_verified",
        "analysis_use_permitted_verified",
        "rights_scope_limited_to_reviewed_source",
    ],
)
def test_review_requires_all_authority_and_rights_gates(tmp_path: Path, field: str) -> None:
    inputs, candidate = _candidate(tmp_path)
    review = _review(candidate)
    review[field] = False
    _refingerprint_review(review)
    with pytest.raises(BenchmarkIntegrityError, match=f"{field}=true"):
        require_reviewed_visus_source_authority(
            *inputs, candidate, _write_review(tmp_path, review)
        )


def test_review_rejects_unsupported_redistribution_status(tmp_path: Path) -> None:
    inputs, candidate = _candidate(tmp_path)
    review = _review(candidate, redistribution="assumed")
    with pytest.raises(BenchmarkIntegrityError, match="supported redistribution status"):
        require_reviewed_visus_source_authority(
            *inputs, candidate, _write_review(tmp_path, review)
        )


@pytest.mark.parametrize(
    "field",
    [
        "participant_mapping_verified",
        "stimulus_mapping_verified",
        "coordinate_basis_verified",
        "timestamp_basis_verified",
        "independent_annotation_streams_verified",
        "empirical_validation_created",
        "raw_source_redistributed",
    ],
)
def test_review_cannot_promote_scientific_gates(tmp_path: Path, field: str) -> None:
    inputs, candidate = _candidate(tmp_path)
    review = _review(candidate)
    review[field] = True
    _refingerprint_review(review)
    with pytest.raises(BenchmarkIntegrityError, match=f"cannot promote {field}"):
        require_reviewed_visus_source_authority(
            *inputs, candidate, _write_review(tmp_path, review)
        )


def test_review_closed_schema_rejects_extra_claim(tmp_path: Path) -> None:
    inputs, candidate = _candidate(tmp_path)
    review = _review(candidate)
    review["model_validation_ready"] = True
    _refingerprint_review(review)
    with pytest.raises(BenchmarkIntegrityError, match="source-authority review schema drifted"):
        require_reviewed_visus_source_authority(
            *inputs, candidate, _write_review(tmp_path, review)
        )


@pytest.mark.parametrize("redistribution", ["permitted", "prohibited", "not_stated"])
def test_approved_review_emits_non_empirical_certificate(
    tmp_path: Path,
    redistribution: str,
) -> None:
    inputs, candidate = _candidate(tmp_path)
    review_path = _write_review(tmp_path, _review(candidate, redistribution=redistribution))
    reviewed = require_reviewed_visus_source_authority(*inputs, candidate, review_path)
    certificate = validate_certificate_record(reviewed.certificate)
    assert certificate["record_type"] == CERTIFICATE_RECORD_TYPE
    assert certificate["rights"]["analysis_use_permitted"] is True
    assert certificate["rights"]["redistribution_status"] == redistribution
    assert certificate["authority_boundary"]["source_audit_stage_authorized"] is True
    assert all(value is False for value in certificate["scientific_boundary"].values())
    assert certificate["rights"]["raw_source_redistribution_action_authorized"] is False
    assert "synthetic rights evidence used only for tests" not in json.dumps(certificate)


def test_certificate_fingerprint_tamper_rejected(tmp_path: Path) -> None:
    inputs, candidate = _candidate(tmp_path)
    certificate = require_reviewed_visus_source_authority(
        *inputs, candidate, _write_review(tmp_path, _review(candidate))
    ).certificate
    certificate["inventory"]["file_count"] = 3
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint drifted"):
        validate_certificate_record(certificate)


def test_refingerprinted_certificate_extra_field_rejected(tmp_path: Path) -> None:
    inputs, candidate = _candidate(tmp_path)
    certificate = require_reviewed_visus_source_authority(
        *inputs, candidate, _write_review(tmp_path, _review(candidate))
    ).certificate
    certificate["empirical_ready"] = True
    _refingerprint_certificate(certificate)
    with pytest.raises(BenchmarkIntegrityError, match="certificate schema drifted"):
        validate_certificate_record(certificate)


def test_refingerprinted_certificate_scientific_promotion_rejected(tmp_path: Path) -> None:
    inputs, candidate = _candidate(tmp_path)
    certificate = require_reviewed_visus_source_authority(
        *inputs, candidate, _write_review(tmp_path, _review(candidate))
    ).certificate
    certificate["scientific_boundary"]["model_human_validation_created"] = True
    _refingerprint_certificate(certificate)
    with pytest.raises(BenchmarkIntegrityError, match="must not promote"):
        validate_certificate_record(certificate)


def test_refingerprinted_certificate_redistribution_action_rejected(tmp_path: Path) -> None:
    inputs, candidate = _candidate(tmp_path)
    certificate = require_reviewed_visus_source_authority(
        *inputs, candidate, _write_review(tmp_path, _review(candidate, redistribution="permitted"))
    ).certificate
    certificate["rights"]["raw_source_redistribution_action_authorized"] = True
    _refingerprint_certificate(certificate)
    with pytest.raises(BenchmarkIntegrityError, match="cannot itself authorize redistribution"):
        validate_certificate_record(certificate)
