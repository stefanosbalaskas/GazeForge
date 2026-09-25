# GazeForge tour: what it does and how to use it

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Tutorial</strong> · First-success package overview: understand the input → GazeForge → output workflow before choosing a specialist method.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>


If you are unsure what GazeForge is for, start here.

**GazeForge is not one eye-tracking algorithm.** It is a Python research workflow that helps you turn gaze samples into reviewable analysis artifacts while keeping automated decisions, uncertainty, provenance, and human review visible.

!!! info "If you remember only one thing"
    GazeForge helps with the **analysis layer after eye-tracking data have been collected**. You give it gaze samples plus documented study metadata. It can canonicalise the data, flag quality problems without silently deleting rows, classify eye events, work with static or dynamic AOIs, create semantic scanpaths, validate learned event models, and freeze provenance/reporting artifacts.

!!! warning "Running GazeForge is not validation by itself"
    A successful workflow does not establish tracker validity, calibration quality, native 60 Hz validity, Gazepoint/GP3 validity, event-model validity, or measurement validity. Evidence strength depends on the data and validation design you actually supply.

## The 30-second picture

```text
YOUR STUDY
tracker export + participant/trial identity + timestamps + coordinates
                         │
                         ▼
                    GAZEFORGE
      ┌──────────────────┼──────────────────┐
      │                  │                  │
 canonical schema   non-destructive QC   eye events
      │                  │                  │
      └──────────────┬───┴──────────────┬──┘
                     ▼                  ▼
              static/dynamic AOIs   validation
                     │                  │
                     ▼                  ▼
                scanpaths          held-out evidence
                     └──────────┬───────┘
                                ▼
                    reviewable analysis bundle
        tables + decisions + fingerprints + provenance + report inputs
```

The design principle is simple: **automation can add information, but it should not silently rewrite the empirical record**. Gaze samples go in; reviewable analysis artifacts come out.

## What goes in?

The core input is a sample-level gaze table. For a real study you should know, from acquisition/export documentation rather than guessing:

| Information | Example |
| --- | --- |
| participant identity | `P001` |
| trial/media/stimulus identity | `ad_03`, `screen_A`, `video_2` |
| timestamp and unit | seconds or milliseconds |
| x/y gaze coordinates and coordinate system | normalized fractions or pixels |
| screen/stimulus geometry | 1920 × 1080 px |
| nominal/native sampling rate | e.g. acquisition setting recorded by the study |
| optional pupil/validity fields | documented tracker/export semantics |

For Gazepoint-shaped exports, start with the [Worked tracker import and QC](worked-tracker-import.md). For another tracker, use the appropriate adapter or canonicalisation path only after the source contract is known.

## What does GazeForge actually do?

### 1. Canonicalises the source

Different exports use different names, units, and coordinate systems. GazeForge can transform documented source fields into a vendor-neutral table with explicit participant/trial identity, milliseconds, and pixel coordinates.

This is a **documented transformation**, not a claim that different trackers are scientifically interchangeable.

### 2. Adds quality-control evidence without deleting observations

GazeForge can add anomaly scores/flags and trial-quality summaries for missingness, bounds, temporal gaps, and related diagnostics.

A QC flag means **look here**. It does not automatically mean **delete this**. A QC flag is not an automatic exclusion.

For manuscript-facing work, continue from QC evidence to the [QC review and exclusion ledger](qc-review-exclusion-ledger.md), where retained/excluded decisions and denominators are stored separately.

### 3. Creates transparent or learned eye-event labels

You can begin with inspectable rules such as I-VT, or train probabilistic classifiers when you have an appropriate labelled reference corpus.

GazeForge keeps model identity, sampling assumptions, probabilities/confidence, held-out identity, calibration, and event-level performance available for review.

If the goal is a learned classifier, use the [Event-model validation clinic](event-model-validation-clinic.md). Fitting a model is not the same as validating it.

### 4. Connects gaze to meaningful regions

For static stimuli, define AOIs such as a brand, claim, disclosure, product, navigation item, CTA, or interface panel. For moving content, use timestamped AOI geometry with bounded interpolation.

AI-proposed AOIs remain proposals until reviewed. GazeForge can retain source/model/confidence and accept/reject/relabel/edit history.

### 5. Builds scanpaths and sequence representations

Once fixations are assigned to meaningful regions, GazeForge can represent the sequence of attended semantic regions and support motifs, embeddings, similarity, and clustering.

The sequence is a representation of observed gaze behaviour—not an automatic inference about emotion, personality, diagnosis, intention, or another unsupported latent state.

### 6. Validates models without hiding the split

GazeForge includes participant-held-out and dataset-held-out workflows, sample- and event-level metrics, calibration, confidence/coverage, matched-model comparisons, and evidence-aware benchmark records.

The split identity and evidence category matter as much as the metric value. A derived 60 Hz condition remains derived; it does not become native 60 Hz hardware validation.

### 7. Freezes the audit trail

For a manuscript-facing workflow, retain source identity, transformations, QC evidence, review decisions, model identity, AOI provenance, validation design, fingerprints, and the exact software version/commit.

That is the part that makes the analysis reconstructable.

## Run the package-wide tour

From a repository checkout with GazeForge installed:

```bash
python examples/00_gazeforge_tour.py \
  --output-dir gazeforge-tour-demo
```

The tour uses deterministic synthetic/demo data so you can inspect the mechanics without supplying private study data. Its outputs are not empirical validation evidence.

It demonstrates:

```text
source gaze
→ canonical gaze
→ QC flags + trial quality
→ transparent I-VT events
→ fixation centroids
→ researcher-defined AOIs
→ fixation/AOI assignments
→ semantic scanpaths
→ provenance + manifest
```

It writes:

```text
01_source_gaze.csv
02_canonical_gaze.csv
03_qc_samples.csv
04_trial_quality.csv
05_event_samples.csv
06_event_intervals.csv
07_fixation_centroids.csv
08_aoi_definitions.csv
09_fixation_aoi_assignments.csv
10_semantic_scanpaths.csv
provenance.json
workflow_manifest.json
```

The script checks that the source table is unchanged and that sample row counts are preserved through the non-destructive sample-level stages.

## Read the outputs in this order

### `01_source_gaze.csv`

The starting empirical sample table for the demo. In a real study, preserve the original export separately as an immutable source artifact.

### `02_canonical_gaze.csv`

The vendor-neutral representation used by downstream GazeForge functions.

### `03_qc_samples.csv`

The same sample rows plus QC evidence. Compare it with the canonical table: automation adds review fields rather than silently dropping rows.

### `04_trial_quality.csv`

A compact trial-level summary. Use it as evidence for review, not as an automatic exclusion command.

### `05_event_samples.csv` and `06_event_intervals.csv`

A transparent event-labelling example and its contiguous intervals. The teaching threshold is not a universal event-validity standard.

### `07`–`10`

These show how event-derived fixations can be connected to researcher-defined semantic regions and converted into scanpath structures.

### `provenance.json` and `workflow_manifest.json`

These explain what ran, preserve fingerprints/parameters, state scientific boundaries, and point to the next workflow.

## Which GazeForge path do I need?

| Your immediate problem | Start here | Main artifact |
| --- | --- | --- |
| “I just want to understand the package.” | **This tour** | small end-to-end demo bundle |
| “I have a tracker export.” | [Worked tracker import](worked-tracker-import.md) | import contract + canonical/QC tables |
| “QC found problems. What do I exclude?” | [QC review/exclusion ledger](qc-review-exclusion-ledger.md) | explicit decision ledgers + primary derivative |
| “I need eye-event labels.” | [I-VT tutorial](tutorial-ivt-baseline.md) | inspectable event labels |
| “I want to train/compare an event model.” | [Event-model validation clinic](event-model-validation-clinic.md) | participant-held-out predictions + metrics |
| “My AOIs move over time.” | [Worked dynamic-AOI study](worked-dynamic-aoi-study.md) | keyframes + bounded assignments |
| “I need a full study template.” | [Study lifecycle](study-lifecycle.md) | stage-by-stage research artifacts |
| “I am preparing a paper.” | [Publication readiness](publication-readiness.md) | pre-submission audit checklist |
| “I need to know what is empirically supported.” | [Evidence status](evidence-status.md) | generated evidence boundary |

## Real-study route

For a typical eye-tracking project, the recommended order is:

```text
1. Preserve acquisition/export evidence
2. Import with explicit units and identities
3. Freeze canonical pre-review data
4. Generate non-destructive QC evidence
5. Review and record exclusions separately
6. Choose/validate eye-event method
7. Freeze AOI definitions or reviewed dynamic tracks
8. Derive fixation/AOI/scanpath analysis structures
9. Validate any learned models on appropriate held-out units
10. Freeze provenance, analysis derivative, and reporting bundle
```

You may not need every stage. For example, a study using researcher-defined static AOIs and a transparent event rule may not need a learned event classifier or AI-proposed AOIs at all.

## What GazeForge does not do for you

GazeForge does not decide your theory, research question, construct validity, acquisition quality, exclusion rationale, or causal interpretation. It also does not convert gaze into unsupported psychological diagnoses or hidden mental states.

It is designed to make the computational analysis **more inspectable and reproducible**, not to replace research judgment.

## The shortest way to start

If you are new to the project, use this sequence:

```bash
python -m pip install "gazeforge==0.1.0a2"
```

Then, from a repository checkout, run:

```bash
python examples/00_gazeforge_tour.py --output-dir gazeforge-tour-demo
```

Open `workflow_manifest.json`, then compare `01_source_gaze.csv`, `03_qc_samples.csv`, and `10_semantic_scanpaths.csv`. That gives you the fastest concrete picture of what the package adds between raw gaze and a reviewable analysis table.

When you are ready to use your own export, continue to the [Worked tracker import and QC](worked-tracker-import.md).
