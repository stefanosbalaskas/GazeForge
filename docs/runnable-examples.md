# Runnable examples

The repository contains four deterministic examples that move from a small first result to a complete reviewable workflow. Use this page to choose a script, see what it produces, and open the corresponding guide.

!!! warning "Demo output is not validation evidence"
    Every example on this page uses synthetic/demo inputs. The scripts demonstrate software behaviour, composition, plotting, and provenance. They are **not empirical validation evidence** and do not establish native-device, native 60 Hz, Gazepoint, or GP3 validity.

!!! tip "Already have a tracker export?"
    Use the [Real-data import clinic](data-import-clinic.md) before substituting your study data into an example. It makes identity, units, screen geometry, timestamp cadence, duplicate keys, and source fingerprints explicit before QC or modelling.

## At a glance

| Example | Install | Run | Main output |
| --- | --- | --- | --- |
| **Synthetic QC** | base package | `python examples/01_synthetic_qc.py` | printed trial-level QC table |
| **Transparent I-VT** | base package | `python examples/02_ivt_baseline.py` | printed event counts and first-trial transitions |
| **Visual diagnostics** | `.[plot]` | `python examples/03_visual_diagnostics.py --output-dir visual-demo` | six PNG diagnostics |
| **End-to-end workflow** | `.[plot]` by default; base path with `--no-figures` | `python examples/end_to_end_research_workflow.py --output-dir end-to-end-research-demo` | ten CSV tables, provenance, manifest, optional figures |

## 1 · Synthetic QC

Use the smallest example when you want to verify installation and see the non-destructive quality-control contract.

```bash
python examples/01_synthetic_qc.py
```

The script deterministically simulates four participants × three trials, canonicalises the samples at 60 Hz, adds anomaly flags, computes trial quality, and prints:

- `participant_id` and `trial_id`;
- `missing_rate`;
- `offscreen_rate`;
- `anomaly_rate`;
- `large_gap_rate`; and
- `quality_score`.

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

It also writes:

- `provenance.json`, recording the operation trail;
- `workflow_manifest.json`, recording software identity, evidence classification, sampling rate, screen geometry, fingerprints, output inventory, and scientific boundary; and
- when figures are enabled, `figures/01_qc_timeline.png`, `figures/02_aoi_overlay.png`, and `figures/03_scanpath.png`.

The script takes a deep snapshot of the synthetic source table and verifies at the end that the source table remains unchanged. Its manifest labels the bundle `synthetic_demo_not_empirical_evidence`.

[Open the script on GitHub](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/end_to_end_research_workflow.py) · [Read the practical workflow](practical-workflow.md)

## Which example should I run first?

```text
Need to verify installation / QC?        → 01_synthetic_qc.py
Need an inspectable event baseline?       → 02_ivt_baseline.py
Need figure-generation patterns?          → 03_visual_diagnostics.py
Need a complete reviewable output bundle? → end_to_end_research_workflow.py
```

## Move from demo data to a study

The examples intentionally avoid pretending that synthetic behaviour validates a tracker or analysis method. For a real study:

1. start with the [Real-data import clinic](data-import-clinic.md), then replace the simulated source with an explicit tracker adapter or canonical table;
2. record actual acquisition hardware, native sampling rate, observed timestamp cadence, units, screen geometry, and participant/trial identity;
3. keep QC flags and AI-assisted outputs reviewable rather than silently rewriting source samples;
4. justify thresholds and model choices for the study population and task;
5. validate event models with an appropriate labelled corpus and leakage-safe split design;
6. preserve whether lower-rate data are native or derived; and
7. freeze software identity, provenance, fingerprints, and evidence boundaries with the reported result.

Continue with [Real-data import clinic](data-import-clinic.md), [Methods overview](methods-overview.md), [Practical end-to-end workflow](practical-workflow.md), [Validation guide](validation-evidence-guide.md), and [Reproducible reporting](reproducible-reporting.md).
