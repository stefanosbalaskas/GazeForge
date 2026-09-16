# Worked study: static advertising/interface attention

This worked example shows how a domain study can be structured from source-like gaze rows to reviewable AOI sequences and provenance without inventing an empirical advertising effect.

!!! warning "Illustrative synthetic study — not empirical validation evidence"
    The bundled data are deterministic **synthetic, real-data-shaped demonstration data**. The workflow is classified `synthetic_demo_not_empirical_evidence`. It does not establish persuasion, liking, comprehension, purchase intention, tracker validity, native 60 Hz validity, Gazepoint validity, or GP3 validity.

## Research question

> Which predefined visible regions are inspected, and in what semantic order?

That question is intentionally observable. A real advertising study could connect these process measures to independently measured outcomes, but the gaze sequence alone should not be relabelled as persuasion, comprehension, or intention.

## Study layout

The example uses a 1920 × 1080 static stimulus with four non-overlapping researcher-defined AOIs:

| AOI | Illustrative role | Bounds `(xmin, ymin, xmax, ymax)` | Source |
| --- | --- | --- | --- |
| `brand` | brand/logo region | `(80, 80, 520, 280)` | researcher-defined |
| `claim` | focal message/claim region | `(80, 340, 940, 650)` | researcher-defined |
| `disclosure` | disclosure/qualifier region | `(80, 760, 940, 920)` | researcher-defined |
| `product` | product/hero visual region | `(1080, 150, 1840, 930)` | researcher-defined |

The script constructs four synthetic participants and two trials with deterministic fixation-like dwell segments and rapid transitions. The construction is for software demonstration only; it is not intended to mimic a validated physiological generative model.

## Run it

From a repository checkout with the development/base dependencies installed:

```bash
python examples/04_worked_advertising_study.py \
  --output-dir worked-advertising-study-demo
```

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/04_worked_advertising_study.py)

## What the script demonstrates

```text
synthetic source-like gaze
        ↓
immutable source snapshot + fingerprint
        ↓
canonical gaze table
        ↓
non-destructive anomaly flags + trial quality
        ↓
transparent I-VT event baseline
        ↓
fixation centroids
        ↓
researcher-defined brand / claim / disclosure / product AOIs
        ↓
fixation → AOI assignment
        ↓
semantic scanpaths
        ↓
analysis plan + provenance + manifest
```

## Reviewable outputs

The script writes ten CSV tables:

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
```

It also writes:

- `analysis_plan.json` — the observable question, AOI labels, QC rule, event-baseline purpose, validation plan, and substantive interpretation boundary;
- `provenance.json` — operation-level input/output fingerprints and parameters; and
- `workflow_manifest.json` — software identity, evidence classification, source fingerprint, source-immutability result, output inventory, and scientific boundary.

## Why the source is kept separate

The source table is copied deeply before analysis and fingerprinted. The script verifies at the end that the source remains unchanged.

```text
source_unchanged: true
```

This is a provenance guarantee about the demonstration workflow. It is not a validity claim about an acquisition device or the synthetic data-generating process.

## QC is review evidence, not automatic deletion

The worked example runs the same non-destructive QC pattern used elsewhere in GazeForge:

```python
flagged = ai_flag_anomalies(
    gaze.data,
    sampling_rate_hz=gaze.sampling_rate_hz,
    random_state=42,
    trail=trail,
)
quality = score_trial_quality(flagged, screen_size_px=(1920, 1080))
```

A real confirmatory study should specify the review/exclusion rule independently. Do not convert `anomaly_flag=True` into “invalid sample” without that decision layer.

## The event layer is deliberately transparent

The example uses the pixel-velocity I-VT baseline with an explicit threshold:

```python
event_samples = ivt_classify_events(
    flagged,
    sampling_rate_hz=60.0,
    velocity_threshold_px_s=1000.0,
)
```

The threshold is used to teach an inspectable pipeline. It is not claimed to be optimal for every tracker, geometry, task, participant population, or scientific question.

For a learned event model in a real study, use appropriate reference labels and a leakage-safe validation design before making performance claims.

## AOIs remain measurement definitions

The four AOIs are defined by the research design, not inferred as psychological states. The resulting fixation assignments can support measures such as:

- number/duration of fixations assigned to a visible region;
- latency to first assigned fixation when the design supports it;
- transitions among predefined semantic regions; and
- semantic scanpath sequences.

Those measures can enter a separate substantive model, but the AOI label itself does not establish why the participant looked there or what they believed.

## What participant-disjoint validation would mean here

The bundled script does **not** estimate event-model performance. If a real version of this study used a learned event classifier, a defensible plan could be:

1. obtain suitable reference event labels;
2. split by participant rather than by individual sample rows;
3. fit preprocessing/model components using training participants only;
4. generate held-out predictions for untouched participants;
5. report sample-level and event-level metrics that match the estimand;
6. add calibration if confidence values are interpreted; and
7. preserve native versus derived sampling-rate status.

That is a validation design, not a property created by the worked example itself.

## Manuscript-style reporting template

A real study can adapt a compact description such as:

> Gaze samples were retained as an immutable source table and transformed into the GazeForge canonical schema with explicit participant, trial, timestamp, coordinate, sampling-rate, and screen-geometry metadata. Quality-control procedures added reviewable anomaly and trial-quality fields without automatically deleting observations. Eye events were defined using the prespecified event method, and fixation-level coordinates were assigned to frozen researcher-defined AOIs representing the brand, claim, disclosure, and product regions. Semantic sequences were retained by participant and trial. Model validation, where applicable, used the prespecified held-out unit and reference labels, and native versus derived sampling-rate evidence was reported separately. Software/environment identity and analysis fingerprints were archived with the final outputs.

Replace every generic phrase with the actual study facts. Do not copy a stronger validation statement than the design supports.

## Move from the example to real data

1. Use the [Real-data import clinic](data-import-clinic.md) to map the actual tracker export.
2. Freeze the study-specific AOIs and review protocol.
3. Replace the demonstration threshold/model only after defining the empirical justification.
4. Use the [Validation guide](validation-evidence-guide.md) for evidence claims.
5. Complete the [Publication-readiness checklist](publication-readiness.md).
6. Translate the frozen workflow with [Reproducible reporting](reproducible-reporting.md).

For the broader sequence, return to the [Study lifecycle](study-lifecycle.md).
