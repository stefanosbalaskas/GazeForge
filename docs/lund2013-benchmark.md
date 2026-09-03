# Lund2013 empirical event benchmark

GazeForge treats Lund2013 as an **external empirical benchmark**, not bundled package data.
The public `richardandersson/EyeMovementDetectorEvaluation` repository contains the stimuli,
MATLAB analysis code, and recordings labelled by two annotators that were used in Andersson et al.
(2017), *One algorithm to rule them all? An evaluation and discussion of ten eye movement
event-detection algorithms*.

The source repository carries a GPL-3.0 license. GazeForge therefore records the source and license
in the benchmark card but does not copy the raw recordings into the Python package.

## Pinned local acquisition

`gazeforge lund2013-fetch` provides an explicit opt-in path from the external repository to a local
benchmark cache. It is pinned to the same upstream commit recorded in the validation protocol:

```text
richardandersson/EyeMovementDetectorEvaluation
3e12416ab3fd6254c81811cf03f8e5d67c5d7129
annotated_data/data used in the article
```

```bash
gazeforge lund2013-fetch ./external/lund2013
```

The default fetch includes both `RA` and `MN` annotations across `dots`, `img`, and `video`. A
restricted checkout can be requested explicitly:

```bash
gazeforge lund2013-fetch ./external/lund2013-ra \
  --annotators RA \
  --families dots,img,video
```

Every downloaded MATLAB file is checked against the Git blob SHA and byte size reported by GitHub
for the pinned commit. Existing files are reused only when their Git blob identity still matches.
A mismatching local file causes a hard failure unless `--overwrite` is explicitly requested.

The fetcher writes `_gazeforge_source_manifest.json` in the local checkout. The manifest records the
repository, commit, data path, requested annotators and stimulus families, each file's relative path,
Git blob SHA, size, and a deterministic manifest SHA-256 fingerprint. Raw files remain local and are
not added to the GazeForge package or repository.

When this manifest exists, Lund benchmark runners validate the manifest fingerprint, pinned source
identity, file inventory, byte sizes, and Git blob identities again before analysis. The verified
manifest summary is embedded in the resulting benchmark protocol. User-managed Lund directories
without a GazeForge manifest remain supported, but they cannot claim this verified checkout chain.

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
    "/path/to/lund",
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

- deterministic angular I-VT at an explicit 45°/s threshold;
- Random Forest sample classification;
- the boundary-safe temporal-context MLP.

All three methods see exactly the same participant-held-out test rows. The I-VT baseline converts
pixel displacement into degrees of visual angle from each recording's `screenRes`, `screenDim`, and
`viewDist` geometry before thresholding. The 45°/s value is recorded in the protocol rather than
hidden as a device-specific pixel threshold. The learned models are fitted from scratch inside each
fold. Calibration metrics are computed only for probabilistic models.

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

The individual runners remain available:

```bash
gazeforge lund2013-agreement ./external/lund2013 --target-rate 60

gazeforge lund2013-benchmark ./external/lund2013 \
  --annotator RA \
  --target-rate 60 \
  --min-label-purity 0.75 \
  --n-splits 5 \
  --output validation/lund2013-ra-60hz.json

gazeforge lund2013-sensitivity ./external/lund2013 \
  --annotator RA \
  --target-rates 120,90,60,30 \
  --purities 0.60,0.75,0.90 \
  --output validation/lund2013-ra-sensitivity.json
```

`freeze_benchmark_report()` protects an existing report from accidental overwrite unless
`--overwrite` is explicitly supplied.

## One-command validation suite

For the first complete Lund evidence tranche, `gazeforge lund2013-suite` runs the analyses together
and freezes them into one output directory:

```bash
gazeforge lund2013-fetch ./external/lund2013

gazeforge lund2013-suite \
  ./external/lund2013 \
  ./validation/lund2013-v1 \
  --target-rate 60 \
  --min-label-purity 0.75 \
  --n-splits 5 \
  --ivt-threshold-deg-s 45 \
  --target-rates 120,90,60,30 \
  --purities 0.60,0.75,0.90
```

The suite computes all analyses before it writes a completion manifest. The default tranche contains:

1. native 500 Hz MN-vs-RA human-human agreement;
2. derived 60 Hz MN-vs-RA human-human agreement;
3. the RA-labelled 60 Hz participant-held-out I-VT/RF/ContextMLP comparison;
4. the same 60 Hz model comparison using MN labels as annotator sensitivity;
5. the RA sampling-rate × label-purity sensitivity surface.

Each child JSON remains independently fingerprinted. Before freezing, the suite recomputes each
child fingerprint and rejects an inconsistent report. It then writes `lund2013-suite-manifest.json`
**last**. The suite manifest records the verified source-manifest summary, complete protocol, child
filenames, child report fingerprints, and a deterministic suite SHA-256 fingerprint.

If analysis fails, no child reports or completion manifest are written. If protected output files
already exist, the suite fails before analysis starts unless `--overwrite` is explicitly requested.
An incomplete directory without a valid suite manifest must not be described as a completed
validation tranche.

## Post-freeze verification

A copied, archived, or committed suite can be verified independently from the execution step:

```bash
gazeforge lund2013-suite-validate ./validation/lund2013-v1
```

The default verification recomputes the suite-manifest fingerprint, requires the exact five-member
report inventory, checks safe and unique child paths, validates the pinned Lund source identity when
source-manifest provenance is present, and recomputes every referenced child report fingerprint.
Any changed or missing child report invalidates the suite.

For metadata inspection only, child-file I/O can be skipped explicitly:

```bash
gazeforge lund2013-suite-validate ./validation/lund2013-v1 --manifest-only
```

This mode reports `reports_verified: false` and must not be interpreted as evidence that the child
reports themselves were checked. The website uses full verification: a suite is shown as a verified
report suite only when the completion manifest **and every referenced child report** validate.
Individual child reports remain separate evidence rows rather than being replaced by the suite row.

## Planned empirical interpretation

The first empirical release should report:

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

## Event-level reporting

The matched-fold Lund comparison reports event precision/recall/F1, temporal IoU, and boundary
errors alongside sample-level metrics. Event intervals are segmented independently within each
participant/trial using the declared analysis sampling rate. Ambiguous lower-rate windows remain
hard separators and cannot join otherwise adjacent events across an uncertain boundary.
