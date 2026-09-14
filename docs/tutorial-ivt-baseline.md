# Tutorial: build an inspectable I-VT event baseline

This tutorial uses GazeForge's deterministic pixel-velocity I-VT implementation to create fixation, saccade, and noise labels. It is deliberately simple: the goal is to establish a transparent reference before adding a learned classifier.

!!! info "Baseline, not validation"
    Running I-VT on synthetic or unlabelled data does not establish event-detection validity. Validation requires an appropriate human-reference corpus and an explicit held-out design.

## 1. Create and canonicalise synthetic gaze

```python
from gazeforge import canonicalize_gaze, simulate_gaze

raw = simulate_gaze(
    n_participants=3,
    n_trials=2,
    samples_per_trial=300,
    sampling_rate_hz=60,
    random_state=42,
)

gaze = canonicalize_gaze(
    raw,
    sampling_rate_hz=60,
    screen_size_px=(1920, 1080),
)
```

## 2. Run the transparent baseline

```python
from gazeforge import ivt_classify_events

classified = ivt_classify_events(
    gaze.data,
    sampling_rate_hz=gaze.sampling_rate_hz,
    velocity_threshold_px_s=1000.0,
)

print(classified["predicted_event"].value_counts())
```

The pixel-coordinate implementation assigns:

- `noise` when gaze coordinates are missing;
- `saccade` when velocity exceeds the explicit threshold;
- `fixation` otherwise.

The output also records `event_model="I-VT"` and `event_model_version="deterministic"`.

## 3. Inspect event transitions by trial

```python
cols = [
    "participant_id",
    "trial_id",
    "timestamp_ms",
    "x_px",
    "y_px",
    "predicted_event",
]

first_trial = classified.loc[
    (classified["participant_id"] == classified["participant_id"].iloc[0])
    & (classified["trial_id"] == classified["trial_id"].iloc[0]),
    cols,
]

changes = first_trial["predicted_event"].ne(
    first_trial["predicted_event"].shift()
)
print(first_trial.loc[changes].to_string(index=False))
```

Looking at transitions is often more informative than looking only at sample-level class counts. Boundary timing is one reason GazeForge reports event-level metrics separately from sample-level classification metrics.

## 4. Prefer angular velocity when geometry is known

Pixel velocity is easy to inspect but is not geometry-normalised. The angular baseline requires geometry columns in the gaze table so every participant/trial is tied to explicit, invariant screen dimensions and viewing distance.

```python
from gazeforge import ivt_classify_events_angular

with_geometry = gaze.data.assign(
    screen_width_px=1920.0,
    screen_height_px=1080.0,
    screen_width_physical=53.0,
    screen_height_physical=29.8,
    view_distance_physical=65.0,
)

angular = ivt_classify_events_angular(
    with_geometry,
    sampling_rate_hz=60,
    velocity_threshold_deg_s=45.0,
)
```

The physical screen dimensions and viewing distance may use any shared length unit. Use the actual geometry of the experiment; do not copy the illustrative values above into an empirical analysis unless they match the acquisition setup.

## 5. Move from labels to validation

If expert-labelled data are available, the next question is not "which model has the highest training score?" It is whether each method performs on the same held-out participants and rows.

Start with:

```python
from gazeforge import compare_event_models_grouped

comparison = compare_event_models_grouped(
    labelled_samples,
    label_col="event_label",
    group_col="participant_id",
    n_splits=5,
    sampling_rate_hz=60,
)
```

Then add calibration and event-level temporal evaluation where relevant.

## Why keep I-VT in the benchmark?

The current reviewed external evidence illustrates why a transparent baseline remains scientifically useful. In the Lund2013 derived-60-Hz checkpoint, ContextMLP leads the reported sample-level multiclass metrics, while I-VT leads event-F1. In the reviewed Hollywood2EM source-token checkpoint, the same broad multi-criterion pattern appears.

See the [Results gallery](results-gallery.md) for the plots and the exact evidence boundaries.

## Complete runnable example

The repository contains the synthetic baseline workflow as [`examples/02_ivt_baseline.py`](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/02_ivt_baseline.py).
