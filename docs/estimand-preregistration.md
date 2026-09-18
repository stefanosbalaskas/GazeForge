---
description: Freeze primary, secondary, and exploratory gaze outcomes, estimands, contrasts, denominators, censoring, and sensitivity plans before statistical modelling.
search:
  boost: 1.7
---

# Outcome & estimand preregistration clinic

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Preregistration clinic</strong> · Freeze what will be measured, compared, aggregated, and reported before model fitting—without letting GazeForge silently choose a statistical estimator.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

Use this page **before** model fitting when the study question is defined but the analysis needs a reviewable record of exactly which gaze outcomes and contrasts are primary, secondary, or exploratory.

!!! warning "Preregistration is not model selection or validity"
    A frozen registry prevents silent outcome switching and makes deviations visible. It does not establish construct validity, causal validity, detector validity, or the suitability of a particular GLM, GLMM, survival model, SEM, Bayesian model, or other estimator.

## Outcome, estimand, and model are different records

| Layer | Question | Example |
| --- | --- | --- |
| **Outcome** | What observable variable is constructed? | claim-AOI dwell in milliseconds |
| **Estimand** | What quantity/comparison is the study trying to estimate? | difference in expected participant-trial claim dwell between conditions B and A |
| **Contrast** | Which levels/comparison define that estimand? | disclosure B − disclosure A |
| **Model** | Which statistical machinery estimates it? | chosen later in specialist software from the design/distribution/assumptions |

Do not jump from an outcome name such as `dwell_ms` to an estimator without first declaring the estimand and inferential unit.

## Freeze the outcome contract

For every registered outcome, record at least:

- stable outcome ID and **primary / secondary / exploratory** status;
- exact observable definition;
- measurement unit;
- row/inferential structure;
- participant/trial/AOI/event grouping;
- time window;
- observed exposure or denominator;
- observed-zero versus missing versus absent-by-design versus undefined semantics;
- no-event censoring when relevant;
- any transformation or normalization;
- event detector/model source and version;
- AOI source/review state;
- multiplicity family when several outcomes belong to one confirmatory family;
- the relevant GazeForge API/artifact identity.

The registry should be detailed enough that two analysts could construct the same measurement table without seeing the final results.

## Example registry

| Status | Outcome | Unit | Exposure / missing rule | Interpretation boundary |
| --- | --- | --- | --- | --- |
| **Primary** | claim AOI dwell | participant × trial × AOI | retain AOI-observable and gaze-observed milliseconds; zero only after actual observation | visual inspection, not direct trust/persuasion |
| **Secondary** | claim fixation count | participant × trial × AOI | retain observable exposure; missing trial ≠ zero fixations | event frequency, not automatic interest/effort |
| **Secondary** | disclosure first-fixation latency | participant × trial × AOI | no fixation is **right-censored**, not latency zero | timing of observed fixation, not proof of awareness |
| **Exploratory** | claim→product transitions | participant × trial sequence | retain sequence length and unassigned-state policy | sequence structure, not persuasion strategy |

Relevant interfaces: [Eye-events API](api-reference.md#eye-events) · [Semantic AOI API](api-reference.md#semantic-aois) · [Scanpath API](api-reference.md#scanpaths).

## Define the estimand before the estimator

A useful estimand record states:

~~~text
target_population: <who/what the claim concerns>
outcome_id: <registered observable>
condition_contrast: <levels/direction>
summary_target: <difference / ratio / association / time-to-event contrast / other>
inferential_unit: <participant/trial/event hierarchy>
aggregation_before_model: <none or explicit measurement construction>
missingness_policy: <declared>
censoring_policy: <declared>
~~~

GazeForge does **not** fill in `model_family` or `estimator` automatically. Those choices depend on the design, outcome support/distribution, repeated-measures structure, inferential framework, assumptions, and diagnostics in specialist statistical software.

## Missing, zero, absent, undefined, and censored are not interchangeable

Before analysis, decide what each state means.

- **Observed zero:** the outcome was observable and the event/count/dwell truly equalled zero under the declared measurement rule.
- **Missing:** the measurement was unavailable.
- **Absent by design:** the relevant AOI/stimulus feature did not exist in that condition.
- **Undefined:** a denominator or derived metric does not exist mathematically for that observation.
- **Right-censored latency:** the fixation/event was not observed before the available exposure ended.

Never use a convenient zero to stand in for the other states.

The [Analysis handoff](analysis-handoff.md) shows how these statuses survive into model-ready tables.

## Counts, rates, proportions, dwell, latency, and sequences

Different outcome families need different registration fields even before the model is chosen.

### Counts
Record the counting unit, observable exposure, event definition, and whether zero is observable.

### Rates
Record both numerator and exposure denominator; do not archive only the computed rate.

### Proportions
Record numerator, denominator, support, and what happens when the denominator is zero/undefined.

### Dwell/duration
Record event definition, AOI geometry/review source, observable time, and time window.

### First-fixation latency
Record the time origin, event indicator, censor time, AOI/event definition, and available exposure.

### Scanpaths/transitions
Record sequence construction, repeat-collapse rule, unassigned-state rule, transition definition, and trial boundaries.

## Multiplicity family: declare the family, not a universal correction

If several confirmatory outcomes or contrasts belong to one inferential family, record that family before results are examined.

The registry should answer:

- Which outcomes/contrasts are in the family?
- Which are primary versus secondary?
- Which analyses are exploratory and outside the confirmatory family?
- What inferential/multiplicity strategy will specialist statistical software use?

This clinic deliberately does **not** prescribe one correction procedure for every design.

## Sensitivity analysis is not outcome shopping

A prespecified sensitivity analysis asks whether a scientifically defensible alternative measurement decision changes the conclusion. After model fitting, execute and report that frozen set through the [Sensitivity & robustness clinic](sensitivity-robustness-clinic.md) rather than selecting favourable variants.

Examples include:

- small reviewed AOI-boundary perturbations;
- one justified event-detector/threshold alternative;
- a prespecified quality/coverage rule;
- a justified sampling derivation;
- a censoring/exposure definition;
- a sequence-preprocessing rule.

Record the alternatives **before** looking for the most favourable result. If a new analysis is invented after results are known, label it as a deviation/exploratory analysis rather than silently rewriting the original registry.

## Deviation ledger

The worked example begins with an empty but schema-valid deviation table:

~~~text
deviation_id
registered_at
affected_registry
affected_id
change
reason
status_after_change
~~~

If the study changes later, append a row. Do not edit the original primary outcome into a new definition and erase the history.

A deviation record should explain whether the changed analysis remains confirmatory under the study's governance or becomes exploratory. GazeForge does not decide that status automatically.

## Worked outcome/estimand registry

Run:

~~~bash
python examples/13_worked_estimand_preregistration.py \
  --output-dir worked-estimand-preregistration
~~~

It writes:

~~~text
01_outcome_registry.csv
02_estimand_registry.csv
03_contrast_registry.csv
04_sensitivity_registry.csv
05_deviation_registry.csv
06_reporting_plan.csv
preregistration_manifest.json
README.md
~~~

The worked bundle contains four registered outcomes: primary claim-AOI dwell, secondary fixation count, secondary right-censored disclosure first-fixation latency, and an exploratory semantic-transition outcome.

It performs **no model fit**, creates **no p-values/effect sizes/results**, selects **no estimator/model family**, and never converts missing or censored observations to zero.

The entire example is `synthetic_demo_not_empirical_evidence`.

## Reporting plan before results exist

For each outcome, write the reporting rule while the result is still unknown.

**Primary dwell**

> Report the estimate and uncertainty from the prespecified specialist model together with the retained analysis population and observed exposure. Interpret the gaze variable as visual inspection unless a separate construct bridge supports more.

**Secondary fixation count**

> Report the registered secondary status, exposure/denominator, and multiplicity-family treatment; do not relabel the count as interest or cognitive effort.

**First-fixation latency**

> Report the event/censoring definition and the number/exposure of no-fixation observations; do not discard them to create a complete-case mean.

**Exploratory transitions**

> Label the result exploratory in tables and prose and report the exact sequence-construction rule.

## How this connects to the rest of GazeForge

<div class="gf-flow" aria-label="Preregistered outcome workflow">
<div><strong>01</strong><span>Question</span><small>Define the observable research question.</small></div>
<div><strong>02</strong><span>Register</span><small>Freeze outcomes, estimands, contrasts, sensitivities, and deviation schema.</small></div>
<div><strong>03</strong><span>Measure</span><small>Import, QC, events, AOIs, and sequences under the recorded definitions.</small></div>
<div><strong>04</strong><span>Handoff</span><small>Build model-ready tables without losing grouping, exposure, or censoring.</small></div>
<div><strong>05</strong><span>Interpret</span><small>Audit observable→construct bridges and validity threats.</small></div>
<div><strong>06</strong><span>Report</span><small>Report primary/secondary/exploratory status and all deviations.</small></div>
</div>

Continue with:

- [Study-design templates](study-design-templates.md) for acquisition/QC/AOI/validation records;
- [Analysis handoff](analysis-handoff.md) for model-ready tables;
- [Measurement & interpretation clinic](measurement-interpretation.md) for construct-bridge boundaries;
- [Reporting & interpretation clinic](reporting-clinic.md) for manuscript wording;
- [Sensitivity & robustness clinic](sensitivity-robustness-clinic.md) to reconcile the registered sensitivity set with executed, non-evaluable, non-converged, exploratory, and deviation analyses;
- [Publication readiness](publication-readiness.md) for the final audit;
- [Quality-control API](api-reference.md#quality-control), [Eye-events API](api-reference.md#eye-events), [Semantic AOI API](api-reference.md#semantic-aois), [Scanpath API](api-reference.md#scanpaths), and [Sampling-sensitivity API](api-reference.md#sampling-sensitivity) for the underlying measurement interfaces.

## Scientific boundary

Preregistration improves transparency about planned measurements and estimands. It does not make a weak construct measure valid, make an observational contrast causal, make a detector accurate, or rescue a model with failed convergence/diagnostics.

The registry is a **decision record**, not an automatic scientific-certification system.
