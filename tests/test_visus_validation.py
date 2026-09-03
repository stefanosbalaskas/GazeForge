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
from gazeforge.visus_validation import run_visus_dynamic_aoi_model_validation


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


def _audit(root: Path, *, coordinate_unit: str = "pixels"):
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
        dataset_version="validation-fixture",
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
        coordinate_unit=coordinate_unit,
        coordinate_unit_verified=True,
        coordinate_verification_basis="Fixture coordinate documentation.",
        timestamp_basis_verified=True,
        timestamp_verification_basis="Fixture video frame-time documentation.",
        files=files,
    )
    return audit_visus_source(root, spec)


def _inputs():
    stimuli = [f"S{index:02d}" for index in range(1, 12)]
    references = {}
    predictions = {}
    timestamps = {}
    fixations = {}
    for index, stimulus in enumerate(stimuli):
        shift = float(index)
        references[stimulus] = [
            DynamicAOIKeyframe("target", "person", 0.0, shift, 0.0, 100.0 + shift, 100.0),
            DynamicAOIKeyframe(
                "target",
                "person",
                100.0,
                20.0 + shift,
                0.0,
                120.0 + shift,
                100.0,
            ),
        ]
        predictions[stimulus] = [
            DynamicAOIKeyframe(
                "pred-target",
                "person",
                0.0,
                shift,
                0.0,
                100.0 + shift,
                100.0,
                model_name="FixtureTracker",
                model_version="1.0",
            ),
            DynamicAOIKeyframe(
                "pred-target",
                "person",
                100.0,
                20.0 + shift,
                0.0,
                120.0 + shift,
                100.0,
                model_name="FixtureTracker",
                model_version="1.0",
            ),
        ]
        timestamps[stimulus] = [0.0, 50.0, 100.0]
        fixations[stimulus] = pd.DataFrame(
            {
                "timestamp_ms": [0.0, 50.0, 100.0],
                "x_px": [20.0 + shift, 30.0 + shift, 40.0 + shift],
                "y_px": [20.0, 20.0, 20.0],
            }
        )
    return predictions, references, timestamps, fixations


def test_visus_model_validation_requires_full_audited_coverage_and_is_fingerprinted(tmp_path):
    audit = _audit(tmp_path)
    predictions, references, timestamps, fixations = _inputs()
    run = run_visus_dynamic_aoi_model_validation(
        audit,
        predicted_by_stimulus=predictions,
        reference_by_stimulus=references,
        timestamps_by_stimulus=timestamps,
        fixations_by_stimulus=fixations,
        reference_stream_id="published_curated",
        model_name="FixtureTracker",
        model_version="1.0",
        timestamp_grid_basis="fixture video frame timestamps",
        max_interpolation_gap_ms=100.0,
        include_matches=True,
    )

    assert len(run.per_stimulus) == 11
    assert len(run.per_timestamp) == 33
    assert run.report["metrics"]["dynamic_aoi_summary"]["f1"] == pytest.approx(1.0)
    assert run.report["metrics"]["dynamic_aoi_summary"]["mean_matched_iou"] == pytest.approx(1.0)
    assert run.fixation_assignment is not None
    assert run.fixation_assignment["exact_agreement"] == pytest.approx(1.0)
    assert run.report["benchmark"]["human_annotator_count"] == 1
    assert run.report["protocol"]["human_human_agreement_claimed"] is False
    assert run.report["protocol"]["complete_audited_stimulus_coverage_required"] is True
    assert len(run.report["report_fingerprint_sha256"]) == 64


def test_visus_model_validation_rejects_incomplete_prediction_coverage(tmp_path):
    audit = _audit(tmp_path)
    predictions, references, timestamps, _ = _inputs()
    predictions.pop("S11")
    with pytest.raises(SchemaError, match="exactly cover"):
        run_visus_dynamic_aoi_model_validation(
            audit,
            predicted_by_stimulus=predictions,
            reference_by_stimulus=references,
            timestamps_by_stimulus=timestamps,
            reference_stream_id="published_curated",
            model_name="FixtureTracker",
            model_version="1.0",
            timestamp_grid_basis="fixture video frame timestamps",
            max_interpolation_gap_ms=100.0,
        )


def test_visus_model_validation_rejects_unmanifested_reference_stream(tmp_path):
    audit = _audit(tmp_path)
    predictions, references, timestamps, _ = _inputs()
    with pytest.raises(SchemaError, match="reference stream"):
        run_visus_dynamic_aoi_model_validation(
            audit,
            predicted_by_stimulus=predictions,
            reference_by_stimulus=references,
            timestamps_by_stimulus=timestamps,
            reference_stream_id="invented_second_annotator",
            model_name="FixtureTracker",
            model_version="1.0",
            timestamp_grid_basis="fixture video frame timestamps",
            max_interpolation_gap_ms=100.0,
        )


def test_visus_model_validation_revalidates_source_audit_fingerprint(tmp_path):
    audit = _audit(tmp_path)
    predictions, references, timestamps, _ = _inputs()
    audit.report["identity"]["participant_count"] = 999
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        run_visus_dynamic_aoi_model_validation(
            audit,
            predicted_by_stimulus=predictions,
            reference_by_stimulus=references,
            timestamps_by_stimulus=timestamps,
            reference_stream_id="published_curated",
            model_name="FixtureTracker",
            model_version="1.0",
            timestamp_grid_basis="fixture video frame timestamps",
            max_interpolation_gap_ms=100.0,
        )


def test_visus_fixation_assignment_requires_audited_pixel_coordinates(tmp_path):
    audit = _audit(tmp_path, coordinate_unit="normalized")
    predictions, references, timestamps, fixations = _inputs()
    with pytest.raises(SchemaError, match="pixel coordinates"):
        run_visus_dynamic_aoi_model_validation(
            audit,
            predicted_by_stimulus=predictions,
            reference_by_stimulus=references,
            timestamps_by_stimulus=timestamps,
            fixations_by_stimulus=fixations,
            reference_stream_id="published_curated",
            model_name="FixtureTracker",
            model_version="1.0",
            timestamp_grid_basis="fixture video frame timestamps",
            max_interpolation_gap_ms=100.0,
        )
