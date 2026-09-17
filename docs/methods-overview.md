# Methods overview

GazeForge has a broad technical surface, but most studies only need a subset of it. Start from the research task below, then move to the detailed method page that matches the analysis you actually need. For a shorter task-first route with expected artifacts and claim boundaries, use [Research recipes](research-recipes.md).

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

### :material-eye-outline: Model & validate eye events

Begin with transparent event rules when appropriate, then add learned classifiers only with a leakage-safe held-out design, matched comparisons, calibration, confidence/coverage, and event-level evaluation.

**Start:** [Event-model validation clinic](event-model-validation-clinic.md)  
**Run it:** [Worked validation study](runnable-examples.md#7-worked-event-model-validation-study)  
**Then:** [Temporal models](temporal-models.md) · [Model comparison](model-comparison.md) · [Event-level evaluation](event-level-evaluation.md) · [Calibration & dataset holdouts](calibration.md)

</div>

<div class="gf-path-card" markdown>

### :material-vector-rectangle: Build semantic or dynamic AOIs

Represent static regions directly or use reviewable proposals and time-bounded geometry for moving stimuli.

**Start:** [Dynamic AOIs](dynamic-aois.md)  
**Run it:** [Worked dynamic-AOI study](worked-dynamic-aoi-study.md)  
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
**Do event validation:** [Event-model validation clinic](event-model-validation-clinic.md)  
**Plan/report:** [Study-design templates](study-design-templates.md) · [Validation reporting cookbook](validation-reporting-cookbook.md) · [Reproducible reporting](reproducible-reporting.md)

</div>

</div>

## Method map

| Research question | Primary method pages | Typical reviewable output |
| --- | --- | --- |
| How should tracker data enter GazeForge? | [Real-data import clinic](data-import-clinic.md), [Adapters & validation](adapters-validation.md) | canonical gaze table with declared units/rate and source provenance |
| Which samples or trials need review? | [Motion-quality gating](motion-quality-gating.md), [Synthetic QC tutorial](tutorial-synthetic-qc.md) | flags, weights, quality summaries; source rows retained |
| How should gaze samples become event labels? | [I-VT tutorial](tutorial-ivt-baseline.md), [Temporal models](temporal-models.md) | labels/probabilities with model and threshold provenance |
| How should a learned event model be validated? | [Event-model validation clinic](event-model-validation-clinic.md), [Model comparison](model-comparison.md), [Calibration](calibration.md) | participant/split ledger, matched held-out predictions, probabilities, sample/event metrics, calibration and coverage |
| How should event performance be evaluated? | [Event-level evaluation](event-level-evaluation.md), [Stratified performance](stratified-event-performance.md), [Matched-fold differences](paired-model-differences.md), [Calibration](calibration.md) | held-out metrics, matched differences, calibration tables with the split unit named |
| How should moving semantic regions be represented? | [Dynamic AOIs](dynamic-aois.md), [Worked dynamic-AOI study](worked-dynamic-aoi-study.md), [Video-frame derivation](video-frame-derivation.md), [Dynamic AOI evaluation](dynamic-aoi-evaluation.md) | reviewed keyframes, bounded interpolation, no-extrapolation audit, fixation assignments |
| How can AI propose visual regions without becoming the empirical record? | [Grounding DINO + SAM 2 backend](grounded-sam2-backend.md), [Dynamic AOIs](dynamic-aois.md) | proposals plus confidence and review decisions |
| How should sequence/process structure be represented? | [Research workflows](research-workflows.md), [Practical workflow](practical-workflow.md) | semantic scanpaths and provenance-bound exports |
| How should a study be preregistered and archived? | [Study-design templates](study-design-templates.md), [Study lifecycle](study-lifecycle.md), [Publication readiness](publication-readiness.md) | explicit acquisition/QC/AOI/split/rate/archive records |
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
leakage-safe evaluation + calibration
        ↓
reviewed static/dynamic AOIs / fixation assignments / scanpaths
        ↓
statistics or hierarchical models
        ↓
provenance + evidence boundary + reproducible report
```

The order is deliberately review-first. AI-generated anomaly flags, event probabilities, or AOI boxes remain inspectable analytic data; they do not silently overwrite the source observations.

## Event modelling: baseline before complexity

For a new dataset, a transparent baseline can make model behaviour easier to inspect before a learned classifier is introduced. The [I-VT tutorial](tutorial-ivt-baseline.md) shows a deterministic pixel-velocity baseline. When expert-labelled events are available, use the [Event-model validation clinic](event-model-validation-clinic.md) to preserve participant identity, leakage checks, matched held-out rows, probabilities, calibration, confidence/coverage, and separate sample/event estimands. Then use [model comparison](model-comparison.md), [matched-fold differences](paired-model-differences.md), [event-level evaluation](event-level-evaluation.md), [stratified performance](stratified-event-performance.md), and [calibration](calibration.md) for the required detail.

A method being available in the package does not establish that it is superior for a new population, device, sampling regime, or task. Those are empirical questions that require an appropriate validation design. Likewise, a confidence threshold chosen for one validation design is not a universal abstention cutoff.

## AOIs and scanpaths: observable structure, not latent state

Semantic and dynamic AOIs describe where reviewed regions are located. Scanpaths describe observable fixation order across those regions. Neither surface, by itself, establishes emotion, persuasion, comprehension, intent, diagnosis, or another latent psychological state.

For video or moving interfaces, use [Dynamic AOIs](dynamic-aois.md) with bounded interpolation and explicit review. The [worked dynamic-AOI study](worked-dynamic-aoi-study.md) demonstrates exact keyframes, interpolation within a declared maximum gap, fixation assignment, semantic sequences, and explicit **no extrapolation** before/after the observed track. For end-to-end static composition from events to AOI assignments and scanpaths, use the [practical workflow](practical-workflow.md).

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

If you are starting from a real tracker or processed export, use the [Real-data import clinic](data-import-clinic.md) first. If you are validating a learned event classifier, continue with the [Event-model validation clinic](event-model-validation-clinic.md) and run `examples/06_worked_event_model_validation.py` before adapting the structure to real labelled data. If you know the task but not the API, open [Research recipes](research-recipes.md). If you want executable examples, open the [Runnable examples gallery](runnable-examples.md): static studies can start from the [worked advertising/interface study](worked-advertising-study.md), moving stimuli can start from the [worked dynamic-AOI study](worked-dynamic-aoi-study.md), and learned event validation can start from the [worked validation study](runnable-examples.md#7-worked-event-model-validation-study). Use the [Study-design templates](study-design-templates.md) to freeze the corresponding preregistration, acquisition, QC, AOI, split, native/derived, and archive records, and the [Validation reporting cookbook](validation-reporting-cookbook.md) to keep manuscript wording proportional to the design.
