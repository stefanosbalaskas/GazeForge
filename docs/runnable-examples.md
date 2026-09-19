# Runnable examples

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Runnable reference</strong> · Choose a deterministic example, exact command, and expected output bundle.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>


The repository contains **twenty deterministic examples** that move from a small
installation check to complete reviewable workflows, tracker import/QC,
human-reviewed exclusion decisions, domain-shaped studies, leakage-safe
event-model validation, and an explicit statistical-analysis handoff. Use this page to choose a script, inspect its exact
artifacts, and continue to the corresponding research guide.

!!! warning "Demo output is not empirical validation evidence"
    Every example on this page uses synthetic/demo inputs. The scripts demonstrate software behaviour, composition, plotting, provenance, reporting, and audit structure. They are **not empirical validation evidence** and do not establish native-device, native 60 Hz, Gazepoint, GP3, event-model, calibration, or measurement validity.

!!! tip "Already have a tracker export?"
    Start with [Worked tracker import and QC](worked-tracker-import.md), use the [Real-data import clinic](data-import-clinic.md) for source variants and troubleshooting, then continue to [QC review and exclusion ledger](qc-review-exclusion-ledger.md) before applying exclusions. These routes keep source identity, units, cadence, QC evidence, human review, denominators, and analysis derivatives separate.

## At a glance

| Example | Install | Run | Main output |
| --- | --- | --- | --- |
| **GazeForge tour** | base | `python examples/00_gazeforge_tour.py --output-dir gazeforge-tour-demo` | ten core CSVs + provenance/manifest |
| **Synthetic QC** | base | `python examples/01_synthetic_qc.py` | printed trial QC |
| **Transparent I-VT** | base | `python examples/02_ivt_baseline.py` | event counts/transitions |
| **Visual diagnostics** | `.[plot]` | `python examples/03_visual_diagnostics.py --output-dir visual-demo` | six PNG diagnostics |
| **End-to-end workflow** | base with `--no-figures` | `python examples/end_to_end_research_workflow.py --output-dir end-to-end-research-demo` | ten CSVs + provenance |
| **Worked advertising/interface study** | base | `python examples/04_worked_advertising_study.py --output-dir worked-advertising-demo` | study-shaped bundle |
| **Worked dynamic-AOI study** | base with `--no-figures` | `python examples/05_worked_dynamic_aoi_study.py --output-dir worked-dynamic-aoi-demo` | dynamic-AOI audit bundle |
| **Worked event-model validation** | base with `--no-figures` | `python examples/06_worked_event_model_validation.py --output-dir worked-event-model-validation-demo` | held-out validation bundle |
| **Worked tracker import + QC** | base | `python examples/07_worked_tracker_import_qc.py --output-dir worked-tracker-import-qc-demo` | import/QC evidence bundle |
| **QC review + exclusion ledger** | base | `python examples/08_worked_qc_review_ledger.py --output-dir worked-qc-review-ledger-demo` | criteria + review/exclusion ledgers |
| **Research evidence bundle** | base | `python examples/09_worked_research_evidence_bundle.py --output-dir worked-research-evidence-bundle` | archive-shaped source/QC/review/analysis/provenance bundle |
| **Statistical analysis handoff** | base with `--no-figures` | `python examples/10_worked_analysis_handoff.py --output-dir worked-analysis-handoff-demo` | trial × AOI/event tables + handoff metadata + optional diagnostics |
| **Manuscript/reporting bundle** | base | `python examples/11_worked_manuscript_reporting_bundle.py --output-dir worked-manuscript-reporting-bundle` | reporting-only Methods/Results/boundary/citation derivatives |
| **Measurement/interpretation audit** | base | `python examples/12_worked_measurement_interpretation_audit.py --output-dir worked-measurement-interpretation-audit` | claim registry + measure/validity/sensitivity/reporting audit |
| **Outcome/estimand preregistration** | base | `python examples/13_worked_estimand_preregistration.py --output-dir worked-estimand-preregistration` | outcome + estimand + contrast + sensitivity + deviation registries |
| **Reviewer/replication handoff** | base | `python examples/14_worked_reviewer_replication_bundle.py --output-dir worked-reviewer-replication-bundle` | claim-artifact + rerun + limitations + API + hash audit bundle |
| **Sensitivity/robustness audit** | base | `python examples/15_worked_sensitivity_robustness_audit.py --output-dir worked-sensitivity-robustness-audit` | registered/executed variants + denominator/result comparison + deviations + reporting guidance |
| **Denominator/exposure audit** | base | `python examples/16_worked_denominator_exposure_audit.py --output-dir worked-denominator-exposure-audit` | observation-status + exposure/rate/proportion/censoring reconciliation bundle |
| **Model diagnostics audit** | base | `python examples/17_worked_model_diagnostics_audit.py --output-dir worked-model-diagnostics-audit` | fit registry + diagnostic status + interpretation gate + replacement linkage |
| **Missing-data assumptions audit** | base | `python examples/18_worked_missing_data_assumptions_audit.py --output-dir worked-missing-data-assumptions-audit` | source registry + mechanism questions + non-selecting treatment/sensitivity/reporting handoff |

## 0 · GazeForge tour

**Start here if you are not yet sure what GazeForge does.**

```bash
python examples/00_gazeforge_tour.py --output-dir gazeforge-tour-demo
```

This is the shortest package-wide demonstration. It moves one deterministic gaze
table through canonicalisation, non-destructive QC, transparent I-VT events,
researcher-defined AOIs, semantic scanpaths, and provenance. It verifies source
immutability and sample-row preservation and writes ten CSV tables plus
`provenance.json` and `workflow_manifest.json`.

The example is `synthetic_demo_not_empirical_evidence`: a QC flag is not an
automatic exclusion, successful execution is not device or measurement validity,
and the I-VT demonstration is not evidence of general model superiority.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/00_gazeforge_tour.py)
· [Read the GazeForge tour](gazeforge-tour.md)

## 1 · Synthetic QC

```bash
python examples/01_synthetic_qc.py
```

The smallest base-install example simulates gaze, canonicalises it, adds
non-destructive anomaly flags, and prints trial-level quality summaries.
No source rows are automatically deleted.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/01_synthetic_qc.py)
· [Read the QC tutorial](tutorial-synthetic-qc.md)

## 2 · Transparent I-VT baseline

```bash
python examples/02_ivt_baseline.py
```

The script applies an inspectable pixel-velocity I-VT baseline with an explicit
threshold and prints event-class counts plus first-trial transitions. The
threshold is an example setting, not a universal physiological cutoff.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/02_ivt_baseline.py)
· [Read the I-VT tutorial](tutorial-ivt-baseline.md)

## 3 · Visual diagnostics

```bash
python -m pip install -e ".[plot]"
python examples/03_visual_diagnostics.py --output-dir visual-demo
```

The script writes exactly six synthetic/demo figures:

```text
01_qc_timeline.png
02_event_probabilities.png
03_calibration.png
04_aoi_overlay.png
05_scanpath.png
06_dynamic_aoi.png
```

<div class="gf-preview-grid">
  <a class="gf-preview-card" href="visual-diagnostics/">
    <img src="assets/figures/synthetic-qc-diagnostics.svg" alt="Synthetic demo quality-control timeline with flagged samples." loading="lazy">
    <span class="gf-preview-kicker">Review quality</span>
    <strong>QC timeline</strong>
    <span>Inspect anomaly flags without treating them as automatic exclusions.</span>
  </a>
  <a class="gf-preview-card" href="visual-diagnostics/">
    <img src="assets/figures/synthetic-event-diagnostics.svg" alt="Synthetic demo event probability and calibration diagnostics." loading="lazy">
    <span class="gf-preview-kicker">Review predictions</span>
    <strong>Probability &amp; calibration</strong>
    <span>Keep confidence and calibration visible rather than reducing output to a label.</span>
  </a>
  <a class="gf-preview-card" href="visual-diagnostics/">
    <img src="assets/figures/synthetic-aoi-scanpath.svg" alt="Synthetic demo semantic AOIs with a numbered fixation scanpath." loading="lazy">
    <span class="gf-preview-kicker">Review structure</span>
    <strong>AOIs &amp; scanpaths</strong>
    <span>Inspect geometry, semantic labels, fixation order, and sequence structure.</span>
  </a>
</div>

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/03_visual_diagnostics.py)
· [Read the visual diagnostics guide](visual-diagnostics.md)

## 4 · Complete end-to-end research workflow

```bash
python examples/end_to_end_research_workflow.py \
  --output-dir end-to-end-research-demo
```

Without figures:

```bash
python examples/end_to_end_research_workflow.py \
  --output-dir end-to-end-research-demo \
  --no-figures
```

The workflow writes:

```text
01_source_gaze.csv
02_canonical_gaze.csv
03_qc_samples.csv
04_trial_quality.csv
05_event_samples.csv
06_event_intervals.csv
07_fixation_centroids.csv
08_aoi_definitions.csv
09_fixation_aoi_assignments.csv
10_semantic_scanpaths.csv
provenance.json
workflow_manifest.json
figures/03_scanpath.png
```

The script verifies that the **source table remains unchanged**, that sample row count is preserved through non-destructive stages, and records `synthetic_demo_not_empirical_evidence`.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/end_to_end_research_workflow.py)
· [Read the practical workflow](practical-workflow.md)

## 5 · Worked advertising / interface study

```bash
python examples/04_worked_advertising_study.py \
  --output-dir worked-advertising-demo
```

The demonstration predeclares `brand`, `claim`, `disclosure`, and `product`
AOIs and writes the same ten study-shaped tables plus `analysis_plan.json`,
`provenance.json`, and `workflow_manifest.json`. Its outputs are software-demo
artifacts, not estimates of real consumer effects.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/04_worked_advertising_study.py)
· [Read the worked-study guide](worked-advertising-study.md)

## 6 · Worked dynamic-AOI study

```bash
python examples/05_worked_dynamic_aoi_study.py \
  --output-dir worked-dynamic-aoi-demo \
  --no-figures
```

The deterministic moving-stimulus example writes:

```text
01_source_fixations.csv
02_dynamic_aoi_keyframes.csv
03_fixation_dynamic_aoi_assignments.csv
04_semantic_scanpaths.csv
05_interpolation_audit.csv
06_assignment_summary.csv
analysis_plan.json
provenance.json
workflow_manifest.json
```

The probes before and after the reviewed keyframe range verify **no extrapolation** outside the observed track. With plotting enabled the example
also emits dynamic-AOI and scanpath figures.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/05_worked_dynamic_aoi_study.py)
· [Read the dynamic-AOI guide](worked-dynamic-aoi-study.md)

## 7 · Worked event-model validation study

```bash
python examples/06_worked_event_model_validation.py \
  --output-dir worked-event-model-validation-demo \
  --no-figures
```

The script constructs participant-disjoint folds, verifies zero participant
overlap, and compares models on **matched held-out rows**. It writes:

```text
01_source_event_samples.csv
02_participant_split_ledger.csv
03_matched_heldout_predictions.csv
04_sample_level_metrics.csv
05_event_level_metrics.csv
06_model_summary.csv
07_calibration_bins.csv
08_confidence_coverage.csv
09_illustrative_abstention_policy.csv
analysis_plan.json
provenance.json
workflow_manifest.json
figures/01_calibration.png
figures/02_confidence_coverage.png
```

The illustrative abstention policy is not a universal cutoff, and synthetic
model ordering is not evidence of general superiority.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/06_worked_event_model_validation.py)
· [Open the validation clinic](event-model-validation-clinic.md)
· [Use the reporting cookbook](validation-reporting-cookbook.md)

## 8 · Worked tracker import + QC

```bash
python examples/07_worked_tracker_import_qc.py \
  --output-dir worked-tracker-import-qc-demo
```

The Gazepoint-shaped teaching source uses explicit `USER_FILE`, `MEDIA_ID`,
`TIME`, `BPOGX`, and `BPOGY` mappings. It declares seconds→milliseconds and
normalized→pixel conversion, then keeps duplicate keys, missing gaze, bounds,
nominal rate, and **observed cadence** visible.

It writes:

```text
01_source_tracker_export.csv
02_canonical_gaze.csv
03_import_preflight.csv
04_qc_samples.csv
05_trial_quality.csv
import_contract.json
analysis_plan.json
provenance.json
workflow_manifest.json
```

The script verifies that the **source table remains unchanged** and that **row count** is preserved. Matching nominal/observed cadence is not proof of native hardware rate.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/07_worked_tracker_import_qc.py)
· [Read the import/QC guide](worked-tracker-import.md)
· [Use the real-data import clinic](data-import-clinic.md)

## 9 · QC review + exclusion ledger

Use this example after non-destructive QC when the scientific task is deciding
what to retain or exclude without turning software flags into automatic truth.

```bash
python examples/08_worked_qc_review_ledger.py \
  --output-dir worked-qc-review-ledger-demo
```

The deterministic source contains 270 canonical rows: three participants ×
three trials × 30 samples. Two prespecified **trial-level** criteria are
reviewed, while one sample-level anomaly flag is explicitly retained and one
post-hoc rule is isolated as exploratory sensitivity only.

The command writes:

```text
01_canonical_source.csv
02_pre_review_qc_samples.csv
03_trial_quality.csv
04_decision_criteria.csv
05_sample_review_ledger.csv
06_trial_review_ledger.csv
07_participant_review_ledger.csv
08_exclusion_flow.csv
09_reviewed_sample_status.csv
10_primary_analysis_rows.csv
11_exploratory_sensitivity.csv
analysis_plan.json
provenance.json
workflow_manifest.json
```

The primary reconciliation is deliberately inspectable:

```text
pre-review QC rows      = 270
trial denominator       = 9
excluded trials         = 2
retained trials         = 7
participant denominator = 3
retained participants   = 3
primary-analysis rows   = 210
```

The pre-review QC table remains unchanged. `qc_flag=True` is demonstrated as a
**review trigger, not an exclusion rule**. The exploratory criterion is tagged
`sensitivity_only` and is never applied to the primary-analysis table.

The thresholds are teaching values, not universal recommendations. The bundle
is `synthetic_demo_not_empirical_evidence`; reproducible decisions do not
establish tracker, event-model, calibration, or measurement validity.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/08_worked_qc_review_ledger.py)
· [Read the QC review/exclusion clinic](qc-review-exclusion-ledger.md)


## 10 · Worked research evidence bundle

Use this example when you understand the individual workflow stages and need to
see **what a reviewable manuscript/archive directory should actually look like**.

```bash
python examples/09_worked_research_evidence_bundle.py \
  --output-dir worked-research-evidence-bundle
```

The script composes existing public APIs into one archive-facing route:

```text
tracker-shaped source
  → canonical gaze
  → immutable pre-review QC
  → explicit decision criteria
  → reviewed trial ledger
  → separate primary-analysis derivative
  → transparent I-VT events
  → researcher-defined AOIs
  → fixation assignments
  → semantic scanpaths
  → artifact index + analysis plan + provenance + manifest + README
```

The output directory contains `01_source_tracker_export.csv` through
`13_semantic_scanpaths.csv`, plus `source_contract.json`,
`artifact_index.csv`, `analysis_plan.json`, `provenance.json`,
`workflow_manifest.json`, and a reviewer-facing `README.md`.

The example verifies that the source, canonical pre-review table, and pre-review
QC table remain unchanged while reviewed exclusions create a **new**
`07_primary_analysis_rows.csv`. Its thresholds are teaching values only.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/09_worked_research_evidence_bundle.py)
· [Read the evidence-bundle guide](research-evidence-bundle.md)
· [Use the artifact dictionary](artifact-dictionary.md)

## 11 · Statistical analysis handoff

Use this example after event/AOI outputs have been reviewed and you need an explicit
handoff to specialist statistical software without losing repeated-measures identity,
exposure denominators, missing-versus-zero semantics, or latency censoring.

```bash
python examples/10_worked_analysis_handoff.py \
  --output-dir worked-analysis-handoff-demo
```

Without the optional diagnostic figures:

```bash
python examples/10_worked_analysis_handoff.py \
  --output-dir worked-analysis-handoff-demo \
  --no-figures
```

The deterministic teaching design contains 20 participant × trial rows and produces
80 participant × trial × AOI rows plus 40 participant × trial × event-type rows. It
contains all three cases researchers must keep distinct: an AOI absent by design,
a present/observed AOI with a true zero fixation count, and a completely missing
trial. No-fixation latency remains explicitly right-censored rather than receiving
an invented latency value.

The bundle writes:

```text
01_reviewed_fixation_assignments.csv
02_reviewed_event_intervals.csv
03_trial_design_and_coverage.csv
04_trial_aoi_metrics.csv
05_trial_event_metrics.csv
06_descriptive_participant_condition_summary.csv
07_model_handoff_dictionary.csv
08_aoi_definitions.csv
upstream_reference.json
analysis_handoff_plan.json
provenance.json
workflow_manifest.json
figures/01_aoi_dwell_by_condition.png
figures/02_trial_coverage_status.png
```

The participant × condition summary is explicitly marked descriptive-only; it does
not silently replace the trial-level model inputs. GazeForge does not fit or choose an
inferential estimator in this example, and a failed-convergence model in downstream
software would remain a stop condition rather than a valid result.

The complete bundle is `synthetic_demo_not_empirical_evidence`; it creates no device,
native-rate, event-model, AOI-construct, causal, or psychological-state validity claim.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/10_worked_analysis_handoff.py)
· [Read the analysis-handoff guide](analysis-handoff.md)
· [Use the artifact dictionary](artifact-dictionary.md)

## 12 · Manuscript/reporting bundle

Use this after the evidence bundle is frozen and you need reporting derivatives without rewriting upstream source/QC/review/analysis artifacts.

```bash
python examples/11_worked_manuscript_reporting_bundle.py \
  --output-dir worked-manuscript-reporting-bundle
```

The script reuses `09_worked_research_evidence_bundle.py` in a temporary directory, hashes every upstream file before and after reporting extraction, and fails if any upstream byte changes. It writes only:

```text
methods_record.json
denominator_flow.csv
artifact_citation_table.csv
reporting_boundaries.json
software_identity.json
methods_example.md
results_example.md
archive_readme.md
reporting_manifest.json
```

No p-values, effect sizes, inferential statistics, device-validity claims, or psychological-state claims are invented. The entire worked route remains `synthetic_demo_not_empirical_evidence`.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/11_worked_manuscript_reporting_bundle.py)
· [Read the reporting clinic](reporting-clinic.md)
· [Run publication readiness](publication-readiness.md)

## 13 · Measurement/interpretation audit

Use this after gaze-derived measures exist but before treating them as trust, persuasion, interest, comprehension, emotion, intent, diagnosis, preference, cognitive effort, prediction correctness, or scientific invalidity.

```bash
python examples/12_worked_measurement_interpretation_audit.py \
  --output-dir worked-measurement-interpretation-audit
```

The deterministic teaching bundle writes a claim registry, measurement/interpretation matrix, validity-threat register, sensitivity plan, reporting-language table, audit manifest, and README. It preserves no-fixation latency as right-censored rather than zero, never assigns `valid`/`invalid` truth-label statuses, performs no inferential statistics, and never infers a latent state from gaze alone.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/12_worked_measurement_interpretation_audit.py)
· [Read the measurement & interpretation clinic](measurement-interpretation.md)
· [Continue to reporting](reporting-clinic.md)

## 14 · Outcome & estimand preregistration

Use this **before model fitting** to freeze primary/secondary/exploratory outcomes, exact observable definitions, inferential units, exposure/denominator rules, missing/zero/censoring semantics, contrasts, multiplicity families, and prespecified sensitivity checks.

```bash
python examples/13_worked_estimand_preregistration.py \\
  --output-dir worked-estimand-preregistration
```

The worked bundle writes `01_outcome_registry.csv`, `02_estimand_registry.csv`, `03_contrast_registry.csv`, `04_sensitivity_registry.csv`, an initially empty but schema-valid `05_deviation_registry.csv`, `06_reporting_plan.csv`, `preregistration_manifest.json`, and `README.md`.

It fits no model, selects no estimator/model family, creates no p-values/effect sizes/results, never converts missing/no-fixation to zero, and does not claim construct or causal validity.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/13_worked_estimand_preregistration.py)
· [Read the preregistration clinic](estimand-preregistration.md)
· [Continue to the analysis handoff](analysis-handoff.md)


## 15 · Reviewer/replication handoff

Use this after preregistration/estimand records, evidence, analysis handoff,
measurement interpretation, and manuscript-facing reporting are frozen and an
external reviewer or replicator needs to know **what can actually be rerun**.

```bash
python examples/14_worked_reviewer_replication_bundle.py \
  --output-dir worked-reviewer-replication-bundle
```

The deterministic base-install example writes:

```text
01_claim_artifact_matrix.csv
02_rerun_plan.csv
03_reproducibility_checklist.csv
04_limitations_register.csv
05_api_route_map.csv
software_environment.json
reviewer_start_here.md
artifact_hash_ledger.csv
replication_manifest.json
```

It distinguishes `fully_rerunnable_demo`,
`rerunnable_with_private_input`, and `inspectable_only`. Private/restricted
source files are not bundled. Matching hashes establish file identity only; they do
not create device, model, measurement/construct, causal, external, or
psychological validity.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/14_worked_reviewer_replication_bundle.py)
· [Read the reviewer & replication handoff](reviewer-replication-handoff.md)
· [Inspect the API reference](api-reference.md)
· [Run publication readiness](publication-readiness.md)


## 16 · Sensitivity/robustness audit

Use this after the primary outcome/estimand and sensitivity registry are frozen and
the relevant analysis variants have been executed.

```bash
python examples/15_worked_sensitivity_robustness_audit.py \
  --output-dir worked-sensitivity-robustness-audit
```

The deterministic teaching bundle writes:

```text
01_sensitivity_registry.csv
02_executed_conditions.csv
03_result_comparison.csv
04_deviation_ledger.csv
05_interpretation_matrix.csv
06_reporting_language.csv
README.md
sensitivity_manifest.json
```

The example preserves the primary estimand as the reference, reports all registered
variants, retains one `non_converged` and one `not_evaluable` condition, separates
an exploratory AOI variant from a post-registration changed-estimand deviation, and
never creates a p-value, significance decision, or automatic robustness verdict.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/15_worked_sensitivity_robustness_audit.py)
· [Read the sensitivity & robustness clinic](sensitivity-robustness-clinic.md)
· [Continue to reporting](reporting-clinic.md)


## 17 · Denominator/exposure audit

Use this before specialist modelling when counts, rates, proportions, dwell, or latency
depend on unequal exposure, missing trials, absent-by-design AOIs, or no-fixation
censoring.

```bash
python examples/16_worked_denominator_exposure_audit.py \
  --output-dir worked-denominator-exposure-audit
```

The deterministic teaching bundle writes an observation-status registry, exposure
ledger, count/rate audit, dwell/proportion audit, latency-censoring audit,
reconciliation flow, reporting-language table, API map, README, and manifest.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/16_worked_denominator_exposure_audit.py)
· [Read the denominator/exposure clinic](denominator-exposure-censoring.md)
· [Continue to analysis handoff](analysis-handoff.md)


## 18 · Model diagnostics/convergence audit

Use this after specialist statistical software returns fitted model objects and before
you interpret coefficients, sensitivity variants, or manuscript results.

```bash
python examples/17_worked_model_diagnostics_audit.py \
  --output-dir worked-model-diagnostics-audit
```

The deterministic teaching bundle includes a clean diagnostics-complete fit, a
non-converged fit, a singular/boundary fit, a missing-diagnostics fit, a
separation/invalid-covariance case, and a diagnostically clean replacement candidate
that changes the estimand/population and therefore remains exploratory.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/17_worked_model_diagnostics_audit.py)
· [Read the model diagnostics clinic](model-diagnostics-convergence.md)
· [Continue to sensitivity/robustness](sensitivity-robustness-clinic.md)

## 19 · Missing-data assumptions/treatment audit

Use this after denominator/exposure/censoring states are reconciled and before a
specialist statistical analysis selects how unavailable measurements will be treated.

```bash
python examples/18_worked_missing_data_assumptions_audit.py \
  --output-dir worked-missing-data-assumptions-audit
```

The deterministic bundle writes:

```text
01_missing_data_source_registry.csv
02_mechanism_assumption_questions.csv
03_analysis_treatment_registry.csv
04_exclusion_missingness_separation.csv
05_sensitivity_handoff.csv
06_reporting_language.csv
README.md
missing_data_assumptions_manifest.json
```

It never infers MCAR/MAR/MNAR, never performs automatic complete-case filtering,
never selects imputation, weighting, joint-model, survival, GLM/GLMM, SEM, Bayesian,
or another inferential treatment, and keeps censoring, design absence, and undefined
derived metrics distinct from ordinary unavailable measurement.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/18_worked_missing_data_assumptions_audit.py)
· [Read the missing-data assumptions handoff](missing-data-assumptions.md)
· [Continue to analysis handoff](analysis-handoff.md)

## Which example should I run first?

```text
Not sure what GazeForge does?                → 00_gazeforge_tour.py
Have a real tracker export?                  → 07_worked_tracker_import_qc.py
Have QC evidence; need review/exclusions?    → 08_worked_qc_review_ledger.py
Need to verify installation / QC?            → 01_synthetic_qc.py
Need an inspectable event baseline?          → 02_ivt_baseline.py
Need figure-generation patterns?             → 03_visual_diagnostics.py
Need a complete reviewable output bundle?    → end_to_end_research_workflow.py
Need a static domain-shaped worked study?    → 04_worked_advertising_study.py
Need moving AOIs + interpolation auditing?   → 05_worked_dynamic_aoi_study.py
Need participant-held-out event validation?  → 06_worked_event_model_validation.py
Need a manuscript/archive evidence bundle?    → 09_worked_research_evidence_bundle.py
Need model-ready trial/AOI/event tables?       → 10_worked_analysis_handoff.py
Need manuscript/reporting derivatives?         → 11_worked_manuscript_reporting_bundle.py
Need to audit what a gaze metric supports?      → 12_worked_measurement_interpretation_audit.py
Need to freeze outcomes/estimands first?         → 13_worked_estimand_preregistration.py
Need a reviewer/replication handoff?             → 14_worked_reviewer_replication_bundle.py
Need to audit sensitivity/robustness?             → 15_worked_sensitivity_robustness_audit.py
Need to reconcile denominators/exposure?          → 16_worked_denominator_exposure_audit.py
Need to audit model diagnostics/convergence?       → 17_worked_model_diagnostics_audit.py
Need to document missing-data assumptions?         → 18_worked_missing_data_assumptions_audit.py
```

## Move from demo data to a study

A practical research sequence is:

1. freeze the intended primary/secondary/exploratory outcomes and estimands with the [Outcome & estimand preregistration clinic](estimand-preregistration.md);
2. preserve acquisition/source identity;
3. run the [Worked tracker import and QC](worked-tracker-import.md) and use the [Real-data import clinic](data-import-clinic.md) when the source contract differs from the worked example;
4. freeze the actual source mapping, units, geometry, nominal rate, and observed cadence;
5. preserve the pre-review QC derivative;
6. use the [QC review and exclusion ledger](qc-review-exclusion-ledger.md) to record criteria, denominators, review status, and retained/excluded units;
7. keep exploratory sensitivity decisions separate from the primary table;
8. continue to event/AOI/scanpath analysis;
9. use the [Denominator, exposure & censoring clinic](denominator-exposure-censoring.md) to reconcile observation-state, exposure, rate/proportion, and censoring mechanics;
10. use the [Missing-data assumptions & treatment handoff](missing-data-assumptions.md) when unavailable/partial measurements require explicit assumptions or treatment planning;
11. use the [Analysis handoff](analysis-handoff.md) to build model-ready tables while preserving participant/trial grouping and those semantics;
12. use participant-disjoint or dataset-held-out validation where the intended claim requires it;
13. assemble the [Research evidence bundle](research-evidence-bundle.md) so source, QC, decisions, derivatives, provenance, and reporting metadata remain distinct;
14. use the [Measurement & interpretation clinic](measurement-interpretation.md) to audit any observable→construct bridge and justified sensitivity checks;
15. use the [Sensitivity & robustness clinic](sensitivity-robustness-clinic.md) to execute/report the complete registered sensitivity set without replacing the primary estimand; and
16. freeze software identity, figures, tables, and evidence boundaries before reporting.

Synthetic examples are learning tools. They do not turn a derived lower-rate
condition into native-device validation, turn Gazepoint/GP3 compatibility into
device validity, or turn an auditable exclusion rule into measurement validity.
