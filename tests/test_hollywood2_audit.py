import hashlib
from pathlib import Path

import pytest

from gazeforge.cross_dataset import prepare_cross_dataset_event_benchmark
from gazeforge.exceptions import SchemaError
from gazeforge.hollywood2 import load_hollywood2_directory
from gazeforge.hollywood2_audit import (
    Hollywood2SourceAuditSpec,
    Hollywood2SourceFileRecord,
    audit_hollywood2_source,
    load_audited_hollywood2_directory,
)


def _write_arff(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = """@RELATION hollywood2
@ATTRIBUTE time NUMERIC
@ATTRIBUTE x NUMERIC
@ATTRIBUTE y NUMERIC
@ATTRIBUTE confidence NUMERIC
@ATTRIBUTE handlabeller_1 {FIX,SACCADE,SP,NOISE}
@ATTRIBUTE handlabeller_final {FIX,SACCADE,SP,NOISE}
@DATA
0,100,200,1.0,FIX,FIX
2000,0,0,0.0,NOISE,NOISE
4000,130,210,0.9,SACCADE,SACCADE
6000,140,220,0.8,SP,SP
"""
    path.write_text(text, encoding="utf-8")


def _record(data_root: Path, relative: str, participant: str, trial: str):
    path = data_root / relative
    payload = path.read_bytes()
    return Hollywood2SourceFileRecord(
        path=relative,
        sha256=hashlib.sha256(payload).hexdigest(),
        bytes=len(payload),
        participant_id=participant,
        trial_id=trial,
    )


def _empirical_spec(root: Path) -> Hollywood2SourceAuditSpec:
    data_root = root / "ground_truth"
    return Hollywood2SourceAuditSpec(
        dataset_name="Hollywood2EM",
        dataset_version="test-snapshot",
        source="https://example.invalid/hollywood2",
        source_revision="snapshot-abc123",
        license="Research use terms verified for this test fixture.",
        reuse_terms_source="https://example.invalid/terms",
        dataset_status="empirical",
        reuse_terms_verified=True,
        analysis_use_permitted=True,
        redistribution_status="restricted",
        coordinate_unit="pixels",
        coordinate_unit_verified=True,
        coordinate_verification_basis="Fixture schema documents x/y as screen pixels.",
        participant_identity_mapping_verified=True,
        participant_identity_mapping_basis="Fixture path-to-observer manifest.",
        files=[
            _record(data_root, "test/a.arff", "P01", "clip-a"),
            _record(data_root, "test/b.arff", "P02", "clip-b"),
        ],
    )


def _fixture(root: Path) -> Hollywood2SourceAuditSpec:
    _write_arff(root / "ground_truth" / "test" / "a.arff")
    _write_arff(root / "ground_truth" / "test" / "b.arff")
    return _empirical_spec(root)


def _identity_parser(spec: Hollywood2SourceAuditSpec):
    records = {item.path: item for item in spec.files}

    def parser(relative: Path) -> tuple[str, str]:
        item = records[relative.as_posix()]
        return item.participant_id, item.trial_id

    return parser


def test_hollywood2_source_audit_verifies_inventory_identities_and_gaze(tmp_path):
    spec = _fixture(tmp_path)
    run = audit_hollywood2_source(tmp_path, spec)

    assert run.report["status"] == "verified"
    assert run.report["source_inventory"]["file_count"] == 2
    assert run.report["annotations"]["same_underlying_gaze_verified"] is True
    assert run.report["participant_identity"]["participant_count"] == 2
    assert len(run.report["report_fingerprint_sha256"]) == 64
    assert run.final_annotations.metadata["source_audit_status"] == "verified"
    assert run.student_annotations.metadata["source_audit_status"] == "verified"
    assert run.final_annotations.metadata["redistribution_status"] == "restricted"


def test_audited_loader_selects_expert_or_student_only_after_full_audit(tmp_path):
    spec = _fixture(tmp_path)
    expert = load_audited_hollywood2_directory(tmp_path, spec, annotator="expert")
    student = load_audited_hollywood2_directory(tmp_path, spec, annotator="student")

    assert expert.metadata["annotator"] == "final"
    assert student.metadata["annotator"] == "student"
    assert expert.metadata["coordinate_unit_verified"] is True
    with pytest.raises(ValueError, match="annotator"):
        load_audited_hollywood2_directory(tmp_path, spec, annotator="third-labeller")


def test_cross_dataset_hollywood2_requires_source_audit_not_only_pixel_assertion(tmp_path):
    spec = _fixture(tmp_path)
    direct = load_hollywood2_directory(
        tmp_path,
        identity_parser=_identity_parser(spec),
        coordinate_unit="pixels",
    )
    audited = load_audited_hollywood2_directory(tmp_path, spec)
    other = audited.copy()
    other.data["dataset_id"] = "Other"
    other.metadata["source_dataset"] = "Other"

    with pytest.raises(SchemaError, match="source-audit"):
        prepare_cross_dataset_event_benchmark(
            {"Hollywood2EM": direct, "Other": other},
            target_sampling_rate_hz=500.0,
        )

    prepared = prepare_cross_dataset_event_benchmark(
        {"Hollywood2EM": audited, "Other": other},
        target_sampling_rate_hz=500.0,
    )
    report = prepared.dataset_reports["Hollywood2EM"]
    assert report["source_audit_status"] == "verified"
    assert len(report["source_audit_report_fingerprint_sha256"]) == 64
    assert prepared.design["require_source_audits"] is True


def test_hollywood2_source_audit_rejects_tampered_file(tmp_path):
    spec = _fixture(tmp_path)
    path = tmp_path / "ground_truth" / "test" / "a.arff"
    original = path.read_text(encoding="utf-8")
    path.write_text(original.replace("100,200", "101,200"), encoding="utf-8")

    with pytest.raises(SchemaError, match="SHA-256 mismatch"):
        audit_hollywood2_source(tmp_path, spec)


def test_hollywood2_source_audit_rejects_extra_unmanifested_arff(tmp_path):
    spec = _fixture(tmp_path)
    _write_arff(tmp_path / "ground_truth" / "train" / "unexpected.arff")

    with pytest.raises(SchemaError, match="inventory"):
        audit_hollywood2_source(tmp_path, spec)


def test_template_cannot_certify_empirical_hollywood2_data(tmp_path):
    _write_arff(tmp_path / "ground_truth" / "test" / "a.arff")
    spec = Hollywood2SourceAuditSpec(
        dataset_name="Hollywood2EM",
        dataset_version="template",
        source="https://example.invalid/hollywood2",
        source_revision="pending",
        license="Pending verification.",
        reuse_terms_source="https://example.invalid/terms",
    )
    with pytest.raises(SchemaError, match="Template"):
        audit_hollywood2_source(tmp_path, spec)


def test_empirical_spec_rejects_duplicate_participant_trial_identity(tmp_path):
    _write_arff(tmp_path / "ground_truth" / "test" / "a.arff")
    _write_arff(tmp_path / "ground_truth" / "test" / "b.arff")
    data_root = tmp_path / "ground_truth"
    files = [
        _record(data_root, "test/a.arff", "P01", "same"),
        _record(data_root, "test/b.arff", "P01", "same"),
    ]
    with pytest.raises(ValueError, match="identities must be unique"):
        Hollywood2SourceAuditSpec(
            dataset_name="Hollywood2EM",
            dataset_version="test-snapshot",
            source="https://example.invalid/hollywood2",
            source_revision="snapshot-abc123",
            license="Verified research-use terms.",
            reuse_terms_source="https://example.invalid/terms",
            dataset_status="empirical",
            reuse_terms_verified=True,
            analysis_use_permitted=True,
            coordinate_unit_verified=True,
            coordinate_verification_basis="Verified pixel coordinates.",
            participant_identity_mapping_verified=True,
            participant_identity_mapping_basis="Verified path mapping.",
            files=files,
        )
