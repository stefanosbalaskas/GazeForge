# Lund2013 empirical event benchmark

GazeForge treats Lund2013 as an **external empirical benchmark**, not bundled package data.
The public `richardandersson/EyeMovementDetectorEvaluation` repository contains the stimuli,
MATLAB analysis code, and recordings labelled by two annotators that were used in Andersson et al.
(2017), *One algorithm to rule them all? An evaluation and discussion of ten eye movement
event-detection algorithms*.

The source repository carries a GPL-3.0 license. GazeForge therefore records the source and license
in the benchmark card but does not copy the raw recordings into the Python package.

## Native loader

`load_lund2013_mat()` reads the MATLAB `ETdata` structure directly. The adapter uses:

- `ETdata.sampFreq` for the recording frequency;
- columns 4 and 5 of MATLAB's one-based `ETdata.pos` matrix for x/y gaze coordinates;
- column 6 for the expert event code;
- the original event coding: 0 unlabelled, 1 fixation, 2 saccade, 3 PSO, 4 pursuit,
  5 blink, and 6 undefined.

A paired `(0, 0)` gaze coordinate is converted to missing by default, matching established loaders
for this benchmark. The original value is never overwritten in the source file.

```python
from gazeforge import load_lund2013_mat

gaze = load_lund2013_mat("TH34_img_Europe_labelled_RA.mat")
print(gaze.sampling_rate_hz)
print(gaze.data[["timestamp_ms", "x_px", "y_px", "event_label"]].head())
```

`load_lund2013_directory()` concatenates all files for one requested annotator while retaining
participant, trial, stimulus type, source file, and annotator provenance.

## Deriving the 60 Hz tranche

The original files are approximately 500 Hz. A GP3-class benchmark therefore requires a documented
lower-rate derivation rather than simple row skipping.

`resample_labeled_gaze()` uses two separate rules:

1. continuous gaze coordinates are linearly interpolated only across gaps below an explicit maximum;
2. the event label for each target sample is the majority source label in that target-sample window.

The majority label is accepted only when its purity reaches `min_label_purity`. Tied or mixed
boundary windows are marked `ambiguous`. Their prevalence is recorded before they are excluded from
the primary model-comparison table.

```python
from gazeforge import prepare_lund2013_benchmark

prepared = prepare_lund2013_benchmark(
    "/path/to/EyeMovementDetectorEvaluation/annotated_data/data used in the article",
    annotator="RA",
    target_sampling_rate_hz=60,
    min_label_purity=0.75,
)

print(prepared.preparation_report["resampling"]["ambiguous_fraction"])
```

This design prevents GazeForge from claiming that a 60 Hz sample close to a 500 Hz expert event
boundary has an unambiguous ground-truth identity.

## Human-human agreement

The benchmark includes paired MN and RA annotations. `compare_lund2013_annotators()` reports exact
sample agreement, Cohen's kappa, and confusion matrices. At a derived sampling rate the two
annotators are resampled independently before alignment, so lower-rate agreement is not obtained by
copying one annotator's temporal boundaries onto the other.

```python
from gazeforge import compare_lund2013_annotators

agreement = compare_lund2013_annotators(
    "/path/to/lund",
    target_sampling_rate_hz=60,
)
```

Human-human agreement should be reported alongside model-human performance. It is a reference for
annotation variability, not a claim that one annotator is error-free ground truth.

## Matched-fold model comparison

`run_lund2013_event_benchmark()` prepares the requested annotator's 60 Hz table and evaluates:

- deterministic I-VT;
- Random Forest sample classification;
- the boundary-safe temporal-context MLP.

All three methods see exactly the same participant-held-out test rows. The learned models are fitted
from scratch inside each fold. Calibration metrics are computed only for probabilistic models.

```python
from gazeforge import run_lund2013_event_benchmark

run = run_lund2013_event_benchmark(
    "/path/to/lund",
    annotator="RA",
    target_sampling_rate_hz=60,
    n_splits=5,
)

print(run.comparison.summary)
print(run.report["report_fingerprint_sha256"])
```

No empirical performance numbers should be quoted until the exact source checkout, preparation
policy, model configuration, and resulting report fingerprint are frozen.

## Command line

```bash
gazeforge lund2013-agreement /path/to/lund --target-rate 60

gazeforge lund2013-benchmark /path/to/lund \
  --annotator RA \
  --target-rate 60 \
  --min-label-purity 0.75 \
  --n-splits 5 \
  --output validation/lund2013-ra-60hz.json
```

`freeze_benchmark_report()` protects an existing report from accidental overwrite unless
`--overwrite` is explicitly supplied.

## Planned frozen analyses

The first empirical release report should include:

1. native MN-vs-RA agreement;
2. derived-60-Hz MN-vs-RA agreement;
3. ambiguity fraction introduced by 500-to-60-Hz label transfer;
4. participant-held-out I-VT/RF/ContextMLP comparison using RA labels;
5. sensitivity using MN labels;
6. sensitivity to the label-purity threshold;
7. per-stimulus-family performance for image, moving-dot, and video recordings;
8. limitations caused by deriving 60 Hz data from a high-rate device rather than collecting a
   native 60 Hz expert-labelled corpus.

The derived 60 Hz tranche is therefore a bridge benchmark. A native GP3-class manually annotated
corpus remains desirable before claiming device-specific validity.
