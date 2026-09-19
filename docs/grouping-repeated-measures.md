---
description: Audit observation rows, measurement units, inferential units, repeated-measures grouping, nested/crossed identities, aggregation changes, and pseudoreplication risk before specialist modelling.
search:
  boost: 1.6
---

# Grouping, repeated measures & pseudoreplication clinic

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Statistical handoff clinic</strong> · Preserve dependence and generalisation identities before a specialist model turns repeated gaze rows into inference.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

Use this clinic after the [Analysis handoff](analysis-handoff.md) has produced
model-ready measurement rows and before specialist statistical software chooses the
model structure.

!!! warning "Many gaze rows do not create many independent participants"
    Samples, fixations, AOI rows, events, and trials can repeat within the same
    participant, stimulus, session, or experimental unit. Treating those rows as
    independent replicates can create pseudoreplication.

!!! warning "This clinic does not choose a mixed-model specification"
    GazeForge records grouping identities and dependence risks. It does not
    automatically choose fixed effects, random intercepts, random slopes, covariance
    structures, cluster-robust standard errors, GEE, LMM/GLMM, Bayesian hierarchical
    models, or another estimator.

## Four units to name explicitly

Before modelling, distinguish four concepts.

| Unit | Question | Example |
| --- | --- | --- |
| **Observation row** | What does one table row represent? | participant × trial × AOI |
| **Measurement unit** | What observable was constructed? | trial-level AOI dwell |
| **Inferential unit** | At what experimental/statistical level is the target contrast defined? | participant-trial repeated observation |
| **Generalisation unit** | To what population/material class is the claim intended to extend? | participants, stimuli, sessions, or a bounded combination |

These units can differ. A fixation-level table can still have a participant-level or
participant-trial inferential structure.

## Repeated observations within participant

Eye-tracking studies commonly contain many observations from each participant:

~~~text
participant
  ├── session
  │    ├── trial
  │    │    ├── AOI outcomes
  │    │    ├── event outcomes
  │    │    └── scanpath features
  │    └── ...
  └── ...
~~~

Repeated rows share participant-level influences and therefore should not be described
as independent participants.

Preserve at least:

- participant identity;
- trial/session identity;
- condition;
- stimulus identity when materials repeat;
- AOI/event identity when rows repeat by measure;
- denominator/exposure and missing/censoring status;
- QC/review/exclusion status.

## Nested versus crossed is a design statement

A grouping structure should be justified from the study design.

### Nested example

If trial IDs are unique only within participant, it can be meaningful to describe
trials as indexed/nested within participant.

### Crossed example

If the same advertisement, image, webpage, or video is viewed by multiple
participants, participant and stimulus are **crossed identities** in the design.

~~~text
participant P01 → stimulus S01, S02, S03
participant P02 → stimulus S01, S02, S03
participant P03 → stimulus S01, S02, S03
~~~

This does not automatically imply a particular random-effects formula. It means the
stimulus identity must survive the handoff so specialist modelling can represent the
design appropriately.

## Stimulus identity and generalisation

If a study uses a small set of stimuli and then makes claims about a broader class of
advertisements, interfaces, images, or destinations, stimulus sampling and stimulus
dependence matter.

A model that conditions on a fixed set of stimuli can support a different
generalisation claim from one whose design and model represent variability across
stimuli.

Do not silently remove `stimulus_id` after assigning condition labels.

!!! note "Stimulus-as-fixed-effect limitation"
    Treating stimuli only as fixed materials can be a defensible design choice in some
    studies, but it constrains the supported generalisation. This clinic records the
    design identity; it does not decide whether stimuli should enter as fixed effects,
    random effects, strata, clusters, or another structure.

## AOI and event rows are repeated measurements

A participant can contribute several AOI rows within one trial.

~~~text
P01 × T01 × brand
P01 × T01 × claim
P01 × T01 × disclosure
P01 × T01 × product
~~~

Those four rows are not four participants.

The same applies to event-type rows, multiple windows, repeated visits, sequence
features, and multiple derived outcomes.

## Pseudoreplication stop conditions

Stop before inferential modelling when any of these are true:

- samples or fixations are being treated as independent participants;
- participant identity has been dropped from repeated rows;
- trial/session identity was lost even though the analysis uses repeated observations;
- recurring stimulus/material identity was discarded;
- AOI/event rows are counted as independent experimental units;
- participant-condition means silently replaced trial-level model inputs;
- the declared generalisation unit cannot be reconstructed;
- the only record of grouping lives in plotting code rather than the analysis table.

## Descriptive aggregation versus inferential aggregation

Participant × condition means can be excellent for descriptive plots and tables.

They can also change the inferential problem if they replace trial-level rows.

### Descriptive use

~~~text
trial-level inferential input
        ↓
participant-condition summary
        ↓
figure / descriptive table only
~~~

### Changed analysis

~~~text
trial-level registered estimand
        ↓
participant-condition aggregation
        ↓
different variance/dependence representation
        ↓
potentially different inferential target
~~~

Do not let convenience aggregation silently redefine the analysis.

## Measurement construction can aggregate without creating pseudoreplication

Some aggregation is part of the prespecified measurement definition.

Example:

~~~text
fixation rows
  ↓ prespecified AOI aggregation
participant × trial × AOI dwell
~~~

That is different from treating fixation rows as independent inferential units.

The [Outcome & estimand preregistration clinic](estimand-preregistration.md) should
state the intended measurement construction before model fitting.

## Missingness, QC, and exclusions must preserve grouping

When rows are missing, censored, flagged, or excluded, retain the grouping identities
needed to understand which units lost information.

Use:

- [Denominator, exposure & censoring](denominator-exposure-censoring.md) for observable
  support and censoring;
- [Missing-data assumptions](missing-data-assumptions.md) for missing-data mechanism
  assumptions and treatment handoff;
- [QC review & exclusion ledger](qc-review-exclusion-ledger.md) for reviewed exclusion
  decisions.

Do not complete-case filter away participant/stimulus structure before those decisions
are auditable.

## Small variance does not erase the design

A small, zero-boundary, or unavailable estimated variance component is a model
diagnostic/result from specialist software. It does not retroactively prove that a
participant, stimulus, session, or other grouping identity was scientifically
irrelevant.

Keep design identity separate from model diagnostics.

Use the [Model diagnostics & convergence clinic](model-diagnostics-convergence.md)
after fitting.

## Specialist-statistics handoff

The grouping audit can hand off identities such as:

~~~text
participant_id
trial_id
session_id
stimulus_id
condition
aoi_label / event_type
outcome_id
estimand_id
analysis_population_id
~~~

The specialist statistical plan then decides how those identities enter the model.

GazeForge deliberately leaves these choices unselected:

- fixed effects;
- random intercepts;
- random slopes;
- covariance structure;
- cluster-robust standard errors;
- GEE correlation structure;
- LMM/GLMM;
- Bayesian hierarchical model;
- another design-appropriate estimator.

## Worked grouping audit

Run:

~~~bash
python examples/20_worked_grouping_pseudoreplication_audit.py \
  --output-dir worked-grouping-pseudoreplication-audit
~~~

The deterministic teaching bundle writes:

~~~text
01_unit_registry.csv
02_grouping_structure.csv
03_row_independence_audit.csv
04_aggregation_risk_register.csv
05_crossed_nested_handoff.csv
06_reporting_language.csv
07_api_route_map.csv
README.md
grouping_pseudoreplication_manifest.json
~~~

The example deliberately contains:

- fixation rows incorrectly treated as independent participants;
- a participant × trial × AOI handoff with grouping preserved;
- participant-condition aggregation that changes the inferential representation;
- the same aggregation used appropriately for descriptive plotting;
- nested trial identity;
- crossed participant × stimulus identity;
- repeated AOI identity.

The bundle is `synthetic_demo_not_empirical_evidence`.

## Reporting examples

### Methods

> Model-ready gaze outcomes retained participant, trial, stimulus, and AOI/event
> identities needed to represent repeated observations. Observation-row identity was
> distinguished from the prespecified inferential and generalisation units.

### Crossed stimuli

> The same stimuli were viewed by multiple participants; stimulus identity was
> therefore retained in the statistical handoff rather than being discarded after
> condition coding.

### Descriptive aggregation

> Participant-condition means were used for descriptive visualization only and did not
> replace the registered trial-level inferential input.

### Specialist model structure

> Grouping identities were transferred to the prespecified specialist statistical
> workflow. GazeForge did not automatically select fixed effects, random effects,
> covariance structures, clustering corrections, or the estimator.

### Limitation

> The grouping audit preserves dependence and generalisation identities but does not
> establish that any specific hierarchical, marginal, cluster-robust, or Bayesian
> model is correct.

## Interpretation

A clean grouping audit supports the statement that the analysis handoff preserved the
design identities needed for specialist modelling.

It does **not** establish:

- independence of repeated observations;
- the correct random-effects structure;
- the correct covariance structure;
- negligible stimulus or participant variability;
- causal identification;
- construct validity;
- device validity;
- external validity.

## API and workflow links

This clinic uses existing public surfaces rather than introducing a new model-selection
API:

- [Schema API](api-reference.md#schema) — preserve participant/trial/time identity.
- [Quality-control API](api-reference.md#quality-control) — retain QC evidence without
  turning it into grouping or exclusion decisions.
- [Eye-events API](api-reference.md#eye-events) — preserve event identity before
  aggregation.
- [Semantic AOI API](api-reference.md#semantic-aois) and
  [Dynamic AOI API](api-reference.md#dynamic-aois) — preserve AOI/stimulus/time
  identities.
- [Scanpath API](api-reference.md#scanpaths) — preserve participant/trial sequence
  identity.
- [Hierarchical location-scale API](api-reference.md#hierarchical-location-scale-models)
  — an existing specialist modelling surface; its availability does not make it an
  automatic model choice.

Continue through [Outcome & estimand preregistration](estimand-preregistration.md),
[Analysis handoff](analysis-handoff.md),
[Model diagnostics & convergence](model-diagnostics-convergence.md),
[Uncertainty, multiplicity & inferential reporting](inferential-reporting-audit.md),
[Sensitivity & robustness](sensitivity-robustness-clinic.md), and
[Reporting & interpretation](reporting-clinic.md).
