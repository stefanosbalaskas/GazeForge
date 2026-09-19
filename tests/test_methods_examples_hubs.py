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
        "00_gazeforge_tour.py",
        "01_synthetic_qc.py",
        "02_ivt_baseline.py",
        "03_visual_diagnostics.py",
        "end_to_end_research_workflow.py",
        "04_worked_advertising_study.py",
        "05_worked_dynamic_aoi_study.py",
        "06_worked_event_model_validation.py",
        "07_worked_tracker_import_qc.py",
        "08_worked_qc_review_ledger.py",
        "09_worked_research_evidence_bundle.py",
        "10_worked_analysis_handoff.py",
        "11_worked_manuscript_reporting_bundle.py",
        "12_worked_measurement_interpretation_audit.py",
        "13_worked_estimand_preregistration.py",
        "14_worked_reviewer_replication_bundle.py",
        "15_worked_sensitivity_robustness_audit.py",
        "16_worked_denominator_exposure_audit.py",
    )
    for script in scripts:
        assert script in page
        assert f"blob/main/examples/{script}" in page

    assert "eighteen deterministic examples" in page
    assert "python examples/00_gazeforge_tour.py" in page
    assert "--output-dir gazeforge-tour-demo" in page
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
    assert "python examples/08_worked_qc_review_ledger.py" in page
    assert "--output-dir worked-qc-review-ledger-demo" in page
    assert "python examples/09_worked_research_evidence_bundle.py" in page
    assert "--output-dir worked-research-evidence-bundle" in page
    assert "python examples/10_worked_analysis_handoff.py" in page
    assert "--output-dir worked-analysis-handoff-demo" in page
    assert "python examples/11_worked_manuscript_reporting_bundle.py" in page
    assert "--output-dir worked-manuscript-reporting-bundle" in page
    assert "python examples/12_worked_measurement_interpretation_audit.py" in page
    assert "--output-dir worked-measurement-interpretation-audit" in page
    assert "python examples/13_worked_estimand_preregistration.py" in page
    assert "--output-dir worked-estimand-preregistration" in page
    assert "python examples/14_worked_reviewer_replication_bundle.py" in page
    assert "--output-dir worked-reviewer-replication-bundle" in page
    assert "python examples/15_worked_sensitivity_robustness_audit.py" in page
    assert "python examples/16_worked_denominator_exposure_audit.py" in page
    assert "--output-dir worked-denominator-exposure-audit" in page
    assert "--output-dir worked-sensitivity-robustness-audit" in page


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
        "01_canonical_source.csv",
        "02_pre_review_qc_samples.csv",
        "04_decision_criteria.csv",
        "05_sample_review_ledger.csv",
        "06_trial_review_ledger.csv",
        "07_participant_review_ledger.csv",
        "08_exclusion_flow.csv",
        "09_reviewed_sample_status.csv",
        "10_primary_analysis_rows.csv",
        "11_exploratory_sensitivity.csv",
        "import_contract.json",
        "analysis_plan.json",
        "provenance.json",
        "workflow_manifest.json",
        "source_contract.json",
        "artifact_index.csv",
        "07_primary_analysis_rows.csv",
        "13_semantic_scanpaths.csv",
        "figures/03_scanpath.png",
        "figures/01_calibration.png",
        "figures/02_confidence_coverage.png",
        "03_trial_design_and_coverage.csv",
        "04_trial_aoi_metrics.csv",
        "05_trial_event_metrics.csv",
        "06_descriptive_participant_condition_summary.csv",
        "07_model_handoff_dictionary.csv",
        "analysis_handoff_plan.json",
        "figures/01_aoi_dwell_by_condition.png",
        "figures/02_trial_coverage_status.png",
        "methods_record.json",
        "denominator_flow.csv",
        "artifact_citation_table.csv",
        "reporting_boundaries.json",
        "software_identity.json",
        "methods_example.md",
        "results_example.md",
        "archive_readme.md",
        "reporting_manifest.json",
        "01_claim_registry.csv",
        "02_measurement_interpretation_matrix.csv",
        "03_validity_threats.csv",
        "04_sensitivity_plan.csv",
        "05_reporting_language.csv",
        "interpretation_audit.json",
        "01_outcome_registry.csv",
        "02_estimand_registry.csv",
        "03_contrast_registry.csv",
        "04_sensitivity_registry.csv",
        "05_deviation_registry.csv",
        "06_reporting_plan.csv",
        "preregistration_manifest.json",
        "01_claim_artifact_matrix.csv",
        "02_rerun_plan.csv",
        "03_reproducibility_checklist.csv",
        "04_limitations_register.csv",
        "05_api_route_map.csv",
        "artifact_hash_ledger.csv",
        "replication_manifest.json",
        "01_sensitivity_registry.csv",
        "02_executed_conditions.csv",
        "03_result_comparison.csv",
        "04_deviation_ledger.csv",
        "05_interpretation_matrix.csv",
        "06_reporting_language.csv",
        "sensitivity_manifest.json",
        "01_observation_status_registry.csv",
        "02_denominator_exposure_ledger.csv",
        "03_count_rate_audit.csv",
        "04_proportion_dwell_audit.csv",
        "05_latency_censoring_audit.csv",
        "06_reconciliation_flow.csv",
        "08_api_route_map.csv",
        "denominator_exposure_manifest.json",
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
    assert "qc flag" in lower
    assert "automatic exclusion" in lower
    assert "prespecified" in lower
    assert "exploratory" in lower
    assert "synthetic_demo_not_empirical_evidence" in page


def test_new_hubs_are_discoverable_without_expanding_homepage_hero() -> None:
    mkdocs = _read("mkdocs.yml")
    homepage = _read("docs/index.md")
    getting_started = _read("docs/getting-started.md")
    learning_paths = _read("docs/learning-paths.md")
    examples_readme = _read("examples/README.md")

    assert "      - Runnable examples: runnable-examples.md" in mkdocs
    assert "gazeforge-tour.md" in mkdocs
    assert "worked-tracker-import.md" in mkdocs
    assert "qc-review-exclusion-ledger.md" in mkdocs
    assert "event-model-validation-clinic.md" in mkdocs
    assert "gazeforge-tour.md" in homepage
    assert "methods-overview.md" in homepage
    assert "runnable-examples.md" in homepage
    assert "study-lifecycle.md" in homepage
    assert "worked-advertising-study.md" in homepage
    assert "worked-tracker-import.md" in homepage
    assert "publication-readiness.md" in homepage
    assert "reviewer-replication-handoff.md" in homepage
    assert "sensitivity-robustness-clinic.md" in homepage
    assert "denominator-exposure-censoring.md" in homepage
    assert "event-model-validation-clinic.md" in homepage
    assert "gazeforge-tour.md" in getting_started
    assert "runnable-examples.md" in getting_started
    assert "worked-tracker-import.md" in getting_started
    assert "gazeforge-tour.md" in learning_paths
    assert "runnable-examples.md" in learning_paths
    assert "worked-tracker-import.md" in learning_paths
    assert "event-model-validation-clinic.md" in learning_paths
    assert "../docs/runnable-examples.md" in examples_readme
    assert "00_gazeforge_tour.py" in examples_readme
    assert "04_worked_advertising_study.py" in examples_readme
    assert "05_worked_dynamic_aoi_study.py" in examples_readme
    assert "06_worked_event_model_validation.py" in examples_readme
    assert "07_worked_tracker_import_qc.py" in examples_readme
    assert "08_worked_qc_review_ledger.py" in examples_readme
    assert "09_worked_research_evidence_bundle.py" in examples_readme
    assert "10_worked_analysis_handoff.py" in examples_readme
    assert "../docs/analysis-handoff.md" in examples_readme
    assert "11_worked_manuscript_reporting_bundle.py" in examples_readme
    assert "../docs/reporting-clinic.md" in examples_readme
    assert "12_worked_measurement_interpretation_audit.py" in examples_readme
    assert "../docs/measurement-interpretation.md" in examples_readme
    assert "13_worked_estimand_preregistration.py" in examples_readme
    assert "../docs/estimand-preregistration.md" in examples_readme
    assert "14_worked_reviewer_replication_bundle.py" in examples_readme
    assert "../docs/reviewer-replication-handoff.md" in examples_readme
    assert "15_worked_sensitivity_robustness_audit.py" in examples_readme
    assert "16_worked_denominator_exposure_audit.py" in examples_readme
    assert "../docs/denominator-exposure-censoring.md" in examples_readme
    assert "../docs/sensitivity-robustness-clinic.md" in examples_readme

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
