---
description: Troubleshooting and diagnostics for GazeForge source contracts, QC, event models, dynamic AOIs, reproducibility, and privacy-safe issue reports.
search:
  boost: 1.4
---

# Troubleshooting & diagnostics

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>How-to guide</strong> · Diagnose a failure or surprising result without hiding uncertainty or modifying the empirical record just to make the workflow run.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md" aria-current="page">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>

GazeForge is designed to fail visibly when an assumption matters. A diagnostic is useful when it helps you identify the source contract, transformation, review decision, model identity, or evidence boundary responsible for an unexpected result. It is not useful if it merely suppresses the symptom.

!!! warning "Stop rather than guess"
    Stop the analysis when a required fact is unknown and materially affects interpretation: timestamp unit, coordinate basis, participant/trial identity, native/nominal rate, observed cadence, geometry, exclusion denominator, validation split identity, or evidence provenance. Record the unresolved item and fix the source contract before continuing.

## Symptom → diagnostic → action

| Symptom | Inspect first | Safe next action | Do not do |
| --- | --- | --- | --- |
| Package will not import | Python version, environment, exact install command | reproduce in a clean environment and capture the full traceback | edit package files until the import happens to work |
| Tracker timestamps are implausible | declared unit, monotonicity, within-trial deltas, observed cadence | verify the export specification and explicit conversion | infer units solely from a visually plausible plot |
| Most gaze is off-screen | coordinate basis, screen/stimulus geometry, normalization | verify pixels vs normalized coordinates and geometry | clip coordinates silently into the screen |
| Duplicate sample keys appear | participant/trial/timestamp identity and export semantics | retain and quantify duplicates until their meaning is known | drop duplicates by default |
| `qc_flag` is unexpectedly high | missingness, jumps, gaps, grouping, sampling rate | inspect features and review flagged rows/trials | equate `qc_flag=True` with automatic exclusion |
| Trial quality is poor | missing/off-screen/anomaly/gap components | document the relevant component and apply a reviewed criterion | tune a threshold post hoc and call it prespecified |
| I-VT yields implausible events | units, cadence, threshold, boundaries, missing gaze | verify the input contract and run a sensitivity check | describe the demonstration threshold as universal |
| Learned model performance looks too good | participant/stimulus/source identity across folds | verify disjoint grouping and matched held-out rows | use random row splits when the claim requires participant holdout |
| Calibration curve is unstable | support per bin, held-out probabilities, class balance | report support and uncertainty; reduce claims if data are sparse | hide empty/sparse bins |
| Dynamic AOI assignments disappear | keyframe support range, timebase, interpolation audit | inspect the support window and assignment audit | extrapolate tracks silently beyond reviewed support |
| Scanpath output looks surprising | fixation/AOI assignments and unassigned handling | inspect the assignment table before sequence construction | interpret a sequence as a latent mental-state measure |
| Docs build fails | strict MkDocs error, target path, nav entry, generated hooks | fix the broken path/configuration and rebuild strictly | disable strict validation to ship the page |

## Minimal environment diagnostic

Record the exact interpreter and package identity before debugging scientific output:

```bash
python --version
python -c "import gazeforge; print(gazeforge.__version__)"
python -m pip show gazeforge
```

For a repository checkout, also record the exact commit SHA:

```bash
git rev-parse HEAD
```

A version string alone is not enough when analyzing an unreleased development tree.

## Import diagnostics

Before fitting models or applying exclusions, establish a source contract containing at least:

- participant identifier column;
- trial/stimulus identifier column;
- timestamp column and unit;
- gaze-coordinate columns and coordinate basis;
- screen/stimulus geometry;
- native/nominal acquisition rate when known;
- observed timestamp cadence as a separate diagnostic;
- duplicate sample-key count;
- missing identity and missing gaze counts; and
- source fingerprint/checksum when the workflow is manuscript-facing.

Use [Worked tracker import + QC](worked-tracker-import.md) for the executable pattern and [Real-data import clinic](data-import-clinic.md) for source variants.

## QC diagnostics

QC should add evidence, not rewrite the source record. When flags are surprising:

1. compare source and QC row counts;
2. inspect missingness and off-screen rates;
3. inspect within-trial timestamp gaps;
4. verify grouping boundaries;
5. inspect the features that drive anomaly scoring; and
6. preserve the pre-review QC table before any exclusion decision.

Then use [QC review & exclusion ledger](qc-review-exclusion-ledger.md). A flagged sample can be reviewed and retained.

## Validation diagnostics

When a validation result is unexpectedly strong or weak, check the design before the metric:

- What entity is held out: row, trial, participant, stimulus, dataset, or opaque source token?
- Is the same grouping entity present in both train and test?
- Are all compared models evaluated on the same held-out rows?
- Is the sampling condition native or derived?
- Are probabilities genuinely held out before calibration is assessed?
- Are event-level timing and boundary metrics consistent with sample-level metrics?

Use [Event-model validation clinic](event-model-validation-clinic.md) and [Validation reporting cookbook](validation-reporting-cookbook.md).

## Dynamic-AOI diagnostics

For time-varying AOIs, preserve:

- reviewed keyframes;
- source and target timebases;
- interpolation method;
- support start/end;
- assignments outside support; and
- explicit **no extrapolation** behavior unless a scientifically justified policy says otherwise.

Unexpected missing assignments can be correct if the fixation falls outside reviewed temporal support.

## Privacy-safe issue report

A useful issue should contain enough information to reproduce the software behavior without exposing participant data.

Include:

- GazeForge version or full commit SHA;
- Python version and operating system;
- exact command or minimal code snippet;
- expected behavior and observed behavior;
- full sanitized traceback/error text;
- column names, dtypes, units, and a tiny **synthetic** reproduction when possible;
- whether the source is canonical, imported, QC-enriched, reviewed, or analysis-ready; and
- the smallest output/manifest fragment needed to show the problem.

Do **not** attach participant names, emails, study IDs that can be linked to people, raw private tracker exports, credentials, tokens, unpublished stimuli without permission, or medical/biometric records to a public issue.

## What automated checks can and cannot establish

The project can automatically test file existence, links, strict documentation builds, output schemas, deterministic examples, focus/reduced-motion CSS guards, and selected accessibility-oriented invariants. Those checks are useful regression protection.

They are **not proof of complete WCAG conformance**, complete usability, scientific validity, or empirical measurement validity. Manual keyboard/screen-reader review and context-specific scientific review remain separate tasks.

## Continue

Return to the [Documentation map](documentation-map.md) when the immediate diagnostic is resolved, or use the persistent help row at the top of this page to move to the Tour, examples, or issue tracker.
