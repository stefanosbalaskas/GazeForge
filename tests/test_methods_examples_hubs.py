"""Regression tests for task-oriented methods and runnable-example navigation."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_methods_overview_is_first_methods_route_and_groups_real_pages() -> None:
    mkdocs = _read("mkdocs.yml")
    methods = _read("docs/methods-overview.md")

    overview = "      - Overview: methods-overview.md"
    adapters = "      - Adapters & validation: adapters-validation.md"
    assert overview in mkdocs
    assert mkdocs.index(overview) < mkdocs.index(adapters)

    for target in (
        "adapters-validation.md",
        "motion-quality-gating.md",
        "temporal-models.md",
        "event-model-validation-clinic.md",
        "event-level-evaluation.md",
        "dynamic-aois.md",
        "grounded-sam2-backend.md",
        "research-workflows.md",
        "hierarchical-location-scale.md",
        "full-covariance-location-random-slope-scale.md",
        "validation-evidence-guide.md",
        "validation-reporting-cookbook.md",
        "reproducible-reporting.md",
    ):
        assert target in methods


def test_examples_gallery_covers_all_real_scripts_and_exact_commands() -> None:
    page = _read("docs/runnable-examples.md")

    scripts = (
        "01_synthetic_qc.py",
        "02_ivt_baseline.py",
        "03_visual_diagnostics.py",
        "end_to_end_research_workflow.py",
        "04_worked_advertising_study.py",
        "05_worked_dynamic_aoi_study.py",
        "06_worked_event_model_validation.py",
        "07_worked_tracker_import_qc.py",
    )
    for script in scripts:
        assert script in page
        assert f"blob/main/examples/{script}" in page

    assert "eight deterministic examples" in page
    assert "python examples/01_synthetic_qc.py" in page
    assert "python examples/02_ivt_baseline.py" in page
    assert "python examples/03_visual_diagnostics.py --output-dir visual-demo" in page
    assert "--output-dir end-to-end-research-demo" in page
    assert "--no-figures" in page
    assert "python examples/04_worked_advertising_study.py" in page
    assert "--output-dir worked-advertising-demo" in page
    assert "python examples/05_worked_dynamic_aoi_study.py" in page
    assert "--output-dir worked-dynamic-aoi-demo" in page
    assert "python examples/06_worked_event_model_validation.py" in page
    assert "--output-dir worked-event-model-validation-demo" in page
    assert "python examples/07_worked_tracker_import_qc.py" in page
    assert "--output-dir worked-tracker-import-qc-demo" in page


def test_examples_gallery_names_real_outputs_and_preserves_demo_boundary() -> None:
    page = _read("docs/runnable-examples.md")

    for output in (
        "01_qc_timeline.png",
        "06_dynamic_aoi.png",
        "01_source_gaze.csv",
        "10_semantic_scanpaths.csv",
        "01_source_fixations.csv",
        "06_assignment_summary.csv",
        "05_interpolation_audit.csv",
        "01_source_event_samples.csv",
        "02_participant_split_ledger.csv",
        "03_matched_heldout_predictions.csv",
        "04_sample_level_metrics.csv",
        "05_event_level_metrics.csv",
        "07_calibration_bins.csv",
        "08_confidence_coverage.csv",
        "09_illustrative_abstention_policy.csv",
        "01_source_tracker_export.csv",
        "02_canonical_gaze.csv",
        "03_import_preflight.csv",
        "04_qc_samples.csv",
        "05_trial_quality.csv",
        "import_contract.json",
        "analysis_plan.json",
        "provenance.json",
        "workflow_manifest.json",
        "figures/03_scanpath.png",
        "figures/01_calibration.png",
        "figures/02_confidence_coverage.png",
    ):
        assert output in page

    for aoi in ("`brand`", "`claim`", "`disclosure`", "`product`"):
        assert aoi in page

    lower = page.lower()
    assert "not empirical validation evidence" in lower
    assert "native-device" in lower
    assert "native 60 hz" in lower
    assert "gazepoint" in lower
    assert "gp3" in lower
    assert "source table remains unchanged" in lower
    assert "row count" in lower
    assert "duplicate" in lower
    assert "observed cadence" in lower
    assert "no extrapolation" in lower
    assert "participant-disjoint" in lower
    assert "matched held-out rows" in lower
    assert "synthetic_demo_not_empirical_evidence" in page


def test_new_hubs_are_discoverable_without_expanding_homepage_hero() -> None:
    mkdocs = _read("mkdocs.yml")
    homepage = _read("docs/index.md")
    getting_started = _read("docs/getting-started.md")
    learning_paths = _read("docs/learning-paths.md")
    examples_readme = _read("examples/README.md")

    assert "      - Runnable examples: runnable-examples.md" in mkdocs
    assert "worked-tracker-import.md" in mkdocs
    assert "event-model-validation-clinic.md" in mkdocs
    assert "methods-overview.md" in homepage
    assert "runnable-examples.md" in homepage
    assert "study-lifecycle.md" in homepage
    assert "worked-advertising-study.md" in homepage
    assert "worked-tracker-import.md" in homepage
    assert "publication-readiness.md" in homepage
    assert "event-model-validation-clinic.md" in homepage
    assert "runnable-examples.md" in getting_started
    assert "worked-tracker-import.md" in getting_started
    assert "runnable-examples.md" in learning_paths
    assert "worked-tracker-import.md" in learning_paths
    assert "event-model-validation-clinic.md" in learning_paths
    assert "../docs/runnable-examples.md" in examples_readme
    assert "04_worked_advertising_study.py" in examples_readme
    assert "05_worked_dynamic_aoi_study.py" in examples_readme
    assert "06_worked_event_model_validation.py" in examples_readme
    assert "07_worked_tracker_import_qc.py" in examples_readme

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3


def test_methods_page_keeps_empirical_evidence_boundaries_explicit() -> None:
    methods = _read("docs/methods-overview.md").lower()

    assert "derived lower-rate evidence remains derived" in methods
    assert "not participant-disjoint" in methods
    assert "task-agnostic" in methods
    assert "bounded partial public-derivative evidence" in methods
    assert "native 60 hz" in methods
    assert "gazepoint gp3" in methods
