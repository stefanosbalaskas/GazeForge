"""Regression coverage for the canonical GazeForge tour."""

from __future__ import annotations

import json
import pathlib
import runpy
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_gazeforge_tour_runs_and_preserves_source(tmp_path, monkeypatch, capsys) -> None:
    output_dir = tmp_path / "gazeforge-tour-demo"
    monkeypatch.setattr(
        sys,
        "argv",
        ["00_gazeforge_tour.py", "--output-dir", str(output_dir)],
    )

    runpy.run_path(
        str(ROOT / "examples" / "00_gazeforge_tour.py"),
        run_name="__main__",
    )
    captured = capsys.readouterr()

    expected_csv = {
        "01_source_gaze.csv",
        "02_canonical_gaze.csv",
        "03_qc_samples.csv",
        "04_trial_quality.csv",
        "05_event_samples.csv",
        "06_event_intervals.csv",
        "07_fixation_centroids.csv",
        "08_aoi_definitions.csv",
        "09_fixation_aoi_assignments.csv",
        "10_semantic_scanpaths.csv",
    }
    assert {path.name for path in output_dir.glob("*.csv")} == expected_csv
    assert {path.name for path in output_dir.glob("*.json")} == {
        "provenance.json",
        "workflow_manifest.json",
    }

    source = pd.read_csv(output_dir / "01_source_gaze.csv")
    canonical = pd.read_csv(output_dir / "02_canonical_gaze.csv")
    qc = pd.read_csv(output_dir / "03_qc_samples.csv")
    events = pd.read_csv(output_dir / "05_event_samples.csv")
    manifest = json.loads(
        (output_dir / "workflow_manifest.json").read_text(encoding="utf-8")
    )

    assert len(source) == len(canonical) == len(qc) == len(events) == 240
    assert manifest["source_unchanged"] is True
    assert manifest["sample_row_count_preserved"] is True
    assert manifest["evidence_classification"] == "synthetic_demo_not_empirical_evidence"
    assert manifest["boundaries"] == {
        "synthetic_output_is_empirical_validation": False,
        "qc_flag_is_automatic_exclusion": False,
        "workflow_execution_is_device_validation": False,
        "workflow_execution_is_measurement_validation": False,
        "ivt_demo_establishes_general_event_model_superiority": False,
    }
    assert (
        manifest["next_steps"]["real_tracker_import"]
        == "docs/worked-tracker-import.md"
    )
    assert (
        manifest["next_steps"]["qc_review_and_exclusions"]
        == "docs/qc-review-exclusion-ledger.md"
    )
    assert "GazeForge tour complete" in captured.out
    assert "synthetic/demo only; not empirical validation" in captured.out


def test_tour_is_primary_discovery_route_and_branding_is_shared() -> None:
    readme = _read("README.md")
    tour = _read("docs/gazeforge-tour.md")
    homepage = _read("docs/index.md")
    getting_started = _read("docs/getting-started.md")
    learning_paths = _read("docs/learning-paths.md")
    gallery = _read("docs/runnable-examples.md")
    examples_readme = _read("examples/README.md")
    mkdocs = _read("mkdocs.yml")

    assert "gazeforge-lockup.svg" not in readme
    assert "python-suite-logo" in readme
    assert "docs/gazeforge-tour.md" in readme
    assert "00_gazeforge_tour.py" in readme

    lower = tour.lower()
    for phrase in (
        "gaze samples go in",
        "canonical",
        "qc",
        "eye-event",
        "aoi",
        "scanpath",
        "provenance",
        "qc flag is not an automatic exclusion",
        "not empirical validation evidence",
    ):
        assert phrase in lower

    for page in (
        homepage,
        getting_started,
        learning_paths,
        gallery,
        examples_readme,
        mkdocs,
    ):
        assert "gazeforge-tour" in page

    assert "00_gazeforge_tour.py" in gallery
    assert "00_gazeforge_tour.py" in examples_readme
    assert "sixteen deterministic examples" in gallery

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
