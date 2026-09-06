from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest
from scipy.io import savemat

from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError
from gazeforge.gaze_in_wild_candidate_preflight import (
    build_gaze_in_wild_candidate_processdata_screen,
    candidate_processdata_screen_fingerprint,
    validate_gaze_in_wild_candidate_processdata_screen,
    verify_gaze_in_wild_candidate_processdata_screen,
    write_gaze_in_wild_candidate_processdata_screen,
)
from gazeforge.gaze_in_wild_recovery import (
    build_gaze_in_wild_recovery_candidate_review,
    validate_gaze_in_wild_recovery_candidate_review,
)


def _write_processdata(path: Path, *, labels: bool = True) -> None:
    n = 8
    t = np.arange(n, dtype=float) / 300.0
    etg: dict[str, object] = {
        "POR": np.column_stack(
            [np.linspace(100.0, 800.0, n), np.linspace(200.0, 900.0, n)]
        ),
        "Confidence": np.array([1.0, 0.9, np.nan, 0.8, 1.0, 0.7, 0.95, 0.85]),
        "SceneResolution": np.array([1920.0, 1080.0]),
    }
    if labels:
        etg["Labels"] = np.arange(n, dtype=float) % 3
    savemat(
        path,
        {
            "ProcessData": {
                "PrIdx": 3,
                "TrIdx": 4,
                "SR": 300.0,
                "T": t,
                "ETG": etg,
            }
        },
    )


def _candidate_tree(tmp_path: Path) -> Path:
    root = tmp_path / "candidate"
    process = root / "unclassified"
    process.mkdir(parents=True)
    _write_processdata(process / "opaque-a.mat")
    (root / "other.bin").write_bytes(b"not a matlab ProcessData file")
    (root / "README").write_text(
        "Unverified recovery candidate; names do not establish file roles.\n",
        encoding="utf-8",
    )
    return root


def _recovery(root: Path) -> dict:
    return build_gaze_in_wild_recovery_candidate_review(
        root,
        candidate_kind="candidate_original_layout_unverified",
        provenance_source="recovery lead",
        provenance_note="Candidate retained for identity review; authority and rights unresolved.",
    )


def _screen(root: Path, recovery: dict) -> dict:
    return build_gaze_in_wild_candidate_processdata_screen(
        root,
        recovery,
        processdata_relative_path="unclassified/opaque-a.mat",
    )


def _refingerprint(screen: dict) -> None:
    screen["record_fingerprint_sha256"] = candidate_processdata_screen_fingerprint(screen)


def test_explicit_selected_file_is_screened_but_candidate_stays_quarantined(
    tmp_path: Path,
) -> None:
    root = _candidate_tree(tmp_path)
    recovery = _recovery(root)
    screen = _screen(root, recovery)

    assert screen["candidate_status"] == "quarantined"
    assert screen["selected_file"]["relative_path"] == "unclassified/opaque-a.mat"
    assert screen["selected_file"]["generic_recovery_role"] == "unclassified"
    assert screen["processdata_preflight"]["participant_index"] == 3
    assert screen["processdata_preflight"]["trial_index"] == 4
    assert screen["processdata_preflight"]["stored_rate_hz"] == pytest.approx(300.0)
    assert screen["processdata_preflight"]["timestamp_count"] == 8
    assert screen["processdata_preflight"]["por_shape"] == (8, 2)
    assert screen["processdata_preflight"]["confidence_shape"] == (8,)
    assert screen["processdata_preflight"]["labels_present"] is True
    assert screen["processdata_preflight"]["top_level_labeldata_present"] is False
    assert screen["scientific_boundary"]["candidate_tree_binding_verified"] is True
    assert screen["scientific_boundary"]["selected_processdata_structure_compatible"] is True
    assert screen["scientific_boundary"]["quarantine_exit_authorized"] is False
    assert screen["scientific_boundary"]["source_audit_ready"] is False
    assert screen["scientific_boundary"]["empirical_evidence_eligible"] is False

    validated = validate_gaze_in_wild_candidate_processdata_screen(screen)
    assert validated == screen


def test_screen_binds_exact_recovery_record_tree_and_file_identity(tmp_path: Path) -> None:
    root = _candidate_tree(tmp_path)
    recovery = _recovery(root)
    screen = _screen(root, recovery)
    by_path = {item["path"]: item for item in recovery["inventory"]["files"]}
    selected = by_path["unclassified/opaque-a.mat"]

    assert screen["recovery_record_fingerprint_sha256"] == recovery[
        "record_fingerprint_sha256"
    ]
    assert screen["recovery_tree_fingerprint_sha256"] == recovery["inventory"][
        "tree_fingerprint_sha256"
    ]
    assert screen["selected_file"]["sha256"] == selected["sha256"]
    assert screen["selected_file"]["bytes"] == selected["bytes"]
    assert screen["processdata_preflight"]["sha256"] == selected["sha256"]
    assert screen["processdata_preflight"]["bytes"] == selected["bytes"]


def test_screen_does_not_modify_generic_recovery_review_or_file_roles(tmp_path: Path) -> None:
    root = _candidate_tree(tmp_path)
    recovery = _recovery(root)
    before = copy.deepcopy(recovery)
    screen = _screen(root, recovery)

    assert recovery == before
    validate_gaze_in_wild_recovery_candidate_review(recovery)
    assert all(item["role"] == "unclassified" for item in recovery["inventory"]["files"])
    assert recovery["interpretation_policy"]["matlab_schema_inference_permitted"] is False
    assert screen["screening_policy"]["generic_recovery_file_roles_remain_unclassified"]


def test_screen_requires_explicit_inventory_member(tmp_path: Path) -> None:
    root = _candidate_tree(tmp_path)
    recovery = _recovery(root)
    with pytest.raises(BenchmarkIntegrityError, match="exactly one reviewed inventory file"):
        build_gaze_in_wild_candidate_processdata_screen(
            root,
            recovery,
            processdata_relative_path="missing.mat",
        )


@pytest.mark.parametrize("unsafe", ["../escape.mat", "/absolute.mat", "a/../../escape.mat"])
def test_screen_rejects_unsafe_explicit_paths(tmp_path: Path, unsafe: str) -> None:
    root = _candidate_tree(tmp_path)
    recovery = _recovery(root)
    with pytest.raises(BenchmarkIntegrityError, match="safe explicit relative path"):
        build_gaze_in_wild_candidate_processdata_screen(
            root,
            recovery,
            processdata_relative_path=unsafe,
        )


def test_screen_rejects_candidate_tree_drift_before_opening_selected_file(tmp_path: Path) -> None:
    root = _candidate_tree(tmp_path)
    recovery = _recovery(root)
    (root / "unexpected.txt").write_text("new material", encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="no longer matches"):
        _screen(root, recovery)


def test_screen_rejects_selected_file_byte_drift(tmp_path: Path) -> None:
    root = _candidate_tree(tmp_path)
    recovery = _recovery(root)
    selected = root / "unclassified" / "opaque-a.mat"
    selected.write_bytes(selected.read_bytes() + b"drift")
    with pytest.raises(BenchmarkIntegrityError, match="no longer matches"):
        _screen(root, recovery)


def test_explicit_non_processdata_inventory_file_fails_structural_preflight(
    tmp_path: Path,
) -> None:
    root = _candidate_tree(tmp_path)
    recovery = _recovery(root)
    with pytest.raises(SchemaError):
        build_gaze_in_wild_candidate_processdata_screen(
            root,
            recovery,
            processdata_relative_path="other.bin",
        )


def test_malformed_processdata_candidate_fails_without_promoting_recovery(
    tmp_path: Path,
) -> None:
    root = tmp_path / "candidate"
    root.mkdir()
    savemat(root / "opaque.mat", {"Other": np.array([1.0])})
    recovery = _recovery(root)
    before = copy.deepcopy(recovery)

    with pytest.raises(SchemaError, match="does not contain MATLAB variable 'ProcessData'"):
        build_gaze_in_wild_candidate_processdata_screen(
            root,
            recovery,
            processdata_relative_path="opaque.mat",
        )
    assert recovery == before
    validate_gaze_in_wild_recovery_candidate_review(recovery)


def test_etg_labels_never_imply_separate_labeldata_or_labeller_recovery(tmp_path: Path) -> None:
    root = _candidate_tree(tmp_path)
    screen = _screen(root, _recovery(root))
    assert screen["processdata_preflight"]["labels_present"] is True
    assert screen["processdata_preflight"]["top_level_labeldata_present"] is False
    assert screen["scientific_boundary"]["separate_labeldata_recovered"] is False
    assert screen["scientific_boundary"]["independent_labeller_recoverability_verified"] is False


@pytest.mark.parametrize(
    "gate",
    [
        "source_authority_verified",
        "exact_original_distribution_format_verified",
        "exact_original_copy_identity_verified",
        "dataset_file_rights_resolved",
        "analysis_use_authorized",
        "redistribution_authorized",
        "participant_mapping_verified",
        "complete_trial_task_mapping_verified",
        "coordinate_unit_verified_from_candidate",
        "sampling_cadence_verified_from_candidate",
        "corpus_sampling_rate_distribution_verified",
        "published_acquisition_cadence_verified_from_candidate",
        "separate_labeldata_recovered",
        "independent_labeller_recoverability_verified",
        "quarantine_exit_authorized",
        "source_audit_ready",
        "empirical_evidence_eligible",
        "human_human_agreement_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_performance_created",
        "gp3_validity_created",
        "frozen_evidence_performance_claim_created",
    ],
)
def test_validator_rejects_every_scientific_promotion_even_after_refingerprinting(
    tmp_path: Path,
    gate: str,
) -> None:
    root = _candidate_tree(tmp_path)
    screen = _screen(root, _recovery(root))
    screen["scientific_boundary"][gate] = True
    _refingerprint(screen)
    with pytest.raises(BenchmarkIntegrityError, match="scientific boundary"):
        validate_gaze_in_wild_candidate_processdata_screen(screen)


@pytest.mark.parametrize(
    "policy",
    [
        "filename_identity_inference_permitted",
        "source_authority_inference_permitted",
        "rights_inference_permitted",
        "selected_file_structure_can_establish_distribution_identity",
        "selected_file_structure_can_authorize_quarantine_exit",
        "candidate_can_materialize_empirical_audit_spec",
    ],
)
def test_validator_rejects_screening_policy_promotion_after_refingerprinting(
    tmp_path: Path,
    policy: str,
) -> None:
    root = _candidate_tree(tmp_path)
    screen = _screen(root, _recovery(root))
    screen["screening_policy"][policy] = True
    _refingerprint(screen)
    with pytest.raises(BenchmarkIntegrityError, match="screening policy"):
        validate_gaze_in_wild_candidate_processdata_screen(screen)


def test_validator_rejects_generic_role_promotion_after_refingerprinting(
    tmp_path: Path,
) -> None:
    root = _candidate_tree(tmp_path)
    screen = _screen(root, _recovery(root))
    screen["selected_file"]["generic_recovery_role"] = "process_data"
    _refingerprint(screen)
    with pytest.raises(BenchmarkIntegrityError, match="generic recovery file role"):
        validate_gaze_in_wild_candidate_processdata_screen(screen)


def test_validator_rejects_preflight_identity_drift_after_refingerprinting(
    tmp_path: Path,
) -> None:
    root = _candidate_tree(tmp_path)
    screen = _screen(root, _recovery(root))
    screen["processdata_preflight"]["sha256"] = "0" * 64
    _refingerprint(screen)
    with pytest.raises(BenchmarkIntegrityError, match="SHA-256 binding drifted"):
        validate_gaze_in_wild_candidate_processdata_screen(screen)


def test_verify_rebuilds_screen_and_detects_recovery_binding_substitution(
    tmp_path: Path,
) -> None:
    root = _candidate_tree(tmp_path)
    recovery = _recovery(root)
    screen = _screen(root, recovery)
    verify_gaze_in_wild_candidate_processdata_screen(root, recovery, screen)

    substituted = copy.deepcopy(recovery)
    substituted["provenance"]["note"] += " changed"
    from gazeforge.gaze_in_wild_recovery import recovery_candidate_record_fingerprint

    substituted["record_fingerprint_sha256"] = recovery_candidate_record_fingerprint(substituted)
    with pytest.raises(BenchmarkIntegrityError, match="different recovery review"):
        verify_gaze_in_wild_candidate_processdata_screen(root, substituted, screen)


def test_write_screen_requires_reverification_and_output_outside_candidate_tree(
    tmp_path: Path,
) -> None:
    root = _candidate_tree(tmp_path)
    recovery = _recovery(root)
    screen = _screen(root, recovery)

    with pytest.raises(BenchmarkIntegrityError, match="outside the candidate tree"):
        write_gaze_in_wild_candidate_processdata_screen(
            screen,
            root / "screen.json",
            candidate_root=root,
            recovery_record_or_path=recovery,
        )

    target = tmp_path / "screen.json"
    assert write_gaze_in_wild_candidate_processdata_screen(
        screen,
        target,
        candidate_root=root,
        recovery_record_or_path=recovery,
    ) == target
    validate_gaze_in_wild_candidate_processdata_screen(target)

    with pytest.raises(FileExistsError):
        write_gaze_in_wild_candidate_processdata_screen(
            screen,
            target,
            candidate_root=root,
            recovery_record_or_path=recovery,
        )
