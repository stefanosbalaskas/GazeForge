import json

import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_audit import (
    GazeInWildLabelFileRecord,
    GazeInWildProcessFileRecord,
    GazeInWildSourceAuditSpec,
)
from gazeforge.hollywood2_audit import Hollywood2SourceAuditSpec, Hollywood2SourceFileRecord
from gazeforge.source_audit_lineage import (
    SourceAuditLineageReceipt,
    build_source_audit_lineage_receipt,
    load_source_audit_lineage_receipt,
    write_source_audit_lineage_receipt,
)
from gazeforge.source_candidate_authorization import (
    CandidateSourceAuditAuthorization,
    authorize_candidate_source_audit_template,
    source_audit_template_fingerprint,
)

_SHA_A = "a" * 64
_SHA_B = "b" * 64


def _hollywood_template():
    return Hollywood2SourceAuditSpec(
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
                sha256=_SHA_A,
                bytes=111,
                participant_id="P01",
                trial_id="T01",
            )
        ],
    )


def _gaze_template():
    return GazeInWildSourceAuditSpec(
        dataset_name="Gaze-in-the-Wild",
        dataset_version="reviewed-version",
        source="authoritative-source",
        source_revision="source-revision-1",
        license="reviewed terms",
        reuse_terms_source="reviewed terms source",
        dataset_status="template",
        participant_mapping_basis="reviewed participant mapping basis",
        coordinate_unit="pixels",
        coordinate_verification_basis="reviewed coordinate basis",
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
    )


def _authorization(template, *, pixel_kinematics_compatible=False):
    dataset_key = (
        "hollywood2em"
        if isinstance(template, Hollywood2SourceAuditSpec)
        else "gaze-in-the-wild"
    )
    return CandidateSourceAuditAuthorization(
        dataset_key=dataset_key,
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
        pixel_kinematics_compatible=pixel_kinematics_compatible,
        authorization_basis="all source-audit entry gates reviewed",
    )


def _stamp_report(body):
    return {**body, "report_fingerprint_sha256": benchmark_fingerprint(body)}


def _hollywood_report(template, authorization):
    spec = authorize_candidate_source_audit_template(template, authorization)
    manifest_files = [spec.files[0].to_dict()]
    manifest = {
        "file_count": len(manifest_files),
        "exact_inventory_match": True,
        "files": manifest_files,
        "source_manifest_fingerprint_sha256": benchmark_fingerprint(manifest_files),
    }
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
        "source_inventory": manifest,
        "spec_fingerprint_sha256": benchmark_fingerprint(spec.to_dict()),
        "claim_limits": ["source/provenance only"],
    }
    return _stamp_report(body)


def _gaze_report(template, authorization):
    spec = authorize_candidate_source_audit_template(template, authorization)
    label_files = [spec.label_files[0].to_dict()]
    process_files = [spec.process_files[0].to_dict()]
    label_inventory = {
        "file_count": len(label_files),
        "exact_inventory_match": True,
        "files": label_files,
        "manifest_fingerprint_sha256": benchmark_fingerprint(label_files),
    }
    process_inventory = {
        "file_count": len(process_files),
        "exact_inventory_match": True,
        "files": process_files,
        "manifest_fingerprint_sha256": benchmark_fingerprint(process_files),
    }
    body = {
        "audit": "Gaze-in-the-Wild-source-audit",
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
        "identity": {
            "participant_mapping_verified": True,
            "participant_mapping_basis": spec.participant_mapping_basis,
            "participant_count": 1,
            "participant_ids": ["P01"],
            "participant_trial_count": 1,
            "labeller_ids": [1],
            "labeller_count": 1,
            "multi_labeller_trial_count": 0,
            "same_underlying_gaze_verified_for_multi_labeller_trials": False,
        },
        "coordinates": {
            "unit": "pixels",
            "verified": True,
            "verification_basis": spec.coordinate_verification_basis,
            "pixel_kinematics_compatible": spec.pixel_kinematics_compatible,
        },
        "sampling": {
            "source": "inferred_from_LabelData.T_per_file",
            "published_hardware_sampling_rate_hz": 120.0,
            "file_count": 1,
            "min_observed_sampling_rate_hz": 120.0,
            "median_observed_sampling_rate_hz": 120.0,
            "max_observed_sampling_rate_hz": 120.0,
            "files": [],
        },
        "confidence_threshold": spec.confidence_threshold,
        "label_inventory": label_inventory,
        "process_inventory": process_inventory,
        "spec_fingerprint_sha256": benchmark_fingerprint(spec.to_dict()),
        "claim_limits": ["source/provenance only"],
    }
    return _stamp_report(body)


def test_hollywood_lineage_binds_all_upstream_fingerprints():
    template = _hollywood_template()
    authorization = _authorization(template)
    report = _hollywood_report(template, authorization)

    receipt = build_source_audit_lineage_receipt(template, authorization, report)

    assert receipt.dataset_key == "hollywood2em"
    assert receipt.audit_template_fingerprint_sha256 == source_audit_template_fingerprint(template)
    assert receipt.audit_report_fingerprint_sha256 == report["report_fingerprint_sha256"]
    assert receipt.source_manifest_fingerprints_sha256 == {
        "source": report["source_inventory"]["source_manifest_fingerprint_sha256"]
    }
    assert receipt.source_audit_verified is True
    assert receipt.lineage_verified is True
    assert receipt.to_dict()["scientific_boundary"]["creates_new_empirical_metrics"] is False


def test_gaze_lineage_preserves_separate_label_process_manifests():
    template = _gaze_template()
    authorization = _authorization(template, pixel_kinematics_compatible=True)
    report = _gaze_report(template, authorization)

    receipt = build_source_audit_lineage_receipt(template, authorization, report)

    assert receipt.dataset_key == "gaze-in-the-wild"
    assert receipt.source_manifest_fingerprints_sha256 == {
        "label": report["label_inventory"]["manifest_fingerprint_sha256"],
        "process": report["process_inventory"]["manifest_fingerprint_sha256"],
    }
    assert receipt.source_revision == "source-revision-1"


def test_lineage_rejects_report_fingerprint_tampering():
    template = _hollywood_template()
    authorization = _authorization(template)
    report = _hollywood_report(template, authorization)
    report["sampling"]["observed_sampling_rate_hz"] = 60.0

    with pytest.raises(BenchmarkIntegrityError, match="report fingerprint mismatch"):
        build_source_audit_lineage_receipt(template, authorization, report)


def test_lineage_rejects_report_for_different_authorized_spec():
    template = _hollywood_template()
    authorization = _authorization(template)
    report = _hollywood_report(template, authorization)
    body = dict(report)
    body.pop("report_fingerprint_sha256")
    body["spec_fingerprint_sha256"] = "c" * 64
    report = _stamp_report(body)

    with pytest.raises(BenchmarkIntegrityError, match="exact authorized empirical specification"):
        build_source_audit_lineage_receipt(template, authorization, report)


def test_lineage_rejects_non_authorized_decision():
    template = _hollywood_template()
    authorized = _authorization(template)
    report = _hollywood_report(template, authorized)
    pending = CandidateSourceAuditAuthorization(
        dataset_key="hollywood2em",
        audit_template_fingerprint_sha256=source_audit_template_fingerprint(template),
    )

    with pytest.raises(BenchmarkIntegrityError, match="explicit authorized decision"):
        build_source_audit_lineage_receipt(template, pending, report)


def test_lineage_rejects_dataset_specific_audit_invariant_failure():
    template = _hollywood_template()
    authorization = _authorization(template)
    report = _hollywood_report(template, authorization)
    body = dict(report)
    body.pop("report_fingerprint_sha256")
    body["annotations"] = dict(body["annotations"])
    body["annotations"]["same_underlying_gaze_verified"] = False
    report = _stamp_report(body)

    with pytest.raises(BenchmarkIntegrityError, match="shared gaze"):
        build_source_audit_lineage_receipt(template, authorization, report)


def test_lineage_rejects_nested_manifest_fingerprint_mismatch():
    template = _gaze_template()
    authorization = _authorization(template)
    report = _gaze_report(template, authorization)
    body = dict(report)
    body.pop("report_fingerprint_sha256")
    body["label_inventory"] = dict(body["label_inventory"])
    body["label_inventory"]["manifest_fingerprint_sha256"] = _SHA_A
    report = _stamp_report(body)

    with pytest.raises(BenchmarkIntegrityError, match="manifest fingerprint mismatch"):
        build_source_audit_lineage_receipt(template, authorization, report)


def test_lineage_rejects_authorized_contract_drift_inside_report():
    template = _hollywood_template()
    authorization = _authorization(template)
    report = _hollywood_report(template, authorization)
    body = dict(report)
    body.pop("report_fingerprint_sha256")
    body["reuse"] = dict(body["reuse"])
    body["reuse"]["redistribution_status"] = "permitted"
    report = _stamp_report(body)

    with pytest.raises(BenchmarkIntegrityError, match="reuse.redistribution_status"):
        build_source_audit_lineage_receipt(template, authorization, report)


def test_lineage_receipt_round_trip_and_tamper_detection(tmp_path):
    template = _gaze_template()
    authorization = _authorization(template)
    receipt = build_source_audit_lineage_receipt(
        template,
        authorization,
        _gaze_report(template, authorization),
    )
    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir()
    path = tmp_path / "lineage.json"

    assert (
        write_source_audit_lineage_receipt(
            receipt,
            path,
            candidate_root=candidate_root,
        )
        == path
    )
    loaded = load_source_audit_lineage_receipt(path)
    assert loaded == receipt

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source_revision"] = "tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="receipt fingerprint mismatch"):
        load_source_audit_lineage_receipt(path)


def test_lineage_writer_refuses_candidate_tree_output(tmp_path):
    template = _hollywood_template()
    authorization = _authorization(template)
    receipt = build_source_audit_lineage_receipt(
        template,
        authorization,
        _hollywood_report(template, authorization),
    )
    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir()

    with pytest.raises(BenchmarkIntegrityError, match="outside the candidate source tree"):
        write_source_audit_lineage_receipt(
            receipt,
            candidate_root / "lineage.json",
            candidate_root=candidate_root,
        )


def test_receipt_constructor_refuses_wrong_manifest_shape():
    with pytest.raises(ValueError, match="dataset audit contract"):
        SourceAuditLineageReceipt(
            dataset_key="hollywood2em",
            audit_template_fingerprint_sha256=_SHA_A,
            authorization_fingerprint_sha256=_SHA_A,
            authorized_spec_fingerprint_sha256=_SHA_A,
            audit_report_fingerprint_sha256=_SHA_A,
            source_manifest_fingerprints_sha256={"label": _SHA_A},
            source_revision="revision",
        )
