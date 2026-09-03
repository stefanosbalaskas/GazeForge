# Getting started

GazeForge is currently alpha research software. The recommended installation path is an editable development checkout so that the exact commit used for analysis is visible and reproducible.

## Install

```bash
git clone https://github.com/stefanosbalaskas/GazeForge.git
cd GazeForge
python -m pip install -e ".[dev]"
```

Optional open-vocabulary semantic AOI detection:

```bash
python -m pip install -e ".[vision]"
```

Run the test suite before using a development checkout in a study:

```bash
pytest
```

## 1. Canonicalise gaze samples

GazeForge works around a vendor-neutral sample table. The core required columns are participant, trial, timestamp, and gaze coordinates.

```python
from gazeforge import canonicalize_gaze

gaze = canonicalize_gaze(
    samples,
    sampling_rate_hz=60,
    screen_size_px=(1920, 1080),
)
```

For Gazepoint exports, use the dedicated adapter so normalized screen coordinates and time units are converted explicitly rather than guessed.

```python
from gazeforge import adapt_gazepoint_samples

gaze = adapt_gazepoint_samples(
    gazepoint_export,
    screen_size_px=(1920, 1080),
)
```

## 2. Add QC without deleting the record

```python
from gazeforge import ai_flag_anomalies, score_trial_quality

flagged = ai_flag_anomalies(
    gaze.data,
    sampling_rate_hz=gaze.sampling_rate_hz,
)
quality = score_trial_quality(flagged)
```

The original rows remain present. GazeForge adds anomaly scores and flags so exclusions can be reviewed and documented later.

## 3. Train an eye-event model

```python
from gazeforge import ai_classify_events, train_event_classifier

model = train_event_classifier(
    labelled_samples,
    label_col="event_label",
    sampling_rate_hz=60,
)
classified = ai_classify_events(
    new_samples,
    model,
    sampling_rate_hz=60,
)
```

The training sampling rate is stored with the model and checked at inference.

For a boundary-safe temporal baseline:

```python
from gazeforge import ai_classify_events_context, train_context_event_classifier

model = train_context_event_classifier(
    labelled_samples,
    label_col="event_label",
    sampling_rate_hz=60,
    context_radius_ms=50,
)
classified = ai_classify_events_context(new_samples, model, sampling_rate_hz=60)
```

Temporal windows never cross participant/trial boundaries.

## 4. Validate before interpreting

```python
from gazeforge import grouped_event_cross_validate

result = grouped_event_cross_validate(
    labelled_samples,
    label_col="event_label",
    group_col="participant_id",
    n_splits=5,
    sampling_rate_hz=60,
)
```

A fresh model is fitted inside every fold. GazeForge also provides matched-model comparisons, leave-one-dataset-out validation, calibration diagnostics, and event-level temporal evaluation.

## 5. Add semantic AOIs when needed

Static and dynamic AOIs are separate from the event-modelling layer. AI-generated boxes are proposals until reviewed.

```python
from gazeforge.aoi import HuggingFaceZeroShotAOIProvider, detect_semantic_aois

provider = HuggingFaceZeroShotAOIProvider()
aois = detect_semantic_aois(
    "stimulus.png",
    labels=["brand", "price", "claim", "product"],
    provider=provider,
    min_confidence=0.10,
)
```

See [Dynamic AOIs](dynamic-aois.md) for time-varying stimuli.

## 6. Freeze benchmark evidence

For Lund2013:

```bash
gazeforge lund2013-benchmark /path/to/lund \
  --annotator RA \
  --target-rate 60 \
  --ivt-threshold-deg-s 45 \
  --output validation/lund2013-ra-60hz.json
```

For a rate × boundary-purity surface:

```bash
gazeforge lund2013-sensitivity /path/to/lund \
  --annotator RA \
  --target-rates 120,90,60,30 \
  --purities 0.60,0.75,0.90 \
  --output validation/lund2013-ra-sensitivity.json
```

Frozen benchmark JSON includes a deterministic SHA-256 fingerprint and the evidence metadata required to interpret the result.

## What to record in a manuscript

At minimum, report:

- GazeForge version or commit SHA;
- tracker and native sampling rate;
- any resampling target and label-purity rule;
- event/AOI model and version;
- participant/stimulus split policy;
- excluded labels and QC rules;
- calibration/event-level metrics where applicable;
- human-human reference agreement when available;
- whether evidence is native or derived.

Continue with [Scientific governance](scientific-governance.md) and [Validation status](validation-status.md).
