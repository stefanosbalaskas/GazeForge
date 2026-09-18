# Learning paths

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>How-to router</strong> · Choose a learning route from the research task rather than from package internals.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>


GazeForge spans data preparation, quality control, human review, eye-event modelling, semantic AOIs, scanpaths, benchmark validation, and scientific provenance. You do not need to learn every layer before starting.

If you are not yet sure what the package does, begin with the [GazeForge Tour](gazeforge-tour.md). It is the canonical orientation route: one gaze table goes through the main layers and produces ordinary CSV/JSON artifacts you can inspect. If you understand the package but need to turn a research question into a complete study workflow, continue with the [First study blueprint](first-study-blueprint.md). If the task is already clear but the method is not, use the [Method chooser](method-chooser.md); if the files are unfamiliar, use the [Artifact & output dictionary](artifact-dictionary.md).

Choose the path that matches your immediate research question. If you are planning an entire study rather than learning one method, use the [Study lifecycle](study-lifecycle.md) as the orchestration layer from acquisition through publication. If you already know the task you need to perform, the [Research recipes](research-recipes.md) page gives the shortest defensible route and the artifacts to retain.

<div class="gf-path-grid" markdown>

<div class="gf-path-card" markdown>

### :material-map-search-outline: I am new — what does GazeForge do?

Run the smallest package-wide walkthrough before choosing a specialist method. See canonicalisation, QC, transparent events, AOIs, scanpaths, provenance, and the resulting output bundle in one place.

**Next:** [GazeForge Tour](gazeforge-tour.md)  
**Run it:** `python examples/00_gazeforge_tour.py --output-dir gazeforge-tour-demo`

</div>

<div class="gf-path-card" markdown>

### :material-database-arrow-right-outline: I have a real tracker export

Start with the executable import/QC route before event modelling. Preserve the source, declare identity/time/coordinate semantics, compare nominal rate with observed timestamp cadence, inspect duplicate keys and bounds, then add non-destructive QC.

**Next:** [Worked tracker import and QC](worked-tracker-import.md)  
**Deep guide:** [Real-data import clinic](data-import-clinic.md)

</div>

<div class="gf-path-card" markdown>

### :material-clipboard-text-search-outline: QC found problems; what do I exclude?

Do not map anomaly flags directly to deletion. Keep pre-review QC immutable, record criteria and denominators, distinguish prespecified from exploratory rules, and create a separate reviewed analysis derivative.

**Next:** [QC review and exclusion ledger](qc-review-exclusion-ledger.md)  
**Run it:** `python examples/08_worked_qc_review_ledger.py --output-dir worked-qc-review-ledger-demo`

</div>

<div class="gf-path-card" markdown>

### :material-rocket-launch-outline: I want a first result

Start with a deterministic synthetic dataset, canonicalise it, add QC flags, and inspect trial-level quality.

**Time:** about 15 minutes  
**Next:** [Synthetic QC tutorial](tutorial-synthetic-qc.md)

</div>

<div class="gf-path-card" markdown>

### :material-eye-outline: I need eye-event labels

Begin with the transparent I-VT baseline before fitting a learned classifier. This gives you a reference whose decision rule is directly inspectable.

**Time:** about 20 minutes  
**Next:** [I-VT baseline tutorial](tutorial-ivt-baseline.md)

</div>

<div class="gf-path-card" markdown>

### :material-chart-box-outline: I need to validate a learned event model

Keep participant identity, held-out folds, probabilities, sample/event metrics, calibration, confidence/coverage, and model-selection boundaries explicit.

**Next:** [Event-model validation clinic](event-model-validation-clinic.md)  
**Run it:** [Worked validation study](runnable-examples.md#7-worked-event-model-validation-study)

</div>

<div class="gf-path-card" markdown>

### :material-vector-rectangle: I have a video or moving interface

Use timestamped dynamic AOI keyframes, bounded interpolation, explicit review, and fixation assignment without extrapolating geometry outside the observed track.

**Next:** [Worked dynamic-AOI study](worked-dynamic-aoi-study.md)

</div>

<div class="gf-path-card" markdown>

### :material-archive-check-outline: I need a reviewable manuscript/archive bundle

Keep source identity, pre-review QC, reviewed decisions, primary-analysis rows, downstream derivatives, provenance, fingerprints, and reporting metadata as distinct evidence layers.

**Next:** [Research evidence bundle](research-evidence-bundle.md)  
**Run it:** `python examples/09_worked_research_evidence_bundle.py --output-dir worked-research-evidence-bundle`

</div>

<div class="gf-path-card" markdown>

### :material-clipboard-text-clock-outline: I need to freeze outcomes and estimands before modelling

Register primary/secondary/exploratory outcomes, contrasts, exposure/denominator, missing/zero/censoring semantics, sensitivity checks, and a deviation ledger before results exist.

**Next:** [Outcome & estimand preregistration clinic](estimand-preregistration.md)  
**Run it:** `python examples/13_worked_estimand_preregistration.py --output-dir worked-estimand-preregistration`

</div>

<div class="gf-path-card" markdown>

### :material-eye-check-outline: I have a gaze metric and need to know what it supports

Separate the observable from the proposed construct, review validity threats, preserve censoring/exposure, and plan justified sensitivity checks before making a substantive interpretation.

**Next:** [Measurement & interpretation clinic](measurement-interpretation.md)  
**Run it:** `python examples/12_worked_measurement_interpretation_audit.py --output-dir worked-measurement-interpretation-audit`

</div>

<div class="gf-path-card" markdown>

### :material-text-box-check-outline: I need to write Methods, Results, and captions without overclaiming

Translate the frozen evidence identity into claim-safe prose while preserving QC/exclusion, split, sampling, calibration, synthetic/empirical, and observable/latent-state distinctions.

**Next:** [Reporting & interpretation clinic](reporting-clinic.md)  
**Run it:** `python examples/11_worked_manuscript_reporting_bundle.py --output-dir worked-manuscript-reporting-bundle`

</div>

<div class="gf-path-card" markdown>

### :material-shield-check-outline: I need defensible empirical evidence

Use the benchmark/evidence layer only after the split, labels, sampling condition, and source provenance match the claim you intend to make.

**Next:** [Validation guide](validation-evidence-guide.md)

</div>

<div class="gf-path-card" markdown>

### :material-file-document-edit-outline: I am planning or preregistering a study

Use copy-ready records for acquisition metadata, QC/exclusion rules, AOI provenance, split identity, native/derived sampling, archive manifests, and manuscript Methods.

**Next:** [Study-design templates](study-design-templates.md)

</div>

<div class="gf-path-card" markdown>

### :material-shield-search-outline: I need to audit evidence

Read the validation matrix, frozen evidence, source-resolution records, and benchmark-specific claim boundaries before interpreting a headline metric.

**Next:** [Validation status](validation-status.md)

</div>

</div>

## Prefer runnable scripts?

Open the [Runnable examples gallery](runnable-examples.md) for **fifteen deterministic examples/workflows** with exact commands, dependencies, expected outputs, and links to the underlying repository files. Start with the [GazeForge Tour](gazeforge-tour.md) if you need the package-wide mental model. The [worked tracker-import/QC example](worked-tracker-import.md) demonstrates the real-data handoff contract; the [QC review/exclusion-ledger clinic](qc-review-exclusion-ledger.md) demonstrates review and denominator accounting; the [worked advertising/interface study](worked-advertising-study.md) demonstrates a static-stimulus design; the [worked dynamic-AOI study](worked-dynamic-aoi-study.md) demonstrates moving regions, bounded interpolation, and explicit no-extrapolation checks; and the [worked event-model validation study](runnable-examples.md#7-worked-event-model-validation-study) demonstrates participant-disjoint model comparison with separate sample/event/calibration outputs; and the [research evidence bundle](research-evidence-bundle.md) demonstrates how to freeze those layers into an archive-facing directory. For a task-first map, start with [Research recipes](research-recipes.md); for deeper technical documentation, use the [Methods overview](methods-overview.md).

## A practical progression

| Stage | Learn | Produce | Do not claim yet |
| --- | --- | --- | --- |
| **0. Import** | source identity, units, geometry, nominal rate vs observed cadence | immutable source + import contract + preflight | adapter compatibility = device validity |
| **1. Canonicalise** | schema, rate, units, participant/trial boundaries | one vendor-neutral gaze table | comparability across datasets |
| **2. QC** | missingness, gaps, off-screen samples, anomaly flags | reviewable QC columns and trial summaries | automatic exclusion validity |
| **3. Review** | criteria, scope, decisions, denominators, prespecified vs exploratory status | immutable pre-review QC + review/exclusion ledger + reviewed derivative | reproducible exclusion rule = validated rule |
| **4. Baseline** | deterministic I-VT or angular I-VT | inspectable event labels | learned-model superiority |
| **5. Validate** | participant-disjoint folds, matched rows, sample/event metrics, calibration/coverage | split ledger + held-out predictions + validation tables | native-device validity from resampled or synthetic data |
| **6. Extend** | semantic/dynamic AOIs, scanpaths, hierarchical models | task-specific analytic structures | unsupported psychological inference |
| **7. Freeze** | manifests, fingerprints, certificates, source resolution | artifact index + auditable evidence bundle + reviewer README | stronger provenance than the source supports |

For a more complete research route, use the [Outcome & estimand preregistration clinic](estimand-preregistration.md) before modelling; the [Study lifecycle](study-lifecycle.md) ties every stage to a reviewable artifact and explicit claim boundary. The [Study-design templates](study-design-templates.md) make the corresponding records copy-ready.

## Which import and QC workflow should I use?

```text
Do you have authoritative source metadata?
│
├─ No → stop; recover units/identity/geometry from acquisition or export records
│
└─ Yes
   ├─ Gazepoint-style fields + known semantics? → adapt_gazepoint_samples()
   ├─ Other known processed columns?            → adapt_processed_table()
   ├─ Already canonical ms + pixels?            → canonicalize_gaze()
   └─ Then inspect:
        identity · duplicate keys · cadence · bounds · row counts
                              │
                              ▼
                    non-destructive QC
                              │
                              ▼
              review + exclusion ledger
```

Run the [worked tracker-import example](worked-tracker-import.md) for the import path, then the [QC review/exclusion-ledger clinic](qc-review-exclusion-ledger.md) before dropping observations. Successful import is a transformation result, not device/model validation; a QC flag is review evidence, not an automatic exclusion.

## Which event workflow should I use?

```text
Do you already have expert-labelled event data?
│
├─ No
│  ├─ Need a transparent descriptive baseline? → I-VT / angular I-VT
│  └─ Need publishable classifier validation?  → acquire or use an audited labelled corpus first
│
└─ Yes
   ├─ Same participants in train and test?       → stop; use participant-disjoint splitting
   ├─ Only opaque source tokens available?       → report source-token-disjoint, not participant-disjoint
   ├─ Compatible sampling regime?                → fit + validate model
   ├─ Need boundary-sensitive performance?       → add event-F1 / temporal IoU / boundary error
   ├─ Need probability claims?                   → add Brier / ECE / confidence-coverage
   └─ Need lower-rate claims?                    → preserve native vs derived status + sensitivity
```

Use the [Event-model validation clinic](event-model-validation-clinic.md) for the full leakage-safe route and the [Validation reporting cookbook](validation-reporting-cookbook.md) when converting the final design into manuscript wording.

## Which AOI workflow should I use?

```text
Static stimulus
└─ define or propose AOIs → human review → freeze AOIs → assign fixations

Video / moving interface
└─ timestamped keyframes → bounded interpolation → review → dynamic fixation assignment
                                  │
                                  └─ no extrapolation outside the observed track
```

AI-proposed AOIs remain proposals until reviewed. The provenance record should retain model identity, confidence, and any accept/reject/relabel/edit decision. Run the [dynamic worked study](worked-dynamic-aoi-study.md) for a concrete, deterministic example.

## Read results visually

The [results gallery](results-gallery.md) puts the current reviewed benchmark summaries beside their evidence boundaries. It is intended as an orientation layer, not a replacement for frozen reports or validation certificates.

## Report the analysis so somebody else can reconstruct it

When an analysis becomes manuscript-facing, use the [Measurement & interpretation clinic](measurement-interpretation.md) to audit any substantive gaze claim, then continue with the [Reporting & interpretation clinic](reporting-clinic.md), [Publication-readiness checklist](publication-readiness.md), [QC review and exclusion-ledger clinic](qc-review-exclusion-ledger.md), [Validation reporting cookbook](validation-reporting-cookbook.md), and [Reproducible reporting](reproducible-reporting.md). The reporting surfaces keep import compatibility versus device validity, QC flags versus review/exclusion decisions, demos versus empirical validation, split identity, sample/event metrics, calibration, confidence/coverage, native/derived rate, and model-selection versus confirmatory evaluation explicit. Use [Study-design templates](study-design-templates.md) to keep the required metadata explicit from preregistration onward.