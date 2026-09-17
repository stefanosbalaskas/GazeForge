# Real-data import clinic

Moving from a tracker export to analysis is where small assumptions about time, coordinates, identity, and sampling cadence can become large scientific errors. This clinic gives you a review-first path from **real source data** to GazeForge's canonical gaze table without pretending that successful import is evidence of tracker or model validity.

!!! tip "Prefer an executable worked example?"
    Run the [Worked tracker import and QC](worked-tracker-import.md). It uses a deterministic Gazepoint-style export, explicit seconds→milliseconds and normalized→pixel conversion, duplicate/missing/bounds/cadence preflight, source immutability, row-count preservation, non-destructive QC, provenance, and a manifest.

!!! warning "Import compatibility is not validation"
    A table that can be adapted, canonicalised, or quality-scored is **not thereby validated** for a device, population, task, sampling regime, or eye-event model. In particular, a successful Gazepoint / GP3 import does not establish native 60 Hz or GP3 event validity. Use the [Validation guide](validation-evidence-guide.md) for empirical evidence claims.

## Choose your source path

<div class="gf-task-grid" markdown>

<div class="gf-task-card" markdown>

<span class="gf-task-kicker">Tracker export</span>

### :material-eye-outline: Gazepoint / GP3

Use `adapt_gazepoint_samples()` when your export has Gazepoint-style participant, media/trial, time, and point-of-gaze fields. Declare whether time is in seconds or milliseconds and whether coordinates are normalized or pixels.

[Run the worked import →](worked-tracker-import.md)

</div>

<div class="gf-task-card" markdown>

<span class="gf-task-kicker">Processed table</span>

### :material-table-arrow-right: Custom or upstream table

Use `adapt_processed_table()` when your columns have different names or units. Map every identity/time/gaze field explicitly and declare the scale used to reach milliseconds and pixels.

[Jump to a processed table →](#path-b-generic-processed-table)

</div>

<div class="gf-task-card" markdown>

<span class="gf-task-kicker">Already canonical</span>

### :material-check-decagram-outline: GazeForge-shaped table

Use `canonicalize_gaze()` when the table already uses canonical field names and its timestamps are already milliseconds and gaze coordinates are already pixels.

[Jump to canonical input →](#path-c-already-canonical-table)

</div>

</div>

## Before you import: record the source contract

For each recording or source family, write down the facts you actually know before transforming anything:

| Question | Record explicitly | Why it matters |
| --- | --- | --- |
| Who produced each sample? | participant identifier | prevents accidental participant mixing and leakage |
| Which trial/stimulus does it belong to? | trial/media identifier | bounds temporal operations and review |
| What is the time unit? | seconds, milliseconds, or another documented unit | determines conversion into `timestamp_ms` |
| What do x/y mean? | normalized screen fractions, pixels, or another coordinate system | determines conversion into `x_px`, `y_px` |
| What was the screen geometry? | width × height in pixels | required for normalized→pixel conversion and useful for bounds QC |
| What rate was configured at acquisition? | tracker/native nominal rate | provenance; do not confuse it with observed timestamp cadence |
| Are pupil/validity fields present? | source column names and semantics | optional fields should not be guessed |
| What exact file/table was used? | immutable source copy + fingerprint/checksum | makes downstream transformations auditable |

If one of these facts is unknown, preserve that uncertainty. Do not convert a guess into metadata merely because a function accepts a parameter.

## Preserve the source before transforming it

Fingerprint the source table before adaptation and keep it unchanged beside any canonical derivative.

```python
import pandas as pd
from gazeforge import fingerprint_frame

source = pd.read_csv("recording.csv")
source_snapshot = source.copy(deep=True)
source_fingerprint = fingerprint_frame(source)

print(source.shape)
print(source_fingerprint)
```

GazeForge adapters build a new canonical frame; they do not require you to overwrite the source table.

```python
assert source.equals(source_snapshot)
```

A dataframe fingerprint is useful provenance for the table actually analysed. It is not a replacement for retaining the original acquisition file, acquisition metadata, or a repository/archive checksum when those are available.

## Path A: Gazepoint / GP3 export

The dedicated adapter defaults to common Gazepoint-style fields:

- `USER_FILE` → `participant_id`
- `MEDIA_ID` → `trial_id`
- `TIME` → `timestamp_ms`
- `BPOGX` → `x_px`
- `BPOGY` → `y_px`

The defaults assume `TIME` is in **seconds** and point-of-gaze x/y are **normalized screen fractions**. Those are defaults, not facts about every export variant. Override them when your source documentation says otherwise.

```python
import pandas as pd
from gazeforge import adapt_gazepoint_samples, fingerprint_frame

source = pd.read_csv("gazepoint_export.csv")
source_fingerprint = fingerprint_frame(source)

screen_size_px = (1920, 1080)

gaze = adapt_gazepoint_samples(
    source,
    screen_size_px=screen_size_px,
    participant_col="USER_FILE",
    trial_col="MEDIA_ID",
    timestamp_col="TIME",
    x_col="BPOGX",
    y_col="BPOGY",
    time_unit="seconds",
    coordinates="normalized",
    sampling_rate_hz=None,
)

print(gaze.data.head())
print(gaze.sampling_rate_hz)
print(gaze.metadata)
```

If your export is already in milliseconds or pixels, declare that instead of allowing the defaults to rescale correct values:

```python
gaze = adapt_gazepoint_samples(
    source,
    screen_size_px=(1920, 1080),
    time_unit="milliseconds",
    coordinates="pixels",
)
```

!!! note "Gazepoint adapter ≠ Gazepoint validity"
    The adapter establishes an explicit transformation into the software's canonical schema. It does **not establish device validity**, native 60 Hz eye-event accuracy, calibration quality, or equivalence between different Gazepoint export fields.

The [worked tracker-import example](worked-tracker-import.md) executes this path and deliberately keeps duplicate/off-screen/missing-gaze review cases visible.

## Path B: generic processed table

Use `adapt_processed_table()` when you know which source columns correspond to participant, trial, timestamp, and gaze but the names or units differ.

Example: seconds plus normalized coordinates on a 2560 × 1440 display:

```python
import pandas as pd
from gazeforge import adapt_processed_table

source = pd.read_csv("processed_gaze.csv")
width_px, height_px = 2560, 1440

gaze = adapt_processed_table(
    source,
    participant_col="subject",
    trial_col="stimulus_id",
    timestamp_col="time_s",
    x_col="gaze_x_norm",
    y_col="gaze_y_norm",
    pupil_col="pupil_mm",
    validity_col="valid",
    timestamp_scale_to_ms=1000.0,
    coordinate_scale=(width_px, height_px),
    sampling_rate_hz=None,
    screen_size_px=(width_px, height_px),
    source_name="study_processed_export",
)
```

`adapt_processed_table()` deliberately does not guess columns or units. `timestamp_scale_to_ms` and `coordinate_scale` are direct multiplicative transformations, so choose them from the source specification—not from values that merely “look right.”

For a table already expressed in milliseconds and pixels, both scales are `1.0`.

## Path C: already-canonical table

A canonical sample table requires these columns:

```text
participant_id
trial_id
timestamp_ms
x_px
y_px
```

`pupil` and `validity` are optional.

```python
import pandas as pd
from gazeforge import canonicalize_gaze

source = pd.read_csv("canonical_samples.csv")

gaze = canonicalize_gaze(
    source,
    sampling_rate_hz=None,
    screen_size_px=(1920, 1080),
)
```

You can also rename known source columns with `column_map`. `column_map` renames columns; it does **not** convert seconds to milliseconds or normalized coordinates to pixels. Use an adapter or transform units explicitly before canonicalisation when scaling is required.

## Preflight the data you received

### 1. Check identity fields

Do not let missing participant or trial identifiers become an accidental analysis group.

```python
identity_missing = gaze.data[["participant_id", "trial_id"]].isna().any(axis=1)
print("rows with missing identity:", int(identity_missing.sum()))
```

Investigate missing identity from the source. Whether such rows can be recovered or must be excluded is a study-specific decision that should be documented.

### 2. Inspect duplicate sample keys

```python
sample_key = ["participant_id", "trial_id", "timestamp_ms"]
duplicate_key = gaze.data.duplicated(sample_key, keep=False)
print("rows in duplicated sample keys:", int(duplicate_key.sum()))
```

`canonicalize_gaze()` sorts by participant, trial, and timestamp by default. It **does not silently repair, collapse, or delete duplicate timestamps**. `infer_sampling_rate_hz()` uses positive timestamp differences, so zero-difference duplicates are not evidence that the duplicate rows are harmless. Resolve their meaning from the acquisition/export process before modelling.

### 3. Compare nominal rate with observed timestamp cadence

When `sampling_rate_hz=None`, GazeForge infers a rate from the median **positive within-trial timestamp interval**.

```python
from gazeforge import infer_sampling_rate_hz

observed_rate_hz = infer_sampling_rate_hz(gaze.data)
print(f"observed median-interval rate: {observed_rate_hz:.3f} Hz")
```

If your acquisition metadata says 60 Hz, compare rather than overwrite:

```python
nominal_rate_hz = 60.0
relative_difference = abs(observed_rate_hz - nominal_rate_hz) / nominal_rate_hz
print(f"relative difference: {relative_difference:.1%}")
```

A discrepancy can reflect dropped samples, duplicated timestamps, quantized clocks, pauses, export processing, or a mismatch between the declared and analysed stream. The inferred value is a **cadence diagnostic**, not proof of the tracker's native/nominal hardware rate.

!!! caution "Supplying a rate does not validate timestamps"
    If you pass `sampling_rate_hz=60`, that value is stored after checking only that it is finite and positive. Canonicalisation does not independently prove that the timestamps follow a 60 Hz cadence. Inspect the timestamps when the rate matters scientifically.

### 4. Inspect coordinate bounds

```python
width_px, height_px = gaze.screen_size_px or (1920, 1080)
valid_xy = gaze.data["x_px"].notna() & gaze.data["y_px"].notna()
offscreen = valid_xy & (
    (gaze.data["x_px"] < 0)
    | (gaze.data["x_px"] > width_px)
    | (gaze.data["y_px"] < 0)
    | (gaze.data["y_px"] > height_px)
)
print("off-screen rows:", int(offscreen.sum()))
```

Off-screen values can be meaningful invalid/missing gaze encodings, genuine excursions, or evidence of a coordinate-conversion mistake. Do not clip them merely to make a plot look plausible.

### 5. Reconcile row counts

At the import/QC handoff, make row preservation explicit:

```python
assert len(source) == len(gaze.data)
```

If row counts differ, explain exactly which operation changed them. Do not let filtering happen implicitly inside “cleaning.”

## Move into non-destructive QC

Once identity, units, cadence, geometry, and row counts are reviewable, continue with anomaly flags and trial summaries without deleting source rows:

```python
from gazeforge import ai_flag_anomalies, score_trial_quality

flagged = ai_flag_anomalies(
    gaze.data,
    sampling_rate_hz=gaze.sampling_rate_hz,
)

quality = score_trial_quality(
    flagged,
    screen_size_px=gaze.screen_size_px,
)

print(quality.sort_values("quality_score").head())
```

`ai_flag_anomalies()` adds model-derived QC fields to a copy. `score_trial_quality()` summarizes missingness, screen bounds, anomaly rate, and large temporal gaps. Neither function turns a quality score into a universal exclusion rule.

Run the exact handoff in [Worked tracker import and QC](worked-tracker-import.md), then continue with [Motion-quality gating](motion-quality-gating.md) before event modelling.

## What canonicalisation does—and does not do

| Operation | GazeForge does | GazeForge does not silently do |
| --- | --- | --- |
| schema | require canonical participant/trial/time/x/y columns after mapping | infer arbitrary source-column meaning |
| numeric fields | coerce timestamp/x/y/pupil to numeric | recover corrupted source values |
| ordering | stably sort by participant/trial/timestamp by default | deduplicate repeated timestamps |
| sampling rate | accept an explicit positive rate or infer from median positive within-trial intervals | verify a supplied nominal rate against every timestamp |
| screen metadata | check positive width/height when provided | prove coordinates came from that screen geometry |
| coordinates | preserve canonical x/y values after declared conversion | clip off-screen values or infer an unknown coordinate system |
| scientific validity | provide an auditable software representation | establish device, model, or population validity |

## Troubleshooting clinic

| Symptom | Likely causes to investigate | Review-first remediation |
| --- | --- | --- |
| gaze points are thousands of pixels off screen | normalized values multiplied twice; wrong screen geometry; source already in pixels | inspect source range and metadata; declare `coordinates="pixels"` or correct the explicit scale |
| gaze is squeezed into 0–1 near the top-left | normalized coordinates were treated as pixels | provide the actual screen dimensions and normalized→pixel conversion |
| inferred rate is around 0.06 Hz instead of 60 Hz | milliseconds were treated as seconds or multiplied twice | inspect raw timestamp deltas; correct `time_unit` or `timestamp_scale_to_ms` |
| inferred rate is around 60,000 Hz | seconds were treated as milliseconds | inspect raw timestamp deltas; convert seconds to milliseconds exactly once |
| canonicalisation fails on timestamp values | non-numeric/missing timestamp strings | inspect the original rows and export format; do not fill times by guesswork |
| participant or trial groups collapse together | wrong identity columns or missing identifiers | verify source identity fields before any temporal/model operation |
| duplicate sample keys appear | repeated export rows, multiple streams sharing a clock value, timestamp quantization | inspect source semantics; preserve duplicates until their meaning is resolved |
| many samples are off screen | wrong coordinate system/geometry, source invalid-value encoding, or actual off-screen gaze | inspect source documentation and validity fields; do not clip automatically |
| nominal and observed rates disagree | dropped/duplicated samples, pauses, processed stream, clock quantization | report both provenance and analysed cadence; diagnose before choosing rate-dependent thresholds |
| QC flags seem unexpectedly dense | unit/rate errors or a dataset unlike the model's assumptions | re-check import contract first; then inspect features/thresholds and document any QC rule |
| two imports produce different fingerprints | source values/index/columns/dtypes differ | treat them as different analysis inputs and trace why before comparing outputs |

## A compact real-study handoff

```text
immutable tracker/source table
        ↓  checksum/fingerprint + source contract
explicit adapter / unit conversion
        ↓
canonical participant · trial · ms · pixels table
        ↓  inspect identity + duplicates + observed cadence + bounds + row counts
non-destructive QC
        ↓
reviewed analysis-ready derivative
        ↓
event / AOI / scanpath / statistical methods
        ↓
provenance + validation scope + reproducible report
```

The import stage should make uncertainty more visible, not less. A clean canonical table is the beginning of scientific review—not the end of validation.

## Where to go next

- [Worked tracker import and QC](worked-tracker-import.md) for the executable source→preflight→QC bundle.
- [Getting started](getting-started.md) for the shortest package walkthrough.
- [Adapters & validation](adapters-validation.md) for API-level adapter details.
- [Motion-quality gating](motion-quality-gating.md) for non-destructive QC policy.
- [Runnable examples](runnable-examples.md) for deterministic demo scripts.
- [Practical end-to-end workflow](practical-workflow.md) for a complete reviewable output bundle.
- [Validation guide](validation-evidence-guide.md) before making device/model-validity claims.
