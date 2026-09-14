# Learning paths

GazeForge spans data preparation, quality control, eye-event modelling, semantic AOIs, scanpaths, benchmark validation, and scientific provenance. You do not need to learn every layer before starting.

Choose the path that matches your immediate research question.

<div class="gf-path-grid" markdown>

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

### :material-chart-box-outline: I need defensible validation

Move directly to participant-disjoint folds, matched model comparisons, calibration, event-level temporal metrics, and sampling-rate sensitivity.

**Next:** [Research workflow patterns](research-workflows.md)

</div>

<div class="gf-path-card" markdown>

### :material-shield-search-outline: I need to audit evidence

Read the validation matrix, frozen evidence, source-resolution records, and benchmark-specific claim boundaries before interpreting a headline metric.

**Next:** [Validation status](validation-status.md)

</div>

</div>

## A practical progression

| Stage | Learn | Produce | Do not claim yet |
| --- | --- | --- | --- |
| **1. Canonicalise** | schema, rate, units, participant/trial boundaries | one vendor-neutral gaze table | comparability across datasets |
| **2. QC** | missingness, gaps, off-screen samples, anomaly flags | reviewable QC columns and trial summaries | automatic exclusion validity |
| **3. Baseline** | deterministic I-VT or angular I-VT | inspectable event labels | learned-model superiority |
| **4. Validate** | participant-disjoint folds, calibration, event matching | out-of-sample performance | native-device validity from resampled data |
| **5. Extend** | semantic/dynamic AOIs, scanpaths, hierarchical models | task-specific analytic structures | unsupported psychological inference |
| **6. Freeze** | manifests, fingerprints, certificates, source resolution | auditable evidence bundle | stronger provenance than the source supports |

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
   ├─ Compatible sampling regime?                → fit + validate model
   ├─ Need boundary-sensitive performance?       → add event-F1 / temporal IoU / boundary error
   └─ Need lower-rate claims?                    → add rate × label-purity sensitivity
```

## Which AOI workflow should I use?

```text
Static stimulus
└─ define or propose AOIs → human review → freeze AOIs → assign fixations

Video / moving interface
└─ timestamped keyframes → bounded interpolation → review → dynamic fixation assignment
```

AI-proposed AOIs remain proposals until reviewed. The provenance record should retain model identity, confidence, and any accept/reject/relabel/edit decision.

## Read results visually

The [results gallery](results-gallery.md) puts the current reviewed benchmark summaries beside their evidence boundaries. It is intended as an orientation layer, not a replacement for frozen reports or validation certificates.

## Report the analysis so somebody else can reconstruct it

When an analysis becomes manuscript-facing, continue with [Reproducible reporting](reproducible-reporting.md). That guide turns the package/version, acquisition rate, split policy, model identity, derived/native distinction, and evidence fingerprints into a compact reporting checklist.
