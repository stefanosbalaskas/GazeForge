import hashlib
from pathlib import Path

import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_audit import (
    VisusSourceAuditSpec,
    VisusSourceFileRecord,
    audit_visus_source,
)


def _write(root: Path, relative: str, payload: str) -> tuple[str, int]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest(), len(raw)


def _record(
    root: Path,
    *,
    path: str,
    role: str,
    stimulus_id: str | None = None,
    participant_id: str | None = None,
    participant_group: str | None = None,
    annotation_stream_id: str | None = None,
) -> VisusSourceFileRecord:
    digest, size = _write(root, path, f"fixture:{path}\n")
    return VisusSourceFileRecord(
        path=path,
        sha256=digest,
        bytes=size,
        role=role,
        stimulus_id=stimulus_id,
        participant_id=participant_id,
        participant_group=participant_group,
        annotation_stream_id=annotation_stream_id,
    )


def _fixture(root: Path, *, independent_streams: bool = False) -> VisusSourceAuditSpec:
    records: list[VisusSourceFileRecord] = []
    stimuli = [f"S{index:02d}" for index in range(1, 12)]
    for stimulus in stimuli:
        records.append(
            _record(
                root,
                path=f"video/{stimulus}.avi",
                role="video",
                stimulus_id=stimulus,
            )
        )
        records.append(
            _record(
                root,
                path=f"aoi/{stimulus}.xml",
                role="aoi_annotation",
                stimulus_id=stimulus,
                annotation_stream_id="published_curated",
            )
        )
        if independent_streams:
            records.append(
                _record(
                    root,
                    path=f"aoi-independent/{stimulus}.xml",
                    role="aoi_annotation",
                    stimulus_id=stimulus,
                    annotation_stream_id="independent_second",
                )
            )

    for participant_index in range(1, 26):
        participant = f"P{participant_index:02d}"
        stimulus = stimuli[(participant_index - 1) % len(stimuli)]
        group = "A" if participant_index <= 13 else "B"
        records.append(
            _record(
                root,
                path=f"gaze/{participant}-{stimulus}.tsv",
                role="gaze",
                stimulus_id=stimulus,
                participant_id=participant,
                participant_group=group,
            )
        )

    return VisusSourceAuditSpec(
        dataset_name="VISUS",
        dataset_version="Kurzhals-et-al-2014-fixture",
        source="https://example.invalid/visus",
        source_revision="fixture-snapshot",
        license="Reviewed fixture analysis terms.",
        reuse_terms_source="https://example.invalid/visus-terms",
        dataset_status="empirical",
        reuse_terms_verified=True,
        analysis_use_permitted=True,
        redistribution_status="restricted",
        stimulus_mapping_verified=True,
        stimulus_mapping_basis="Fixture stimulus manifest cross-check.",
        participant_mapping_verified=True,
        participant_mapping_basis="Fixture gaze filename/manifest cross-check.",
        coordinate_unit="pixels",
        coordinate_unit_verified=True,
        coordinate_verification_basis="Fixture source documentation.",
        timestamp_basis_verified=True,
        timestamp_verification_basis="Fixture relative timestamp/frame documentation.",
        independent_annotation_streams_verified=independent_streams,
        independent_annotation_streams_basis=(
            "Fixture exposes two separately manifested streams."
            if independent_streams
            else ""
        ),
        files=records,
    )


def test_visus_audit_verifies_exact_snapshot_without_inventing_human_agreement(tmp_path):
    spec = _fixture(tmp_path)
    run = audit_visus_source(tmp_path, spec)

    assert run.report["status"] == "verified"
    assert run.report["identity"]["stimulus_count"] == 11
    assert run.report["identity"]["participant_count"] == 25
    assert run.report["inventory"]["role_counts"]["video"] == 11
    assert run.report["inventory"]["role_counts"]["aoi_annotation"] == 11
    annotation = run.report["annotation_provenance"]
    assert annotation["annotation_process_contributor_count"] == 2
    assert annotation["independent_annotation_streams_verified"] is False
    assert annotation["human_human_agreement_ready"] is False
    assert annotation["minimum_streams_per_annotated_stimulus"] == 1
    assert len(run.report["report_fingerprint_sha256"]) == 64

    body = {
        key: value
        for key, value in run.report.items()
        if key != "report_fingerprint_sha256"
    }
    assert benchmark_fingerprint(body) == run.report["report_fingerprint_sha256"]


def test_visus_audit_can_only_enable_human_agreement_with_verified_independent_streams(tmp_path):
    spec = _fixture(tmp_path, independent_streams=True)
    run = audit_visus_source(tmp_path, spec)

    annotation = run.report["annotation_provenance"]
    assert annotation["independent_annotation_streams_verified"] is True
    assert annotation["minimum_streams_per_annotated_stimulus"] == 2
    assert annotation["human_human_agreement_ready"] is True


def test_visus_empirical_spec_rejects_independent_stream_claim_without_two_streams(tmp_path):
    spec = _fixture(tmp_path)
    with pytest.raises(ValueError, match="at least two"):
        VisusSourceAuditSpec(
            **{
                **spec.to_dict(),
                "files": spec.files,
                "independent_annotation_streams_verified": True,
                "independent_annotation_streams_basis": "Claimed independent review.",
            }
        )


def test_visus_audit_rejects_extra_files(tmp_path):
    spec = _fixture(tmp_path)
    (tmp_path / "unexpected.txt").write_text("not manifested", encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="exact audited manifest"):
        audit_visus_source(tmp_path, spec)


def test_visus_audit_rejects_tampered_file(tmp_path):
    spec = _fixture(tmp_path)
    (tmp_path / "video" / "S01.avi").write_text("tampered", encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="mismatch"):
        audit_visus_source(tmp_path, spec)


def test_visus_template_cannot_be_audited_as_empirical(tmp_path):
    spec = VisusSourceAuditSpec(
        dataset_name="VISUS",
        dataset_version="REPLACE_WITH_VERSION",
        source="REPLACE_WITH_AUTHORITATIVE_SOURCE",
        source_revision="REPLACE_WITH_SOURCE_REVISION",
        license="VERIFY_REUSE_TERMS",
        reuse_terms_source="REPLACE_WITH_TERMS_SOURCE",
        dataset_status="template",
    )
    with pytest.raises(BenchmarkIntegrityError, match="templates"):
        audit_visus_source(tmp_path, spec)


def test_visus_manifest_rejects_path_traversal():
    with pytest.raises(ValueError, match="safe"):
        VisusSourceFileRecord(
            path="../secret.tsv",
            sha256="0" * 64,
            bytes=1,
            role="gaze",
            stimulus_id="S01",
            participant_id="P01",
        )
