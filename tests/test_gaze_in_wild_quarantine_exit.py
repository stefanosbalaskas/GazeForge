from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_audit import (
    GazeInWildLabelFileRecord,
    GazeInWildProcessFileRecord,
    GazeInWildSourceAuditSpec,
)
from gazeforge.gaze_in_wild_quarantine_exit import (
    GazeInWildQuarantineExitAuthorization,
    build_gaze_in_wild_quarantine_exit_authorization,
    load_gaze_in_wild_quarantine_exit_authorization,
    require_authorized_gaze_in_wild_quarantine_exit,
    validate_gaze_in_wild_quarantine_exit_authorization,
    write_gaze_in_wild_quarantine_exit_authorization,
)
from gazeforge.gaze_in_wild_recovery import build_gaze_in_wild_recovery_candidate_review
from gazeforge.source_candidate import (
    CandidateSourceInventory,
    build_candidate_source_inventory,
)
from gazeforge.source_candidate_authorization import source_audit_template_fingerprint


def _candidate(tmp_path: Path) -> Path:
    root = tmp_path / "candidate"
    (root / "ProcessData").mkdir(parents=True)
    (root / "LabelData").mkdir(parents=True)
    (root / "ProcessData" / "PrIdx_1_TrIdx_1.mat").write_bytes(b"process")
    (root / "LabelData" / "LabellerIdx_7_PrIdx_1_TrIdx_1.mat").write_bytes(b"label")
    (root / "README").write_text("unverified candidate\n", encoding="utf-8")
    return root


def _recovery(root: Path, *, kind: str = "candidate_original_layout_unverified") -> dict:
    return build_gaze_in_wild_recovery_candidate_review(
        root,
        candidate_kind=kind,
        provenance_source="recovery lead",
        provenance_note="Candidate identity only; authority and rights are not inferred.",
    )


def _template(root: Path) -> tuple[CandidateSourceInventory, GazeInWildSourceAuditSpec]:
    inventory = build_candidate_source_inventory(root, dataset_key="gaze-in-the-wild")
    by_path = {item.path: item for item in inventory.files}
    process = by_path["ProcessData/PrIdx_1_TrIdx_1.mat"]
    label = by_path["LabelData/LabellerIdx_7_PrIdx_1_TrIdx_1.mat"]
    spec = GazeInWildSourceAuditSpec(
        dataset_name="Gaze-in-the-Wild",
        dataset_version="reviewed-version",
        source="reviewed-authoritative-source",
        source_revision="reviewed-source-revision",
        license="reviewed source terms",
        reuse_terms_source="reviewed terms source",
        dataset_status="template",
        participant_mapping_basis="reviewed mapping basis",
        coordinate_unit="pixels",
        coordinate_verification_basis="reviewed coordinate basis",
        label_files=[
            GazeInWildLabelFileRecord(
                path=label.path,
                sha256=label.sha256,
                bytes=label.bytes,
                participant_id="P01",
                trial_id="T01",
                labeller_id=7,
                process_path=process.path,
            )
        ],
        process_files=[
            GazeInWildProcessFileRecord(
                path=process.path,
                sha256=process.sha256,
                bytes=process.bytes,
            )
        ],
        notes=[
            f"Candidate inventory fingerprint: {inventory.inventory_fingerprint_sha256}",
            "This template remains non-empirical.",
        ],
    )
    return inventory, spec


def _authorized(pending: GazeInWildQuarantineExitAuthorization):
    return replace(
        pending,
        decision="authorized",
        reviewer="independent scientific reviewer",
        reviewed_at="2026-09-05",
        source_authority_verified=True,
        authoritative_source="reviewed-authoritative-source",
        authoritative_source_revision="reviewed-source-revision",
        source_authority_evidence="first-party authority evidence reviewed independently",
        exact_copy_identity_verified=True,
        exact_copy_identity_evidence="candidate manifest matched authoritative copy identity",
        dataset_file_rights_resolved=True,
        reuse_terms_verified=True,
        reuse_terms_source="reviewed terms source",
        rights_evidence="dataset-file rights and restrictions reviewed",
        analysis_use_permitted=True,
        analysis_use_evidence="analysis use explicitly permitted by reviewed terms",
        redistribution_status="restricted",
        redistribution_evidence="redistribution restrictions explicitly reviewed",
        authorization_basis="authority, exact-copy identity, and current rights independently reviewed",
        notes=("quarantine exit authorization test fixture",),
    )


def test_pending_exit_binds_recovery_inventory_and_template(tmp_path: Path) -> None:
    root = _candidate(tmp_path)
    recovery = _recovery(root)
    inventory, spec = _template(root)

    pending = build_gaze_in_wild_quarantine_exit_authorization(
        root,
        recovery,
        inventory,
        spec,
    )

    assert pending.decision == "pending"
    assert pending.recovery_candidate_kind == "candidate_original_layout_unverified"
    assert pending.candidate_inventory_fingerprint_sha256 == inventory.inventory_fingerprint_sha256
    assert pending.audit_template_fingerprint_sha256 == source_audit_template_fingerprint(spec)
    payload = pending.to_dict()
    assert payload["scientific_boundary"]["empirical_evidence_created"] is False
    assert payload["scientific_boundary"]["source_audit_executed"] is False
    assert payload["scientific_boundary"]["human_human_agreement_created"] is False
    assert len(payload["record_fingerprint_sha256"]) == 64


def test_authorized_exit_still_does_not_open_scientific_result_gates(tmp_path: Path) -> None:
    root = _candidate(tmp_path)
    recovery = _recovery(root)
    inventory, spec = _template(root)
    authorized = _authorized(
        build_gaze_in_wild_quarantine_exit_authorization(root, recovery, inventory, spec)
    )

    require_authorized_gaze_in_wild_quarantine_exit(authorized, spec)
    payload = authorized.to_dict()
    assert authorized.decision == "authorized"
    assert not any(
        payload["scientific_boundary"][key]
        for key in (
            "source_audit_execution_authorized_by_this_record",
            "source_audit_executed",
            "participant_mapping_verified",
            "coordinate_unit_verified",
            "sampling_cadence_verified",
            "independent_labeller_recoverability_verified",
            "human_human_agreement_created",
            "participant_disjoint_model_validation_created",
            "cross_dataset_performance_created",
            "gp3_validity_created",
            "frozen_evidence_performance_claim_created",
            "empirical_evidence_created",
        )
    )


def test_transformed_secondary_candidate_cannot_leave_quarantine(tmp_path: Path) -> None:
    root = _candidate(tmp_path)
    recovery = _recovery(root, kind="transformed_secondary_collection")
    inventory, spec = _template(root)
    pending = build_gaze_in_wild_quarantine_exit_authorization(
        root,
        recovery,
        inventory,
        spec,
    )

    with pytest.raises(BenchmarkIntegrityError, match="cannot leave quarantine"):
        _authorized(pending)


def test_labeller_provenance_only_candidate_cannot_leave_quarantine(tmp_path: Path) -> None:
    root = _candidate(tmp_path)
    recovery = _recovery(root, kind="labeller_provenance_only")
    inventory, spec = _template(root)
    pending = build_gaze_in_wild_quarantine_exit_authorization(
        root,
        recovery,
        inventory,
        spec,
    )

    with pytest.raises(BenchmarkIntegrityError, match="cannot leave quarantine"):
        _authorized(pending)


def test_authorized_exit_requires_exact_copy_and_rights_gates(tmp_path: Path) -> None:
    root = _candidate(tmp_path)
    recovery = _recovery(root)
    inventory, spec = _template(root)
    pending = build_gaze_in_wild_quarantine_exit_authorization(
        root,
        recovery,
        inventory,
        spec,
    )

    with pytest.raises(BenchmarkIntegrityError, match="authority/exact-copy/rights"):
        replace(
            pending,
            decision="authorized",
            reviewer="reviewer",
            reviewed_at="2026-09-05",
            source_authority_verified=True,
            exact_copy_identity_verified=False,
            dataset_file_rights_resolved=True,
            reuse_terms_verified=True,
            analysis_use_permitted=True,
            redistribution_status="restricted",
        )


def test_exit_refuses_recovery_and_generic_inventory_disagreement(tmp_path: Path) -> None:
    root = _candidate(tmp_path)
    recovery = _recovery(root)
    inventory, spec = _template(root)
    tampered = copy.deepcopy(recovery)
    tampered["inventory"]["files"][0]["path"] = "different.mat"

    with pytest.raises(BenchmarkIntegrityError):
        build_gaze_in_wild_quarantine_exit_authorization(root, tampered, inventory, spec)


def test_exit_refuses_template_not_bound_to_inventory(tmp_path: Path) -> None:
    root = _candidate(tmp_path)
    recovery = _recovery(root)
    inventory, spec = _template(root)
    spec.notes = ["reviewed template but missing exact candidate inventory binding"]

    with pytest.raises(BenchmarkIntegrityError, match="candidate inventory fingerprint"):
        build_gaze_in_wild_quarantine_exit_authorization(root, recovery, inventory, spec)


def test_authorized_exit_refuses_conflicting_source_identity(tmp_path: Path) -> None:
    root = _candidate(tmp_path)
    recovery = _recovery(root)
    inventory, spec = _template(root)
    authorized = _authorized(
        build_gaze_in_wild_quarantine_exit_authorization(root, recovery, inventory, spec)
    )
    conflicting = replace(authorized, authoritative_source="different source")

    with pytest.raises(BenchmarkIntegrityError, match="source/rights identity conflicts"):
        validate_gaze_in_wild_quarantine_exit_authorization(
            conflicting,
            root=root,
            recovery_record_or_path=recovery,
            inventory=inventory,
            spec=spec,
        )


def test_exit_revalidation_detects_candidate_tree_drift(tmp_path: Path) -> None:
    root = _candidate(tmp_path)
    recovery = _recovery(root)
    inventory, spec = _template(root)
    pending = build_gaze_in_wild_quarantine_exit_authorization(
        root,
        recovery,
        inventory,
        spec,
    )
    (root / "unexpected.bin").write_bytes(b"drift")

    with pytest.raises(BenchmarkIntegrityError):
        validate_gaze_in_wild_quarantine_exit_authorization(
            pending,
            root=root,
            recovery_record_or_path=recovery,
            inventory=inventory,
            spec=spec,
        )


def test_exit_writer_loader_and_fingerprint_tamper(tmp_path: Path) -> None:
    root = _candidate(tmp_path)
    recovery = _recovery(root)
    inventory, spec = _template(root)
    pending = build_gaze_in_wild_quarantine_exit_authorization(
        root,
        recovery,
        inventory,
        spec,
    )
    target = tmp_path / "exit.json"
    write_gaze_in_wild_quarantine_exit_authorization(
        pending,
        target,
        candidate_root=root,
    )
    loaded = load_gaze_in_wild_quarantine_exit_authorization(target)
    assert loaded == pending

    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["decision"] = "authorized"
    target.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError):
        load_gaze_in_wild_quarantine_exit_authorization(target)


def test_exit_writer_stays_outside_candidate_tree(tmp_path: Path) -> None:
    root = _candidate(tmp_path)
    recovery = _recovery(root)
    inventory, spec = _template(root)
    pending = build_gaze_in_wild_quarantine_exit_authorization(
        root,
        recovery,
        inventory,
        spec,
    )

    with pytest.raises(BenchmarkIntegrityError, match="outside"):
        write_gaze_in_wild_quarantine_exit_authorization(
            pending,
            root / "exit.json",
            candidate_root=root,
        )
