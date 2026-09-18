---
description: Choose the GazeForge method or workflow that matches the research question, input evidence, generalisation unit, and intended claim.
search:
  boost: 1.6
---

# Method chooser

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Decision guide</strong> · Choose a workflow from the scientific question and available evidence, not from the name of a Python function.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

GazeForge contains several ways to import, review, label, summarize, and validate gaze data. The right route depends on **what you are trying to learn**, **what evidence you actually have**, and **which unit must generalize**.

!!! warning "Do not choose a method from a headline metric"
    A workflow that is useful for one question can be invalid for another. Start from the study unit, reference labels, source identity, timebase, AOI support, and intended generalisation unit. Software availability is not scientific justification.

## Quick chooser

| Research need | Required input | Generalisation / grouping unit to protect | Start with | Primary outputs | Validation requirement | Do not infer | Continue to |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Import a tracker export | authoritative source mapping, units, geometry | participant/trial identity must survive import | [Worked tracker import + QC](worked-tracker-import.md) | canonical gaze + preflight + import contract | transformation checks | adapter compatibility ≠ device validity | [QC review](qc-review-exclusion-ledger.md) |
| Inspect data quality | canonical gaze + sampling assumptions | participant/trial boundaries | [Synthetic QC](tutorial-synthetic-qc.md) | anomaly flags + trial quality | review against study policy | flag ≠ invalid observation | [QC review](qc-review-exclusion-ledger.md) |
| Apply exclusions | immutable pre-review QC + criteria | sample/trial/participant scope | [QC review & exclusion ledger](qc-review-exclusion-ledger.md) | criteria + review ledgers + denominator flow | prespecification/review provenance | reproducible rule ≠ validated rule | analysis derivative |
| Create an inspectable event baseline | gaze samples + rate/timebase | trial boundaries | [I-VT baseline](tutorial-ivt-baseline.md) | event-labelled samples + intervals | threshold sensitivity where relevant | example threshold ≠ universal physiology | [Event validation](event-model-validation-clinic.md) |
| Fit a learned event classifier | expert/reference labels | **participant** or intended deployment unit | [Event-model validation clinic](event-model-validation-clinic.md) | held-out predictions + sample/event metrics | leakage-safe held-out validation | training fit ≠ validated performance | [Validation reporting](validation-reporting-cookbook.md) |
| Compare event models | same held-out rows for every model | same folds / same units | [Worked validation study](runnable-examples.md#7-worked-event-model-validation-study) | matched predictions + model summary | paired/matched held-out comparison | one metric ≠ overall superiority | [Model comparison](model-comparison.md) |
| Assess probability quality | held-out class probabilities | same held-out units as classifier claim | [Calibration](calibration.md) | calibration bins + Brier/ECE + confidence/coverage | held-out probabilities only | confidence ≠ correctness | [Validation reporting](validation-reporting-cookbook.md) |
| Use static AOIs | reviewed stimulus geometry | stimulus/version identity | [First study blueprint](first-study-blueprint.md) | AOI definitions + fixation assignments | AOI construct rationale | AOI membership ≠ psychological state | scanpaths / analysis |
| Use moving AOIs | reviewed timestamped keyframes/tracks | stimulus + timebase | [Worked dynamic-AOI study](worked-dynamic-aoi-study.md) | keyframes + interpolation audit + assignments | support/no-extrapolation checks | detected track ≠ ground truth | scanpaths / dynamic evaluation |
| Build semantic scanpaths | reviewed fixation/AOI assignments | participant/trial sequence identity | [Practical workflow](practical-workflow.md) | semantic sequence table | assignment provenance | sequence ≠ latent mental state | downstream sequence analysis |
| Build statistical model inputs | reviewed event/AOI outputs + design/coverage | participant/trial hierarchy | [Analysis handoff](analysis-handoff.md) | trial × AOI/event measures + denominators + censoring | preserve missing/zero/exposure semantics | samples/fixations ≠ independent participants | specialist statistical software |
| Interpret a gaze-derived measure | frozen observable + intended substantive claim | declared measurement/inferential unit | [Measurement & interpretation clinic](measurement-interpretation.md) | claim registry + threats + sensitivity/reporting boundaries | construct bridge must be explicit | gaze observable ≠ latent construct | [Reporting clinic](reporting-clinic.md) |
| Freeze a study | reviewed analysis derivative + final settings | exact source/software identity | [Study lifecycle](study-lifecycle.md) | manifest + provenance + fingerprints | deterministic reconstruction | reproducibility ≠ external validity | [Publication readiness](publication-readiness.md) |
| Prepare a paper/archive | reconciled denominators + final results | claim-specific population/unit | [Research evidence bundle](research-evidence-bundle.md) | artifact index + methods/figures/tables + provenance/manifest | evidence class must match wording | archive completeness ≠ validity | [Reporting clinic](reporting-clinic.md) |
| Write claim-safe Methods/Results/captions | frozen evidence bundle + reporting facts | claim-specific population/unit | [Reporting & interpretation clinic](reporting-clinic.md) | methods/results examples + citation table + evidence boundaries | wording must match evidence identity | prose cannot strengthen evidence | [Publication readiness](publication-readiness.md) |
| Evaluate benchmark evidence | exact source/provenance + labels | participant/source/dataset identity | [Validation guide](validation-evidence-guide.md) | evidence status/certificate/report | benchmark-specific | derived/native or token/participant distinctions cannot be collapsed | [Evidence status](evidence-status.md) |

## Decision rules that should stop the workflow

### No expert/reference labels

You can run a transparent descriptive event baseline, but do **not** describe a learned classifier as empirically validated merely because it produces labels or probabilities.

### Participant-level generalisation claim

Use participant-disjoint splitting. Random row splitting is not a substitute when observations from the same participant are correlated across train and test.

### Only opaque source tokens are available

Report **source-token-disjoint** if that is what the evidence supports. Do not rename it participant-disjoint without an authoritative token→participant mapping.

### Lower-rate evidence is derived from higher-rate acquisition

Call it **derived**. Derived 60 Hz evidence is not native 60 Hz or native Gazepoint/GP3 validation.

### QC anomaly is detected

Treat it as review evidence. Do not convert `qc_flag=True` directly into sample, trial, or participant exclusion unless the study policy explicitly specifies and reviews that decision.

### Moving AOI falls outside reviewed temporal support

Return unassigned / unsupported according to the declared workflow. Preserve **no extrapolation** unless a separately justified policy explicitly allows extrapolation.

### One model leads on one metric

Report the metric-specific result. Sample-level classification, event-boundary fidelity, calibration, confidence/coverage, and downstream utility answer different questions.

### A model-ready table contains missing values

Stop before replacing them. Use the [Analysis handoff](analysis-handoff.md) to distinguish observed zeros from missing trials, AOIs absent by design, undefined denominators, and right-censored latency. Preserve participant/trial grouping to avoid pseudoreplication.

### The statistical model fails diagnostics or convergence

Do not treat returned coefficients as a valid result. GazeForge does not automatically select or rescue an inferential estimator; resolve the statistical specification and diagnostics in the prespecified specialist analysis environment.

### A gaze result is being used as a psychological construct

Open the [Measurement & interpretation clinic](measurement-interpretation.md). Separate the observable from the proposed construct, name the external outcome/theory required, review measurement threats, and keep unsupported latent-state language out of the result.

### The analysis is frozen but the manuscript wording feels stronger than the evidence

Use the [Reporting & interpretation clinic](reporting-clinic.md). Preserve import/device, QC/exclusion, split identity, calibration/correctness, native/derived rate, synthetic/empirical, and observable/latent-state distinctions in prose and captions.

## Which event route should I use?

```text
Do you have suitable reference labels?
│
├─ No
│  ├─ Need transparent descriptive segmentation?
│  │     → I-VT / angular I-VT baseline
│  └─ Need a validated learned classifier?
│        → stop; acquire/audit labelled reference data first
│
└─ Yes
   ├─ Is participant identity available?
   │  ├─ Yes → participant-disjoint validation when participants must generalize
   │  └─ No  → report the weaker identity boundary actually supported
   │
   ├─ Need probability interpretation?
   │     → add calibration + confidence/coverage
   │
   └─ Need temporal boundary performance?
         → add event-F1 / temporal IoU / boundary-sensitive metrics
```

## Which AOI route should I use?

```text
Static stimulus?
└─ define/propose AOIs → review → freeze AOIs → assign fixations

Moving stimulus?
└─ reviewed keyframes/tracks
      → verify timebase
      → bounded interpolation
      → no extrapolation outside support
      → assign fixations
      → retain interpolation/assignment audit
```

AI proposals remain proposals until the study's review policy is satisfied.

## Which evidence should I keep?

Use the [Artifact & output dictionary](artifact-dictionary.md) to identify which CSV/JSON is source evidence, QC/review evidence, an analysis derivative, validation evidence, or reporting/provenance metadata.

Run the [Worked research evidence bundle](research-evidence-bundle.md) to see those layers assembled into one deterministic archive-facing output directory, then use [Publication readiness](publication-readiness.md) before freezing manuscript claims.

## Method choice is not a ranking

This page does not identify a universal “best” event model, AOI method, threshold, or validation metric. It routes methods to questions and evidence conditions. Performance comparisons belong in the corresponding held-out validation context.
