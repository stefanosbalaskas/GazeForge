# Visual diagnostics

GazeForge's plotting layer is designed for **inspection, communication, and review**. It renders analytic structures that already exist; it does not refit models, delete observations, change event labels, or upgrade evidence strength.

!!! warning "Visuals do not create validation evidence"
    Every figure on this page uses synthetic/demo data. The examples demonstrate software behaviour and reporting patterns only. They do not validate a tracker, event model, AOI detector, scanpath method, or exclusion rule.

## Install the plotting layer

For a repository checkout, install the optional plotting extra:

```bash
git clone https://github.com/stefanosbalaskas/GazeForge.git
cd GazeForge
python -m pip install -e ".[plot]"
```

The plotting extra is a development-surface addition after the `0.1.0a1` public archive. Use an exact repository commit for work that depends on it until it appears in a later public release.

Library plotting functions deliberately **do not call `show()` or `savefig()`**. Each function returns a Matplotlib `Axes`, so the researcher decides whether to compose panels, add manuscript annotations, display interactively, or save a file.

## QC flags: inspect before excluding

<figure class="gf-figure-card">
  <img src="assets/figures/synthetic-qc-diagnostics.svg" alt="Synthetic quality-control anomaly timeline with four flagged samples marked using X symbols." loading="lazy">
  <figcaption>Synthetic/demo QC view. Flags are review targets, not automatic deletion rules.</figcaption>
</figure>

```python
from gazeforge import ai_flag_anomalies, canonicalize_gaze, simulate_gaze
from gazeforge.visualization import plot_qc_timeline

raw = simulate_gaze(n_participants=1, n_trials=1, samples_per_trial=180)
gaze = canonicalize_gaze(raw, sampling_rate_hz=60)
flagged = ai_flag_anomalies(gaze.data, sampling_rate_hz=60)

ax = plot_qc_timeline(flagged)
```

The figure uses an explicit X marker for flagged samples, so the distinction is not carried by colour alone.

## Event probabilities and calibration

<figure class="gf-figure-card">
  <img src="assets/figures/synthetic-event-diagnostics.svg" alt="Synthetic event probabilities using solid, dashed, and dotted lines beside a top-label calibration plot with an ideal diagonal and observed labelled points." loading="lazy">
  <figcaption>Synthetic/demo probability and calibration diagnostics. Probability traces use line-style cues as well as colour.</figcaption>
</figure>

```python
from gazeforge.visualization import (
    plot_event_calibration,
    plot_event_probabilities,
)

probability_ax = plot_event_probabilities(
    predictions,
    confidence_threshold=0.60,
)
calibration_ax = plot_event_calibration(
    labelled_predictions,
    n_bins=10,
)
```

`plot_event_calibration()` delegates calibration binning to the existing `top_label_calibration_table()` implementation. Empty bins are not fabricated, and non-empty points are annotated with their bin sample count.

A confidence threshold drawn on the probability plot is a visual reference only. It does not change the prediction table or apply abstention automatically.

## Semantic AOIs and scanpaths

<figure class="gf-figure-card">
  <img src="assets/figures/synthetic-aoi-scanpath.svg" alt="Synthetic semantic AOI rectangles labelled logo, nutrition claim, and product with a numbered five-fixation scanpath." loading="lazy">
  <figcaption>Synthetic/demo semantic AOIs and fixation order. Labels and sequence numbers remain readable independently of colour.</figcaption>
</figure>

```python
from gazeforge.aoi import AOI
from gazeforge.visualization import plot_aoi_overlay, plot_scanpath

aois = [
    AOI("logo", "logo", 120, 90, 430, 270),
    AOI("claim", "nutrition claim", 1080, 110, 1710, 330),
    AOI("product", "product", 620, 360, 1320, 920),
]

plot_aoi_overlay(aois, fixations=fixations)
plot_scanpath(fixations, label_col="aoi_label")
```

The AOI plot preserves semantic text labels and AOI IDs. `plot_scanpath()` can annotate fixation order and semantic label beside each point so a printed or low-saturation figure still communicates sequence meaning.

## Dynamic AOIs: show the temporal source

<figure class="gf-figure-card">
  <img src="assets/figures/synthetic-dynamic-aoi.svg" alt="Three synthetic dynamic AOI snapshots at 0, 50, and 100 milliseconds; the middle rectangle is explicitly identified as bounded interpolation." loading="lazy">
  <figcaption>Synthetic/demo dynamic AOI snapshots. The middle geometry is interpolated only because it lies inside the observed keyframe interval and within the maximum gap.</figcaption>
</figure>

```python
from gazeforge.visualization import plot_dynamic_aoi_snapshot

ax = plot_dynamic_aoi_snapshot(
    keyframes,
    timestamp_ms=50,
    max_interpolation_gap_ms=100,
)
```

This function reuses GazeForge's existing `interpolate_dynamic_aoi()` semantics. It does not extrapolate outside the observed track and does not bridge a keyframe interval larger than `max_interpolation_gap_ms`.

## Compose your own manuscript panel

Because every plotting function accepts an optional `ax`, panels stay under caller control:

```python
from matplotlib import pyplot as plt
from gazeforge.visualization import plot_event_calibration, plot_event_probabilities

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
plot_event_probabilities(predictions, ax=axes[0])
plot_event_calibration(labelled_predictions, ax=axes[1])
fig.tight_layout()
```

There is no hidden global style change. GazeForge uses the active Matplotlib configuration and adds redundant marker/line-style/text cues where useful.

## Generate the complete demo set

The repository example writes six PNG files from deterministic synthetic/demo structures:

```bash
python -m pip install -e ".[plot]"
python examples/03_visual_diagnostics.py --output-dir visual-demo
```

The script prints an explicit reminder that its output is software demonstration material rather than empirical validation evidence.

## Reporting guidance

When a visual enters a paper, supplement, teaching deck, or public site:

- state whether the source is **empirical**, **derived empirical**, **known-truth synthetic**, or **software demo**;
- retain the sampling-rate and split-design qualification beside benchmark plots;
- describe what flags/thresholds mean rather than implying automatic invalidity;
- include text, marker, dash, symbol, or direct-label cues instead of encoding meaning only by hue;
- provide a textual table or description for the key values communicated by a chart;
- preserve the exact software version/commit and the evidence/report fingerprint when the plot reflects frozen benchmark evidence.

For manuscript-facing provenance, continue with [Reproducible reporting](reproducible-reporting.md). For reviewed empirical benchmark plots, use the [Results gallery](results-gallery.md).
