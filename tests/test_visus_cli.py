import json
from types import SimpleNamespace

import pandas as pd
import pytest

from gazeforge import visus_cli


def test_visus_cli_parses_complete_suite_provenance():
    args = visus_cli.build_parser().parse_args(
        [
            "suite",
            "/tmp/source",
            "/tmp/spec.json",
            "/tmp/human.csv",
            "/tmp/model.csv",
            "/tmp/grid.json",
            "/tmp/output",
            "--extraction-basis",
            "reviewed extraction",
            "--human-frame-index-base",
            "1",
            "--model-name",
            "detector",
            "--model-version",
            "2.0",
            "--prediction-basis",
            "reviewed detector output",
            "--prediction-coordinate-unit",
            "pixels",
            "--prediction-frame-index-base",
            "0",
            "--reference-stream-id",
            "human-a",
            "--timestamp-grid-basis",
            "independent reviewed video grid",
            "--max-interpolation-gap-ms",
            "80",
            "--human-agreement-streams",
            "human-a,human-b",
        ]
    )

    assert args.human_frame_index_base == 1
    assert args.prediction_frame_index_base == 0
    assert args.human_agreement_streams == ("human-a", "human-b")
    assert args.max_interpolation_gap_ms == 80.0


def test_visus_cli_rejects_invalid_human_agreement_pair():
    with pytest.raises(SystemExit):
        visus_cli.build_parser().parse_args(
            [
                "suite",
                "/tmp/source",
                "/tmp/spec.json",
                "/tmp/human.csv",
                "/tmp/model.csv",
                "/tmp/grid.json",
                "/tmp/output",
                "--extraction-basis",
                "reviewed extraction",
                "--human-frame-index-base",
                "1",
                "--model-name",
                "detector",
                "--model-version",
                "2.0",
                "--prediction-basis",
                "reviewed detector output",
                "--prediction-coordinate-unit",
                "pixels",
                "--prediction-frame-index-base",
                "0",
                "--reference-stream-id",
                "human-a",
                "--timestamp-grid-basis",
                "independent reviewed video grid",
                "--max-interpolation-gap-ms",
                "80",
                "--human-agreement-streams",
                "human-a,human-a",
            ]
        )


def test_timestamp_grid_loader_requires_external_strictly_increasing_grid(tmp_path):
    path = tmp_path / "grid.json"
    path.write_text(
        json.dumps({"S01": [0, 40, 80], "S02": [0.0, 50.0]}),
        encoding="utf-8",
    )
    grids = visus_cli.load_visus_timestamp_grids(path)
    assert grids == {"S01": [0.0, 40.0, 80.0], "S02": [0.0, 50.0]}

    path.write_text(json.dumps({"S01": [0, 40, 40]}), encoding="utf-8")
    with pytest.raises(ValueError, match="strictly increasing"):
        visus_cli.load_visus_timestamp_grids(path)


def test_timestamp_grid_loader_rejects_boolean_and_non_object(tmp_path):
    path = tmp_path / "grid.json"
    path.write_text(json.dumps({"S01": [0, True, 80]}), encoding="utf-8")
    with pytest.raises(ValueError, match="boolean"):
        visus_cli.load_visus_timestamp_grids(path)

    path.write_text(json.dumps([0, 40, 80]), encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty object"):
        visus_cli.load_visus_timestamp_grids(path)


def test_read_table_accepts_csv_and_tsv_only(tmp_path):
    frame = pd.DataFrame({"stimulus_id": ["S01"], "frame_index": [1]})
    csv_path = tmp_path / "rows.csv"
    tsv_path = tmp_path / "rows.tsv"
    frame.to_csv(csv_path, index=False)
    frame.to_csv(tsv_path, index=False, sep="\t")

    assert visus_cli._read_table(csv_path).to_dict("records") == frame.to_dict("records")
    assert visus_cli._read_table(tsv_path).to_dict("records") == frame.to_dict("records")

    bad = tmp_path / "rows.xlsx"
    bad.write_text("not-an-xlsx", encoding="utf-8")
    with pytest.raises(ValueError, match="CSV or TSV"):
        visus_cli._read_table(bad)


def test_suite_command_uses_separate_grid_and_preserves_guards(monkeypatch, tmp_path, capsys):
    audit = SimpleNamespace(report={"report_fingerprint_sha256": "a" * 64})
    reference = SimpleNamespace(report={"report_fingerprint_sha256": "b" * 64})
    prediction = SimpleNamespace(report={"report_fingerprint_sha256": "c" * 64})
    grids = {"S01": [0.0, 40.0, 80.0]}
    captured = {}

    monkeypatch.setattr(visus_cli, "_load_audit", lambda *args: audit)
    monkeypatch.setattr(visus_cli, "_read_table", lambda path: pd.DataFrame({"x": [1]}))

    def fake_reference(audit_arg, table, **kwargs):
        assert audit_arg is audit
        captured["reference_kwargs"] = kwargs
        return reference

    def fake_prediction(audit_arg, table, **kwargs):
        assert audit_arg is audit
        captured["prediction_kwargs"] = kwargs
        return prediction

    monkeypatch.setattr(visus_cli, "prepare_visus_canonical_aoi_intake", fake_reference)
    monkeypatch.setattr(visus_cli, "prepare_visus_dynamic_aoi_predictions", fake_prediction)
    monkeypatch.setattr(visus_cli, "load_visus_timestamp_grids", lambda path: grids)

    output = tmp_path / "suite"
    suite_result = SimpleNamespace(
        manifest={"suite": "visus-dynamic-aoi-validation-v1", "status": "complete"},
        output_dir=output,
        reports={"human": {}, "prediction": {}, "model-human": {}},
        manifest_path=output / "visus-dynamic-aoi-suite-manifest.json",
        suite_fingerprint_sha256="d" * 64,
    )

    def fake_suite(audit_arg, reference_arg, prediction_arg, timestamps_arg, output_arg, **kwargs):
        assert audit_arg is audit
        assert reference_arg is reference
        assert prediction_arg is prediction
        assert timestamps_arg is grids
        assert output_arg == output
        captured["suite_kwargs"] = kwargs
        return suite_result

    monkeypatch.setattr(visus_cli, "run_visus_dynamic_aoi_validation_suite", fake_suite)

    code = visus_cli.main(
        [
            "suite",
            str(tmp_path / "source"),
            str(tmp_path / "spec.json"),
            str(tmp_path / "human.csv"),
            str(tmp_path / "model.csv"),
            str(tmp_path / "grid.json"),
            str(output),
            "--extraction-basis",
            "reviewed human extraction",
            "--human-frame-index-base",
            "1",
            "--model-name",
            "fixture-detector",
            "--model-version",
            "1.0",
            "--prediction-basis",
            "reviewed model output",
            "--prediction-coordinate-unit",
            "pixels",
            "--prediction-frame-index-base",
            "1",
            "--model-artifact-sha256",
            "e" * 64,
            "--reference-stream-id",
            "annotator-a",
            "--timestamp-grid-basis",
            "separately reviewed external grid",
            "--max-interpolation-gap-ms",
            "100",
            "--human-agreement-streams",
            "annotator-a,annotator-b",
            "--allow-label-mismatch",
            "--include-matches",
        ]
    )

    assert code == 0
    assert captured["reference_kwargs"]["frame_index_base"] == 1
    assert captured["prediction_kwargs"]["model_name"] == "fixture-detector"
    assert captured["prediction_kwargs"]["model_artifact_sha256"] == "e" * 64
    assert captured["suite_kwargs"]["human_agreement_streams"] == (
        "annotator-a",
        "annotator-b",
    )
    assert captured["suite_kwargs"]["require_label_match"] is False
    assert captured["suite_kwargs"]["timestamp_grid_basis"] == (
        "separately reviewed external grid"
    )
    assert captured["suite_kwargs"]["include_matches"] is True

    output_text = capsys.readouterr().out
    assert '"external_timestamp_grid_required": true' in output_text
    assert '"prediction_emission_grid_used": false' in output_text
    assert '"suite_fingerprint_sha256": "' in output_text


def test_suite_validate_manifest_only(monkeypatch, tmp_path, capsys):
    calls = {}

    def fake_validate(path, *, verify_reports):
        calls["path"] = path
        calls["verify_reports"] = verify_reports
        return {
            "suite": "visus-dynamic-aoi-validation-v1",
            "status": "complete",
            "report_count": 3,
            "reports_verified": verify_reports,
            "suite_fingerprint_sha256": "f" * 64,
        }

    monkeypatch.setattr(visus_cli, "validate_visus_dynamic_aoi_suite_manifest", fake_validate)
    code = visus_cli.main(["suite-validate", str(tmp_path), "--manifest-only"])

    assert code == 0
    assert calls["path"] == tmp_path
    assert calls["verify_reports"] is False
    assert '"reports_verified": false' in capsys.readouterr().out


def test_report_output_refuses_accidental_overwrite(tmp_path):
    target = tmp_path / "report.json"
    target.write_text("existing", encoding="utf-8")
    report = {"report_fingerprint_sha256": "f" * 64}

    with pytest.raises(FileExistsError):
        visus_cli._emit_report(report, output=target, overwrite=False)
