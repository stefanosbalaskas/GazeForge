"""Regression coverage for the worked tracker-import and QC learning path."""

from __future__ import annotations

import json
import pathlib
import runpy
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_worked_tracker_import_qc_runs_and_preserves_source(tmp_path, monkeypatch, capsys) -> None:
    output_dir = tmp_path / "worked-tracker-import-qc-demo"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "07_worked_tracker_import_qc.py",
            "--output-dir",
            str(output_dir),
        ],
    )

    runpy.run_path(
        str(ROOT / "examples" / "07_worked_tracker_import_qc.py"),
        run_name="__main__",
    )
    captured = capsys.readouterr()

    expected_csv = {
        "01_source_tracker_export.csv",
        "02_canonical_gaze.csv",
        "03_import_preflight.csv",
        "04_qc_samples.csv",
        "05_trial_quality.csv",
    }
    expected_json = {
        "import_contract.json",
        "analysis_plan.json",
        "provenance.json",
        "workflow_manifest.json",
    }
    assert {path.name for path in output_dir.glob("*.csv")} == expected_csv
    assert {path.name for path in output_dir.glob("*.json")} == expected_json

    source = pd.read_csv(output_dir / "01_source_tracker_export.csv")
    canonical = pd.read_csv(output_dir / "02_canonical_gaze.csv")
    qc = pd.read_csv(output_dir / "04_qc_samples.csv")
    preflight = pd.read_csv(output_dir / "03_import_preflight.csv")
    manifest = json.loads(
        (output_dir / "workflow_manifest.json").read_text(encoding="utf-8")
    )
    contract = json.loads(
        (output_dir / "import_contract.json").read_text(encoding="utf-8")
    )

    assert len(source) == len(canonical) == len(qc)
    assert manifest["source_unchanged"] is True
    assert manifest["row_count_preserved"] is True
    assert manifest["evidence_classification"] == "synthetic_demo_not_empirical_evidence"
    assert manifest["event_model_fitted"] is False
    assert manifest["exclusions_applied"] is False
    assert manifest["adapter_compatibility_is_device_validation"] is False
    assert manifest["native_60hz_validity_claim_created"] is False
    assert manifest["gazepoint_gp3_validity_claim_created"] is False
    assert manifest["duplicate_sample_key_rows_retained"] >= 2
    assert manifest["offscreen_rows_retained"] >= 2
    assert manifest["missing_identity_rows"] == 0

    assert contract["source_columns"]["participant_id"] == "USER_FILE"
    assert contract["source_columns"]["trial_id"] == "MEDIA_ID"
    assert contract["source_columns"]["timestamp"] == "TIME"
    assert contract["source_columns"]["x"] == "BPOGX"
    assert contract["source_columns"]["y"] == "BPOGY"
    assert contract["time_unit"] == "seconds"
    assert contract["timestamp_scale_to_ms"] == 1000.0
    assert contract["coordinate_basis"] == "normalized_screen_fraction"
    assert contract["coordinate_scale_to_pixels"] == {"x": 1920, "y": 1080}
    assert contract["nominal_rate_hz"] == 60.0
    assert contract["observed_cadence_method"].startswith("median positive")

    diagnostics = set(preflight["diagnostic"])
    assert {
        "source_row_count",
        "canonical_row_count",
        "duplicate_sample_key_rows",
        "missing_identity_rows",
        "missing_gaze_rows",
        "offscreen_rows",
        "nominal_rate_hz",
        "observed_cadence_hz",
        "nominal_vs_observed_relative_difference",
    } <= diagnostics

    assert "qc_flag" in qc.columns
    assert "Source table unchanged: yes" in captured.out
    assert "Row count preserved: yes" in captured.out
    assert "import compatibility is not Gazepoint/GP3 or native-60-Hz validation" in captured.out


def test_tracker_import_learning_path_is_discoverable_and_claim_safe() -> None:
    script = _read("examples/07_worked_tracker_import_qc.py")
    guide = _read("docs/worked-tracker-import.md")
    gallery = _read("docs/runnable-examples.md")
    examples_readme = _read("examples/README.md")
    clinic = _read("docs/data-import-clinic.md")
    getting_started = _read("docs/getting-started.md")
    learning_paths = _read("docs/learning-paths.md")
    recipes = _read("docs/research-recipes.md")
    lifecycle = _read("docs/study-lifecycle.md")
    publication = _read("docs/publication-readiness.md")
    homepage = _read("docs/index.md")
    mkdocs = _read("mkdocs.yml")

    for token in (
        'participant_col="USER_FILE"',
        'trial_col="MEDIA_ID"',
        'timestamp_col="TIME"',
        'x_col="BPOGX"',
        'y_col="BPOGY"',
        'time_unit="seconds"',
        'coordinates="normalized"',
        "infer_sampling_rate_hz",
        "ai_flag_anomalies",
        "score_trial_quality",
        "synthetic_demo_not_empirical_evidence",
    ):
        assert token in script

    lower = guide.lower()
    assert "seconds" in lower and "milliseconds" in lower
    assert "normalized" in lower and "pixels" in lower
    assert "duplicate" in lower
    assert "missing identity" in lower
    assert "observed cadence" in lower
    assert "nominal rate" in lower
    assert "not proof of native 60 hz" in lower
    assert "does not establish gazepoint validity" in lower
    assert "does not establish" in lower and "gp3" in lower

    assert "twelve deterministic examples" in gallery
    assert "07_worked_tracker_import_qc.py" in gallery
    assert "worked-tracker-import.md" in gallery
    assert "07_worked_tracker_import_qc.py" in examples_readme

    for page in (
        clinic,
        getting_started,
        learning_paths,
        recipes,
        lifecycle,
        publication,
        homepage,
        mkdocs,
    ):
        assert "worked-tracker-import.md" in page

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
