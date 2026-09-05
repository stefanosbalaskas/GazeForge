import json

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_audit import (
    GazeInWildLabelFileRecord,
    GazeInWildProcessFileRecord,
    GazeInWildSourceAuditSpec,
)
from gazeforge.gaze_in_wild_quarantine_exit import GazeInWildQuarantineExitAuthorization
from gazeforge.hollywood2_audit import Hollywood2SourceAuditSpec, Hollywood2SourceFileRecord
from gazeforge.source_candidate_authorization import (
    CandidateSourceAuditAuthorization,
    authorize_candidate_source_audit_template,
    build_candidate_source_audit_authorization,
    source_audit_template_fingerprint,
    validate_candidate_source_audit_authorization,
    write_authorized_source_audit_spec,
    write_candidate_source_audit_authorization,
)

_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64


def _hollywood_template():
    return Hollywood2SourceAuditSpec(
        dataset_name="Hollywood2EM",
        dataset_version="reviewed-version",
        source="reviewed-authoritative-source",
        source_revision="reviewed-revision",
        license="reviewed terms",
        reuse_terms_source="reviewed terms source",
        dataset_status="template",
        coordinate_unit="pixels",
        coordinate_verification_basis="reviewed coordinate evidence",
        participant_identity_mapping_basis="reviewed participant mapping evidence",
        files=[
            Hollywood2SourceFileRecord(
                path="P01_T01.arff",
                sha256=_SHA_A,
                bytes=111,
                participant_id="P01",
                trial_id="T01",
            )
        ],
        notes=["compiled template note"],
    )


def _gaze_template(*, coordinate_unit="pixels"):
    return GazeInWildSourceAuditSpec(
        dataset_name="Gaze-in-the-Wild",
        dataset_version="reviewed-version",
        source="reviewed-authoritative-source",
        source_revision="reviewed-revision",
        license="reviewed terms",
        reuse_terms_source="reviewed terms source",
        dataset_status="template",
        participant_mapping_basis="reviewed participant mapping evidence",
        coordinate_unit=coordinate_unit,
        coordinate_verification_basis="reviewed coordinate evidence",
        label_files=[
            GazeInWildLabelFileRecord(
                path="label.mat",
                sha256=_SHA_A,
                bytes=111,
                participant_id="P01",
                trial_id="T01",
                labeller_id=1,
                process_path="process.mat",
            )
        ],
        process_files=[
            GazeInWildProcessFileRecord(
                path="process.mat",
                sha256=_SHA_B,
                bytes=222,
            )
        ],
        notes=["compiled template note"],
    )


def _authorized(spec, *, pixel_kinematics_compatible=False, redistribution_status="restricted"):
    dataset_key = (
        "hollywood2em" if isinstance(spec, Hollywood2SourceAuditSpec) else "gaze-in-the-wild"
    )
    return CandidateSourceAuditAuthorization(
        dataset_key=dataset_key,
        audit_template_fingerprint_sha256=source_audit_template_fingerprint(spec),
        decision="authorized",
        reviewer="independent scientific reviewer",
        reviewed_at="2026-09-04",
        source_authority_verified=True,
        source_authority_evidence="authoritative distribution evidence reviewed",
        reuse_terms_verified=True,
        reuse_terms_evidence="current reuse terms reviewed",
        analysis_use_permitted=True,
        analysis_use_evidence="analysis use permission reviewed",
        redistribution_status=redistribution_status,
        redistribution_evidence="redistribution restrictions reviewed",
        coordinate_unit_verified=True,
        coordinate_verification_evidence="coordinate documentation reviewed",
        participant_mapping_verified=True,
        participant_mapping_evidence="participant and task mapping reviewed",
        sampling_contract_reviewed=True,
        sampling_contract_evidence="sampling contract and provenance reviewed",
        annotation_contract_reviewed=True,
        annotation_contract_evidence="annotation streams and roles reviewed",
        pixel_kinematics_compatible=pixel_kinematics_compatible,
        authorization_basis="all required source-audit gates independently reviewed",
        notes=("manual authorization note",),
    )


def _gaze_exit(spec, *, redistribution_status="restricted", validated=True):
    record = GazeInWildQuarantineExitAuthorization(
        recovery_candidate_kind="candidate_original_layout_unverified",
        recovery_record_fingerprint_sha256=_SHA_A,
        recovery_tree_fingerprint_sha256=_SHA_B,
        candidate_inventory_fingerprint_sha256=_SHA_C,
        audit_template_fingerprint_sha256=source_audit_template_fingerprint(spec),
        decision="authorized",
        reviewer="independent recovery reviewer",
        reviewed_at="2026-09-05",
        source_authority_verified=True,
        authoritative_source=spec.source,
        authoritative_source_revision=spec.source_revision,
        source_authority_evidence="source authority independently verified",
        exact_copy_identity_verified=True,
        exact_copy_identity_evidence="exact candidate copy matched authoritative identity",
        dataset_file_rights_resolved=True,
        reuse_terms_verified=True,
        reuse_terms_source=spec.reuse_terms_source,
        rights_evidence="dataset-file rights independently reviewed",
        analysis_use_permitted=True,
        analysis_use_evidence="analysis use explicitly permitted",
        redistribution_status=redistribution_status,
        redistribution_evidence="redistribution restriction reviewed",
        authorization_basis="authority, exact-copy identity, and rights reviewed",
    )
    if validated:
        object.__setattr__(record, "_binding_validated", True)
    return record


def test_build_pending_authorization_is_bound_and_non_empirical(tmp_path):
    spec = _hollywood_template()
    authorization = build_candidate_source_audit_authorization(spec)

    assert authorization.dataset_key == "hollywood2em"
    assert authorization.decision == "pending"
    assert authorization.audit_template_fingerprint_sha256 == source_audit_template_fingerprint(
        spec
    )
    payload = authorization.to_dict()
    assert payload["scientific_boundary"]["source_audit_executed"] is False
    assert payload["scientific_boundary"]["empirical_evidence_created"] is False
    assert authorization.analysis_use_permitted is False

    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir()
    path = tmp_path / "authorization.json"
    write_candidate_source_audit_authorization(
        authorization,
        path,
        candidate_root=candidate_root,
    )
    validated = validate_candidate_source_audit_authorization(path, spec)
    assert validated == authorization


def test_authorization_binding_refuses_template_drift(tmp_path):
    spec = _hollywood_template()
    authorization = build_candidate_source_audit_authorization(spec)
    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir()
    path = tmp_path / "authorization.json"
    write_candidate_source_audit_authorization(
        authorization,
        path,
        candidate_root=candidate_root,
    )

    changed = _hollywood_template()
    changed.source_revision = "different-revision"
    with pytest.raises(BenchmarkIntegrityError, match="exact audit-template fingerprint"):
        validate_candidate_source_audit_authorization(path, changed)


def test_authorized_record_requires_all_manual_gates():
    spec = _hollywood_template()
    values = _authorized(spec).to_dict()
    values.pop("record_type")
    values.pop("scientific_boundary")
    values["reuse_terms_verified"] = False

    with pytest.raises(BenchmarkIntegrityError, match="affirmative manual review gates"):
        CandidateSourceAuditAuthorization(**values)


def test_hollywood_authorization_materializes_empirical_spec_only():
    template = _hollywood_template()
    authorization = _authorized(template)
    spec = authorize_candidate_source_audit_template(template, authorization)

    assert isinstance(spec, Hollywood2SourceAuditSpec)
    assert spec.dataset_status == "empirical"
    assert spec.reuse_terms_verified is True
    assert spec.analysis_use_permitted is True
    assert spec.coordinate_unit_verified is True
    assert spec.participant_identity_mapping_verified is True
    assert spec.redistribution_status == "restricted"
    assert spec.files[0].sha256 == _SHA_A
    assert spec.files[0].participant_id == "P01"
    assert any("permits audit execution only" in note for note in spec.notes)
    assert any("Authorization record fingerprint" in note for note in spec.notes)


def test_denied_authorization_cannot_materialize_empirical_spec():
    template = _hollywood_template()
    authorization = CandidateSourceAuditAuthorization(
        dataset_key="hollywood2em",
        audit_template_fingerprint_sha256=source_audit_template_fingerprint(template),
        decision="denied",
        reviewer="scientific reviewer",
        reviewed_at="2026-09-04",
        authorization_basis="source authority remains unresolved",
    )

    with pytest.raises(BenchmarkIntegrityError, match="decision='authorized'"):
        authorize_candidate_source_audit_template(template, authorization)


def test_gaze_pixel_kinematics_requires_pixel_coordinate_contract():
    template = _gaze_template(coordinate_unit="degrees")
    authorization = _authorized(template, pixel_kinematics_compatible=True)

    with pytest.raises(BenchmarkIntegrityError, match="verified pixel units"):
        authorize_candidate_source_audit_template(
            template,
            authorization,
            gaze_in_wild_quarantine_exit=_gaze_exit(template),
        )


def test_gaze_authorization_requires_separate_quarantine_exit():
    template = _gaze_template(coordinate_unit="pixels")
    authorization = _authorized(template)

    with pytest.raises(BenchmarkIntegrityError, match="quarantine-exit"):
        authorize_candidate_source_audit_template(template, authorization)


def test_gaze_authorization_rejects_unvalidated_quarantine_exit():
    template = _gaze_template()
    with pytest.raises(BenchmarkIntegrityError, match="freshly revalidated"):
        authorize_candidate_source_audit_template(
            template,
            _authorized(template),
            gaze_in_wild_quarantine_exit=_gaze_exit(template, validated=False),
        )


def test_gaze_authorization_preserves_mapping_and_controls_pixel_kinematics():
    template = _gaze_template(coordinate_unit="pixels")
    authorization = _authorized(template, pixel_kinematics_compatible=True)
    exit_record = _gaze_exit(template)
    spec = authorize_candidate_source_audit_template(
        template,
        authorization,
        gaze_in_wild_quarantine_exit=exit_record,
    )

    assert isinstance(spec, GazeInWildSourceAuditSpec)
    assert spec.dataset_status == "empirical"
    assert spec.participant_mapping_verified is True
    assert spec.coordinate_unit_verified is True
    assert spec.pixel_kinematics_compatible is True
    assert spec.label_files[0].process_path == "process.mat"
    assert spec.label_files[0].sha256 == _SHA_A
    assert spec.process_files[0].sha256 == _SHA_B
    assert any(
        f"GIW quarantine-exit record fingerprint: {exit_record.record_fingerprint_sha256}" == note
        for note in spec.notes
    )


def test_gaze_quarantine_exit_must_match_exact_template():
    template = _gaze_template(coordinate_unit="pixels")
    exit_record = _gaze_exit(template)
    changed = _gaze_template(coordinate_unit="pixels")
    changed.notes.append("template drift")
    changed_authorization = _authorized(changed)

    with pytest.raises(BenchmarkIntegrityError, match="not bound to this exact audit template"):
        authorize_candidate_source_audit_template(
            changed,
            changed_authorization,
            gaze_in_wild_quarantine_exit=exit_record,
        )


def test_gaze_authorization_rejects_redistribution_disagreement():
    template = _gaze_template()
    with pytest.raises(BenchmarkIntegrityError, match="redistribution status conflicts"):
        authorize_candidate_source_audit_template(
            template,
            _authorized(template, redistribution_status="permitted"),
            gaze_in_wild_quarantine_exit=_gaze_exit(
                template,
                redistribution_status="restricted",
            ),
        )


def test_hollywood_refuses_gaze_quarantine_exit_record():
    hollywood = _hollywood_template()
    gaze = _gaze_template()
    with pytest.raises(BenchmarkIntegrityError, match="cannot authorize a Hollywood2EM"):
        authorize_candidate_source_audit_template(
            hollywood,
            _authorized(hollywood),
            gaze_in_wild_quarantine_exit=_gaze_exit(gaze),
        )


def test_authorization_boundary_tamper_is_rejected(tmp_path):
    template = _hollywood_template()
    authorization = build_candidate_source_audit_authorization(template)
    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir()
    path = tmp_path / "authorization.json"
    write_candidate_source_audit_authorization(
        authorization,
        path,
        candidate_root=candidate_root,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["scientific_boundary"]["empirical_evidence_created"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="preserve the manual gate"):
        validate_candidate_source_audit_authorization(path, template)


def test_authorized_spec_writer_stays_outside_candidate_tree(tmp_path):
    template = _hollywood_template()
    authorization = _authorized(template)
    spec = authorize_candidate_source_audit_template(template, authorization)
    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir()

    output = tmp_path / "empirical-spec.json"
    assert (
        write_authorized_source_audit_spec(
            spec,
            output,
            candidate_root=candidate_root,
        )
        == output
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["dataset_status"] == "empirical"

    with pytest.raises(BenchmarkIntegrityError, match="outside the candidate source tree"):
        write_authorized_source_audit_spec(
            spec,
            candidate_root / "forbidden.json",
            candidate_root=candidate_root,
        )

    with pytest.raises(BenchmarkIntegrityError, match="requires dataset_status='empirical'"):
        write_authorized_source_audit_spec(
            template,
            tmp_path / "template.json",
            candidate_root=candidate_root,
        )
