from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from scipy.io import savemat

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_audit import GazeInWildSourceAuditSpec
from gazeforge.gaze_in_wild_candidate_preflight import (
    build_gaze_in_wild_candidate_processdata_screen,
)
from gazeforge.gaze_in_wild_exact_copy_review import (
    bind_verified_exact_copy_review_to_quarantine_exit,
    build_gaze_in_wild_exact_copy_review,
    exact_copy_review_fingerprint,
    review_gaze_in_wild_exact_copy_record,
    validate_gaze_in_wild_exact_copy_review,
    verify_gaze_in_wild_exact_copy_review,
    write_gaze_in_wild_exact_copy_review,
)
from gazeforge.gaze_in_wild_first_party_readiness import (
    build_gaze_in_wild_first_party_quarantine_readiness,
)
from gazeforge.gaze_in_wild_first_party_resolution import (
    build_gaze_in_wild_first_party_resolution_response_scaffold,
    response_fingerprint,
    validate_gaze_in_wild_first_party_resolution_request,
)
from gazeforge.gaze_in_wild_quarantine_exit import (
    build_gaze_in_wild_quarantine_exit_authorization,
)
from gazeforge.gaze_in_wild_recovery import build_gaze_in_wild_recovery_candidate_review
from gazeforge.source_candidate import build_candidate_source_inventory

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
    root.mkdir(parents=True)
    _write_processdata(root / "opaque.mat")
    (root / "README").write_text("unverified recovery candidate\n", encoding="utf-8")
    recovery = build_gaze_in_wild_recovery_candidate_review(
        root,
        candidate_kind=kind,
        provenance_source="recovery lead",
        provenance_note="Candidate retained for exact identity review only.",
    )
    screen = build_gaze_in_wild_candidate_processdata_screen(
        root,
        recovery,
        processdata_relative_path="opaque.mat",
    )
    return root, recovery, screen


def _response(
    tmp_path: Path,
    *,
    analysis: str = "permitted",
    redistribution: str = "restricted",
) -> tuple[dict, Path]:
    request = _request()
    message = tmp_path / "first-party-reply.eml"
    message.write_text("private first-party reply placeholder", encoding="utf-8")
    record = build_gaze_in_wild_first_party_resolution_response_scaffold(message, request)
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
            "status": "verified",
            "authority_scope": "GIW dataset-file terms",
            "evidence_basis": "Human-reviewed authority evidence.",
        }
    )
    record["archive_review"].update(
        {
            "authoritative_archive_location_status": "provided",
            "archive_location": "private-or-public-location-reviewed-locally",
            "source_authority_statement_present": True,
            "evidence_basis": "Human-reviewed archive-location statement.",
        }
    )
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


def _readiness(
    tmp_path: Path,
    *,
    analysis: str = "permitted",
    redistribution: str = "restricted",
) -> tuple[dict, Path, dict, dict]:
    root, recovery, screen = _candidate(tmp_path)
    response, message = _response(
        tmp_path,
        analysis=analysis,
        redistribution=redistribution,
    )
    readiness = build_gaze_in_wild_first_party_quarantine_readiness(
        response,
        message,
        _request(),
        candidate_root=root,
        recovery_record_or_path=recovery,
        candidate_screen_record_or_path=screen,
    )
    return readiness, root, recovery, screen


def _reference(
    tmp_path: Path,
    candidate_root: Path,
    *,
    mutate_readme: bool = False,
    add_extra: bool = False,
) -> tuple[Path, Path]:
    root = tmp_path / "reference"
    shutil.copytree(candidate_root, root)
    if mutate_readme:
        (root / "README").write_text("different reference content\n", encoding="utf-8")
    if add_extra:
        (root / "extra.bin").write_bytes(b"extra")
    provenance = tmp_path / "reference-provenance.txt"
    provenance.write_text(
        "local reviewer evidence linking this tree to the reviewed first-party source",
        encoding="utf-8",
    )
    return root, provenance


def _exact_fixture(
    tmp_path: Path,
    *,
    mutate_readme: bool = False,
    add_extra: bool = False,
):
    readiness, candidate_root, recovery, screen = _readiness(tmp_path)
    reference_root, provenance = _reference(
        tmp_path,
        candidate_root,
        mutate_readme=mutate_readme,
        add_extra=add_extra,
    )
    record = build_gaze_in_wild_exact_copy_review(
        readiness,
        candidate_root=candidate_root,
        recovery_record_or_path=recovery,
        candidate_screen_record_or_path=screen,
        reference_root=reference_root,
        reference_provenance_path=provenance,
    )
    return record, readiness, candidate_root, recovery, screen, reference_root, provenance


def _reviewed(record: dict, *, reference_binding_verified: bool = True) -> dict:
    return review_gaze_in_wild_exact_copy_record(
        record,
        reviewer="independent exact-copy reviewer",
        reviewed_at="2026-09-06",
        reference_binding_verified=reference_binding_verified,
        evidence_basis="Reference provenance digest and local acquisition record reviewed.",
    )


def _verify(record: dict, fixture) -> object:
    _, readiness, candidate_root, recovery, screen, reference_root, provenance = fixture
    return verify_gaze_in_wild_exact_copy_review(
        record,
        readiness_record_or_path=readiness,
        candidate_root=candidate_root,
        recovery_record_or_path=recovery,
        candidate_screen_record_or_path=screen,
        reference_root=reference_root,
        reference_provenance_path=provenance,
    )


def _quarantine_pending(root: Path, recovery: dict):
    inventory = build_candidate_source_inventory(root, dataset_key="gaze-in-the-wild")
    spec = GazeInWildSourceAuditSpec(
        dataset_name="Gaze-in-the-Wild",
        dataset_version="reviewed-version",
        source="reviewed-authoritative-source",
        source_revision="reviewed-source-revision",
        license="reviewed dataset-file terms",
        reuse_terms_source="reviewed terms source",
        notes=[
            f"Candidate inventory fingerprint: {inventory.inventory_fingerprint_sha256}",
            "Template remains non-empirical.",
        ],
    )
    pending = build_gaze_in_wild_quarantine_exit_authorization(
        root,
        recovery,
        inventory,
        spec,
    )
    return pending


def test_pending_exact_copy_review_binds_complete_equal_manifests(tmp_path: Path) -> None:
    fixture = _exact_fixture(tmp_path)
    record = fixture[0]

    assert record["comparison"]["exact_manifest_match"] is True
    assert record["comparison"]["candidate_only_path_count"] == 0
    assert record["comparison"]["reference_only_path_count"] == 0
    assert record["decision"] == "pending_review"
    assert record["result"]["exact_copy_identity_verified"] is False
    assert record["scientific_boundary"]["quarantine_exit_authorized"] is False
    assert record["scientific_boundary"]["empirical_evidence_created"] is False
    serialized = json.dumps(record)
    assert "local reviewer evidence linking" not in serialized
    assert "private-or-public-location-reviewed-locally" not in serialized


def test_reviewed_equal_reference_can_satisfy_exact_copy_gate_only(tmp_path: Path) -> None:
    fixture = _exact_fixture(tmp_path)
    record = _reviewed(fixture[0])
    validated = _verify(record, fixture)

    assert validated.exact_copy_identity_verified is True
    assert record["decision"] == "verified_against_reviewed_reference_manifest"
    assert record["result"]["exact_copy_gate_satisfied"] is True
    assert record["result"]["historical_original_distribution_equivalence_verified"] is False
    assert record["result"]["quarantine_exit_authorized"] is False


def test_human_reference_binding_is_required_even_for_equal_bytes(tmp_path: Path) -> None:
    fixture = _exact_fixture(tmp_path)
    record = _reviewed(fixture[0], reference_binding_verified=False)
    validated = _verify(record, fixture)

    assert validated.exact_copy_identity_verified is False
    assert record["decision"] == "not_verified"


def test_manifest_mismatch_cannot_be_overridden_by_human_reference_binding(tmp_path: Path) -> None:
    fixture = _exact_fixture(tmp_path, mutate_readme=True)
    record = _reviewed(fixture[0])
    validated = _verify(record, fixture)

    assert record["comparison"]["exact_manifest_match"] is False
    assert record["comparison"]["shared_path_content_mismatch_count"] == 1
    assert validated.exact_copy_identity_verified is False
    assert record["decision"] == "not_verified"


def test_selected_processdata_match_is_not_enough_when_reference_has_extra_file(
    tmp_path: Path,
) -> None:
    fixture = _exact_fixture(tmp_path, add_extra=True)
    record = _reviewed(fixture[0])

    assert record["candidate_binding"]["selected_file"]["sha256"] == fixture[1][
        "candidate_binding"
    ]["selected_file"]["sha256"]
    assert record["comparison"]["reference_only_path_count"] == 1
    assert record["result"]["exact_copy_identity_verified"] is False


def test_exact_copy_review_rejects_blocked_first_party_readiness(tmp_path: Path) -> None:
    readiness, candidate_root, recovery, screen = _readiness(
        tmp_path,
        analysis="unresolved",
        redistribution="unresolved",
    )
    reference_root, provenance = _reference(tmp_path, candidate_root)

    with pytest.raises(BenchmarkIntegrityError, match="preliminary blockers"):
        build_gaze_in_wild_exact_copy_review(
            readiness,
            candidate_root=candidate_root,
            recovery_record_or_path=recovery,
            candidate_screen_record_or_path=screen,
            reference_root=reference_root,
            reference_provenance_path=provenance,
        )


def test_exact_copy_review_requires_distinct_non_nested_trees(tmp_path: Path) -> None:
    readiness, candidate_root, recovery, screen = _readiness(tmp_path)
    provenance = tmp_path / "provenance.txt"
    provenance.write_text("reviewed locally", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="separate, non-nested"):
        build_gaze_in_wild_exact_copy_review(
            readiness,
            candidate_root=candidate_root,
            recovery_record_or_path=recovery,
            candidate_screen_record_or_path=screen,
            reference_root=candidate_root,
            reference_provenance_path=provenance,
        )


def test_reference_provenance_must_be_outside_compared_trees(tmp_path: Path) -> None:
    readiness, candidate_root, recovery, screen = _readiness(tmp_path)
    reference_root, _ = _reference(tmp_path, candidate_root)
    inside = reference_root / "provenance.txt"
    inside.write_text("would contaminate the reference snapshot", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="outside both"):
        build_gaze_in_wild_exact_copy_review(
            readiness,
            candidate_root=candidate_root,
            recovery_record_or_path=recovery,
            candidate_screen_record_or_path=screen,
            reference_root=reference_root,
            reference_provenance_path=inside,
        )


def test_result_promotion_is_rejected_even_after_refingerprinting(tmp_path: Path) -> None:
    fixture = _exact_fixture(tmp_path)
    record = fixture[0]
    record["result"]["exact_copy_identity_verified"] = True
    record["record_fingerprint_sha256"] = exact_copy_review_fingerprint(record)

    with pytest.raises(BenchmarkIntegrityError, match="result derivation"):
        validate_gaze_in_wild_exact_copy_review(record)


def test_scientific_gate_promotion_is_rejected_after_refingerprinting(tmp_path: Path) -> None:
    fixture = _exact_fixture(tmp_path)
    record = fixture[0]
    record["scientific_boundary"]["quarantine_exit_authorized"] = True
    record["record_fingerprint_sha256"] = exact_copy_review_fingerprint(record)

    with pytest.raises(BenchmarkIntegrityError, match="scientific boundary"):
        validate_gaze_in_wild_exact_copy_review(record)


def test_candidate_tree_drift_is_detected_by_fresh_verification(tmp_path: Path) -> None:
    fixture = _exact_fixture(tmp_path)
    record = _reviewed(fixture[0])
    candidate_root = fixture[2]
    (candidate_root / "unexpected.bin").write_bytes(b"drift")

    with pytest.raises(BenchmarkIntegrityError):
        _verify(record, fixture)


def test_reference_tree_drift_is_detected_by_fresh_verification(tmp_path: Path) -> None:
    fixture = _exact_fixture(tmp_path)
    record = _reviewed(fixture[0])
    reference_root = fixture[5]
    (reference_root / "README").write_text("drift", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="reference inventory drifted"):
        _verify(record, fixture)


def test_reference_provenance_digest_drift_is_detected(tmp_path: Path) -> None:
    fixture = _exact_fixture(tmp_path)
    record = _reviewed(fixture[0])
    provenance = fixture[6]
    provenance.write_text("different provenance evidence", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="provenance digest drifted"):
        _verify(record, fixture)


def test_persisted_review_requires_fresh_binding_before_quarantine_handoff(
    tmp_path: Path,
) -> None:
    fixture = _exact_fixture(tmp_path)
    record = _reviewed(fixture[0])
    target = tmp_path / "exact-copy-review.json"
    write_gaze_in_wild_exact_copy_review(
        record,
        target,
        candidate_root=fixture[2],
        reference_root=fixture[5],
    )
    loaded = validate_gaze_in_wild_exact_copy_review(target)
    pending = _quarantine_pending(fixture[2], fixture[3])

    with pytest.raises(BenchmarkIntegrityError, match="freshly revalidated"):
        bind_verified_exact_copy_review_to_quarantine_exit(pending, loaded)

    fresh = verify_gaze_in_wild_exact_copy_review(
        target,
        readiness_record_or_path=fixture[1],
        candidate_root=fixture[2],
        recovery_record_or_path=fixture[3],
        candidate_screen_record_or_path=fixture[4],
        reference_root=fixture[5],
        reference_provenance_path=fixture[6],
    )
    bound = bind_verified_exact_copy_review_to_quarantine_exit(pending, fresh)
    assert bound.decision == "pending"
    assert bound.exact_copy_identity_verified is True
    assert fresh.record_fingerprint_sha256 in bound.exact_copy_identity_evidence
    assert bound.source_authority_verified is False
    assert bound.dataset_file_rights_resolved is False
    assert bound.analysis_use_permitted is False


def test_non_verified_review_cannot_support_quarantine_handoff(tmp_path: Path) -> None:
    fixture = _exact_fixture(tmp_path, mutate_readme=True)
    record = _reviewed(fixture[0])
    fresh = _verify(record, fixture)
    pending = _quarantine_pending(fixture[2], fixture[3])

    with pytest.raises(BenchmarkIntegrityError, match="identity decision is not verified"):
        bind_verified_exact_copy_review_to_quarantine_exit(pending, fresh)


def test_exact_copy_writer_refuses_both_compared_trees(tmp_path: Path) -> None:
    fixture = _exact_fixture(tmp_path)
    record = fixture[0]

    with pytest.raises(BenchmarkIntegrityError, match="outside both"):
        write_gaze_in_wild_exact_copy_review(
            record,
            fixture[2] / "review.json",
            candidate_root=fixture[2],
            reference_root=fixture[5],
        )
    with pytest.raises(BenchmarkIntegrityError, match="outside both"):
        write_gaze_in_wild_exact_copy_review(
            record,
            fixture[5] / "review.json",
            candidate_root=fixture[2],
            reference_root=fixture[5],
        )
