# GazeForge examples

These scripts are intentionally deterministic. They are learning, smoke-test,
workflow, and audit examples—not empirical validation artifacts.

Website gallery: [Runnable examples](../docs/runnable-examples.md) ·
Task-first routes: [Research recipes](../docs/research-recipes.md)


## 0. GazeForge tour

```bash
python examples/00_gazeforge_tour.py --output-dir gazeforge-tour-demo
```

Start here when you want to understand the whole package before choosing a method.
The tour creates a compact, reviewable source → canonical → QC → event → AOI →
scanpath → provenance bundle and verifies that the source remains unchanged.

Guide: [What GazeForge does and how to use it](../docs/gazeforge-tour.md)

## 1. Synthetic QC

```bash
python examples/01_synthetic_qc.py
```

Simulates gaze, canonicalises it, adds non-destructive anomaly flags, and prints
trial-level quality summaries.

Guide: [Synthetic gaze to auditable QC](../docs/tutorial-synthetic-qc.md)

## 2. Transparent I-VT baseline

```bash
python examples/02_ivt_baseline.py
```

Applies the deterministic pixel-velocity I-VT baseline and prints event counts
and first-trial transitions.

Guide: [Build an inspectable I-VT event baseline](../docs/tutorial-ivt-baseline.md)

## 3. Visual diagnostics

```bash
python -m pip install -e ".[plot]"
python examples/03_visual_diagnostics.py --output-dir visual-demo
```

Generates six synthetic/demo figures covering QC, event probabilities,
calibration, semantic AOIs, scanpaths, and bounded dynamic AOIs.

Guide: [Visual diagnostics](../docs/visual-diagnostics.md)

## 4. End-to-end research workflow

```bash
python examples/end_to_end_research_workflow.py \
  --output-dir end-to-end-research-demo
```

For the table/provenance path without Matplotlib:

```bash
python examples/end_to_end_research_workflow.py \
  --output-dir end-to-end-research-demo \
  --no-figures
```

Writes source/canonical/QC/event/fixation/AOI/scanpath tables, provenance, a
workflow manifest, fingerprints, and optional figures.

Guide: [Practical end-to-end research workflow](../docs/practical-workflow.md)

## 5. Worked advertising / interface study

```bash
python examples/04_worked_advertising_study.py \
  --output-dir worked-advertising-demo
```

Uses explicit `brand`, `claim`, `disclosure`, and `product` AOIs and produces a
reviewable static-stimulus study bundle.

Guide: [Worked advertising / interface study](../docs/worked-advertising-study.md)

## 6. Worked dynamic-AOI study

```bash
python examples/05_worked_dynamic_aoi_study.py \
  --output-dir worked-dynamic-aoi-demo \
  --no-figures
```

Exercises reviewed keyframes, bounded interpolation, semantic assignments, and
mechanically verified no-extrapolation behaviour.

Guide: [Worked dynamic-AOI study](../docs/worked-dynamic-aoi-study.md)

## 7. Worked event-model validation study

```bash
python examples/06_worked_event_model_validation.py \
  --output-dir worked-event-model-validation-demo \
  --no-figures
```

Builds participant-disjoint folds and matched held-out comparisons with
separate sample/event metrics, calibration, confidence/coverage, and an
explicitly illustrative abstention policy.

Guide: [Event-model validation clinic](../docs/event-model-validation-clinic.md)

## 8. Worked tracker import + QC

```bash
python examples/07_worked_tracker_import_qc.py \
  --output-dir worked-tracker-import-qc-demo
```

Transforms a Gazepoint-shaped export through an explicit seconds→milliseconds
and normalized→pixel contract while retaining duplicate, missing, off-screen,
and cadence diagnostics for review. It verifies source immutability and
row-count preservation.

Guide: [Worked tracker import and QC](../docs/worked-tracker-import.md)

## 9. Worked QC review + exclusion ledger

```bash
python examples/08_worked_qc_review_ledger.py \
  --output-dir worked-qc-review-ledger-demo
```

Demonstrates the next research handoff: non-destructive QC evidence → explicit
criteria → sample/trial/participant review ledgers → denominator accounting →
a separate primary-analysis derivative.

The deterministic example contains 270 pre-review rows and nine trials. Exactly
two trials are excluded after review under prespecified trial-level rules, all
three participants remain retained, and one `qc_flag=True` sample is explicitly
reviewed and retained. A post-hoc criterion is kept in a separate exploratory
sensitivity table and never modifies the primary analysis.

The script writes eleven CSV tables plus `analysis_plan.json`,
`provenance.json`, and `workflow_manifest.json`. It verifies that the canonical
source and pre-review QC table remain unchanged and records
`synthetic_demo_not_empirical_evidence`.

Guide:
[QC review and exclusion ledger](../docs/qc-review-exclusion-ledger.md)


## 10. Worked research evidence bundle

```bash
python examples/09_worked_research_evidence_bundle.py \
  --output-dir worked-research-evidence-bundle
```

Composes the existing import, QC, review, transparent-event, AOI, scanpath, and
provenance APIs into one archive-facing directory. It keeps the immutable
tracker-shaped source, canonical pre-review table, pre-review QC evidence,
reviewed trial ledger, and primary-analysis derivative distinct, then adds an
`artifact_index.csv`, `source_contract.json`, analysis plan, provenance,
workflow manifest, file hashes, and reviewer-facing README.

The demonstration thresholds are teaching values only. The complete bundle is
`synthetic_demo_not_empirical_evidence` and creates no tracker/device,
native-60-Hz, Gazepoint/GP3, event-model, AOI-construct, measurement, or
psychological-state validity claim.

Guide: [Research evidence bundle](../docs/research-evidence-bundle.md) ·
[Artifact & output dictionary](../docs/artifact-dictionary.md)

## 11. Statistical analysis handoff

```bash
python examples/10_worked_analysis_handoff.py \
  --output-dir worked-analysis-handoff-demo
```

Builds explicit participant × trial × AOI and participant × trial × event tables
from reviewed deterministic synthetic/demo records. The handoff preserves repeated-
measures identity, observed exposure/denominators, observed zero versus missing or
absent-by-design states, and right-censored no-fixation latency.

The script also writes a model-handoff dictionary, analysis-handoff plan,
provenance, manifest, a descriptive-only participant × condition summary, and two
optional diagnostic figures. Use `--no-figures` for a base-install run.

No statistical estimator is selected or fitted. The entire bundle remains
`synthetic_demo_not_empirical_evidence` and makes no device, event-model, AOI-
construct, causal, or psychological-state validity claim.

Guide: [Analysis handoff](../docs/analysis-handoff.md) ·
[Artifact & output dictionary](../docs/artifact-dictionary.md)

## 12. Manuscript/reporting bundle

```bash
python examples/11_worked_manuscript_reporting_bundle.py \
  --output-dir worked-manuscript-reporting-bundle
```

Reuses the existing evidence-bundle example in a temporary directory and writes reporting derivatives only. It verifies byte-level upstream immutability, reconciles denominators, maps manuscript-facing statements to exact upstream filenames/hashes, and records explicit evidence boundaries.

No inferential statistics or substantive effects are invented. The reporting bundle remains `synthetic_demo_not_empirical_evidence`.

Guide: [Reporting & interpretation clinic](../docs/reporting-clinic.md)

## 13. Measurement/interpretation audit

```bash
python examples/12_worked_measurement_interpretation_audit.py \
  --output-dir worked-measurement-interpretation-audit
```

Builds a deterministic claim registry plus measurement, validity-threat, sensitivity, and reporting-language tables. Statuses are workflow prompts rather than scientific truth labels; no-fixation latency remains right-censored, no missing value is silently converted to zero, and no latent construct is inferred automatically.

Guide: [Measurement & interpretation clinic](../docs/measurement-interpretation.md)

## 14. Outcome/estimand preregistration

```bash
python examples/13_worked_estimand_preregistration.py \\
  --output-dir worked-estimand-preregistration
```

Builds deterministic outcome, estimand, contrast, sensitivity, deviation, and reporting-plan registries before model fitting. The example keeps primary/secondary/exploratory status explicit, preserves exposure and right-censoring semantics, starts with a schema-valid empty deviation ledger, and never selects an estimator or creates inferential results.

Guide: [Outcome & estimand preregistration clinic](../docs/estimand-preregistration.md)


## 15. Reviewer/replication handoff

```bash
python examples/14_worked_reviewer_replication_bundle.py \
  --output-dir worked-reviewer-replication-bundle
```

Builds reviewer-facing reproducibility metadata without running a new scientific
analysis or bundling private/restricted source data. The bundle records
claim→artifact/API traceability, rerun access classes, reproducibility checks,
limitations, software identity, SHA-256 file identities, and a start-here guide.

The worked example distinguishes `fully_rerunnable_demo`,
`rerunnable_with_private_input`, and `inspectable_only`. Matching hashes improve
auditability but do not establish empirical, device, model, measurement/construct,
causal, or external validity.

Guide: [Reviewer & replication handoff](../docs/reviewer-replication-handoff.md) ·
[Publication readiness](../docs/publication-readiness.md)


## 16. Sensitivity/robustness audit

```bash
python examples/15_worked_sensitivity_robustness_audit.py \
  --output-dir worked-sensitivity-robustness-audit
```

Builds a deterministic post-analysis audit of the registered sensitivity set. The
example keeps the primary estimand fixed for direct comparisons, records denominator
and exposure changes, retains `not_evaluable` and `non_converged` conditions, and
separates a changed-estimand post-registration deviation from same-estimand checks.

It uses fixed synthetic teaching values only: no p-values, significance decisions,
causal/construct/native-device validity claims, or automatic robustness verdict are
created.

Guide: [Sensitivity & robustness clinic](../docs/sensitivity-robustness-clinic.md) ·
[Reporting clinic](../docs/reporting-clinic.md)


## 17. Denominator/exposure audit

```bash
python examples/16_worked_denominator_exposure_audit.py \
  --output-dir worked-denominator-exposure-audit
```

Builds a deterministic audit of observed zero, missing trial, absent-by-design,
undefined denominator, partial exposure, count/rate and dwell/proportion construction,
and right-censored no-fixation latency. It performs no inferential modelling.

Guide: [Denominator, exposure & censoring clinic](../docs/denominator-exposure-censoring.md)


## 18. Model diagnostics/convergence audit

```bash
python examples/17_worked_model_diagnostics_audit.py \
  --output-dir worked-model-diagnostics-audit
```

Builds a deterministic vendor-neutral audit of convergence, singular/boundary states,
separation/invalid covariance, diagnostic completeness, and changed-estimand
replacement candidates. It fits no real model and creates no p-values/effect sizes.

Guide: [Model diagnostics & convergence clinic](../docs/model-diagnostics-convergence.md)

## 19. Missing-data assumptions/treatment audit

```bash
python examples/18_worked_missing_data_assumptions_audit.py \
  --output-dir worked-missing-data-assumptions-audit
```

Builds a deterministic source/reason registry, MCAR/MAR/MNAR assumption-question
table, non-selecting treatment registry, exclusion/missingness separation ledger,
sensitivity handoff, reporting-language contrasts, and safeguard manifest.

The example selects no missing-data or inferential treatment. It complements rather
than duplicates the denominator/exposure/censoring and model-diagnostics audits.

Guide: [Missing-data assumptions & treatment handoff](../docs/missing-data-assumptions.md)


## 20. Uncertainty/multiplicity & inferential reporting audit

```bash
python examples/19_worked_inferential_reporting_audit.py \
  --output-dir worked-inferential-reporting-audit
```

Builds a deterministic post-fit audit of effect scale/unit, uncertainty identity,
multiplicity-family completeness, raw versus adjusted p-value identity, diagnostics,
and confirmatory versus exploratory status. All inferential numbers are synthetic
teaching values.

Guide: [Uncertainty, multiplicity & inferential reporting clinic](../docs/inferential-reporting-audit.md)

## Reproducibility notes

The twenty-one examples use fixed or explicitly constructed synthetic/demo inputs.
For manuscript-facing work:

- record the GazeForge version or exact commit SHA;
- preserve source and pre-review derivatives;
- keep nominal/native acquisition facts separate from observed timestamp
  cadence;
- treat QC flags as review evidence rather than automatic exclusions;
- report exclusion denominators and decision scope;
- distinguish prespecified rules from exploratory sensitivity analyses; and
- do not treat synthetic output, adapter compatibility, reproducible thresholds,
  or software execution as tracker/model/measurement validation.

Use the [Study-design templates](../docs/study-design-templates.md) while
planning, the [Outcome & estimand preregistration clinic](../docs/estimand-preregistration.md) before confirmatory model fitting, [Worked tracker import](../docs/worked-tracker-import.md) for the
import/QC handoff, [QC review and exclusion ledger](../docs/qc-review-exclusion-ledger.md)
before exclusions, the [Event-model validation clinic](../docs/event-model-validation-clinic.md)
for learned event evaluation, the [Research evidence bundle](../docs/research-evidence-bundle.md)
for archive assembly, the [Measurement & interpretation clinic](../docs/measurement-interpretation.md) before promoting gaze observables into substantive constructs, the [Denominator, exposure & censoring clinic](../docs/denominator-exposure-censoring.md) to preserve observation-state mechanics, the [Missing-data assumptions & treatment handoff](../docs/missing-data-assumptions.md) before any missing-data strategy is selected, the [Sensitivity & robustness clinic](../docs/sensitivity-robustness-clinic.md) before final reporting, the [Reviewer & replication handoff](../docs/reviewer-replication-handoff.md) before external sharing, and [Publication readiness](../docs/publication-readiness.md)
before freezing a study bundle.
