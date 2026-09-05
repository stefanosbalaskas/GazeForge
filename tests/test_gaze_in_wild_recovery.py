from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_recovery import (
    build_gaze_in_wild_recovery_candidate_review,
    recovery_candidate_record_fingerprint,
    validate_gaze_in_wild_recovery_candidate_review,
    verify_gaze_in_wild_recovery_candidate_tree,
    write_gaze_in_wild_recovery_candidate_review,
)


def _candidate_tree(tmp_path: Path) -> Path:
    root = tmp_path / "candidate"
    process = root / "ProcessData"
    labels = root / "LabelData"
    process.mkdir(parents=True)
    labels.mkdir(parents=True)
    (process / "PrIdx_1_TrIdx_1.mat").write_bytes(b"unverified-process-copy")
    (labels / "LabellerIdx_7_PrIdx_1_TrIdx_1.mat").write_bytes(
        b"unverified-label-copy"
    )
    (root / "README").write_text(
        "Candidate recovery material; this text is not source authority or a licence.\n",
        encoding="utf-8",
    )
    return root


def _review(root: Path) -> dict:
    return build_gaze_in_wild_recovery_candidate_review(
        root,
        candidate_kind="candidate_original_layout_unverified",
        provenance_source="secondary recovery lead",
        provenance_note="Unverified candidate retained for identity review only.",
    )


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_candidate_review_is_deterministic_and_quarantined(tmp_path: Path) -> None:
    root = _candidate_tree(tmp_path)
    first = _review(root)
    second = _review(root)

    assert first == second
    assert first["candidate_status"] == "quarantined"
    assert first["provenance"]["authority_status"] == "unverified"
    assert first["provenance"]["rights_status"] == "unresolved"
    assert all(item["role"] == "unclassified" for item in first["inventory"]["files"])
    assert first["interpretation_policy"] == {
        "all_file_roles_are_unclassified": True,
        "filename_identity_inference_permitted": False,
        "matlab_schema_inference_permitted": False,
        "license_inference_permitted": False,
        "candidate_can_materialize_empirical_audit_spec": False,
    }
    assert not any(first["scientific_boundary"].values())

    validated = validate_gaze_in_wild_recovery_candidate_review(first)
    assert validated.file_count == 3
    assert validated.total_bytes == sum(
        item["bytes"] for item in first["inventory"]["files"]
    )
    assert validated.tree_fingerprint_sha256 == first["inventory"][
        "tree_fingerprint_sha256"
    ]
    assert validated.record_fingerprint_sha256 == first["record_fingerprint_sha256"]
    assert len(validated.tree_fingerprint_sha256) == 64
    assert len(validated.record_fingerprint_sha256) == 64


def test_candidate_tree_verification_detects_content_drift(tmp_path: Path) -> None:
    root = _candidate_tree(tmp_path)
    review = _review(root)
    verify_gaze_in_wild_recovery_candidate_tree(root, review)

    (root / "ProcessData" / "PrIdx_1_TrIdx_1.mat").write_bytes(b"changed")
    with pytest.raises(BenchmarkIntegrityError, match="no longer matches"):
        verify_gaze_in_wild_recovery_candidate_tree(root, review)


@pytest.mark.parametrize(
    ("section", "key", "promoted_value"),
    [
        ("provenance", "authority_status", "verified"),
        ("provenance", "rights_status", "resolved"),
        (
            "interpretation_policy",
            "filename_identity_inference_permitted",
            True,
        ),
        (
            "interpretation_policy",
            "matlab_schema_inference_permitted",
            True,
        ),
        ("interpretation_policy", "license_inference_permitted", True),
        (
            "interpretation_policy",
            "candidate_can_materialize_empirical_audit_spec",
            True,
        ),
        ("scientific_boundary", "source_authority_verified", True),
        ("scientific_boundary", "dataset_file_rights_resolved", True),
        ("scientific_boundary", "participant_mapping_verified", True),
        (
            "scientific_boundary",
            "independent_labeller_recoverability_verified",
            True,
        ),
        ("scientific_boundary", "empirical_evidence_eligible", True),
        ("scientific_boundary", "human_human_agreement_created", True),
        (
            "scientific_boundary",
            "participant_disjoint_model_validation_created",
            True,
        ),
        ("scientific_boundary", "cross_dataset_performance_created", True),
        ("scientific_boundary", "gp3_validity_created", True),
        (
            "scientific_boundary",
            "frozen_evidence_performance_claim_created",
            True,
        ),
    ],
)
def test_review_rejects_promotions_even_with_valid_record_fingerprint(
    tmp_path: Path,
    section: str,
    key: str,
    promoted_value: object,
) -> None:
    record = copy.deepcopy(_review(_candidate_tree(tmp_path)))
    record[section][key] = promoted_value
    record["record_fingerprint_sha256"] = recovery_candidate_record_fingerprint(record)

    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_recovery_candidate_review(record)


def test_file_role_promotion_is_rejected_even_after_rehashing(tmp_path: Path) -> None:
    record = copy.deepcopy(_review(_candidate_tree(tmp_path)))
    record["inventory"]["files"][0]["role"] = "process_data"
    record["inventory"]["tree_fingerprint_sha256"] = _canonical_sha256(
        record["inventory"]["files"]
    )
    record["record_fingerprint_sha256"] = recovery_candidate_record_fingerprint(record)

    with pytest.raises(BenchmarkIntegrityError, match="roles must remain unclassified"):
        validate_gaze_in_wild_recovery_candidate_review(record)


def test_write_review_must_be_outside_candidate_tree(tmp_path: Path) -> None:
    root = _candidate_tree(tmp_path)
    review = _review(root)

    with pytest.raises(BenchmarkIntegrityError, match="outside the candidate tree"):
        write_gaze_in_wild_recovery_candidate_review(
            review,
            root / "review.json",
            candidate_root=root,
        )

    target = tmp_path / "review.json"
    written = write_gaze_in_wild_recovery_candidate_review(
        review,
        target,
        candidate_root=root,
    )
    assert written == target
    validated = validate_gaze_in_wild_recovery_candidate_review(target)
    assert validated.record_fingerprint_sha256 == review["record_fingerprint_sha256"]

    with pytest.raises(FileExistsError):
        write_gaze_in_wild_recovery_candidate_review(
            review,
            target,
            candidate_root=root,
        )


def test_empty_candidate_tree_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    with pytest.raises(BenchmarkIntegrityError, match="at least one file"):
        _review(root)


def test_candidate_requires_supported_kind_and_explicit_provenance(tmp_path: Path) -> None:
    root = _candidate_tree(tmp_path)
    with pytest.raises(BenchmarkIntegrityError, match="Unsupported"):
        build_gaze_in_wild_recovery_candidate_review(
            root,
            candidate_kind="authoritative_copy",
            provenance_source="unknown",
            provenance_note="unknown",
        )
    with pytest.raises(BenchmarkIntegrityError, match="explicit provenance"):
        build_gaze_in_wild_recovery_candidate_review(
            root,
            candidate_kind="unknown_recovered_copy",
            provenance_source="",
            provenance_note="",
        )
