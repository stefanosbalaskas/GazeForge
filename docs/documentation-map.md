---
description: Task-first map for choosing the shortest defensible GazeForge workflow, runnable example, artifact bundle, and scientific boundary.
search:
  boost: 1.6
---

# Documentation map

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>How-to router</strong> · Choose the shortest GazeForge route for the research task you have now.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md" aria-current="page">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

GazeForge has deep method, validation, benchmark, and workflow documentation. You do not need to read it in navigation order. Start from the task you need to complete, use the shortest runnable route, inspect the artifacts it produces, and only then move into explanation or reference pages.

!!! info "How this map is organized"
    The site separates four documentation needs: **tutorials** for first success, **how-to guides** for a concrete task, **explanations** for method/evidence reasoning, and **reference** for exact API or status information. A page can link across those types, but it should not try to be all four at once.

!!! warning "Software routes are not scientific validation"
    A successful command, reproducible artifact bundle, or passing software check demonstrates software behavior. It does not by itself establish tracker validity, event-model validity, calibration validity, measurement validity, or general scientific suitability for a study.

## Choose by research task

| Research task | Prerequisite | Primary start | Run / public surface | Main artifact | Boundary to keep visible | Continue to |
| --- | --- | --- | --- | --- | --- | --- |
| Understand GazeForge | none | [GazeForge Tour](gazeforge-tour.md) | `python examples/00_gazeforge_tour.py --output-dir gazeforge-tour-demo` | source→QC→events→AOIs→scanpaths bundle | synthetic demo ≠ empirical validation | [Learning paths](learning-paths.md) |
| Plan a first study | clear research question + acquisition plan | [First study blueprint](first-study-blueprint.md) | existing worked static-study route | analysis contract + artifact plan | auditable workflow ≠ construct validity | [Study lifecycle](study-lifecycle.md) |
| Choose a method for a known task | explicit research question + available evidence | [Method chooser](method-chooser.md) | question/evidence/generalisation decision table | defensible workflow route | software availability ≠ scientific justification | [Artifact dictionary](artifact-dictionary.md) |
| Understand output files | one or more GazeForge artifacts | [Artifact & output dictionary](artifact-dictionary.md) | artifact role/unit/boundary reference | source/QC/review/analysis/validation/provenance classification | filename order ≠ evidence strength | [Research evidence bundle](research-evidence-bundle.md) |
| Install or check the environment | supported Python | [Getting started](getting-started.md) | `python -m pip install "gazeforge==0.1.0a1"` | importable environment | installation success ≠ measurement validity | [Runnable examples](runnable-examples.md) |
| Import a tracker export | known source columns/units | [Worked tracker import + QC](worked-tracker-import.md) | `adapt_gazepoint_samples()` / canonical schema | source, canonical, preflight, QC tables | adapter compatibility ≠ device validity | [Real-data import clinic](data-import-clinic.md) |
| Inspect QC without deleting data | canonical gaze table | [Synthetic QC tutorial](tutorial-synthetic-qc.md) | `ai_flag_anomalies()`, `score_trial_quality()` | anomaly flags + trial-quality table | flag ≠ invalid sample | [QC review & exclusion ledger](qc-review-exclusion-ledger.md) |
| Review exclusions | preserved pre-review QC table | [QC review & exclusion ledger](qc-review-exclusion-ledger.md) | `python examples/08_worked_qc_review_ledger.py --output-dir worked-qc-review-ledger-demo` | sample/trial/participant ledgers + denominator flow | reproducible rule ≠ validated rule | [Study lifecycle](study-lifecycle.md) |
| Label eye events transparently | gaze samples + sampling assumptions | [I-VT baseline tutorial](tutorial-ivt-baseline.md) | `ivt_classify_events()` | event-labelled samples / intervals | example threshold ≠ universal cutoff | [Event-model validation clinic](event-model-validation-clinic.md) |
| Validate learned event models | labelled event data + valid grouping unit | [Event-model validation clinic](event-model-validation-clinic.md) | grouped CV / calibration / event metrics | split ledger + matched held-out predictions + metrics | held-out design must match the intended claim | [Validation reporting cookbook](validation-reporting-cookbook.md) |
| Define static or dynamic AOIs | stimulus geometry or reviewed tracks | [Research recipes](research-recipes.md) | AOI mapping / dynamic AOI assignment | AOI definitions + assignments + review/audit | AI proposal ≠ ground truth; no silent extrapolation | [Worked dynamic-AOI study](worked-dynamic-aoi-study.md) |
| Build semantic scanpaths | reviewed fixation/AOI assignments | [Practical workflow](practical-workflow.md) | `to_semantic_scanpaths()` | semantic sequence table | sequence representation ≠ latent-state inference | [Methods overview](methods-overview.md) |
| Build statistical model inputs | reviewed event/AOI outputs + preserved design/coverage | [Analysis handoff](analysis-handoff.md) | `python examples/10_worked_analysis_handoff.py --output-dir worked-analysis-handoff-demo` | participant × trial × AOI/event tables + denominators + censoring | missing ≠ zero; samples/fixations are not independent participants | [Measurement clinic](measurement-interpretation.md) |
| Audit what a gaze-derived measure supports | frozen measurement definitions + intended claims | [Measurement & interpretation clinic](measurement-interpretation.md) | `python examples/12_worked_measurement_interpretation_audit.py --output-dir worked-measurement-interpretation-audit` | claim registry + interpretation matrix + threats + sensitivity/reporting tables | observable ≠ latent construct; audit status ≠ truth label | [Reporting clinic](reporting-clinic.md) |
| Reproduce or freeze a study | finalized analysis plan + provenance | [Study lifecycle](study-lifecycle.md) | fingerprints / manifests / deterministic exports | frozen inputs, outputs, provenance | frozen software artifact ≠ external validity | [Publication readiness](publication-readiness.md) |
| Prepare manuscript/archive evidence | finalized results and denominators | [Research evidence bundle](research-evidence-bundle.md) | `python examples/09_worked_research_evidence_bundle.py --output-dir worked-research-evidence-bundle` | artifact index + source/QC/review/analysis/provenance layers | archive completeness ≠ empirical validity | [Reporting clinic](reporting-clinic.md) |
| Translate frozen evidence into manuscript language | frozen bundle + reconciled denominators | [Reporting & interpretation clinic](reporting-clinic.md) | `python examples/11_worked_manuscript_reporting_bundle.py --output-dir worked-manuscript-reporting-bundle` | Methods/results examples + citation table + boundaries + reporting manifest | reporting prose cannot strengthen evidence | [Publication readiness](publication-readiness.md) |
| Hand a frozen study to a reviewer/replicator | frozen archive + access/licensing status | [Reviewer & replication handoff](reviewer-replication-handoff.md) | `python examples/13_worked_reviewer_replication_bundle.py --output-dir worked-reviewer-replication-bundle` | claim-artifact map + rerun plan + reproducibility class + limitations + API/hash ledger | inspectability/reruns ≠ scientific validity | [Publication readiness](publication-readiness.md) |
| Inspect current empirical support | no prerequisite | [Evidence status](evidence-status.md) | generated evidence/status pages | Frozen / Reviewed / Bounded / pending status | native/derived and split/identity boundaries remain explicit | [Validation status](validation-status.md) |

## Eight worked routes

### Route A · I have a Gazepoint-style export and need an analysis table

1. Read [Worked tracker import + QC](worked-tracker-import.md).
2. Freeze the source-column mapping, timestamp unit, coordinate basis, geometry, nominal/native rate, and observed timestamp cadence.
3. Use the [Real-data import clinic](data-import-clinic.md) when the export differs from the worked source contract.
4. Preserve the pre-review QC table.
5. Use the [QC review & exclusion ledger](qc-review-exclusion-ledger.md) before creating the primary-analysis derivative.
6. Continue to an event/AOI/scanpath route only after denominators and exclusion decisions reconcile.
7. When the analysis is frozen, use the [Research evidence bundle](research-evidence-bundle.md) pattern to package source identity, decisions, derivatives, and provenance separately.

**Stop rather than guess:** unknown units, unknown participant/trial identity, unexplained duplicate keys, or an unverified timestamp basis are source-contract problems. Do not repair them by silently coercing the table until it “looks right.”

### Route B · I have labelled events and want to compare classifiers

1. Start with the [Event-model validation clinic](event-model-validation-clinic.md).
2. Define the grouping unit that must remain disjoint across train/test partitions.
3. Compare models on matched held-out observations.
4. Inspect calibration and event-level temporal behavior, not only sample accuracy.
5. Use the [Validation reporting cookbook](validation-reporting-cookbook.md) to report split design, denominators, uncertainty, and limitations.

**Stop rather than guess:** source-token separation is not participant separation, derived 60 Hz is not native 60 Hz, and a synthetic ordering does not establish general model superiority.

### Route C · I have a moving stimulus and need semantic AOIs

1. Use the [Worked dynamic-AOI study](worked-dynamic-aoi-study.md).
2. Preserve reviewed keyframes and the temporal support range.
3. Audit interpolation and verify **no extrapolation** outside reviewed support.
4. Keep AI-generated boxes or tracks as proposals until the intended review policy is satisfied.
5. Build scanpaths only from the reviewed AOI-assignment derivative.

**Stop rather than guess:** a detected object, track, or semantic label is not automatically a scientifically valid AOI for the study construct.


### Route D · I need a manuscript/archive bundle a reviewer can understand

1. Start with the [Research evidence bundle](research-evidence-bundle.md).
2. Open the [Artifact & output dictionary](artifact-dictionary.md) when a CSV/JSON role is unclear.
3. Preserve source identity and pre-review QC separately from review decisions.
4. Build the primary-analysis derivative from the reviewed ledger rather than editing QC in place.
5. Freeze an artifact index, analysis plan, provenance, workflow manifest, software identity, and reviewer-facing README.
6. Run the [Publication readiness](publication-readiness.md) checklist before sharing or citing the archive.

**Stop rather than guess:** a complete archive proves neither measurement validity nor external validity. Archive only the evidence class the study actually supports, and respect participant privacy and source licensing.

### Route E · I have reviewed gaze outputs and need statistical model inputs

1. Start with the [Analysis handoff](analysis-handoff.md).
2. Preserve participant, trial/session, condition, stimulus, and repeated-measures identity.
3. Carry observed exposure/denominators into count, rate, proportion, and dwell summaries.
4. Keep observed zero, absent-by-design, undefined, and missing states distinct.
5. Carry no-fixation latency as explicit censoring when the AOI was observable.
6. Generate descriptive participant × condition summaries separately from trial-level inferential inputs.
7. Fit the prespecified inferential model in specialist statistical software; do not let the handoff choose an estimator.

**Stop rather than guess:** never use `fillna(0)` as a convenience repair, never aggregate away the inferential unit without changing the estimand explicitly, and never interpret a failed-convergence model as a valid result.

### Route F · I have gaze-derived measures and need to audit interpretation

1. Start with the [Measurement & interpretation clinic](measurement-interpretation.md).
2. Name the observable separately from the proposed construct.
3. Preserve missing, zero, exposure, and censoring semantics.
4. Review event/AOI/sampling/QC and generalisation threats.
5. Prespecify scientifically justified sensitivity checks rather than selecting favourable variants.
6. Record what external outcome or construct-validation evidence is required.
7. Route only the supported wording into manuscript reporting.

**Stop rather than guess:** dwell, fixation count, latency, scanpaths, confidence, and QC flags do not automatically establish trust, persuasion, interest, comprehension, emotion, intent, diagnosis, correctness, or scientific invalidity.

### Route G · I have frozen evidence and need manuscript/supplement wording

1. Start with the [Reporting & interpretation clinic](reporting-clinic.md).
2. Keep import compatibility separate from device validity.
3. Report QC evidence separately from review/exclusion decisions.
4. Name event/AOI/scanpath identity and its validation boundary.
5. Preserve participant/stimulus/source-token/dataset split identity exactly.
6. Keep native/nominal, observed cadence, and derived analysis rates distinct.
7. Put critical evidence qualifiers in figure/table captions when the visual could be overread.
8. Run [Publication readiness](publication-readiness.md) before submission or archive release.

**Stop rather than guess:** prose cannot upgrade a synthetic demo into empirical evidence, derived 60 Hz into native 60 Hz, or an observable gaze pattern into trust, persuasion, comprehension, emotion, diagnosis, preference, or intent.


### Route H · I need to hand the frozen study to a reviewer or replicator

1. Start with the [Reviewer & replication handoff](reviewer-replication-handoff.md).
2. Classify the archive as `fully_rerunnable_demo`, `rerunnable_with_private_input`, or `inspectable_only` rather than using an ambiguous “reproducible” label.
3. Map each material statement to an exact artifact, access requirement, API/guide route, and interpretation boundary.
4. Record exact software/version/full-commit identity plus any material environment/configuration information.
5. State whether public, private, or restricted inputs are required and never imply that unavailable/restricted source files are bundled.
6. Reconcile denominators, exclusions, missing-versus-zero states, and censoring before sharing the handoff.
7. Carry the limitations register and evidence class with the archive.
8. Run [Publication readiness](publication-readiness.md) before release.

**Stop rather than guess:** matching hashes, deterministic reruns, or reviewer inspectability do not establish device, model, measurement/construct, causal, external, or latent-state validity.

## Documentation types

### Tutorial · first success

Use tutorials when you are learning the package and want a controlled path that works end to end. Start with the [GazeForge Tour](gazeforge-tour.md), [Synthetic QC tutorial](tutorial-synthetic-qc.md), or [I-VT baseline tutorial](tutorial-ivt-baseline.md).

### How-to guide · complete a task

Use how-to guides when you already know the outcome you need: import a real export, review exclusions, validate a model, audit dynamic AOIs, freeze a study, build an evidence bundle, or prepare a manuscript.

### Explanation · understand a method or boundary

Use method and governance pages when you need the reasoning behind a choice: [Methods overview](methods-overview.md), [Scientific governance](scientific-governance.md), event-level evaluation, calibration, sampling sensitivity, or benchmark-specific evidence pages.

### Reference · exact API/status

Use [API reference](api-reference.md), [Evidence status](evidence-status.md), [Validation status](validation-status.md), and generated benchmark/status pages when you need exact current interfaces or evidence classifications rather than a teaching sequence.

## When you are stuck

Use the same help order on task pages. The persistent help row at the top of this page links to the Tour, this task map, troubleshooting, runnable examples, and the issue tracker.

The [Troubleshooting & Diagnostics](troubleshooting.md) guide is for failures, surprising output, uncertain source contracts, and minimal reproducible issue reports. If the problem is a scientific-evidence question rather than a software failure, use [Evidence status](evidence-status.md) or the relevant validation page instead.
