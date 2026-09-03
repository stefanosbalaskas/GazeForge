import hashlib
from pathlib import Path

import pandas as pd
import pytest

from gazeforge.dynamic_aoi import DynamicAOIKeyframe
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError
from gazeforge.visus_audit import (
    VisusSourceAuditSpec,
    VisusSourceFileRecord,
    audit_visus_source,
)
from gazeforge.visus_intake import prepare_visus_canonical_aoi_intake


def _write(root: Path, relative: str) -> tuple[str, int]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"fixture:{relative}\n", encoding="utf-8")
    payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest(), len(payload)


def _record(
    root: Path,
    *,
    path: str,
    role: str,
    stimulus_id: str,
    participant_id: str | None = None,
    annotation_stream_id: str | None = None,
) -> VisusSourceFileRecord:
    digest, size = _write(root, path)
    return VisusSourceFileRecord(
        path=path,
        sha256=digest,
        bytes=size,
        role=role,
        stimulus_id=stimulus_id,
        participant_id=participant_id,
        annotation_stream_id=annotation_stream_id,
    )


def _audit(root: Path):
    stimuli = [f"S{index:02d}" for index in range(1, 12)]
    files: list[VisusSourceFileRecord] = []
    for stimulus in stimuli:
        files.append(
            _record(
                root,
                path=f"video/{stimulus}.avi",
                role="video",
                stimulus_id=stimulus,
            )
        )
        files.append(
            _record(
                root,
                path=f"aoi/{stimulus}.xml",
                role="aoi_annotation",
                stimulus_id=stimulus,
                annotation_stream_id="published_curated",
            )
        )
    for index in range(1, 26):
        participant = f"P{index:02d}"
        stimulus = stimuli[(index - 1) % len(stimuli)]
        files.append(
            _record(
                root,
                path=f"gaze/{participant}-{stimulus}.tsv",
                role="gaze",
                stimulus_id=stimulus,
                participant_id=participant,
            )
        )

    spec = VisusSourceAuditSpec(
        dataset_name="VISUS",
        dataset_version="intake-fixture",
        source="https://example.invalid/visus",
        source_revision="fixture-snapshot",
        license="Reviewed fixture terms.",
        reuse_terms_source="https://example.invalid/terms",
        dataset_status="empirical",
        reuse_terms_verified=True,
        analysis_use_permitted=True,
        redistribution_status="restricted",
        stimulus_mapping_verified=True,
        stimulus_mapping_basis="Fixture stimulus manifest.",
        participant_mapping_verified=True,
        participant_mapping_basis="Fixture participant manifest.",
        coordinate_unit="pixels",
        coordinate_unit_verified=True,
        coordinate_verification_basis="Fixture coordinate documentation.",
        timestamp_basis_verified=True,
        timestamp_verification_basis="Fixture frame-time documentation.",
        files=files,
    )
    return audit_visus_source(root, spec)


def _table() -> pd.DataFrame:
    rows = []
    for index in range(1, 12):
        stimulus = f"S{index:02d}"
        rows.extend(
            [
                {
                    "source_path": f"aoi/{stimulus}.xml",
                    "stimulus_id": stimulus,
                    "annotation_stream_id": "published_curated",
                    "frame_index": 1,
                    "aoi_id": "target",
                    "label": "person",
                    "xmin": 10.0,
                    "ymin": 20.0,
                    "xmax": 110.0,
                    "ymax": 220.0,
                },
                {
                    "source_path": f"aoi/{stimulus}.xml",
                    "stimulus_id": stimulus,
                    "annotation_stream_id": "published_curated",
                    "frame_index": 26,
                    "aoi_id": "target",
                    "label": "person",
                    "xmin": 20.0,
                    "ymin": 20.0,
                    "xmax": 120.0,
                    "ymax": 220.0,
                },
            ]
        )
    return pd.DataFrame(rows)


def test_visus_canonical_intake_links_every_aoi_file_and_converts_frame_time(tmp_path):
    audit = _audit(tmp_path)
    run = prepare_visus_canonical_aoi_intake(
        audit,
        _table(),
        extraction_basis="Reviewed fixture extraction from the audited XML files.",
        frame_index_base=1,
    )

    assert len(run.canonical) == 22
    assert run.canonical["timestamp_ms"].min() == pytest.approx(0.0)
    assert run.canonical["timestamp_ms"].max() == pytest.approx(1000.0)
    assert set(run.by_stream) == {"published_curated"}
    assert set(run.by_stream["published_curated"]) == {
        f"S{index:02d}" for index in range(1, 12)
    }
    assert isinstance(run.by_stream["published_curated"]["S01"][0], DynamicAOIKeyframe)
    assert run.report["video_frame_rate_hz"] == pytest.approx(25.0)
    assert run.report["complete_annotation_manifest_coverage_required"] is True
    assert len(run.report["report_fingerprint_sha256"]) == 64


def test_visus_canonical_intake_is_deterministic(tmp_path):
    audit = _audit(tmp_path)
    table = _table()
    first = prepare_visus_canonical_aoi_intake(
        audit,
        table,
        extraction_basis="Reviewed fixture extraction.",
        frame_index_base=1,
    )
    second = prepare_visus_canonical_aoi_intake(
        audit,
        table,
        extraction_basis="Reviewed fixture extraction.",
        frame_index_base=1,
    )
    assert first.report["report_fingerprint_sha256"] == second.report["report_fingerprint_sha256"]
    assert first.report["canonical_table_fingerprint_sha256"] == second.report[
        "canonical_table_fingerprint_sha256"
    ]


def test_visus_canonical_intake_rejects_manifest_identity_mismatch(tmp_path):
    audit = _audit(tmp_path)
    table = _table()
    table.loc[table.index[0], "stimulus_id"] = "S02"
    with pytest.raises(SchemaError, match="stimulus_id"):
        prepare_visus_canonical_aoi_intake(
            audit,
            table,
            extraction_basis="Reviewed fixture extraction.",
            frame_index_base=1,
        )


def test_visus_canonical_intake_requires_complete_annotation_file_coverage(tmp_path):
    audit = _audit(tmp_path)
    table = _table().loc[lambda frame: frame["stimulus_id"] != "S11"].copy()
    with pytest.raises(SchemaError, match="cover every audited AOI annotation file"):
        prepare_visus_canonical_aoi_intake(
            audit,
            table,
            extraction_basis="Reviewed fixture extraction.",
            frame_index_base=1,
        )


def test_visus_canonical_intake_rejects_noninteger_frames_and_bad_geometry(tmp_path):
    audit = _audit(tmp_path)
    fractional = _table()
    fractional["frame_index"] = fractional["frame_index"].astype(float)
    fractional.loc[fractional.index[0], "frame_index"] = 1.5
    with pytest.raises(SchemaError, match="integers"):
        prepare_visus_canonical_aoi_intake(
            audit,
            fractional,
            extraction_basis="Reviewed fixture extraction.",
            frame_index_base=1,
        )

    outside = _table()
    outside.loc[outside.index[0], "xmax"] = 2000.0
    with pytest.raises(SchemaError, match="video resolution"):
        prepare_visus_canonical_aoi_intake(
            audit,
            outside,
            extraction_basis="Reviewed fixture extraction.",
            frame_index_base=1,
        )


def test_visus_canonical_intake_rejects_duplicate_track_frame_identity(tmp_path):
    audit = _audit(tmp_path)
    table = pd.concat([_table(), _table().iloc[[0]]], ignore_index=True)
    with pytest.raises(SchemaError, match="duplicate"):
        prepare_visus_canonical_aoi_intake(
            audit,
            table,
            extraction_basis="Reviewed fixture extraction.",
            frame_index_base=1,
        )


def test_visus_canonical_intake_revalidates_source_audit_fingerprint(tmp_path):
    audit = _audit(tmp_path)
    audit.report["identity"]["participant_count"] = 999
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        prepare_visus_canonical_aoi_intake(
            audit,
            _table(),
            extraction_basis="Reviewed fixture extraction.",
            frame_index_base=1,
        )
