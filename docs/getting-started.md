# Getting started

<div class="gf-doc-kind" role="note" aria-label="Documentation type">
<strong>Tutorial</strong> · Install GazeForge, run a first workflow, and learn the minimum source/QC/validation contract.
</div>

<nav class="gf-help" aria-label="Documentation help">
<a href="gazeforge-tour.md">Tour</a>
<a href="documentation-map.md">Task map</a>
<a href="troubleshooting.md">Troubleshooting</a>
<a href="runnable-examples.md">Examples</a>
<a href="https://github.com/stefanosbalaskas/GazeForge/issues">Ask / report</a>
</nav>


GazeForge is currently alpha research software. The first public alpha release is available from PyPI, while editable development checkouts remain the preferred path when an analysis must be tied to an exact commit.

!!! tip "Not sure what GazeForge actually does?"
    Start with the [GazeForge Tour](gazeforge-tour.md) before reading the API reference. It follows one deterministic gaze table through canonicalisation, non-destructive QC, transparent eye events, AOIs, scanpaths, and provenance, then shows the CSV/JSON artifacts each layer produces.

    ```bash
    python examples/00_gazeforge_tour.py --output-dir gazeforge-tour-demo
    ```

    The tour uses synthetic/demo data. It is a software walkthrough, not empirical tracker, event-model, or measurement validation.

## Install the public alpha

```bash
python -m pip install "gazeforge==0.1.0a1"
```

Optional open-vocabulary semantic AOI detection:

```bash
python -m pip install "gazeforge[vision]==0.1.0a1"
```

The archived release is available as **GazeForge 0.1.0a1**, DOI [`10.5281/zenodo.22650013`](https://doi.org/10.5281/zenodo.22650013).

## Development checkout

For development, validation work, or analyses that must preserve the exact repository commit:

```bash
git clone https://github.com/stefanosbalaskas/GazeForge.git
cd GazeForge
python -m pip install -e ".[dev]"
pytest
```

!!! tip "Have a tracker export?"
    Run the [worked tracker-import/QC example](worked-tracker-import.md) first. It shows an explicit Gazepoint-style `USER_FILE`/`MEDIA_ID`/`TIME`/`BPOGX`/`BPOGY` contract, seconds→milliseconds and normalized→pixel conversion, duplicate/missing/bounds/cadence preflight, source immutability, row-count preservation, and non-destructive QC.

    ```bash
    python examples/07_worked_tracker_import_qc.py \
      --output-dir worked-tracker-import-qc-demo
    ```

    Then use the [Real-data import clinic](data-import-clinic.md) for source variants and troubleshooting. Adapter compatibility is not tracker/device validation.

!!! tip "QC found problems? Review before excluding"
    Continue with the [QC review and exclusion-ledger clinic](qc-review-exclusion-ledger.md). It separates flags, review-required cases, retained observations, reviewed exclusions, and exploratory sensitivity rules instead of turning anomaly flags directly into data deletion.

    ```bash
    python examples/08_worked_qc_review_ledger.py \
      --output-dir worked-qc-review-ledger-demo
    ```

!!! tip "Run one complete workflow"
    Want to see the layers composed before adapting your own tracker export? Run the [practical end-to-end workflow](practical-workflow.md), which writes reviewable source/canonical/QC/event/AOI/scanpath/provenance artifacts and keeps the demo explicitly separate from empirical validation.

    Prefer to choose among smaller scripts first? Browse the [runnable examples](runnable-examples.md) for exact commands, dependencies, and expected outputs.

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
    time_unit="seconds",
    coordinates="normalized",
)
```

For real exports, verify the source units, **nominal/native acquisition rate**, separately **observed timestamp cadence**, duplicate sample keys, and screen geometry in the [Worked tracker import](worked-tracker-import.md) and [Real-data import clinic](data-import-clinic.md). Adapter compatibility does not by itself establish tracker or event-model validity.

## 2. Add QC without deleting the record

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
```

The original rows remain present. GazeForge adds anomaly scores and flags so exclusions can be reviewed and documented later. QC flags are not automatic invalidity labels.

## 3. Review QC and freeze exclusion decisions

Before modelling, preserve the pre-review QC table and record any sample-, trial-, or participant-level decision separately. Keep the criterion ID, scope, rationale, prespecified/exploratory status, decision, denominator, and affected row count visible.

Use the [QC review and exclusion-ledger clinic](qc-review-exclusion-ledger.md) for the executable pattern. A reproducible exclusion rule is not automatically a validated rule, and an anomaly flag is not itself an exclusion decision.

## 4. Train an eye-event model

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

## 5. Validate before interpreting

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

Use the [Event-model validation clinic](event-model-validation-clinic.md) before turning model predictions into manuscript-facing validation claims.

## 6. Add semantic AOIs when needed

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

## 7. Freeze benchmark evidence

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
- tracker and native/nominal sampling rate;
- observed timestamp cadence separately from the nominal/native rate;
- exact source-column mapping, timestamp unit, coordinate basis, and screen/stimulus geometry;
- source fingerprint/checksum plus duplicate/missing/bounds preflight;
- pre-review QC fingerprint and explicit review/exclusion ledger;
- prespecified versus exploratory exclusion/sensitivity criteria and denominator flow;
- any resampling target and label-purity rule;
- event/AOI model and version;
- participant/stimulus split policy;
- calibration/event-level metrics where applicable;
- human-human reference agreement when available; and
- whether evidence is native or derived.

For the public alpha, cite the exact version DOI [`10.5281/zenodo.22650013`](https://doi.org/10.5281/zenodo.22650013) and record `0.1.0a1` in the analysis environment.

Continue with the [GazeForge Tour](gazeforge-tour.md), [Worked tracker import](worked-tracker-import.md), [QC review and exclusion-ledger clinic](qc-review-exclusion-ledger.md), [Real-data import clinic](data-import-clinic.md), [practical end-to-end workflow](practical-workflow.md), [Scientific governance](scientific-governance.md), and [Validation status](validation-status.md).