---
description: Move reviewed GazeForge outputs into model-ready statistical tables without losing grouping, exposure, missingness, censoring, or provenance.
search:
  boost: 1.6
---

# Analysis handoff: from reviewed gaze outputs to model-ready tables

Use the [Denominator, exposure & censoring clinic](denominator-exposure-censoring.md) when exposure, zero/missing, or no-fixation censoring needs a dedicated reconciliation audit.

If primary/secondary/exploratory outcomes, contrasts, exposure rules, or censoring semantics are not frozen yet, start with the [Outcome & estimand preregistration clinic](estimand-preregistration.md) before constructing model inputs.

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>How-to + statistical handoff guide</strong> · Build auditable analysis tables while keeping the inferential unit, repeated-measures structure, denominators, missingness, and provenance explicit.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

GazeForge takes you from source data through reviewable measurement outputs. This page covers the next boundary: turning reviewed fixation, event, AOI, and scanpath records into tables that a **specialist statistical package** can model.

The goal is not to make GazeForge choose a model. The goal is to hand the model the right rows, grouping keys, denominators, missingness semantics, censoring information, and provenance.

!!! warning "No statistical model is fitted on this page"
    GazeForge prepares auditable measurement and handoff artifacts. It does **not** silently choose a GLM, GLMM, survival model, SEM, Bayesian model, or another estimator. Model choice belongs in the study's statistical analysis plan and in specialist statistical software.

## The handoff contract

A model-ready table should make these questions answerable from the columns alone:

1. **What is one row?** Participant × trial × AOI? Participant × trial × event type?
2. **Which observations repeat within the same participant?**
3. **What denominator or exposure generated a count, rate, or proportion?**
4. **Is a zero a real observed zero, or was the observation missing or impossible by design?**
5. **Was a latency observed, undefined, or right-censored?**
6. **Which QC/review decisions produced this row?**
7. **Which event detector, AOI definition, source, and software version produced it?**
8. **Is the table inferential input or only a descriptive summary?**

If those questions cannot be answered, the table is not ready for confirmatory inference.

## Missing is not zero

This is the most important aggregation rule.

| Situation | Example | Store |
| --- | --- | --- |
| **Observed zero** | disclosure AOI was present and the full trial was observed, but no fixation entered it | `0` plus `metric_status="observed_zero"` |
| **AOI absent by design** | the standard-condition stimulus contains no disclosure AOI | `NA`, not `0` |
| **Tracking missing** | the trial exists but no usable gaze was observed | `NA`, not `0` |
| **Undefined denominator** | exposure time is zero or unknown | `NA`, not a fabricated proportion/rate |
| **Observed no-event latency** | AOI was observable but was never fixated before observation ended | latency `NA` plus an explicit right-censored status and censor time |

A silent `fillna(0)` can change the estimand. It can turn “not observed,” “not present,” or “undefined” into “observed absence.” Do not do that.

## Preserve the inferential unit

Eye tracking produces many samples and fixations per participant. Those rows are not automatically independent experimental units.

```text
participant
  └── trial
       ├── gaze samples
       ├── events/fixations
       └── AOI assignments
```

A common model-ready handoff is therefore:

```text
participant × trial × AOI
```

rather than:

```text
one row per gaze sample treated as an independent participant
```

The correct unit depends on the scientific question, but the grouping structure must survive aggregation. Losing `participant_id` or `trial_id` creates pseudoreplication risk and makes it impossible to represent repeated measures correctly.

## Pattern 1 · Fixations → trial × AOI measures

Start from reviewed fixation-to-AOI assignments. Preserve the trial design and reviewed AOI inventory separately, then aggregate with explicit keys.

Useful trial × AOI outputs include:

- fixation count;
- total dwell time;
- observed dwell proportion;
- first-fixation latency;
- visit count when a visit definition is prespecified;
- AOI-present indicator;
- observed trial time;
- AOI-observable time;
- metric/missingness status;
- latency censoring status.

Do not create only rows for AOIs that happened to receive fixations. Build the expected trial × AOI design matrix first, then distinguish:

- present + observed + no fixation → observed zero;
- absent by design → `NA`;
- missing trial → `NA`.

This preserves both the denominator and the meaning of a zero.

## Pattern 2 · Event intervals → trial-level event measures

Event intervals can be summarized by participant × trial × event type while keeping:

- number of events;
- total event duration;
- mean/median event duration where scientifically appropriate;
- observed gaze time;
- events per observed second;
- detector/model identity;
- native-versus-derived sampling status.

Counts without exposure can be misleading when trial coverage differs. If one trial has 3 s of observed gaze and another has 1.5 s, retain `observed_gaze_ms` rather than comparing raw counts as though exposure were equal.

## Pattern 3 · Latency → observed or censored outcome

First-fixation latency needs special treatment.

If an AOI was present and observable for 3,000 ms but was never fixated, the data do not show an infinite latency and do not justify inserting `3000` as though it were observed. Instead keep:

```text
first_fixation_latency_ms = NA
latency_status = right_censored_no_fixation
latency_censor_time_ms = 3000
```

If the AOI did not exist in that condition, use `not_present_by_design`, not a censored observation. If the trial was missing, use `missing_trial`.

A later survival/time-to-event analysis can then use the censoring information explicitly.

## Pattern 4 · Scanpaths → declared sequence features

A semantic scanpath is already a derived sequence. If you convert it again into counts, transitions, motifs, edit-distance summaries, or embeddings, record that transformation as another derivation.

Do not silently turn a sequence into a psychological label. A transition count or motif is an observable representation feature, not direct evidence of intent, comprehension, persuasion, or emotion.

## QC variables belong to a separate decision layer

QC and review information can accompany a model-ready table, but it must retain its role.

Examples:

- `coverage_fraction`;
- trial-quality score;
- missingness burden;
- reviewed exclusion status;
- source/review flags.

Do not replace the outcome with a QC score, and do not automatically delete rows because a diagnostic field is high. The reviewed exclusion ledger remains the authority for exclusions.

## Descriptive summaries are not automatically model inputs

Participant × condition means are useful for tables and plots. They can also be useful for some explicitly aggregated designs. But they should not silently replace the participant × trial table if the planned inferential model uses trial-level repeated observations.

The worked example therefore writes both:

- `04_trial_aoi_metrics.csv` — model-ready participant × trial × AOI measurements; and
- `06_descriptive_participant_condition_summary.csv` — explicitly labelled `descriptive_only_not_inferential_input`.

That distinction prevents a convenient plotting table from quietly becoming a different statistical analysis.

## Choose the statistical family outside GazeForge

Use the outcome definition and data-generating structure to choose an estimator in specialist software. The table below is a routing aid, not automatic model selection.

| Outcome/question | Preserve in the handoff | Typical specialist family to consider | Do not do automatically |
| --- | --- | --- | --- |
| continuous dwell/duration | participant/trial grouping, exposure, skew/zeros, condition | linear/mixed, generalized, robust, or Bayesian model as justified | assume Gaussian errors because the column is numeric |
| count of fixations/events | count plus observed exposure/offset | Poisson/negative-binomial or mixed/Bayesian count model as justified | compare counts with unequal exposure and no denominator |
| proportion | numerator + denominator or explicit exposure | binomial/beta-type model depending on construction | model a percentage without knowing how it was formed |
| binary choice/occurrence | repeated unit + outcome definition | logistic/mixed/Bayesian binary model | treat repeated trials as independent people |
| first-fixation latency | event indicator + time + censoring status | survival/time-to-event model | drop no-fixation trials or replace them with arbitrary times |
| repeated multivariate constructs | measurement identity + hierarchy + missingness | SEM/multilevel/other specialist model if theory supports it | infer constructs from AOI labels alone |

A failed convergence, singular fit, invalid covariance estimate, separation problem, or other model diagnostic must not be accepted as a valid result merely because the software returned coefficients.

## Worked example

Run:

```bash
python examples/10_worked_analysis_handoff.py \
  --output-dir worked-analysis-handoff-demo
```

To skip optional figures:

```bash
python examples/10_worked_analysis_handoff.py \
  --output-dir worked-analysis-handoff-demo \
  --no-figures
```

The example uses deterministic synthetic/demo records and existing public GazeForge APIs. It does not fit a statistical model.

### Output inventory

| Artifact | Unit | Role |
| --- | --- | --- |
| `01_reviewed_fixation_assignments.csv` | fixation | reviewed measurement input |
| `02_reviewed_event_intervals.csv` | event | reviewed measurement input |
| `03_trial_design_and_coverage.csv` | participant × trial | design + denominator/coverage registry |
| `04_trial_aoi_metrics.csv` | participant × trial × AOI | primary model-ready AOI handoff |
| `05_trial_event_metrics.csv` | participant × trial × event type | primary model-ready event handoff |
| `06_descriptive_participant_condition_summary.csv` | participant × condition × AOI | descriptive only |
| `07_model_handoff_dictionary.csv` | column | meaning/unit/missingness dictionary |
| `08_aoi_definitions.csv` | AOI | frozen reviewed AOI geometry |
| `upstream_reference.json` | bundle | upstream identity/fingerprints |
| `analysis_handoff_plan.json` | bundle | inferential unit, grouping, zero/censoring policy |
| `provenance.json` | operation | transformation fingerprints/parameters |
| `workflow_manifest.json` | bundle | evidence boundary and safeguards |
| `figures/01_aoi_dwell_by_condition.png` | figure | descriptive diagnostic |
| `figures/02_trial_coverage_status.png` | figure | coverage diagnostic |

The example deliberately contains three different situations:

1. a disclosure AOI that is absent in the standard condition → `NA`;
2. a disclosure AOI that is present and fully observed but receives no fixation → true observed `0`;
3. a completely missing trial → `NA`.

It also represents a no-fixation latency as right-censored rather than inventing a latency value.

## Minimal reporting template

A manuscript-facing methods description can adapt the following structure:

> Reviewed fixation and event outputs were aggregated to participant-by-trial analysis units while retaining participant, trial, condition, AOI/event identity, and observed-exposure denominators. Missing trials and AOIs absent by design were retained as missing rather than converted to zero; zero values were assigned only when the relevant AOI/event was observable and an observed absence was established. First-fixation latencies without an observed fixation were retained with explicit censoring status. Descriptive participant-by-condition summaries were generated separately from the model-input tables. Statistical estimator choice and diagnostics were handled in the prespecified specialist analysis environment rather than selected automatically by GazeForge.

Replace every generic phrase with the actual study facts.

## Pre-model checklist

Before exporting to R, Python, JASP, Stan, or another statistical environment, verify:

- [ ] participant, trial/session, condition, and stimulus identifiers are present;
- [ ] the table states its row/unit of observation;
- [ ] repeated-measures grouping is preserved;
- [ ] every count/rate/proportion has its numerator/denominator or exposure;
- [ ] missing, absent-by-design, undefined, and observed-zero states are distinct;
- [ ] latency censoring is explicit;
- [ ] QC/review decisions reconcile with retained rows;
- [ ] event detector and AOI provenance are recoverable;
- [ ] native/derived sampling status is preserved where relevant;
- [ ] descriptive summaries are labelled separately from inferential inputs;
- [ ] no estimator was selected solely because the software made it convenient;
- [ ] failed convergence or invalid diagnostics will stop interpretation;
- [ ] exact GazeForge/software identity and fingerprints are archived.

Carry the registered outcome/estimand IDs into the handoff dictionary when possible. Continue with the [Measurement & interpretation clinic](measurement-interpretation.md) when deciding what the model-ready measures support substantively, the [Sensitivity & robustness clinic](sensitivity-robustness-clinic.md) after registered sensitivity variants are executed, the [Research evidence bundle](research-evidence-bundle.md) when assembling the final archive, the [Reporting & interpretation clinic](reporting-clinic.md) when translating frozen artifacts into manuscript language, and [Publication readiness](publication-readiness.md) before submission.

!!! note "Evidence boundary"
    The worked handoff is `synthetic_demo_not_empirical_evidence`. It demonstrates row construction, missingness semantics, exposure accounting, censoring, figures, and provenance. It does not establish device validity, event-model validity, AOI construct validity, causal effects, or psychological states.
