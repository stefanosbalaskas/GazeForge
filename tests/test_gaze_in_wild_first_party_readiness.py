from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest
from scipy.io import savemat

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_candidate_preflight import (
    build_gaze_in_wild_candidate_processdata_screen,
)
from gazeforge.gaze_in_wild_first_party_readiness import (
    build_gaze_in_wild_first_party_quarantine_readiness,
    first_party_readiness_fingerprint,
    validate_gaze_in_wild_first_party_quarantine_readiness,
    verify_gaze_in_wild_first_party_quarantine_readiness,
    write_gaze_in_wild_first_party_quarantine_readiness,
)
from gazeforge.gaze_in_wild_first_party_resolution import (
    build_gaze_in_wild_first_party_resolution_response_scaffold,
    response_fingerprint,
    validate_gaze_in_wild_first_party_resolution_request,
)
from gazeforge.gaze_in_wild_recovery import build_gaze_in_wild_recovery_candidate_review

_ROOT = Path(__file__).resolve().parents[1]
_DISTRIBUTION = (
    _ROOT
    / "validation/evidence/gaze-in-wild/gaze-in-wild-distribution-availability-evidence-v1.json"
)
_CURRENT = (
    _ROOT
    / "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-current-first-party-listing-evidence-v1.json"
)
_REQUEST = (
    _ROOT
    / "validation/requests/gaze-in-wild/gaze-in-wild-first-party-resolution-request-v1.json"
)


def _request():
    return validate_gaze_in_wild_first_party_resolution_request(
        _REQUEST,
        _DISTRIBUTION,
        _CURRENT,
    )


def _write_processdata(path: Path) -> None:
    n = 12
    savemat(
        path,
        {
            "ProcessData": {
                "PrIdx": 4,
                "TrIdx": 5,
                "SR": 300.0,
                "T": np.arange(n, dtype=float) / 300.0,
                "ETG": {
                    "POR": np.column_stack(
                        [np.linspace(10.0, 100.0, n), np.linspace(20.0, 200.0, n)]
                    ),
                    "Confidence": np.linspace(0.7, 1.0, n),
                    "SceneResolution": np.array([1920.0, 1080.0]),
                    "Labels": np.arange(n, dtype=float) % 3,
                },
            }
        },
    )


def _candidate(
    tmp_path: Path,
    *,
    kind: str = "candidate_original_layout_unverified",
) -> tuple[Path, dict, dict]:
    root = tmp_path / "candidate"
    root.mkdir()
    _write_processdata(root / "opaque.mat")
    (root / "README").write_text("unverified recovery candidate\n", encoding="utf-8")
    recovery = build_gaze_in_wild_recovery_candidate_review(
        root,
        candidate_kind=kind,
        provenance_source="recovery lead",
        provenance_note="Candidate retained for identity review only.",
    )
    screen = build_gaze_in_wild_candidate_processdata_screen(
        root,
        recovery,
        processdata_relative_path="opaque.mat",
    )
    return root, recovery, screen


def _message(tmp_path: Path) -> Path:
    path = tmp_path / "first-party-reply.eml"
    path.write_text("private first-party reply placeholder", encoding="utf-8")
    return path


def _response(
    tmp_path: Path,
    *,
    reviewed: bool = True,
    authority: str = "verified",
    archive: str = "provided",
    analysis: str = "permitted",
    redistribution: str = "restricted",
) -> tuple[dict, Path]:
    request = _request()
    message = _message(tmp_path)
    record = build_gaze_in_wild_first_party_resolution_response_scaffold(message, request)
    if reviewed:
        record["received_on"] = "2026-09-06"
        record["channel"] = "email"
        record["sender"] = {
            "name": "Reviewed First Party",
            "email_or_identifier": "reviewed@example.invalid",
            "claimed_role": "dataset steward",
        }
        record["review"].update(
            {
                "status": "reviewed",
                "reviewer": "independent reviewer",
                "reviewed_on": "2026-09-06",
            }
        )
        record["authority_review"].update(
            {
                "status": authority,
                "authority_scope": "GIW dataset-file terms",
                "evidence_basis": "Human-reviewed authority evidence.",
            }
        )
        if archive == "provided":
            record["archive_review"].update(
                {
                    "authoritative_archive_location_status": "provided",
                    "archive_location": "private-or-public-location-reviewed-locally",
                    "source_authority_statement_present": True,
                    "evidence_basis": "Human-reviewed archive-location statement.",
                }
            )
        elif archive == "not_available":
            record["archive_review"]["authoritative_archive_location_status"] = "not_available"
        if analysis != "unresolved" or redistribution != "unresolved":
            record["rights_review"].update(
                {
                    "dataset_files_explicitly_in_scope": True,
                    "analysis_use_status": analysis,
                    "redistribution_status": redistribution,
                    "derived_outputs_status": "permitted",
                    "rights_basis_kind": "explicit_first_party_statement",
                    "reuse_terms_source": "reviewed correspondence digest",
                    "evidence_basis": "Explicit dataset-file terms reviewed locally.",
                }
            )
    record["response_fingerprint_sha256"] = response_fingerprint(record)
    return record, message


def _handoff(
    tmp_path: Path,
    *,
    response: dict | None = None,
    message: Path | None = None,
    kind: str = "candidate_original_layout_unverified",
):
    root, recovery, screen = _candidate(tmp_path, kind=kind)
    if response is None or message is None:
        response, message = _response(tmp_path)
    handoff = build_gaze_in_wild_first_party_quarantine_readiness(
        response,
        message,
        _request(),
        candidate_root=root,
        recovery_record_or_path=recovery,
        candidate_screen_record_or_path=screen,
    )
    return handoff, root, recovery, screen, response, message


def _refingerprint(record: dict) -> None:
    record["record_fingerprint_sha256"] = first_party_readiness_fingerprint(record)


def test_reviewed_response_and_screen_become_ready_only_for_exact_copy_review(
    tmp_path: Path,
) -> None:
    handoff, *_ = _handoff(tmp_path)

    assert handoff["handoff_status"] == "ready_for_independent_exact_copy_review"
    assert handoff["readiness"]["response_reviewed"] is True
    assert handoff["readiness"]["source_authority_verified"] is True
    assert handoff["readiness"]["authoritative_archive_location_provided"] is True
    assert handoff["readiness"]["dataset_file_analysis_use_permitted"] is True
    assert handoff["readiness"]["redistribution_terms_reviewed"] is True
    assert handoff["readiness"]["ready_for_independent_exact_copy_review"] is True
    assert handoff["readiness"]["independent_exact_copy_identity_verified"] is False
    assert handoff["readiness"]["quarantine_exit_ready"] is False
    assert [item["id"] for item in handoff["blockers"]] == [
        "independent_exact_copy_identity_review_required"
    ]
    assert handoff["scientific_boundary"]["quarantine_exit_authorized"] is False
    assert handoff["scientific_boundary"]["empirical_evidence_eligible"] is False


def test_handoff_binds_response_digest_and_exact_candidate_screen(tmp_path: Path) -> None:
    handoff, _, recovery, screen, response, _ = _handoff(tmp_path)
    assert handoff["first_party_binding"]["request_fingerprint_sha256"] == response[
        "request_fingerprint_sha256"
    ]
    assert handoff["first_party_binding"]["response_fingerprint_sha256"] == response[
        "response_fingerprint_sha256"
    ]
    assert handoff["first_party_binding"]["correspondence_sha256"] == response[
        "correspondence_sha256"
    ]
    assert handoff["candidate_binding"]["recovery_record_fingerprint_sha256"] == recovery[
        "record_fingerprint_sha256"
    ]
    assert handoff["candidate_binding"]["recovery_tree_fingerprint_sha256"] == recovery[
        "inventory"
    ]["tree_fingerprint_sha256"]
    assert handoff["candidate_binding"]["selected_file"]["sha256"] == screen[
        "selected_file"
    ]["sha256"]


def test_pending_response_lists_precondition_blockers(tmp_path: Path) -> None:
    response, message = _response(tmp_path, reviewed=False)
    handoff, *_ = _handoff(tmp_path, response=response, message=message)
    blocker_ids = [item["id"] for item in handoff["blockers"]]
    assert handoff["handoff_status"] == "blocked_preconditions"
    assert "response_review_required" in blocker_ids
    assert "source_authority_verification_required" in blocker_ids
    assert "authoritative_archive_location_required" in blocker_ids
    assert "dataset_file_analysis_permission_required" in blocker_ids
    assert "redistribution_terms_review_required" in blocker_ids
    assert blocker_ids[-1] == "independent_exact_copy_identity_review_required"


def test_missing_archive_remains_blocked(tmp_path: Path) -> None:
    response, message = _response(tmp_path, archive="not_available")
    handoff, *_ = _handoff(tmp_path, response=response, message=message)
    assert handoff["handoff_status"] == "blocked_preconditions"
    assert "authoritative_archive_location_required" in {
        item["id"] for item in handoff["blockers"]
    }


def test_unverified_authority_remains_blocked(tmp_path: Path) -> None:
    response, message = _response(
        tmp_path,
        authority="not_verified",
        analysis="unresolved",
        redistribution="unresolved",
    )
    handoff, *_ = _handoff(tmp_path, response=response, message=message)
    assert "source_authority_verification_required" in {
        item["id"] for item in handoff["blockers"]
    }


def test_prohibited_redistribution_requires_explicit_mapping_review(tmp_path: Path) -> None:
    response, message = _response(tmp_path, redistribution="prohibited")
    handoff, *_ = _handoff(tmp_path, response=response, message=message)
    assert handoff["readiness"]["redistribution_terms_reviewed"] is True
    assert handoff["readiness"]["redistribution_status_requires_mapping_review"] is True
    assert handoff["handoff_status"] == "blocked_preconditions"
    assert "redistribution_status_mapping_review_required" in {
        item["id"] for item in handoff["blockers"]
    }


def test_transformed_secondary_candidate_cannot_reach_exact_copy_review_readiness(
    tmp_path: Path,
) -> None:
    handoff, *_ = _handoff(tmp_path, kind="transformed_secondary_collection")
    assert handoff["readiness"]["candidate_kind_exit_eligible"] is False
    assert handoff["handoff_status"] == "blocked_preconditions"
    assert "exit_eligible_candidate_required" in {
        item["id"] for item in handoff["blockers"]
    }


@pytest.mark.parametrize(
    "gate",
    [
        "independent_exact_copy_identity_verified",
        "quarantine_exit_authorized",
        "source_audit_ready",
        "source_audit_executed",
        "participant_mapping_verified",
        "coordinate_unit_verified",
        "sampling_cadence_verified",
        "separate_labeldata_recovered",
        "independent_labeller_recoverability_verified",
        "empirical_evidence_eligible",
        "human_human_agreement_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_performance_created",
        "gp3_validity_created",
        "frozen_evidence_performance_claim_created",
        "empirical_evidence_created",
    ],
)
def test_scientific_promotion_is_rejected_even_after_refingerprinting(
    tmp_path: Path,
    gate: str,
) -> None:
    handoff, *_ = _handoff(tmp_path)
    handoff["scientific_boundary"][gate] = True
    _refingerprint(handoff)
    with pytest.raises(BenchmarkIntegrityError, match="scientific boundary"):
        validate_gaze_in_wild_first_party_quarantine_readiness(handoff)


def test_readiness_and_blocker_tampering_are_rejected_after_refingerprinting(
    tmp_path: Path,
) -> None:
    handoff, *_ = _handoff(tmp_path)
    handoff["readiness"]["quarantine_exit_ready"] = True
    _refingerprint(handoff)
    with pytest.raises(BenchmarkIntegrityError, match="readiness derivation"):
        validate_gaze_in_wild_first_party_quarantine_readiness(handoff)

    handoff, *_ = _handoff(tmp_path / "second")
    handoff["blockers"] = []
    _refingerprint(handoff)
    with pytest.raises(BenchmarkIntegrityError, match="blocker list"):
        validate_gaze_in_wild_first_party_quarantine_readiness(handoff)


def test_verify_rejects_correspondence_digest_drift(tmp_path: Path) -> None:
    handoff, root, recovery, screen, response, message = _handoff(tmp_path)
    message.write_text("correspondence changed after review", encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="digest binding"):
        verify_gaze_in_wild_first_party_quarantine_readiness(
            handoff,
            response,
            message,
            _request(),
            candidate_root=root,
            recovery_record_or_path=recovery,
            candidate_screen_record_or_path=screen,
        )


def test_verify_rejects_candidate_tree_drift(tmp_path: Path) -> None:
    handoff, root, recovery, screen, response, message = _handoff(tmp_path)
    (root / "unexpected.txt").write_text("drift", encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="no longer matches"):
        verify_gaze_in_wild_first_party_quarantine_readiness(
            handoff,
            response,
            message,
            _request(),
            candidate_root=root,
            recovery_record_or_path=recovery,
            candidate_screen_record_or_path=screen,
        )


def test_persisted_readiness_record_exactly_reverifies_without_private_content(
    tmp_path: Path,
) -> None:
    handoff, root, recovery, screen, response, message = _handoff(tmp_path)
    target = tmp_path / "readiness.json"
    written = write_gaze_in_wild_first_party_quarantine_readiness(
        handoff,
        target,
        response_record_or_path=response,
        correspondence_path=message,
        request=_request(),
        candidate_root=root,
        recovery_record_or_path=recovery,
        candidate_screen_record_or_path=screen,
    )
    assert written == target
    validated = validate_gaze_in_wild_first_party_quarantine_readiness(target)
    assert validated == handoff
    assert "private first-party reply placeholder" not in target.read_text(encoding="utf-8")
    assert "private-or-public-location-reviewed-locally" not in target.read_text(encoding="utf-8")
    verify_gaze_in_wild_first_party_quarantine_readiness(
        target,
        response,
        message,
        _request(),
        candidate_root=root,
        recovery_record_or_path=recovery,
        candidate_screen_record_or_path=screen,
    )


def test_write_requires_output_outside_candidate_tree(tmp_path: Path) -> None:
    handoff, root, recovery, screen, response, message = _handoff(tmp_path)
    with pytest.raises(BenchmarkIntegrityError, match="outside"):
        write_gaze_in_wild_first_party_quarantine_readiness(
            handoff,
            root / "readiness.json",
            response_record_or_path=response,
            correspondence_path=message,
            request=_request(),
            candidate_root=root,
            recovery_record_or_path=recovery,
            candidate_screen_record_or_path=screen,
        )
