# For Gazepoint and GP3 users

GazeForge is vendor-neutral, but Gazepoint GP3-class workflows are a first-class use case. The package is designed to sit **after export and before final statistical inference**, adding auditable AI/QC, event modelling, semantic AOIs, validation, and provenance around ordinary gaze tables.

## Where GazeForge fits

```text
Gazepoint Control / Analysis export
              │
              ▼
     explicit import + QC
              │
              ▼
      canonical gaze table
              │
       ┌──────┼──────────────┐
       ▼      ▼              ▼
    QC flags  eye events   semantic AOIs
       │      │              │
       └──────┴──────┬───────┘
                     ▼
             reviewed analysis table
                     │
                     ▼
       statistics / reporting / modelling
```

GazeForge does not require Gazepoint data, and it does not replace deterministic import/preprocessing packages. Its role is the AI-assisted and validation-aware layer.

## Import a common Gazepoint sample table

`adapt_gazepoint_samples()` defaults to common Gazepoint-style semantics:

- `USER_FILE` → participant identifier;
- `MEDIA_ID` → trial/stimulus identifier;
- `TIME` → time in seconds;
- `BPOGX`, `BPOGY` → normalized point-of-gaze coordinates.

The screen resolution is **never guessed**.

```python
import pandas as pd

from gazeforge import adapt_gazepoint_samples

raw = pd.read_csv("participant_export.csv")

gaze = adapt_gazepoint_samples(
    raw,
    screen_size_px=(1920, 1080),
    sampling_rate_hz=60,
)

print(gaze.data.head())
print(gaze.metadata)
```

Normalized screen coordinates are converted to pixels in the canonical table. Source units and column mappings remain in metadata.

## Override export conventions explicitly

Gazepoint export formats and upstream preprocessing can vary. Do not rename columns merely to satisfy GazeForge; declare the mapping instead.

```python
gaze = adapt_gazepoint_samples(
    raw,
    screen_size_px=(2560, 1440),
    participant_col="Participant",
    trial_col="Stimulus",
    timestamp_col="TimeMs",
    x_col="GazeX",
    y_col="GazeY",
    time_unit="milliseconds",
    coordinates="pixels",
    pupil_col="PupilDiameter",
    validity_col="Valid",
    sampling_rate_hz=60,
)
```

This explicitness matters for reproducibility: a different time unit or coordinate basis changes velocity-derived features and event thresholds.

## Bridge processed tables from the wider package ecosystem

If gaze has already been processed by `gp3tools`, `eyeprocesspy`, `gpbiometricspy`, or another workflow, use `adapt_processed_table()` and specify the source columns/scales explicitly.

```python
from gazeforge import adapt_processed_table

gaze = adapt_processed_table(
    processed,
    participant_col="participant",
    trial_col="trial",
    timestamp_col="time_ms",
    x_col="x_px",
    y_col="y_px",
    sampling_rate_hz=60,
    screen_size_px=(1920, 1080),
    source_name="existing_pipeline",
)
```

GazeForge intentionally does not hard-code private or unstable column conventions from upstream packages.

## Add QC without silently deleting samples

```python
from gazeforge import ai_flag_anomalies, score_trial_quality

flagged = ai_flag_anomalies(
    gaze.data,
    sampling_rate_hz=gaze.sampling_rate_hz,
)
quality = score_trial_quality(flagged)
```

The source observations remain present. QC produces auditable scores and flags that can be inspected before any exclusion decision.

## Eye-event modelling at 60 Hz

A GP3-class 60 Hz recording should be treated as a 60 Hz signal throughout model training and inference.

```python
from gazeforge import train_event_classifier, ai_classify_events

model = train_event_classifier(
    labelled_training_data,
    label_col="event_label",
    sampling_rate_hz=60,
)

classified = ai_classify_events(
    gaze.data,
    model,
    sampling_rate_hz=60,
)
```

GazeForge stores training-rate metadata and refuses materially incompatible inference rates rather than silently applying a high-rate model to a low-rate recording.

### Important evidence limit

The package currently has strong **derived 60 Hz validation infrastructure** based on expert-labelled high-rate benchmarks, plus native lower-rate human evidence from other hardware/task domains. This does **not** yet establish GP3-specific event-classification validity.

A native 60 Hz/GP3-class manually labelled event corpus remains an explicit validation target.

See [Validation status](validation-status.md).

## Semantic AOIs for experimental stimuli

For screenshots, advertisements, interfaces, product pages, tourism materials, dictionaries, or other visual stimuli, semantic AOI proposals can supplement manually drawn regions.

```python
from gazeforge.aoi import HuggingFaceZeroShotAOIProvider, detect_semantic_aois

provider = HuggingFaceZeroShotAOIProvider()
aois = detect_semantic_aois(
    "stimulus.png",
    labels=["brand", "claim", "evidence", "price", "call to action"],
    provider=provider,
    min_confidence=0.10,
)
```

AI boxes remain proposals until reviewed. GazeForge can preserve accept/reject/relabel/bounds-correction decisions for later audit.

## Recommended GP3 study workflow

For a new 60 Hz study, a conservative workflow is:

1. export raw/sample-level Gazepoint data;
2. preserve the original export unchanged;
3. adapt into the canonical GazeForge table with explicit screen/time semantics;
4. run deterministic QC and inspect AI anomaly flags;
5. use event models only if their training/validation rate and task are defensible for the intended purpose;
6. review AI-generated AOIs before confirmatory analyses;
7. keep participant/stimulus groups separated during model evaluation;
8. freeze model cards, fingerprints, exclusions, and review decisions;
9. report the exact GazeForge version/commit and sampling-rate assumptions in the manuscript.

## What GazeForge should not replace

GazeForge is not a substitute for:

- tracker calibration and experimental-quality procedures;
- preservation of native Gazepoint exports;
- theoretically justified AOI definitions;
- preregistered analysis decisions;
- participant-level statistical modelling;
- manual review of model failure cases.

It is intended to make AI-assisted steps **more inspectable**, not to make scientific judgement unnecessary.
