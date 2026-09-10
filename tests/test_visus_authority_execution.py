import copy
import json

import pandas as pd
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_audit import load_visus_source_audit_spec
from gazeforge.visus_authority_binding import (
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
    audit_visus_source_with_authority,
)
from gazeforge.visus_authority_execution import (
    bind_visus_suite_to_source_authority,
    build_visus_authority_execution_provenance,
    snapshot_visus_authority_execution_inputs,
    validate_visus_authority_execution_provenance,
    verify_visus_authority_execution_inputs_unchanged,
    write_visus_authority_execution_provenance,
)
from gazeforge.visus_execution import (
    build_visus_execution_provenance,
    snapshot_visus_execution_inputs,
)
from gazeforge.visus_intake import prepare_visus_canonical_aoi_intake
from gazeforge.visus_prediction import prepare_visus_dynamic_aoi_predictions
from gazeforge.visus_suite import run_visus_dynamic_aoi_validation_suite

from _visus_authority_fixture import (
    build_visus_authority_certificate,
    build_visus_authority_spec,
    write_visus_authority_certificate,
)


def _reference_table():
    rows = []
    for index in range(1, 12):
        stimulus = f"S{index:02d}"
        shift = float(index)
        for frame_index, x_shift in ((1, 0.0), (3, 8.0)):
            rows.append(
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
    return pd.DataFrame(rows)


def _prediction_table():
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


def _fixture(tmp_path):
    source = tmp_path / "source"
    spec = build_visus_authority_spec(source)
    certificate = build_visus_authority_certificate(spec)

    spec_path = tmp_path / "visus-source-audit.json"
    spec_path.write_text(
        json.dumps(spec.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    certificate_path = write_visus_authority_certificate(
        tmp_path / "visus-source-authority-certificate.json",
        certificate,
    )
    human_path = tmp_path / "human.csv"
    prediction_path = tmp_path / "prediction.csv"
    grid_path = tmp_path / "grid.json"
    _reference_table().to_csv(human_path, index=False)
    _prediction_table().to_csv(prediction_path, index=False)
    grid_path.write_text(
        json.dumps(
            {f"S{index:02d}": [0.0, 40.0, 80.0] for index in range(1, 12)},
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    loaded_spec = load_visus_source_audit_spec(spec_path)
    audit = audit_visus_source_with_authority(source, loaded_spec, certificate)
    reference = prepare_visus_canonical_aoi_intake(
        audit,
        pd.read_csv(human_path),
        extraction_basis="Reviewed synthetic extraction.",
        frame_index_base=1,
    )
    prediction = prepare_visus_dynamic_aoi_predictions(
        audit,
        pd.read_csv(prediction_path),
        model_name="fixture-detector",
        model_version="1.0.0",
        prediction_basis="Reviewed synthetic detector output.",
        prediction_coordinate_unit="pixels",
        frame_index_base=1,
        model_artifact_sha256="a" * 64,
    )
    timestamps = json.loads(grid_path.read_text(encoding="utf-8"))
    suite = run_visus_dynamic_aoi_validation_suite(
        audit,
        reference,
        prediction,
        timestamps,
        tmp_path / "suite",
        reference_stream_id="annotator_a",
        timestamp_grid_basis="Reviewed synthetic video-frame grid.",
        max_interpolation_gap_ms=100.0,
    )
    suite = bind_visus_suite_to_source_authority(audit, suite)
    return {
        "source": source,
        "spec": spec_path,
        "certificate": certificate_path,
        "human": human_path,
        "prediction": prediction_path,
        "grid": grid_path,
        "audit": audit,
        "suite": suite,
    }


def _authority_snapshots(paths):
    return snapshot_visus_authority_execution_inputs(
        source_audit_spec=paths["spec"],
        source_authority_certificate=paths["certificate"],
        human_aoi_table=paths["human"],
        model_prediction_table=paths["prediction"],
        timestamp_grid_json=paths["grid"],
    )


def test_authority_execution_binds_suite_and_exact_five_inputs(tmp_path):
    paths = _fixture(tmp_path)
    snapshots = _authority_snapshots(paths)
    manifest = build_visus_authority_execution_provenance(
        paths["audit"],
        paths["suite"],
        snapshots,
    )
    run = write_visus_authority_execution_provenance(
        manifest,
        paths["suite"].output_dir,
    )
    summary = validate_visus_authority_execution_provenance(run.manifest_path)

    authority = paths["audit"].report[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD]
    assert summary["status"] == "complete"
    assert summary["input_count"] == 5
    assert summary[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] == authority
    assert [row["role"] for row in manifest["raw_inputs"]] == [
        "source_audit_spec",
        "source_authority_certificate",
        "human_aoi_table",
        "model_prediction_table",
        "timestamp_grid_json",
    ]
    assert paths["suite"].manifest["source"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] == authority
    assert paths["suite"].manifest["protocol"]["source_authority_certificate_bound"] is True


def test_authority_execution_detects_certificate_mutation_after_snapshot(tmp_path):
    paths = _fixture(tmp_path)
    snapshots = _authority_snapshots(paths)
    paths["certificate"].write_text(
        paths["certificate"].read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )
    with pytest.raises(BenchmarkIntegrityError, match="changed after"):
        verify_visus_authority_execution_inputs_unchanged(
            snapshots,
            source_audit_spec=paths["spec"],
            source_authority_certificate=paths["certificate"],
            human_aoi_table=paths["human"],
            model_prediction_table=paths["prediction"],
            timestamp_grid_json=paths["grid"],
        )


def test_authority_execution_rejects_rehashed_certificate_semantic_swap(tmp_path):
    paths = _fixture(tmp_path)
    manifest = build_visus_authority_execution_provenance(
        paths["audit"],
        paths["suite"],
        _authority_snapshots(paths),
    )
    altered = copy.deepcopy(manifest)
    altered["raw_inputs"][1]["semantic_fingerprint_sha256"] = "f" * 64
    body = {
        key: value
        for key, value in altered.items()
        if key != "execution_fingerprint_sha256"
    }
    altered["execution_fingerprint_sha256"] = benchmark_fingerprint(body)
    path = tmp_path / "tampered-execution.json"
    path.write_text(json.dumps(altered), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="semantic fingerprint"):
        validate_visus_authority_execution_provenance(path, verify_suite=False)


def test_authority_execution_rejects_legacy_four_input_manifest(tmp_path):
    paths = _fixture(tmp_path)
    base_snapshots = snapshot_visus_execution_inputs(
        source_audit_spec=paths["spec"],
        human_aoi_table=paths["human"],
        model_prediction_table=paths["prediction"],
        timestamp_grid_json=paths["grid"],
    )
    legacy = build_visus_execution_provenance(
        paths["audit"],
        paths["suite"],
        base_snapshots,
    )
    path = tmp_path / "legacy-execution.json"
    path.write_text(json.dumps(legacy), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="provenance v2"):
        validate_visus_authority_execution_provenance(path, verify_suite=False)


def test_authority_execution_rejects_unbound_suite(tmp_path):
    paths = _fixture(tmp_path)
    suite = paths["suite"]
    source = suite.manifest["source"]
    del source[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD]
    protocol = suite.manifest["protocol"]
    del protocol[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD]
    protocol["source_authority_certificate_bound"] = False

    with pytest.raises(BenchmarkIntegrityError, match="missing a valid"):
        build_visus_authority_execution_provenance(
            paths["audit"],
            suite,
            _authority_snapshots(paths),
        )
