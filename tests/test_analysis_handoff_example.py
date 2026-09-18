from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/10_worked_analysis_handoff.py"


def test_worked_analysis_handoff_preserves_units_missingness_and_denominators(
    tmp_path: Path,
) -> None:
    output = tmp_path / "handoff"
    subprocess.run(
        [sys.executable, str(EXAMPLE), "--output-dir", str(output)],
        check=True,
        cwd=ROOT,
    )

    expected_files = {
        "README.md",
        "upstream_reference.json",
        "01_reviewed_fixation_assignments.csv",
        "02_reviewed_event_intervals.csv",
        "03_trial_design_and_coverage.csv",
        "04_trial_aoi_metrics.csv",
        "05_trial_event_metrics.csv",
        "06_descriptive_participant_condition_summary.csv",
        "07_model_handoff_dictionary.csv",
        "08_aoi_definitions.csv",
        "analysis_handoff_plan.json",
        "provenance.json",
        "workflow_manifest.json",
        "figures/01_aoi_dwell_by_condition.png",
        "figures/02_trial_coverage_status.png",
    }
    actual_files = {
        str(path.relative_to(output)).replace("\\", "/")
        for path in output.rglob("*")
        if path.is_file()
    }
    assert actual_files == expected_files
    for figure in (
        output / "figures/01_aoi_dwell_by_condition.png",
        output / "figures/02_trial_coverage_status.png",
    ):
        assert figure.stat().st_size > 0

    design = pd.read_csv(output / "03_trial_design_and_coverage.csv")
    aoi = pd.read_csv(output / "04_trial_aoi_metrics.csv")
    event = pd.read_csv(output / "05_trial_event_metrics.csv")
    descriptive = pd.read_csv(
        output / "06_descriptive_participant_condition_summary.csv"
    )

    assert len(design) == 20
    assert len(aoi) == 80
    assert len(event) == 40
    assert not aoi.duplicated(["participant_id", "trial_id", "aoi_id"]).any()
    assert not event.duplicated(["participant_id", "trial_id", "event_label"]).any()
    assert {
        "observed_gaze_ms",
        "aoi_observable_ms",
        "coverage_fraction",
        "metric_status",
        "latency_status",
    } <= set(aoi.columns)
    assert {"observed_gaze_ms", "coverage_fraction", "metric_status"} <= set(
        event.columns
    )

    true_zero = aoi.loc[
        (aoi["participant_id"] == "P002")
        & (aoi["trial_id"] == "T02")
        & (aoi["aoi_id"] == "disclosure")
    ].iloc[0]
    assert true_zero["metric_status"] == "observed_zero"
    assert true_zero["n_fixations"] == 0
    assert true_zero["dwell_ms"] == 0
    assert true_zero["latency_status"] == "right_censored_no_fixation"
    assert true_zero["latency_censor_time_ms"] == 3000.0

    absent = aoi.loc[
        (aoi["participant_id"] == "P001")
        & (aoi["trial_id"] == "T01")
        & (aoi["aoi_id"] == "disclosure")
    ].iloc[0]
    assert absent["metric_status"] == "not_present_by_design"
    assert pd.isna(absent["n_fixations"])
    assert pd.isna(absent["dwell_ms"])
    assert pd.isna(absent["first_fixation_latency_ms"])

    missing = aoi.loc[
        (aoi["participant_id"] == "P005") & (aoi["trial_id"] == "T04")
    ]
    assert len(missing) == 4
    assert set(missing["metric_status"]) == {"missing_trial"}
    assert missing["dwell_ms"].isna().all()
    assert missing["n_fixations"].isna().all()

    assert set(descriptive["analysis_role"]) == {
        "descriptive_only_not_inferential_input"
    }

    manifest = json.loads((output / "workflow_manifest.json").read_text(encoding="utf-8"))
    assert manifest["evidence_classification"] == "synthetic_demo_not_empirical_evidence"
    assert manifest["missing_values_converted_to_zero"] is False
    assert manifest["unobserved_aoi_exposure_created"] is False
    assert manifest["descriptive_summary_is_model_input"] is False
    assert manifest["statistical_model_fitted"] is False
    assert manifest["automatic_model_selection_performed"] is False
    assert manifest["failed_model_convergence_accepted"] is False
    assert manifest["device_validity_claim_created"] is False
    assert manifest["psychological_state_claim_created"] is False


def test_analysis_handoff_docs_are_discoverable_and_keep_statistical_boundary() -> None:
    guide = (ROOT / "docs/analysis-handoff.md").read_text(encoding="utf-8")
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    homepage = (ROOT / "docs/index.md").read_text(encoding="utf-8")
    chooser = (ROOT / "docs/method-chooser.md").read_text(encoding="utf-8")
    dictionary = (ROOT / "docs/artifact-dictionary.md").read_text(encoding="utf-8")
    recipes = (ROOT / "docs/research-recipes.md").read_text(encoding="utf-8")
    runnable = (ROOT / "docs/runnable-examples.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for page in (mkdocs, homepage, chooser, dictionary, recipes, runnable, readme):
        assert "analysis-handoff" in page

    lower = guide.lower()
    for phrase in (
        "missing is not zero",
        "pseudoreplication",
        "specialist statistical",
        "failed convergence",
        "right-censored",
        "descriptive",
        "inferential unit",
        "no statistical model is fitted",
    ):
        assert phrase in lower

    assert "10_worked_analysis_handoff.py" in guide
    assert "10_worked_analysis_handoff.py" in runnable
    assert "04_trial_aoi_metrics.csv" in guide
    assert "05_trial_event_metrics.csv" in guide

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
