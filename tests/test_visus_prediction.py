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
from gazeforge.visus_prediction import prepare_visus_dynamic_aoi_predictions


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
        dataset_version="prediction-fixture",
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


def _predictions() -> pd.DataFrame:
    rows = []
    for index in range(1, 12):
        stimulus = f"S{index:02d}"
        rows.extend(
            [
                {
                    "stimulus_id": stimulus,
                    "frame_index": 1,
                    "aoi_id": "detected-person",
                    "label": "person",
                    "xmin": 12.0,
                    "ymin": 21.0,
                    "xmax": 112.0,
                    "ymax": 221.0,
                    "confidence": 0.90,
                },
                {
                    "stimulus_id": stimulus,
                    "frame_index": 26,
                    "aoi_id": "detected-person",
                    "label": "person",
                    "xmin": 22.0,
                    "ymin": 21.0,
                    "xmax": 122.0,
                    "ymax": 221.0,
                    "confidence": 0.88,
                },
            ]
        )
    return pd.DataFrame(rows)


def _run(audit, table):
    return prepare_visus_dynamic_aoi_predictions(
        audit,
        table,
        model_name="fixture-detector",
        model_version="1.2.3",
        prediction_basis="Reviewed fixture detector output on each exact audited video.",
        prediction_coordinate_unit="px",
        frame_index_base=1,
        model_artifact_sha256="a" * 64,
    )


def test_visus_prediction_intake_links_complete_audited_video_set(tmp_path):
    audit = _audit(tmp_path)
    run = _run(audit, _predictions())

    assert len(run.canonical) == 22
    assert run.canonical["timestamp_ms"].min() == pytest.approx(0.0)
    assert run.canonical["timestamp_ms"].max() == pytest.approx(1000.0)
    assert set(run.by_stimulus) == {f"S{index:02d}" for index in range(1, 12)}
    first = run.by_stimulus["S01"][0]
    assert isinstance(first, DynamicAOIKeyframe)
    assert first.source == "model"
    assert first.model_name == "fixture-detector"
    assert first.model_version == "1.2.3"
    assert len(run.report["audited_video_files"]) == 11
    assert run.report["evaluation_timestamp_grid_generated"] is False
    assert run.report["model"]["artifact_sha256"] == "a" * 64


def test_visus_prediction_intake_is_deterministic(tmp_path):
    audit = _audit(tmp_path)
    table = _predictions()
    first = _run(audit, table)
    second = _run(audit, table)
    assert first.report["report_fingerprint_sha256"] == second.report[
        "report_fingerprint_sha256"
    ]
    assert first.report["canonical_table_fingerprint_sha256"] == second.report[
        "canonical_table_fingerprint_sha256"
    ]


def test_visus_prediction_intake_requires_complete_stimulus_coverage(tmp_path):
    audit = _audit(tmp_path)
    table = _predictions().loc[lambda frame: frame["stimulus_id"] != "S11"].copy()
    with pytest.raises(SchemaError, match="coverage"):
        _run(audit, table)


def test_visus_prediction_intake_rejects_coordinate_unit_mismatch(tmp_path):
    audit = _audit(tmp_path)
    with pytest.raises(SchemaError, match="coordinate unit"):
        prepare_visus_dynamic_aoi_predictions(
            audit,
            _predictions(),
            model_name="fixture-detector",
            model_version="1.2.3",
            prediction_basis="Reviewed fixture detector output.",
            prediction_coordinate_unit="normalized",
            frame_index_base=1,
        )


def test_visus_prediction_intake_rejects_bad_geometry_and_fractional_frames(tmp_path):
    audit = _audit(tmp_path)
    outside = _predictions()
    outside.loc[outside.index[0], "xmax"] = 2000.0
    with pytest.raises(SchemaError, match="video resolution"):
        _run(audit, outside)

    fractional = _predictions()
    fractional["frame_index"] = fractional["frame_index"].astype(float)
    fractional.loc[fractional.index[0], "frame_index"] = 1.5
    with pytest.raises(SchemaError, match="integers"):
        _run(audit, fractional)


def test_visus_prediction_intake_rejects_duplicate_track_frame_and_label_drift(tmp_path):
    audit = _audit(tmp_path)
    duplicate = pd.concat([_predictions(), _predictions().iloc[[0]]], ignore_index=True)
    with pytest.raises(SchemaError, match="duplicate"):
        _run(audit, duplicate)

    drift = _predictions()
    drift.loc[drift.index[1], "label"] = "vehicle"
    with pytest.raises(SchemaError, match="one label"):
        _run(audit, drift)


def test_visus_prediction_intake_revalidates_source_audit_and_model_digest(tmp_path):
    audit = _audit(tmp_path)
    with pytest.raises(ValueError, match="64-character"):
        prepare_visus_dynamic_aoi_predictions(
            audit,
            _predictions(),
            model_name="fixture-detector",
            model_version="1.2.3",
            prediction_basis="Reviewed fixture detector output.",
            prediction_coordinate_unit="pixels",
            frame_index_base=1,
            model_artifact_sha256="not-a-digest",
        )

    audit.report["identity"]["participant_count"] = 999
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        _run(audit, _predictions())
