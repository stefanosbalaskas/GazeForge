# Methods overview

GazeForge has a broad technical surface, but most studies only need a subset of it. Start from the research task below, then move to the detailed method page that matches the analysis you actually need.

!!! note "Methods are not evidence claims"
    This page organizes software methods and analysis choices. It does not change the generated [Evidence status](evidence-status.md), promote a benchmark, or turn synthetic/demo output into empirical validation. Device adapters likewise do not establish device-specific validity.

## Choose by research task

<div class="gf-path-grid" markdown>

<div class="gf-path-card" markdown>

### :material-database-import-outline: Prepare & quality-check gaze

Use explicit adapters, canonical units, participant/trial identity, and non-destructive quality signals before modelling.

**Start:** [Real-data import clinic](data-import-clinic.md)  
**Then:** [Adapters & validation](adapters-validation.md) · [Motion-quality gating](motion-quality-gating.md) · [Synthetic QC tutorial](tutorial-synthetic-qc.md)

</div>

<div class="gf-path-card" markdown>

### :material-eye-outline: Model eye events

Begin with transparent event rules when appropriate, then add temporal models, matched comparisons, calibration, and event-level evaluation when labelled data support them.

**Start:** [Temporal models](temporal-models.md)  
**Then:** [Model comparison](model-comparison.md) · [Event-level evaluation](event-level-evaluation.md) · [Calibration & dataset holdouts](calibration.md)

</div>

<div class="gf-path-card" markdown>

### :material-vector-rectangle: Build semantic or dynamic AOIs

Represent static regions directly or use reviewable proposals and time-bounded geometry for moving stimuli.

**Start:** [Dynamic AOIs](dynamic-aois.md)  
**Then:** [Grounding DINO + SAM 2](grounded-sam2-backend.md) · [Verified video-frame derivation](video-frame-derivation.md) · [Dynamic AOI evaluation](dynamic-aoi-evaluation.md)

</div>

<div class="gf-path-card" markdown>

### :material-chart-timeline-variant: Represent scanpaths & process

Convert reviewed fixation-to-AOI assignments into observable sequence structures for description, similarity, embeddings, and downstream modelling.

**Start:** [Research workflows](research-workflows.md)  
**Run it:** [Practical end-to-end workflow](practical-workflow.md)

</div>

<div class="gf-path-card" markdown>

### :material-chart-bell-curve-cumulative: Fit hierarchical distributional models

Use the location-scale family when the scientific question concerns both conditional location and residual scale, including random slopes, covariance structure, calibration, and bootstrap uncertainty.

**Start:** [Hierarchical location-scale models](hierarchical-location-scale.md)  
**Then:** [Correlated location-scale effects](correlated-location-scale.md) · [Location random-slope scale model](location-random-slope-scale.md) · [Full-covariance model](full-covariance-location-random-slope-scale.md)

</div>

<div class="gf-path-card" markdown>

### :material-shield-search-outline: Validate, audit & report

Keep split design, sampling-rate handling, calibration, benchmark provenance, frozen evidence, and manuscript-facing software identity visible.

**Start:** [Validation guide](validation-evidence-guide.md)  
**Then:** [Evidence status](evidence-status.md) · [Validation scope certificates](validation-scope-certificates.md) · [Reproducible reporting](reproducible-reporting.md)

</div>

</div>

## Method map

| Research question | Primary method pages | Typical reviewable output |
| --- | --- | --- |
| How should tracker data enter GazeForge? | [Real-data import clinic](data-import-clinic.md), [Adapters & validation](adapters-validation.md) | canonical gaze table with declared units/rate and source provenance |
| Which samples or trials need review? | [Motion-quality gating](motion-quality-gating.md), [Synthetic QC tutorial](tutorial-synthetic-qc.md) | flags, weights, quality summaries; source rows retained |
| How should gaze samples become event labels? | [Temporal models](temporal-models.md), [Model comparison](model-comparison.md) | labels/probabilities with model and threshold provenance |
| How should event performance be evaluated? | [Event-level evaluation](event-level-evaluation.md), [Stratified performance](stratified-event-performance.md), [Matched-fold differences](paired-model-differences.md), [Calibration](calibration.md) | participant-disjoint metrics, matched differences, calibration tables |
| How should moving semantic regions be represented? | [Dynamic AOIs](dynamic-aois.md), [Video-frame derivation](video-frame-derivation.md), [Dynamic AOI evaluation](dynamic-aoi-evaluation.md) | reviewed keyframes, bounded interpolation, fixation assignments |
| How can AI propose visual regions without becoming the empirical record? | [Grounding DINO + SAM 2 backend](grounded-sam2-backend.md), [Dynamic AOIs](dynamic-aois.md) | proposals plus confidence and review decisions |
| How should sequence/process structure be represented? | [Research workflows](research-workflows.md), [Practical workflow](practical-workflow.md) | semantic scanpaths and provenance-bound exports |
| How can conditional variability be modelled? | [Hierarchical location-scale](hierarchical-location-scale.md), [Correlated location-scale](correlated-location-scale.md) | location/scale effects with explicit model assumptions |
| How can random slopes and covariance be represented? | [Location random-slope scale](location-random-slope-scale.md), [Correlated random-slope scale](correlated-location-random-slope-scale.md), [Full-covariance random-slope scale](full-covariance-location-random-slope-scale.md) | random-effect/covariance estimates and diagnostics |
| How should location-scale uncertainty and calibration be checked? | [Residual calibration](location-scale-residual-calibration.md), [Conditional refit calibration](location-scale-refit-residual-calibration.md), [Hierarchical bootstrap](location-scale-hierarchical-bootstrap.md), [Bootstrap Monte Carlo precision](location-scale-bootstrap-monte-carlo.md) | calibration diagnostics and uncertainty summaries |

## A useful order of operations

```text
source / tracker export
        ↓
explicit adapter + canonical schema
        ↓
non-destructive QC / reliability evidence
        ↓
transparent or learned event model
        ↓
participant-disjoint evaluation + calibration
        ↓
reviewed AOIs / fixation assignments / scanpaths
        ↓
statistics or hierarchical models
        ↓
provenance + evidence boundary + reproducible report
```

The order is deliberately review-first. AI-generated anomaly flags, event probabilities, or AOI boxes remain inspectable analytic data; they do not silently overwrite the source observations.

## Event modelling: baseline before complexity

For a new dataset, a transparent baseline can make model behaviour easier to inspect before a learned classifier is introduced. The [I-VT tutorial](tutorial-ivt-baseline.md) shows a deterministic pixel-velocity baseline. When expert-labelled events are available, continue with [model comparison](model-comparison.md), [matched-fold differences](paired-model-differences.md), [event-level evaluation](event-level-evaluation.md), [stratified performance](stratified-event-performance.md), and [calibration](calibration.md).

A method being available in the package does not establish that it is superior for a new population, device, sampling regime, or task. Those are empirical questions that require an appropriate validation design.

## AOIs and scanpaths: observable structure, not latent state

Semantic and dynamic AOIs describe where reviewed regions are located. Scanpaths describe observable fixation order across those regions. Neither surface, by itself, establishes emotion, persuasion, comprehension, intent, diagnosis, or another latent psychological state.

For video or moving interfaces, use [Dynamic AOIs](dynamic-aois.md) with bounded interpolation and explicit review. For end-to-end composition from events to AOI assignments and scanpaths, use the [practical workflow](practical-workflow.md).

## Distributional modelling

The location-scale family is intentionally separated into pages because the models answer different structural questions. Start with [Hierarchical location-scale models](hierarchical-location-scale.md), then add correlation or random-slope structure only when the design and estimand require it:

- [Correlated location-scale effects](correlated-location-scale.md)
- [Location random-slope scale model](location-random-slope-scale.md)
- [Correlated location random-slope scale model](correlated-location-random-slope-scale.md)
- [Full-covariance location random-slope scale model](full-covariance-location-random-slope-scale.md)
- [Location-scale residual calibration](location-scale-residual-calibration.md)
- [Conditional refit residual calibration](location-scale-refit-residual-calibration.md)
- [Hierarchical parametric bootstrap](location-scale-hierarchical-bootstrap.md)
- [Bootstrap Monte Carlo precision](location-scale-bootstrap-monte-carlo.md)

## Keep method choice separate from evidence strength

For empirical claims, use the [Validation guide](validation-evidence-guide.md) and generated [Evidence status](evidence-status.md) rather than inferring validity from method availability.

In particular:

- derived lower-rate evidence remains derived and does not establish native 60 Hz or Gazepoint GP3 validity;
- source-token-disjoint Hollywood2EM evidence is not participant-disjoint;
- current Gaze-in-the-Wild participant-disjoint evidence remains task-agnostic while complete authoritative numeric task mapping is unresolved; and
- current VISUS evidence remains bounded partial public-derivative evidence rather than a full-dataset or native-GP3 validation claim.

## Run instead of browse

If you are starting from a real tracker or processed export, use the [Real-data import clinic](data-import-clinic.md) first. If you want executable examples before reading individual method pages, open the [Runnable examples gallery](runnable-examples.md). For one composed workflow that writes tables, figures, fingerprints, provenance, and a manifest, use the [Practical end-to-end workflow](practical-workflow.md).
