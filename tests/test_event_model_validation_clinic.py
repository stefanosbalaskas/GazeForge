"""Regression tests for the event-model validation clinic and worked example."""

from __future__ import annotations

import json
import pathlib
import runpy
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_worked_event_validation_example_runs_without_figures(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    output_dir = tmp_path / "worked-event-model-validation-demo"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "06_worked_event_model_validation.py",
            "--output-dir",
            str(output_dir),
            "--no-figures",
        ],
    )
    runpy.run_path(
        str(ROOT / "examples" / "06_worked_event_model_validation.py"),
        run_name="__main__",
    )
    captured = capsys.readouterr()

    expected_tables = {
        "01_source_event_samples.csv",
        "02_participant_split_ledger.csv",
        "03_matched_heldout_predictions.csv",
        "04_sample_level_metrics.csv",
        "05_event_level_metrics.csv",
        "06_model_summary.csv",
        "07_calibration_bins.csv",
        "08_confidence_coverage.csv",
        "09_illustrative_abstention_policy.csv",
    }
    assert {path.name for path in output_dir.glob("*.csv")} == expected_tables
    for filename in ("analysis_plan.json", "provenance.json", "workflow_manifest.json"):
        assert (output_dir / filename).is_file()

    manifest = json.loads((output_dir / "workflow_manifest.json").read_text(encoding="utf-8"))
    assert manifest["evidence_classification"] == "synthetic_demo_not_empirical_evidence"
    assert manifest["participant_disjoint_verified"] is True
    assert manifest["matched_test_rows_across_models"] is True
    assert manifest["held_out_unit"] == "participant_id"
    assert manifest["figure_outputs"] == []
    assert manifest["source_unchanged"] is True

    assert "Participant-disjoint folds verified: yes" in captured.out
    assert "Matched held-out rows across models: yes" in captured.out
    assert "Sample-level and event-level metrics exported separately: yes" in captured.out
    assert "Source table unchanged: yes" in captured.out


def test_worked_event_validation_has_zero_participant_overlap_and_matched_rows(tmp_path, monkeypatch) -> None:
    output_dir = tmp_path / "validation"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "06_worked_event_model_validation.py",
            "--output-dir",
            str(output_dir),
            "--no-figures",
        ],
    )
    runpy.run_path(
        str(ROOT / "examples" / "06_worked_event_model_validation.py"),
        run_name="__main__",
    )

    ledger = pd.read_csv(output_dir / "02_participant_split_ledger.csv")
    predictions = pd.read_csv(output_dir / "03_matched_heldout_predictions.csv")
    for fold in sorted(ledger["fold"].unique()):
        train_ids = set(
            ledger.loc[
                (ledger["fold"] == fold) & (ledger["split_role"] == "train"),
                "participant_id",
            ]
        )
        test_ids = set(
            ledger.loc[
                (ledger["fold"] == fold) & (ledger["split_role"] == "test"),
                "participant_id",
            ]
        )
        assert train_ids.isdisjoint(test_ids)
        observed = set(predictions.loc[predictions["validation_fold"] == fold, "participant_id"])
        assert observed == test_ids

        counts = (
            predictions.loc[predictions["validation_fold"] == fold]
            .groupby("comparison_model")["comparison_row_position"]
            .nunique()
        )
        assert counts.nunique() == 1


def test_validation_outputs_keep_estimands_and_probability_policy_separate(tmp_path, monkeypatch) -> None:
    output_dir = tmp_path / "validation"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "06_worked_event_model_validation.py",
            "--output-dir",
            str(output_dir),
            "--no-figures",
        ],
    )
    runpy.run_path(
        str(ROOT / "examples" / "06_worked_event_model_validation.py"),
        run_name="__main__",
    )

    sample = pd.read_csv(output_dir / "04_sample_level_metrics.csv")
    events = pd.read_csv(output_dir / "05_event_level_metrics.csv")
    calibration = pd.read_csv(output_dir / "07_calibration_bins.csv")
    coverage = pd.read_csv(output_dir / "08_confidence_coverage.csv")
    policy = pd.read_csv(output_dir / "09_illustrative_abstention_policy.csv")

    assert {"accuracy", "balanced_accuracy", "macro_f1"} <= set(sample)
    assert {"event_f1", "event_mean_matched_iou"} <= set(events)
    assert set(calibration["model"]) == {"RandomForest", "ContextMLP"}
    assert set(coverage["model"]) == {"RandomForest", "ContextMLP"}
    assert set(policy["policy_status"]) == {"illustrative_not_universal"}
    assert set(policy["illustrative_confidence_threshold"]) == {0.8}


def test_validation_clinic_and_cookbook_preserve_claim_boundaries() -> None:
    clinic = _read("docs/event-model-validation-clinic.md").lower()
    cookbook = _read("docs/validation-reporting-cookbook.md").lower()

    for phrase in (
        "participant-disjoint",
        "source-token-disjoint",
        "sample-level",
        "event-level",
        "calibration",
        "coverage",
        "native",
        "derived",
        "synthetic",
    ):
        assert phrase in clinic
        assert phrase in cookbook

    assert "source-token-disjoint" in clinic and "not participant-disjoint" in clinic
    assert "derived 60 hz evidence remains derived" in clinic
    assert "not a universal confidence cutoff" in cookbook
    assert "synthetic_demo_not_empirical_evidence" in cookbook


def test_validation_surfaces_are_first_class_without_expanding_homepage_hero() -> None:
    mkdocs = _read("mkdocs.yml")
    homepage = _read("docs/index.md")
    recipes = _read("docs/research-recipes.md")
    methods = _read("docs/methods-overview.md")
    lifecycle = _read("docs/study-lifecycle.md")
    readiness = _read("docs/publication-readiness.md")
    runnable = _read("docs/runnable-examples.md")
    examples_readme = _read("examples/README.md")

    assert "event-model-validation-clinic.md" in mkdocs
    assert "validation-reporting-cookbook.md" in mkdocs
    for page in (recipes, methods, lifecycle, readiness, runnable, examples_readme, homepage):
        assert "event-model-validation-clinic.md" in page

    assert "06_worked_event_model_validation.py" in runnable
    assert "06_worked_event_model_validation.py" in examples_readme
    assert "validation-reporting-cookbook.md" in readiness

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
