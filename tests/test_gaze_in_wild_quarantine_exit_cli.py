from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import gazeforge.gaze_in_wild_exact_copy_review as exact_copy_module
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_audit import (
    GazeInWildLabelFileRecord,
    GazeInWildProcessFileRecord,
    GazeInWildSourceAuditSpec,
)
from gazeforge.gaze_in_wild_quarantine_exit import (
    load_gaze_in_wild_quarantine_exit_authorization,
    write_gaze_in_wild_quarantine_exit_authorization,
)
from gazeforge.gaze_in_wild_recovery import (
    build_gaze_in_wild_recovery_candidate_review,
    write_gaze_in_wild_recovery_candidate_review,
)
from gazeforge.source_candidate import (
    build_candidate_source_inventory,
    write_candidate_source_inventory,
)
from gazeforge.source_candidate_authorization import (
    CandidateSourceAuditAuthorization,
    source_audit_template_fingerprint,
    write_candidate_source_audit_authorization,
)
from gazeforge.source_candidate_cli import main

_EXACT_COPY_FP = "a" * 64


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "candidate"
    (root / "ProcessData").mkdir(parents=True)
    (root / "LabelData").mkdir(parents=True)
    (root / "ProcessData" / "PrIdx_1_TrIdx_1.mat").write_bytes(b"process")
    (root / "LabelData" / "LabellerIdx_7_PrIdx_1_TrIdx_1.mat").write_bytes(b"label")
    return root


def _artifacts(tmp_path: Path):
    root = _tree(tmp_path)
    inventory = build_candidate_source_inventory(root, dataset_key="gaze-in-the-wild")
    inventory_path = tmp_path / "inventory.json"
    write_candidate_source_inventory(inventory, inventory_path)

    recovery = build_gaze_in_wild_recovery_candidate_review(
        root,
        candidate_kind="candidate_original_layout_unverified",
        provenance_source="recovery lead",
        provenance_note="unverified candidate identity only",
    )
    recovery_path = tmp_path / "recovery.json"
    write_gaze_in_wild_recovery_candidate_review(
        recovery,
        recovery_path,
        candidate_root=root,
    )

    by_path = {item.path: item for item in inventory.files}
    process = by_path["ProcessData/PrIdx_1_TrIdx_1.mat"]
    label = by_path["LabelData/LabellerIdx_7_PrIdx_1_TrIdx_1.mat"]
    template = GazeInWildSourceAuditSpec(
        dataset_name="Gaze-in-the-Wild",
        dataset_version="reviewed-version",
        source="reviewed source",
        source_revision="reviewed revision",
        license="reviewed terms",
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
        notes=[f"Candidate inventory fingerprint: {inventory.inventory_fingerprint_sha256}"],
    )
    template_path = tmp_path / "template.json"
    template_path.write_text(
        json.dumps(template.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return root, inventory_path, recovery_path, template, template_path


def _generic_authorization(template: GazeInWildSourceAuditSpec):
    return CandidateSourceAuditAuthorization(
        dataset_key="gaze-in-the-wild",
        audit_template_fingerprint_sha256=source_audit_template_fingerprint(template),
        decision="authorized",
        reviewer="scientific reviewer",
        reviewed_at="2026-09-05",
        source_authority_verified=True,
        source_authority_evidence="source authority reviewed",
        reuse_terms_verified=True,
        reuse_terms_evidence="reuse terms reviewed",
        analysis_use_permitted=True,
        analysis_use_evidence="analysis permission reviewed",
        redistribution_status="restricted",
        redistribution_evidence="redistribution restrictions reviewed",
        coordinate_unit_verified=True,
        coordinate_verification_evidence="coordinate unit reviewed",
        participant_mapping_verified=True,
        participant_mapping_evidence="participant mapping reviewed",
        sampling_contract_reviewed=True,
        sampling_contract_evidence="sampling contract reviewed",
        annotation_contract_reviewed=True,
        annotation_contract_evidence="annotation contract reviewed",
        authorization_basis="source-audit entry gates reviewed",
    )


def _structured_cli_inputs(tmp_path: Path) -> dict[str, Path]:
    reference_root = tmp_path / "reference"
    reference_root.mkdir()
    exact_copy_review = tmp_path / "exact-copy-review.json"
    readiness_record = tmp_path / "readiness.json"
    candidate_screen = tmp_path / "candidate-screen.json"
    reference_provenance = tmp_path / "reference-provenance.txt"
    exact_copy_review.write_text("{}\n", encoding="utf-8")
    readiness_record.write_text("{}\n", encoding="utf-8")
    candidate_screen.write_text("{}\n", encoding="utf-8")
    reference_provenance.write_text("reviewed reference fixture\n", encoding="utf-8")
    return {
        "exact_copy_review": exact_copy_review,
        "readiness_record": readiness_record,
        "candidate_screen": candidate_screen,
        "reference_root": reference_root,
        "reference_provenance": reference_provenance,
    }


def _structured_cli_args(paths: dict[str, Path]) -> list[str]:
    return [
        "--exact-copy-review",
        str(paths["exact_copy_review"]),
        "--readiness-record",
        str(paths["readiness_record"]),
        "--candidate-screen",
        str(paths["candidate_screen"]),
        "--reference-root",
        str(paths["reference_root"]),
        "--reference-provenance",
        str(paths["reference_provenance"]),
    ]


def test_cli_builds_validates_and_applies_giw_quarantine_exit(
    tmp_path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
):
    root, inventory_path, recovery_path, template, template_path = _artifacts(tmp_path)
    exit_path = tmp_path / "exit.json"

    assert (
        main(
            [
                "quarantine-exit",
                "--recovery-review",
                str(recovery_path),
                "--inventory",
                str(inventory_path),
                "--template",
                str(template_path),
                "--root",
                str(root),
                "--output",
                str(exit_path),
            ]
        )
        == 0
    )
    pending_payload = json.loads(capsys.readouterr().out)
    assert pending_payload["decision"] == "pending"
    assert pending_payload["scientific_boundary"]["empirical_evidence_created"] is False

    pending = load_gaze_in_wild_quarantine_exit_authorization(exit_path)
    authorized_exit = replace(
        pending,
        decision="authorized",
        reviewer="independent recovery reviewer",
        reviewed_at="2026-09-05",
        source_authority_verified=True,
        authoritative_source=template.source,
        authoritative_source_revision=template.source_revision,
        source_authority_evidence="first-party authority evidence reviewed",
        exact_copy_identity_verified=True,
        exact_copy_identity_evidence=(
            f"Structured GIW exact-copy review fingerprint: {_EXACT_COPY_FP}"
        ),
        dataset_file_rights_resolved=True,
        reuse_terms_verified=True,
        reuse_terms_source=template.reuse_terms_source,
        rights_evidence="dataset-file rights reviewed",
        analysis_use_permitted=True,
        analysis_use_evidence="analysis use explicitly permitted",
        redistribution_status="restricted",
        redistribution_evidence="redistribution restrictions reviewed",
        authorization_basis="authority, exact-copy identity, and rights independently reviewed",
    )
    write_gaze_in_wild_quarantine_exit_authorization(
        authorized_exit,
        exit_path,
        candidate_root=root,
        overwrite=True,
    )

    def fake_verify(*args, **kwargs):
        return SimpleNamespace(
            exact_copy_identity_verified=True,
            record_fingerprint_sha256=_EXACT_COPY_FP,
            recovery_record_fingerprint_sha256=(
                authorized_exit.recovery_record_fingerprint_sha256
            ),
            recovery_tree_fingerprint_sha256=(
                authorized_exit.recovery_tree_fingerprint_sha256
            ),
            candidate_inventory_fingerprint_sha256=(
                authorized_exit.candidate_inventory_fingerprint_sha256
            ),
        )

    monkeypatch.setattr(
        exact_copy_module,
        "verify_gaze_in_wild_exact_copy_review",
        fake_verify,
    )
    structured_paths = _structured_cli_inputs(tmp_path)
    structured_args = _structured_cli_args(structured_paths)

    assert (
        main(
            [
                "quarantine-exit-validate",
                "--quarantine-exit",
                str(exit_path),
                "--recovery-review",
                str(recovery_path),
                "--inventory",
                str(inventory_path),
                "--template",
                str(template_path),
                "--root",
                str(root),
                *structured_args,
            ]
        )
        == 0
    )
    validated_exit = json.loads(capsys.readouterr().out)
    assert validated_exit["decision"] == "authorized"

    generic_path = tmp_path / "generic-authorization.json"
    write_candidate_source_audit_authorization(
        _generic_authorization(template),
        generic_path,
        candidate_root=root,
    )
    empirical_path = tmp_path / "empirical-spec.json"
    assert (
        main(
            [
                "authorization-apply",
                "--dataset",
                "gaze-in-the-wild",
                "--template",
                str(template_path),
                "--authorization",
                str(generic_path),
                "--quarantine-exit",
                str(exit_path),
                "--recovery-review",
                str(recovery_path),
                "--inventory",
                str(inventory_path),
                "--root",
                str(root),
                *structured_args,
                "--output",
                str(empirical_path),
            ]
        )
        == 0
    )
    empirical = json.loads(capsys.readouterr().out)
    assert empirical["dataset_status"] == "empirical"
    assert any(
        authorized_exit.record_fingerprint_sha256 in note for note in empirical["notes"]
    )


def test_cli_giw_authorization_apply_refuses_missing_recovery_lineage(tmp_path):
    root, _, _, template, template_path = _artifacts(tmp_path)
    generic_path = tmp_path / "generic-authorization.json"
    write_candidate_source_audit_authorization(
        _generic_authorization(template),
        generic_path,
        candidate_root=root,
    )

    with pytest.raises(BenchmarkIntegrityError, match="complete recovery quarantine lineage"):
        main(
            [
                "authorization-apply",
                "--dataset",
                "gaze-in-the-wild",
                "--template",
                str(template_path),
                "--authorization",
                str(generic_path),
                "--root",
                str(root),
                "--output",
                str(tmp_path / "forbidden.json"),
            ]
        )
