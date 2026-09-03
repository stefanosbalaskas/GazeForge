import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from gazeforge.dashboard import build_benchmark_dashboard, render_benchmark_dashboard_markdown
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_audit import (
    VisusSourceAuditSpec,
    VisusSourceFileRecord,
    audit_visus_source,
)
from gazeforge.visus_intake import prepare_visus_canonical_aoi_intake
from gazeforge.visus_prediction import prepare_visus_dynamic_aoi_predictions
from gazeforge.visus_suite import (
    run_visus_dynamic_aoi_validation_suite,
    validate_visus_dynamic_aoi_suite_manifest,
)


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


def _audit(root: Path, *, independent: bool):
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
        for stream in ("annotator_a", "annotator_b"):
            files.append(
                _record(
                    root,
                    path=f"aoi/{stimulus}-{stream}.xml",
                    role="aoi_annotation",
                    stimulus_id=stimulus,
                    annotation_stream_id=stream,
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
        dataset_version="suite-fixture",
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
        timestamp_verification_basis="Fixture video frame-time documentation.",
        independent_annotation_streams_verified=independent,
        independent_annotation_streams_basis=(
            "Fixture streams created independently for suite testing." if independent else ""
        ),
        files=files,
    )
    return audit_visus_source(root, spec)


def _reference_table() -> pd.DataFrame:
    rows = []
    for index in range(1, 12):
        stimulus = f"S{index:02d}"
        shift = float(index)
        for stream in ("annotator_a", "annotator_b"):
            for frame_index, x_shift in ((1, 0.0), (3, 8.0)):
                rows.append(
                    {
                        "source_path": f"aoi/{stimulus}-{stream}.xml",
                        "stimulus_id": stimulus,
                        "annotation_stream_id": stream,
                        "frame_index": frame_index,
                        "aoi_id": f"{stream}-person",
                        "label": "person",
                        "xmin": 10.0 + shift + x_shift,
                        "ymin": 20.0,
                        "xmax": 110.0 + shift + x_shift,
                        "ymax": 220.0,
                    }
                )
    return pd.DataFrame(rows)


def _prediction_table() -> pd.DataFrame:
    rows = []
    for index in range(1, 12):
        stimulus = f"S{index:02d}"
        shift = float(index)
        for frame_index, x_shift in ((1, 0.0), (3, 8.0)):
            rows.append(
                {
                    "stimulus_id": stimulus,
                    "frame_index": frame_index,
                    "aoi_id": "model-person",
                    "label": "person",
                    "xmin": 10.0 + shift + x_shift,
                    "ymin": 20.0,
                    "xmax": 110.0 + shift + x_shift,
                    "ymax": 220.0,
                    "confidence": 0.95,
                }
            )
    return pd.DataFrame(rows)


def _inputs(root: Path, *, independent: bool):
    audit = _audit(root, independent=independent)
    reference = prepare_visus_canonical_aoi_intake(
        audit,
        _reference_table(),
        extraction_basis="Reviewed fixture extraction from exact audited AOI XML files.",
        frame_index_base=1,
    )
    prediction = prepare_visus_dynamic_aoi_predictions(
        audit,
        _prediction_table(),
        model_name="fixture-detector",
        model_version="1.0.0",
        prediction_basis="Reviewed fixture detector output on exact audited videos.",
        prediction_coordinate_unit="pixels",
        frame_index_base=1,
        model_artifact_sha256="a" * 64,
    )
    timestamps = {
        f"S{index:02d}": [0.0, 40.0, 80.0]
        for index in range(1, 12)
    }
    return audit, reference, prediction, timestamps


def test_visus_suite_freezes_and_revalidates_model_human_tranche(tmp_path):
    audit, reference, prediction, timestamps = _inputs(tmp_path / "source", independent=False)
    output = tmp_path / "suite"
    run = run_visus_dynamic_aoi_validation_suite(
        audit,
        reference,
        prediction,
        timestamps,
        output,
        reference_stream_id="annotator_a",
        timestamp_grid_basis="Fixed fixture video-frame midpoint grid.",
        max_interpolation_gap_ms=100.0,
    )

    assert set(run.reports) == {
        "human_reference_intake",
        "model_prediction_intake",
        "model_human_validation",
    }
    assert run.manifest["protocol"]["human_human_agreement_included"] is False
    assert run.manifest["protocol"]["independent_annotation_streams_verified"] is False
    assert run.manifest["protocol"]["prediction_emission_grid_used"] is False
    assert len(run.suite_fingerprint_sha256) == 64
    verified = validate_visus_dynamic_aoi_suite_manifest(output)
    assert verified["status"] == "complete"
    assert verified["report_count"] == 3
    assert verified["reports_verified"] is True


def test_visus_suite_dashboard_discovers_only_benchmark_children_and_verified_suite(tmp_path):
    audit, reference, prediction, timestamps = _inputs(tmp_path / "source", independent=False)
    run = run_visus_dynamic_aoi_validation_suite(
        audit,
        reference,
        prediction,
        timestamps,
        tmp_path / "evidence" / "visus",
        reference_stream_id="annotator_a",
        timestamp_grid_basis="Fixed fixture grid.",
        max_interpolation_gap_ms=100.0,
    )

    dashboard = build_benchmark_dashboard(tmp_path / "evidence")
    assert len(dashboard.suites) == 1
    assert dashboard.suite_table.iloc[0]["suite"] == "visus-dynamic-aoi-validation-v1"
    assert dashboard.suite_table.iloc[0]["model"] == "fixture-detector 1.0.0"
    assert dashboard.suite_table.iloc[0]["reference_stream_id"] == "annotator_a"
    assert dashboard.suite_table.iloc[0]["human_human_agreement_included"] == "false"
    assert dashboard.suite_source_files == (str(run.manifest_path),)
    assert len(dashboard.reports) == 1
    assert dashboard.reports[0]["benchmark"]["task"] == "dynamic semantic-AOI model validation"
    markdown = render_benchmark_dashboard_markdown(dashboard)
    assert "visus-dynamic-aoi-validation-v1" in markdown
    assert run.suite_fingerprint_sha256[:12] in markdown


def test_visus_suite_requires_human_agreement_when_independent_streams_exist(tmp_path):
    audit, reference, prediction, timestamps = _inputs(tmp_path / "source", independent=True)
    output = tmp_path / "suite"
    with pytest.raises(BenchmarkIntegrityError, match="must include human-human agreement"):
        run_visus_dynamic_aoi_validation_suite(
            audit,
            reference,
            prediction,
            timestamps,
            output,
            reference_stream_id="annotator_a",
            timestamp_grid_basis="Fixed fixture grid.",
            max_interpolation_gap_ms=100.0,
        )
    assert not output.exists()


def test_visus_suite_includes_not_ground_truth_human_agreement_when_verified(tmp_path):
    audit, reference, prediction, timestamps = _inputs(tmp_path / "source", independent=True)
    run = run_visus_dynamic_aoi_validation_suite(
        audit,
        reference,
        prediction,
        timestamps,
        tmp_path / "suite",
        reference_stream_id="annotator_a",
        timestamp_grid_basis="Fixed fixture grid.",
        max_interpolation_gap_ms=100.0,
        human_agreement_streams=("annotator_a", "annotator_b"),
    )

    assert set(run.reports) == {
        "human_reference_intake",
        "model_prediction_intake",
        "model_human_validation",
        "human_human_agreement",
    }
    assert run.manifest["protocol"]["human_human_agreement_included"] is True
    human_protocol = run.reports["human_human_agreement"]["protocol"]
    assert human_protocol["independent_annotation_streams_verified"] is True
    assert human_protocol["human_agreement_reference_not_ground_truth"] is True
    assert validate_visus_dynamic_aoi_suite_manifest(run.manifest_path)["report_count"] == 4


def test_visus_suite_blocks_human_agreement_without_independence(tmp_path):
    audit, reference, prediction, timestamps = _inputs(tmp_path / "source", independent=False)
    with pytest.raises(BenchmarkIntegrityError, match="blocked"):
        run_visus_dynamic_aoi_validation_suite(
            audit,
            reference,
            prediction,
            timestamps,
            tmp_path / "suite",
            reference_stream_id="annotator_a",
            timestamp_grid_basis="Fixed fixture grid.",
            max_interpolation_gap_ms=100.0,
            human_agreement_streams=("annotator_a", "annotator_b"),
        )


def test_visus_suite_validator_detects_tampered_child_report(tmp_path):
    audit, reference, prediction, timestamps = _inputs(tmp_path / "source", independent=False)
    run = run_visus_dynamic_aoi_validation_suite(
        audit,
        reference,
        prediction,
        timestamps,
        tmp_path / "suite",
        reference_stream_id="annotator_a",
        timestamp_grid_basis="Fixed fixture grid.",
        max_interpolation_gap_ms=100.0,
    )
    child_path = run.report_paths["model_prediction_intake"]
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["row_count"] = 999
    child_path.write_text(json.dumps(child), encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_visus_dynamic_aoi_suite_manifest(run.manifest_path)


def test_visus_suite_revalidates_intake_source_identity_before_writing(tmp_path):
    audit, reference, prediction, timestamps = _inputs(tmp_path / "source", independent=False)
    prediction.report["source_manifest_fingerprint_sha256"] = "0" * 64
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        run_visus_dynamic_aoi_validation_suite(
            audit,
            reference,
            prediction,
            timestamps,
            tmp_path / "suite",
            reference_stream_id="annotator_a",
            timestamp_grid_basis="Fixed fixture grid.",
            max_interpolation_gap_ms=100.0,
        )
