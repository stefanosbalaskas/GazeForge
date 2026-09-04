import json

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.hollywood2_audit import Hollywood2SourceAuditSpec, Hollywood2SourceFileRecord
from gazeforge.source_candidate_authorization import (
    CandidateSourceAuditAuthorization,
    authorize_candidate_source_audit_template,
    source_audit_template_fingerprint,
)
from gazeforge.source_candidate_cli import main


def test_candidate_cli_builds_verified_source_audit_lineage_receipt(tmp_path, capsys):
    root = tmp_path / "candidate"
    root.mkdir()
    template_path = tmp_path / "template.json"
    authorization_path = tmp_path / "authorization.json"
    report_path = tmp_path / "audit-report.json"
    receipt_path = tmp_path / "lineage.json"

    template = Hollywood2SourceAuditSpec(
        dataset_name="Hollywood2EM",
        dataset_version="reviewed-version",
        source="authoritative-source",
        source_revision="source-revision-1",
        license="reviewed terms",
        reuse_terms_source="reviewed terms source",
        dataset_status="template",
        coordinate_unit="pixels",
        coordinate_verification_basis="reviewed coordinate basis",
        participant_identity_mapping_basis="reviewed participant mapping basis",
        files=[
            Hollywood2SourceFileRecord(
                path="P01_T01.arff",
                sha256="a" * 64,
                bytes=111,
                participant_id="P01",
                trial_id="T01",
            )
        ],
    )
    template_path.write_text(json.dumps(template.to_dict()), encoding="utf-8")

    authorization = CandidateSourceAuditAuthorization(
        dataset_key="hollywood2em",
        audit_template_fingerprint_sha256=source_audit_template_fingerprint(template),
        decision="authorized",
        reviewer="scientific reviewer",
        reviewed_at="2026-09-04",
        source_authority_verified=True,
        source_authority_evidence="source authority reviewed",
        reuse_terms_verified=True,
        reuse_terms_evidence="reuse terms reviewed",
        analysis_use_permitted=True,
        analysis_use_evidence="analysis permission reviewed",
        redistribution_status="restricted",
        redistribution_evidence="redistribution status reviewed",
        coordinate_unit_verified=True,
        coordinate_verification_evidence="coordinate unit reviewed",
        participant_mapping_verified=True,
        participant_mapping_evidence="participant mapping reviewed",
        sampling_contract_reviewed=True,
        sampling_contract_evidence="sampling contract reviewed",
        annotation_contract_reviewed=True,
        annotation_contract_evidence="annotation contract reviewed",
        authorization_basis="all source-audit entry gates reviewed",
    )
    authorization_path.write_text(json.dumps(authorization.to_dict()), encoding="utf-8")

    spec = authorize_candidate_source_audit_template(template, authorization)
    body = {
        "audit": "Hollywood2EM-source-audit",
        "status": "verified",
        "dataset": {
            "name": spec.dataset_name,
            "version": spec.dataset_version,
            "source": spec.source,
            "source_revision": spec.source_revision,
            "license": spec.license,
        },
        "reuse": {
            "terms_source": spec.reuse_terms_source,
            "terms_verified": True,
            "analysis_use_permitted": True,
            "redistribution_status": spec.redistribution_status,
        },
        "coordinates": {
            "unit": "pixels",
            "verified": True,
            "verification_basis": spec.coordinate_verification_basis,
        },
        "participant_identity": {
            "verified": True,
            "verification_basis": spec.participant_identity_mapping_basis,
            "participant_count": 1,
            "participant_ids": ["P01"],
            "participant_trial_count": 1,
        },
        "sampling": {
            "expected_sampling_rate_hz": 500.0,
            "observed_sampling_rate_hz": 500.0,
            "tolerance_fraction": 0.05,
            "sampling_origin": "native",
        },
        "annotations": {
            "student_column": "handlabeller_1",
            "expert_column": "handlabeller_final",
            "same_underlying_gaze_verified": True,
            "row_count_per_stream": 10,
        },
        "source_inventory": {
            "file_count": 1,
            "exact_inventory_match": True,
            "files": [spec.files[0].to_dict()],
            "source_manifest_fingerprint_sha256": "b" * 64,
        },
        "spec_fingerprint_sha256": benchmark_fingerprint(spec.to_dict()),
        "claim_limits": ["source/provenance only"],
    }
    report = {**body, "report_fingerprint_sha256": benchmark_fingerprint(body)}
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert (
        main(
            [
                "lineage",
                "--dataset",
                "hollywood2em",
                "--template",
                str(template_path),
                "--authorization",
                str(authorization_path),
                "--audit-report",
                str(report_path),
                "--root",
                str(root),
                "--output",
                str(receipt_path),
            ]
        )
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["record_type"] == "source-audit-lineage-receipt-v1"
    assert receipt["source_audit_verified"] is True
    assert receipt["lineage_verified"] is True
    assert receipt["audit_report_fingerprint_sha256"] == report["report_fingerprint_sha256"]
    assert receipt["source_manifest_fingerprints_sha256"] == {"source": "b" * 64}
    assert receipt["scientific_boundary"]["creates_new_empirical_metrics"] is False
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt
