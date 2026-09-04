import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError
from gazeforge.gaze_in_wild_audit import (
    GazeInWildSourceAuditSpec,
    audit_gaze_in_wild_source,
)
from gazeforge.hollywood2_audit import Hollywood2SourceAuditSpec, audit_hollywood2_source
from gazeforge.source_candidate_audit_template import (
    compile_candidate_source_audit_template,
    write_candidate_source_audit_template,
)
from gazeforge.source_candidate_review import (
    CandidateSourceReviewFile,
    CandidateSourceReviewScaffold,
)

_SHA_A = "a" * 64
_SHA_B = "b" * 64


def _common_review():
    return {
        "dataset_status": "template",
        "dataset_version": "reviewed-version",
        "authoritative_source": "reviewed-authoritative-source",
        "source_revision": "reviewed-revision",
        "license_or_terms": "reviewed terms text",
        "reuse_terms_source": "reviewed terms source",
        "source_authority_evidence": "reviewed authority evidence",
        "analysis_use_evidence": "reviewed analysis-use evidence",
        "redistribution_evidence": "reviewed redistribution evidence",
        "coordinate_unit": "pixels",
        "coordinate_verification_basis": "reviewed coordinate evidence",
        "participant_mapping_basis": "reviewed identity mapping evidence",
        "notes": ["manual review note"],
    }


def _hollywood_scaffold(root: Path):
    review = _common_review()
    review.update(
        {
            "annotation_columns_review": "reviewed student/final annotation columns",
            "sampling_rate_review": "reviewed published/native sampling-rate evidence",
        }
    )
    return CandidateSourceReviewScaffold(
        root=root,
        dataset_key="hollywood2em",
        candidate_inventory_fingerprint_sha256="c" * 64,
        candidate_file_count=2,
        source_review=review,
        files=(
            CandidateSourceReviewFile(
                path="ground_truth/P01_T01.arff",
                sha256=_SHA_A,
                bytes=101,
                role="arff",
                include_in_audit=True,
                participant_id="P01",
                trial_id="T01",
            ),
            CandidateSourceReviewFile(
                path="README.txt",
                sha256=_SHA_B,
                bytes=33,
                role="exclude",
                include_in_audit=False,
            ),
        ),
    )


def _gaze_scaffold(root: Path):
    review = _common_review()
    review.update(
        {
            "label_process_mapping_basis": "reviewed label/process mapping evidence",
            "labeller_mapping_basis": "reviewed labeller mapping evidence",
            "timestamp_sampling_basis": "reviewed timestamp/sampling evidence",
        }
    )
    return CandidateSourceReviewScaffold(
        root=root,
        dataset_key="gaze-in-the-wild",
        candidate_inventory_fingerprint_sha256="d" * 64,
        candidate_file_count=2,
        source_review=review,
        files=(
            CandidateSourceReviewFile(
                path="LabelData/label.mat",
                sha256=_SHA_A,
                bytes=111,
                role="label",
                include_in_audit=True,
                participant_id="P01",
                trial_id="T01",
                labeller_id=1,
                process_path="ProcessData/process.mat",
            ),
            CandidateSourceReviewFile(
                path="ProcessData/process.mat",
                sha256=_SHA_B,
                bytes=222,
                role="process",
                include_in_audit=True,
            ),
        ),
    )


def test_compile_hollywood_review_to_non_empirical_audit_template(tmp_path):
    spec = compile_candidate_source_audit_template(_hollywood_scaffold(tmp_path))

    assert isinstance(spec, Hollywood2SourceAuditSpec)
    assert spec.dataset_status == "template"
    assert spec.reuse_terms_verified is False
    assert spec.analysis_use_permitted is False
    assert spec.coordinate_unit_verified is False
    assert spec.participant_identity_mapping_verified is False
    assert spec.redistribution_status == "unknown"
    assert len(spec.files) == 1
    assert spec.files[0].path == "ground_truth/P01_T01.arff"
    assert spec.files[0].participant_id == "P01"
    assert any("Candidate inventory fingerprint" in note for note in spec.notes)

    reloaded = Hollywood2SourceAuditSpec.from_dict(spec.to_dict())
    assert reloaded.dataset_status == "template"
    with pytest.raises(SchemaError, match="Template Hollywood2"):
        audit_hollywood2_source(tmp_path, reloaded)


def test_compile_gaze_review_to_non_empirical_audit_template(tmp_path):
    spec = compile_candidate_source_audit_template(_gaze_scaffold(tmp_path))

    assert isinstance(spec, GazeInWildSourceAuditSpec)
    assert spec.dataset_status == "template"
    assert spec.reuse_terms_verified is False
    assert spec.analysis_use_permitted is False
    assert spec.coordinate_unit_verified is False
    assert spec.participant_mapping_verified is False
    assert spec.pixel_kinematics_compatible is False
    assert spec.redistribution_status == "unknown"
    assert len(spec.label_files) == 1
    assert len(spec.process_files) == 1
    assert spec.label_files[0].process_path == "ProcessData/process.mat"

    reloaded = GazeInWildSourceAuditSpec.from_dict(spec.to_dict())
    assert reloaded.dataset_status == "template"
    with pytest.raises(SchemaError, match="Template Gaze-in-the-Wild"):
        audit_gaze_in_wild_source(tmp_path, tmp_path, reloaded)


def test_compiler_refuses_unreviewed_placeholder(tmp_path):
    scaffold = _hollywood_scaffold(tmp_path)
    review = dict(scaffold.source_review)
    review["reuse_terms_source"] = "REVIEW_REQUIRED"
    scaffold = CandidateSourceReviewScaffold(
        root=scaffold.root,
        dataset_key=scaffold.dataset_key,
        candidate_inventory_fingerprint_sha256=scaffold.candidate_inventory_fingerprint_sha256,
        candidate_file_count=scaffold.candidate_file_count,
        source_review=review,
        files=scaffold.files,
    )

    with pytest.raises(BenchmarkIntegrityError, match="reviewed reuse_terms_source"):
        compile_candidate_source_audit_template(scaffold)


def test_compiler_refuses_hollywood_coordinate_inference(tmp_path):
    scaffold = _hollywood_scaffold(tmp_path)
    review = dict(scaffold.source_review)
    review["coordinate_unit"] = "unverified"
    scaffold = CandidateSourceReviewScaffold(
        root=scaffold.root,
        dataset_key=scaffold.dataset_key,
        candidate_inventory_fingerprint_sha256=scaffold.candidate_inventory_fingerprint_sha256,
        candidate_file_count=scaffold.candidate_file_count,
        source_review=review,
        files=scaffold.files,
    )

    with pytest.raises(BenchmarkIntegrityError, match="will not infer coordinate units"):
        compile_candidate_source_audit_template(scaffold)


def test_compiler_refuses_included_non_audit_role(tmp_path):
    scaffold = _hollywood_scaffold(tmp_path)
    files = list(scaffold.files)
    files[1] = CandidateSourceReviewFile(
        path=files[1].path,
        sha256=files[1].sha256,
        bytes=files[1].bytes,
        role="unresolved",
        include_in_audit=True,
    )
    scaffold = CandidateSourceReviewScaffold(
        root=scaffold.root,
        dataset_key=scaffold.dataset_key,
        candidate_inventory_fingerprint_sha256=scaffold.candidate_inventory_fingerprint_sha256,
        candidate_file_count=scaffold.candidate_file_count,
        source_review=scaffold.source_review,
        files=tuple(files),
    )

    with pytest.raises(BenchmarkIntegrityError, match="included file roles"):
        compile_candidate_source_audit_template(scaffold)


def test_compiler_requires_included_dataset_files(tmp_path):
    scaffold = _gaze_scaffold(tmp_path)
    files = tuple(
        CandidateSourceReviewFile(
            path=row.path,
            sha256=row.sha256,
            bytes=row.bytes,
            role=row.role,
            include_in_audit=False,
        )
        for row in scaffold.files
    )
    scaffold = CandidateSourceReviewScaffold(
        root=scaffold.root,
        dataset_key=scaffold.dataset_key,
        candidate_inventory_fingerprint_sha256=scaffold.candidate_inventory_fingerprint_sha256,
        candidate_file_count=scaffold.candidate_file_count,
        source_review=scaffold.source_review,
        files=files,
    )

    with pytest.raises(BenchmarkIntegrityError, match="included label and process"):
        compile_candidate_source_audit_template(scaffold)


def test_writer_preserves_template_boundary_and_stays_outside_candidate_tree(tmp_path):
    root = tmp_path / "candidate"
    root.mkdir()
    spec = compile_candidate_source_audit_template(_hollywood_scaffold(root))
    output = tmp_path / "audit-template.json"

    assert write_candidate_source_audit_template(spec, output, candidate_root=root) == output
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["dataset_status"] == "template"
    assert payload["reuse_terms_verified"] is False
    assert payload["analysis_use_permitted"] is False

    with pytest.raises(BenchmarkIntegrityError, match="outside the candidate source tree"):
        write_candidate_source_audit_template(
            spec,
            root / "audit-template.json",
            candidate_root=root,
        )

    spec.dataset_status = "empirical"
    with pytest.raises(BenchmarkIntegrityError, match="must remain dataset_status='template'"):
        write_candidate_source_audit_template(
            spec,
            tmp_path / "forbidden.json",
            candidate_root=root,
        )
