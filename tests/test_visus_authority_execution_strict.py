import json

import pandas as pd

from gazeforge.visus_audit import load_visus_source_audit_spec
from gazeforge.visus_authority_binding import (
    AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD,
    audit_visus_source_with_authority,
)
from gazeforge.visus_authority_execution import (
    bind_visus_suite_to_source_authority,
    snapshot_visus_authority_execution_inputs,
)
from gazeforge.visus_authority_execution_strict import (
    AUTHORITY_CERTIFICATE_RECORD_FIELD,
    build_visus_authority_execution_provenance,
    validate_visus_authority_execution_provenance,
    write_visus_authority_execution_provenance,
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
        for frame_index, x_shift in ((1, 0.0), (3, 8.0)):
            rows.append(
                {
                    "source_path": f"aoi/{stimulus}-annotator_a.xml",
                    "stimulus_id": stimulus,
                    "annotation_stream_id": "annotator_a",
                    "frame_index": frame_index,
                    "aoi_id": "human-person",
                    "label": "person",
                    "xmin": 10.0 + index + x_shift,
                    "ymin": 20.0,
                    "xmax": 110.0 + index + x_shift,
                    "ymax": 220.0,
                }
            )
    return pd.DataFrame(rows)


def _prediction_table():
    rows = []
    for index in range(1, 12):
        stimulus = f"S{index:02d}"
        for frame_index, x_shift in ((1, 0.0), (3, 8.0)):
            rows.append(
                {
                    "stimulus_id": stimulus,
                    "frame_index": frame_index,
                    "aoi_id": "model-person",
                    "label": "person",
                    "xmin": 10.0 + index + x_shift,
                    "ymin": 20.0,
                    "xmax": 110.0 + index + x_shift,
                    "ymax": 220.0,
                    "confidence": 0.95,
                }
            )
    return pd.DataFrame(rows)


def test_strict_authority_execution_preserves_and_revalidates_certificate_semantics(tmp_path):
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
    grids = {f"S{index:02d}": [0.0, 40.0, 80.0] for index in range(1, 12)}
    grid_path.write_text(json.dumps(grids) + "\n", encoding="utf-8")

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
    suite = run_visus_dynamic_aoi_validation_suite(
        audit,
        reference,
        prediction,
        grids,
        tmp_path / "suite",
        reference_stream_id="annotator_a",
        timestamp_grid_basis="Reviewed synthetic video-frame grid.",
        max_interpolation_gap_ms=100.0,
    )
    suite = bind_visus_suite_to_source_authority(audit, suite)
    snapshots = snapshot_visus_authority_execution_inputs(
        source_audit_spec=spec_path,
        source_authority_certificate=certificate_path,
        human_aoi_table=human_path,
        model_prediction_table=prediction_path,
        timestamp_grid_json=grid_path,
    )

    manifest = build_visus_authority_execution_provenance(audit, suite, snapshots)
    assert manifest[AUTHORITY_CERTIFICATE_RECORD_FIELD] == certificate
    assert manifest["source"][AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] == certificate[
        "certificate_fingerprint_sha256"
    ]

    run = write_visus_authority_execution_provenance(
        manifest,
        suite.output_dir,
    )
    summary = validate_visus_authority_execution_provenance(run.manifest_path)
    assert summary["input_count"] == 5
    assert summary["authority_certificate_semantics_verified"] is True
    assert summary[AUTHORITY_CERTIFICATE_FINGERPRINT_FIELD] == certificate[
        "certificate_fingerprint_sha256"
    ]
