import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_audit import (
    VisusSourceAuditSpec,
    VisusSourceFileRecord,
    audit_visus_source,
    load_visus_source_audit_spec,
)
from gazeforge.visus_cli import main as visus_cli_main
from gazeforge.visus_execution import (
    build_visus_execution_provenance,
    snapshot_visus_execution_inputs,
    validate_visus_execution_provenance,
    verify_visus_execution_inputs_unchanged,
    write_visus_execution_provenance,
)
from gazeforge.visus_intake import prepare_visus_canonical_aoi_intake
from gazeforge.visus_prediction import prepare_visus_dynamic_aoi_predictions
from gazeforge.visus_suite import run_visus_dynamic_aoi_validation_suite


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


def _raw_fixture(tmp_path: Path) -> dict[str, Path]:
    source = tmp_path / "source"
    stimuli = [f"S{index:02d}" for index in range(1, 12)]
    files: list[VisusSourceFileRecord] = []
    for stimulus in stimuli:
        files.append(
            _record(
                source,
                path=f"video/{stimulus}.avi",
                role="video",
                stimulus_id=stimulus,
            )
        )
        files.append(
            _record(
                source,
                path=f"aoi/{stimulus}-annotator_a.xml",
                role="aoi_annotation",
                stimulus_id=stimulus,
                annotation_stream_id="annotator_a",
            )
        )
    for index in range(1, 26):
        participant = f"P{index:02d}"
        stimulus = stimuli[(index - 1) % len(stimuli)]
        files.append(
            _record(
                source,
                path=f"gaze/{participant}-{stimulus}.tsv",
                role="gaze",
                stimulus_id=stimulus,
                participant_id=participant,
            )
        )

    spec = VisusSourceAuditSpec(
        dataset_name="VISUS",
        dataset_version="execution-fixture",
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
        independent_annotation_streams_verified=False,
        files=files,
    )
    spec_path = tmp_path / "visus-source-audit.json"
    spec_path.write_text(
        json.dumps(spec.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    human_rows = []
    prediction_rows = []
    for index, stimulus in enumerate(stimuli, start=1):
        shift = float(index)
        for frame_index, x_shift in ((1, 0.0), (3, 8.0)):
            human_rows.append(
                {
                    "source_path": f"aoi/{stimulus}-annotator_a.xml",
                    "stimulus_id": stimulus,
                    "annotation_stream_id": "annotator_a",
                    "frame_index": frame_index,
                    "aoi_id": "annotator_a-person",
                    "label": "person",
                    "xmin": 10.0 + shift + x_shift,
                    "ymin": 20.0,
                    "xmax": 110.0 + shift + x_shift,
                    "ymax": 220.0,
                }
            )
            prediction_rows.append(
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
    human_path = tmp_path / "human.csv"
    prediction_path = tmp_path / "prediction.csv"
    pd.DataFrame(human_rows).to_csv(human_path, index=False)
    pd.DataFrame(prediction_rows).to_csv(prediction_path, index=False)

    grids_path = tmp_path / "timestamp-grids.json"
    grids_path.write_text(
        json.dumps({stimulus: [0.0, 40.0, 80.0] for stimulus in stimuli}, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return {
        "source": source,
        "spec": spec_path,
        "human": human_path,
        "prediction": prediction_path,
        "grids": grids_path,
        "output": tmp_path / "suite",
    }


def _run_from_raw(paths: dict[str, Path]):
    spec = load_visus_source_audit_spec(paths["spec"])
    audit = audit_visus_source(paths["source"], spec)
    reference = prepare_visus_canonical_aoi_intake(
        audit,
        pd.read_csv(paths["human"]),
        extraction_basis="Reviewed fixture extraction from exact audited AOI XML files.",
        frame_index_base=1,
    )
    prediction = prepare_visus_dynamic_aoi_predictions(
        audit,
        pd.read_csv(paths["prediction"]),
        model_name="fixture-detector",
        model_version="1.0.0",
        prediction_basis="Reviewed fixture detector output on exact audited videos.",
        prediction_coordinate_unit="pixels",
        frame_index_base=1,
        model_artifact_sha256="a" * 64,
    )
    timestamps = json.loads(paths["grids"].read_text(encoding="utf-8"))
    suite = run_visus_dynamic_aoi_validation_suite(
        audit,
        reference,
        prediction,
        timestamps,
        paths["output"],
        reference_stream_id="annotator_a",
        timestamp_grid_basis="Reviewed fixed video-frame grid.",
        max_interpolation_gap_ms=100.0,
    )
    return audit, suite


def _snapshots(paths: dict[str, Path]):
    return snapshot_visus_execution_inputs(
        source_audit_spec=paths["spec"],
        human_aoi_table=paths["human"],
        model_prediction_table=paths["prediction"],
        timestamp_grid_json=paths["grids"],
    )


def test_execution_provenance_binds_raw_inputs_to_verified_suite(tmp_path):
    paths = _raw_fixture(tmp_path)
    snapshots = _snapshots(paths)
    audit, suite = _run_from_raw(paths)

    manifest = build_visus_execution_provenance(audit, suite, snapshots)
    run = write_visus_execution_provenance(manifest, paths["output"])
    summary = validate_visus_execution_provenance(run.manifest_path)

    assert summary["status"] == "complete"
    assert summary["input_count"] == 4
    assert summary["suite_verified"] is True
    assert summary["suite_fingerprint_sha256"] == suite.suite_fingerprint_sha256
    assert len(summary["execution_fingerprint_sha256"]) == 64
    assert [row["role"] for row in manifest["raw_inputs"]] == [
        "source_audit_spec",
        "human_aoi_table",
        "model_prediction_table",
        "timestamp_grid_json",
    ]
    assert manifest["parsed_inputs"]["prediction_emission_grid_used"] is False
    assert manifest["source"]["source_audit_spec_fingerprint_sha256"] == (
        manifest["raw_inputs"][0]["semantic_fingerprint_sha256"]
    )


def test_execution_provenance_refuses_raw_input_mutation(tmp_path):
    paths = _raw_fixture(tmp_path)
    snapshots = _snapshots(paths)
    paths["human"].write_text(
        paths["human"].read_text(encoding="utf-8") + "# changed\n",
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="changed after the pre-execution snapshot"):
        verify_visus_execution_inputs_unchanged(
            snapshots,
            source_audit_spec=paths["spec"],
            human_aoi_table=paths["human"],
            model_prediction_table=paths["prediction"],
            timestamp_grid_json=paths["grids"],
        )


def test_execution_provenance_detects_rehashed_suite_binding_tamper(tmp_path):
    paths = _raw_fixture(tmp_path)
    snapshots = _snapshots(paths)
    audit, suite = _run_from_raw(paths)
    run = write_visus_execution_provenance(
        build_visus_execution_provenance(audit, suite, snapshots),
        paths["output"],
    )

    payload = json.loads(run.manifest_path.read_text(encoding="utf-8"))
    payload["source"]["source_manifest_fingerprint_sha256"] = "f" * 64
    body = {
        key: value
        for key, value in payload.items()
        if key != "execution_fingerprint_sha256"
    }
    payload["execution_fingerprint_sha256"] = benchmark_fingerprint(body)
    run.manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="suite source identity mismatch"):
        validate_visus_execution_provenance(run.manifest_path, verify_suite=True)


def test_visus_cli_suite_freezes_and_revalidates_execution_provenance(tmp_path, capsys):
    paths = _raw_fixture(tmp_path)
    result = visus_cli_main(
        [
            "suite",
            str(paths["source"]),
            str(paths["spec"]),
            str(paths["human"]),
            str(paths["prediction"]),
            str(paths["grids"]),
            str(paths["output"]),
            "--extraction-basis",
            "Reviewed fixture extraction from exact audited AOI XML files.",
            "--human-frame-index-base",
            "1",
            "--model-name",
            "fixture-detector",
            "--model-version",
            "1.0.0",
            "--prediction-basis",
            "Reviewed fixture detector output on exact audited videos.",
            "--prediction-coordinate-unit",
            "pixels",
            "--prediction-frame-index-base",
            "1",
            "--model-artifact-sha256",
            "a" * 64,
            "--reference-stream-id",
            "annotator_a",
            "--timestamp-grid-basis",
            "Reviewed fixed video-frame grid.",
            "--max-interpolation-gap-ms",
            "100",
        ]
    )
    assert result == 0
    suite_output = json.loads(capsys.readouterr().out)
    provenance_path = Path(suite_output["execution_provenance"])
    assert provenance_path.is_file()
    assert len(suite_output["execution_fingerprint_sha256"]) == 64
    assert suite_output["prediction_emission_grid_used"] is False

    assert visus_cli_main(["execution-validate", str(paths["output"])]) == 0
    validation = json.loads(capsys.readouterr().out)
    assert validation["suite_verified"] is True
    assert validation["execution_fingerprint_sha256"] == suite_output[
        "execution_fingerprint_sha256"
    ]
