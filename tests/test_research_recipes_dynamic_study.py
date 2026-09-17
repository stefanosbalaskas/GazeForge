"""Regression tests for task-first research recipes and dynamic-AOI worked study."""

from __future__ import annotations

import json
import pathlib
import runpy
import sys

import pandas as pd

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (_REPO_ROOT / relative).read_text(encoding="utf-8")


def test_dynamic_aoi_worked_example_runs_without_figures(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    output_dir = tmp_path / "worked-dynamic-aoi-demo"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "05_worked_dynamic_aoi_study.py",
            "--output-dir",
            str(output_dir),
            "--no-figures",
        ],
    )
    runpy.run_path(
        str(_REPO_ROOT / "examples" / "05_worked_dynamic_aoi_study.py"),
        run_name="__main__",
    )
    captured = capsys.readouterr()

    expected_tables = {
        "01_source_fixations.csv",
        "02_dynamic_aoi_keyframes.csv",
        "03_fixation_dynamic_aoi_assignments.csv",
        "04_semantic_scanpaths.csv",
        "05_interpolation_audit.csv",
        "06_assignment_summary.csv",
    }
    assert {path.name for path in output_dir.glob("*.csv")} == expected_tables
    for filename in ("analysis_plan.json", "provenance.json", "workflow_manifest.json"):
        assert (output_dir / filename).is_file()

    manifest = json.loads((output_dir / "workflow_manifest.json").read_text(encoding="utf-8"))
    assert manifest["evidence_classification"] == "synthetic_demo_not_empirical_evidence"
    assert manifest["source_unchanged"] is True
    assert manifest["no_extrapolation_verified"] is True
    assert manifest["max_interpolation_gap_ms"] == 1000.0
    assert manifest["figure_outputs"] == []

    assignments = pd.read_csv(output_dir / "03_fixation_dynamic_aoi_assignments.csv")
    outside = assignments["probe"].isin({"before_track_range", "after_track_range"})
    assert assignments.loc[outside, "aoi_id"].isna().all()
    assert "interpolated" in set(assignments.loc[~outside, "aoi_source"].dropna())

    interpolation = pd.read_csv(output_dir / "05_interpolation_audit.csv")
    unresolved = interpolation.loc[interpolation["timestamp_ms"].isin([-100.0, 2100.0])]
    assert not unresolved["resolved"].any()

    assert "Bounded interpolation exercised: yes" in captured.out
    assert "No extrapolation verified: yes" in captured.out
    assert "Source table unchanged: yes" in captured.out


def test_research_recipes_cover_study_tasks_and_boundaries() -> None:
    recipes = _read("docs/research-recipes.md")
    for phrase in (
        "Static-stimulus semantic AOIs",
        "Dynamic/video AOIs",
        "Real tracker import",
        "Transparent event baseline",
        "Learned event-model validation and calibration",
        "Scanpaths, transitions, and motifs",
        "Manuscript and archive handoff",
    ):
        assert phrase in recipes

    for boundary in (
        "does not extrapolate",
        "import compatibility",
        "device validation",
        "participant-disjoint",
        "source-token-disjoint",
        "native 60 Hz",
        "derived 60 Hz",
    ):
        assert boundary in recipes


def test_study_design_templates_force_explicit_research_metadata() -> None:
    templates = _read("docs/study-design-templates.md")
    for field in (
        "native_sampling_rate_hz",
        "observed_timestamp_cadence_hz",
        "screen_width_px",
        "screen_height_px",
        "participant_identity_field",
        "trial_identity_field",
        "held_out_unit",
        "reference_label_source",
        "analysis_rate_status",
        "source_fingerprint",
        "software_commit",
    ):
        assert field in templates

    for section in (
        "Preregistration / analysis-plan record",
        "Acquisition metadata record",
        "QC and exclusion protocol",
        "AOI provenance and review record",
        "Validation split and reference-label record",
        "Native-versus-derived sampling statement",
        "Reproducibility / archive manifest",
        "Methods minimum record",
    ):
        assert section in templates


def test_reporting_examples_preserve_claim_strength() -> None:
    reporting = _read("docs/reproducible-reporting.md")
    for contrast in (
        "Import compatibility",
        "QC flags",
        "Software demo",
        "Sample-level versus event-level",
        "Calibration versus correctness",
    ):
        assert contrast in reporting

    assert "source-token-disjoint" in reporting
    assert "participant-disjoint" in reporting
    assert "derived 60 Hz" in reporting
    assert "native 60 Hz" in reporting


def test_new_site_surfaces_are_discoverable_without_expanding_hero() -> None:
    mkdocs = _read("mkdocs.yml")
    index = _read("docs/index.md")
    learning = _read("docs/learning-paths.md")
    runnable = _read("docs/runnable-examples.md")
    examples_readme = _read("examples/README.md")

    for page in (
        "research-recipes.md",
        "worked-dynamic-aoi-study.md",
        "study-design-templates.md",
    ):
        assert page in mkdocs

    for destination in (
        "research-recipes.md",
        "worked-dynamic-aoi-study.md",
        "study-design-templates.md",
    ):
        assert destination in index
        assert destination in learning

    assert "05_worked_dynamic_aoi_study.py" in runnable
    assert "05_worked_dynamic_aoi_study.py" in examples_readme
    assert "benchmark-guide.md" in index
    assert "validation-evidence-guide.md" in index

    hero = index.split('<div class="gf-hero-actions" markdown>', 1)[1].split("</div>", 1)[0]
    assert hero.count("{ .md-button") == 3
