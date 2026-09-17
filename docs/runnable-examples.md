# Runnable examples

The repository contains **eight deterministic examples** that move from a small first result to complete reviewable workflows, domain-shaped static/dynamic studies, leakage-safe event-model validation, and a worked tracker-import/QC handoff. Use this page to choose a script, see what it produces, and open the corresponding guide.

!!! warning "Demo output is not empirical validation evidence"
    Every example on this page uses synthetic/demo inputs. The scripts demonstrate software behaviour, composition, plotting, provenance, and reporting structure. They are **not empirical validation evidence** and do not establish native-device, native 60 Hz, Gazepoint, or GP3 validity.

!!! tip "Already have a tracker export?"
    Start with the [Worked tracker import and QC](worked-tracker-import.md) and [Real-data import clinic](data-import-clinic.md). The worked script makes source identity, explicit units, coordinate conversion, duplicate keys, observed cadence, bounds, row-count preservation, and non-destructive QC executable before event modelling.

## At a glance

| Example | Install | Run | Main output |
| --- | --- | --- | --- |
| **Synthetic QC** | base package | `python examples/01_synthetic_qc.py` | printed trial-level QC table |
| **Transparent I-VT** | base package | `python examples/02_ivt_baseline.py` | printed event counts and first-trial transitions |
| **Visual diagnostics** | `.[plot]` | `python examples/03_visual_diagnostics.py --output-dir visual-demo` | six PNG diagnostics |
| **End-to-end workflow** | `.[plot]` by default; base path with `--no-figures` | `python examples/end_to_end_research_workflow.py --output-dir end-to-end-research-demo` | ten CSV tables, provenance, manifest, optional figures |
| **Worked advertising/interface study** | base package | `python examples/04_worked_advertising_study.py --output-dir worked-advertising-demo` | ten study-shaped CSV tables, analysis plan, provenance, manifest |
| **Worked dynamic-AOI study** | `.[plot]` by default; base path with `--no-figures` | `python examples/05_worked_dynamic_aoi_study.py --output-dir worked-dynamic-aoi-demo` | six CSV tables, analysis plan, provenance, manifest, optional figures |
| **Worked event-model validation study** | `.[plot]` by default; base path with `--no-figures` | `python examples/06_worked_event_model_validation.py --output-dir worked-event-model-validation-demo` | nine CSV tables, analysis plan, provenance, manifest, optional calibration figures |
| **Worked tracker import + QC** | base package | `python examples/07_worked_tracker_import_qc.py --output-dir worked-tracker-import-qc-demo` | five CSV tables, import contract, analysis plan, provenance, manifest |

## 1 · Synthetic QC

Use the smallest example when you want to verify installation and see the non-destructive quality-control contract.

```bash
python examples/01_synthetic_qc.py
```

The script deterministically simulates four participants × three trials, canonicalises the samples at 60 Hz, adds anomaly flags, computes trial quality, and prints `participant_id`, `trial_id`, `missing_rate`, `offscreen_rate`, `anomaly_rate`, `large_gap_rate`, and `quality_score`.

No source rows are automatically deleted. Treat the printed quality fields as review evidence rather than a universal exclusion rule.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/01_synthetic_qc.py) · [Read the QC tutorial](tutorial-synthetic-qc.md)

## 2 · Transparent I-VT baseline

Use this example when you want an inspectable event rule before deciding whether a learned classifier is justified.

```bash
python examples/02_ivt_baseline.py
```

The script applies a deterministic pixel-velocity I-VT rule with an explicit `1000.0 px/s` threshold to synthetic 60 Hz gaze. It prints event-class counts plus each event transition in the first trial.

The threshold is an example setting, not a universal physiological cutoff and not a device-validation claim.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/02_ivt_baseline.py) · [Read the I-VT tutorial](tutorial-ivt-baseline.md)

## 3 · Visual diagnostics

Install the plotting extra from a repository checkout:

```bash
python -m pip install -e ".[plot]"
python examples/03_visual_diagnostics.py --output-dir visual-demo
```

The script writes exactly six synthetic/demo figures:

```text
01_qc_timeline.png
02_event_probabilities.png
03_calibration.png
04_aoi_overlay.png
05_scanpath.png
06_dynamic_aoi.png
```

<div class="gf-preview-grid">
  <a class="gf-preview-card" href="visual-diagnostics/">
    <img src="assets/figures/synthetic-qc-diagnostics.svg" alt="Synthetic demo quality-control timeline with flagged samples." loading="lazy">
    <span class="gf-preview-kicker">Review quality</span>
    <strong>QC timeline</strong>
    <span>Inspect anomaly flags without treating them as automatic exclusions.</span>
  </a>
  <a class="gf-preview-card" href="visual-diagnostics/">
    <img src="assets/figures/synthetic-event-diagnostics.svg" alt="Synthetic demo event probability and calibration diagnostics." loading="lazy">
    <span class="gf-preview-kicker">Review predictions</span>
    <strong>Probability &amp; calibration</strong>
    <span>Keep confidence and calibration visible rather than reducing the output to a label alone.</span>
  </a>
  <a class="gf-preview-card" href="visual-diagnostics/">
    <img src="assets/figures/synthetic-aoi-scanpath.svg" alt="Synthetic demo semantic AOIs with a numbered fixation scanpath." loading="lazy">
    <span class="gf-preview-kicker">Review structure</span>
    <strong>AOIs &amp; scanpaths</strong>
    <span>Inspect region geometry, semantic labels, fixation order, and sequence structure.</span>
  </a>
</div>

Library plotting functions return Matplotlib axes and do not save or show figures by themselves. The example script writes files because output generation is its explicit purpose.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/03_visual_diagnostics.py) · [Read the visual diagnostics guide](visual-diagnostics.md)

## 4 · Complete end-to-end research workflow

Use this example when you want to see the public workflow layers composed into one auditable bundle.

```bash
python examples/end_to_end_research_workflow.py \
  --output-dir end-to-end-research-demo
```

For the table/provenance path without Matplotlib:

```bash
python examples/end_to_end_research_workflow.py \
  --output-dir end-to-end-research-demo \
  --no-figures
```

The workflow writes these ten tables:

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

It also writes `provenance.json`, `workflow_manifest.json`, and—when figures are enabled—`figures/01_qc_timeline.png`, `figures/02_aoi_overlay.png`, and `figures/03_scanpath.png`.

The script takes a deep snapshot of the synthetic source table and verifies at the end that the **source table remains unchanged**. Its manifest labels the bundle `synthetic_demo_not_empirical_evidence`.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/end_to_end_research_workflow.py) · [Read the practical workflow](practical-workflow.md)

## 5 · Worked advertising / interface study

Use this example when you want to see the same auditable layers shaped around a recognizable static-stimulus research design rather than a generic pipeline.

```bash
python examples/04_worked_advertising_study.py \
  --output-dir worked-advertising-demo
```

The study predeclares four semantic AOIs—`brand`, `claim`, `disclosure`, and `product`—then composes source preservation, canonicalisation, QC, transparent I-VT classification, event intervals, fixation/AOI assignment, semantic scanpaths, and provenance.

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
analysis_plan.json
provenance.json
workflow_manifest.json
```

The resulting AOI assignments and scanpaths are descriptive software-demo outputs—not estimates of real consumer attention effects, persuasion, comprehension, liking, or purchase intention. The manifest uses `synthetic_demo_not_empirical_evidence`.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/04_worked_advertising_study.py) · [Read the worked-study guide](worked-advertising-study.md) · [Follow the study lifecycle](study-lifecycle.md)

## 6 · Worked dynamic-AOI study

Use this example when semantic regions move over time and you want the temporal geometry policy itself to remain reviewable.

```bash
python -m pip install -e ".[plot]"
python examples/05_worked_dynamic_aoi_study.py \
  --output-dir worked-dynamic-aoi-demo
```

For the tables/provenance path without Matplotlib:

```bash
python examples/05_worked_dynamic_aoi_study.py \
  --output-dir worked-dynamic-aoi-demo \
  --no-figures
```

The study uses deterministic `product`, `claim`, and `cta` tracks with reviewed keyframes at 0, 1000, and 2000 ms. It exercises exact keyframes and bounded interpolation and deliberately includes fixation probes before and after the track range to verify **no extrapolation beyond the reviewed time range**.

It writes exactly six tables:

```text
01_source_fixations.csv
02_dynamic_aoi_keyframes.csv
03_fixation_dynamic_aoi_assignments.csv
04_semantic_scanpaths.csv
05_interpolation_audit.csv
06_assignment_summary.csv
```

It also writes `analysis_plan.json`, `provenance.json`, and `workflow_manifest.json`; with figures enabled it adds `figures/01_dynamic_aoi_snapshot.png` and `figures/02_dynamic_scanpath.png`.

The manifest records `synthetic_demo_not_empirical_evidence`, source/keyframe fingerprints, the interpolation-gap rule, and `no_extrapolation_verified`. These artifacts demonstrate software composition and auditability; they do not validate a learned detector/tracker, a device, native 60 Hz acquisition, Gazepoint/GP3, or any substantive psychological effect.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/05_worked_dynamic_aoi_study.py) · [Read the worked dynamic-AOI guide](worked-dynamic-aoi-study.md) · [Open research recipes](research-recipes.md)

## 7 · Worked event-model validation study

Use this example when the research task is **learned event-model evaluation**, not merely model fitting.

```bash
python -m pip install -e ".[plot]"
python examples/06_worked_event_model_validation.py \
  --output-dir worked-event-model-validation-demo
```

For the table/provenance path without Matplotlib:

```bash
python examples/06_worked_event_model_validation.py \
  --output-dir worked-event-model-validation-demo \
  --no-figures
```

The deterministic source contains eight synthetic participants × two trials with explicit fixation/saccade reference labels. The script reconstructs four participant-disjoint GroupKFold splits, verifies **zero train/test participant overlap**, and compares I-VT, Random Forest, and ContextMLP on the **same held-out rows**.

It writes exactly nine tables:

```text
01_source_event_samples.csv
02_participant_split_ledger.csv
03_matched_heldout_predictions.csv
04_sample_level_metrics.csv
05_event_level_metrics.csv
06_model_summary.csv
07_calibration_bins.csv
08_confidence_coverage.csv
09_illustrative_abstention_policy.csv
```

It also writes `analysis_plan.json`, `provenance.json`, and `workflow_manifest.json`; with figures enabled it adds `figures/01_calibration.png` and `figures/02_confidence_coverage.png`.

The design deliberately keeps **sample-level metrics**, **event-level temporal metrics**, and **probability calibration** separate. Calibration and confidence/coverage are produced only for probabilistic learned models; deterministic I-VT is not given fabricated probability scores. The illustrative `0.80` abstention threshold is labelled `illustrative_not_universal`, and the manifest records `participant_disjoint_verified`, `matched_test_rows_across_models`, source fingerprint, software identity, and `synthetic_demo_not_empirical_evidence`.

Any model ordering in this synthetic study is a property of the demonstration construction and chosen metrics—not evidence that one model is generally superior. The bundle does not establish empirical benchmark performance, native-device validity, native 60 Hz validity, Gazepoint validity, or GP3 validity.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/06_worked_event_model_validation.py) · [Open the validation clinic](event-model-validation-clinic.md) · [Use the reporting cookbook](validation-reporting-cookbook.md)

## 8 · Worked tracker import + QC

Use this example when the first research problem is **getting a real tracker export into a reviewable canonical/QC state** rather than fitting an event model.

```bash
python examples/07_worked_tracker_import_qc.py \
  --output-dir worked-tracker-import-qc-demo
```

The source is a deterministic Gazepoint-shaped demo table with:

```text
USER_FILE
MEDIA_ID
TIME
BPOGX
BPOGY
PUPIL
VALIDITY
```

The adapter call declares `TIME` as **seconds**, gaze coordinates as **normalized screen fractions**, and screen geometry as **1920 × 1080 px**. The resulting canonical table therefore expresses time in milliseconds and x/y in pixels.

The demonstration deliberately retains:

- a duplicated participant/trial/timestamp key;
- two off-screen coordinates after conversion; and
- one missing gaze coordinate.

Before QC it writes a preflight table covering source/canonical row count, duplicate-key rows, missing identity, missing gaze, coordinate bounds, nominal rate, **observed cadence**, and the nominal-versus-observed difference. The nominal 60 Hz teaching value is kept separate from timestamp-derived cadence; matching values in this demo are **not proof of native hardware rate**.

It writes exactly five CSV tables:

```text
01_source_tracker_export.csv
02_canonical_gaze.csv
03_import_preflight.csv
04_qc_samples.csv
05_trial_quality.csv
```

It also writes:

```text
import_contract.json
analysis_plan.json
provenance.json
workflow_manifest.json
```

The script verifies that the **source table remains unchanged** and that **row count is preserved** through canonicalisation and QC. It does not clip off-screen gaze, delete duplicates, fill missing gaze, infer unknown identity, apply exclusions, or fit a learned event model.

The manifest classifies the bundle `synthetic_demo_not_empirical_evidence` and records that adapter compatibility is **not device/model validation**. It creates no Gazepoint/GP3 or native-60-Hz validity claim.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/07_worked_tracker_import_qc.py) · [Read the worked tracker-import guide](worked-tracker-import.md) · [Open the real-data import clinic](data-import-clinic.md)

## Which example should I run first?

```text
Have a real tracker export?                  → 07_worked_tracker_import_qc.py
Need to verify installation / QC?            → 01_synthetic_qc.py
Need an inspectable event baseline?          → 02_ivt_baseline.py
Need figure-generation patterns?             → 03_visual_diagnostics.py
Need a complete reviewable output bundle?    → end_to_end_research_workflow.py
Need a static domain-shaped worked study?    → 04_worked_advertising_study.py
Need moving AOIs + interpolation auditing?   → 05_worked_dynamic_aoi_study.py
Need participant-held-out event validation?  → 06_worked_event_model_validation.py
```

## Move from demo data to a study

The examples intentionally avoid pretending that synthetic behaviour validates a tracker or analysis method. For a real study:

1. run the [Worked tracker import and QC](worked-tracker-import.md) and [Real-data import clinic](data-import-clinic.md), then replace the demo source only after documenting actual source semantics;
2. record actual acquisition hardware, native sampling rate, **observed timestamp cadence**, units, screen geometry, and participant/trial identity;
3. preserve source files and fingerprints and keep source/canonical row-count diagnostics visible;
4. keep QC flags and AI-assisted outputs reviewable rather than silently rewriting source samples;
5. justify thresholds and model choices for the study population and task;
6. for learned events, use the [Event-model validation clinic](event-model-validation-clinic.md) to preserve participant/split identity, matched held-out rows, probabilities, calibration, confidence/coverage, and separate sample/event estimands;
7. validate event or dynamic-AOI models with an appropriate labelled corpus and leakage-safe split design;
8. preserve whether lower-rate data are native or derived and, for dynamic AOIs, preserve keyframe/review/interpolation provenance without extrapolation; and
9. freeze software identity, provenance, fingerprints, evidence boundaries, and the study records in the [Study-design templates](study-design-templates.md).

Continue with [Research recipes](research-recipes.md), [Study lifecycle](study-lifecycle.md), [Study-design templates](study-design-templates.md), [Worked tracker import](worked-tracker-import.md), [Real-data import clinic](data-import-clinic.md), [Event-model validation clinic](event-model-validation-clinic.md), [Validation reporting cookbook](validation-reporting-cookbook.md), [Methods overview](methods-overview.md), [Publication readiness](publication-readiness.md), [Validation guide](validation-evidence-guide.md), and [Reproducible reporting](reproducible-reporting.md).
