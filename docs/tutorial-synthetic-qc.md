# Tutorial: synthetic gaze to auditable QC

This tutorial runs entirely on deterministic synthetic data bundled through `simulate_gaze()`. It is useful for checking an installation, learning the canonical schema, and understanding GazeForge's quality-control philosophy before touching empirical data.

!!! info "Synthetic example"
    This workflow is for software learning and pipeline validation. It is not empirical evidence and does not validate a tracker, QC threshold, or scientific exclusion rule.

## 1. Simulate a small recording

```python
from gazeforge import simulate_gaze

raw = simulate_gaze(
    n_participants=4,
    n_trials=3,
    samples_per_trial=240,
    sampling_rate_hz=60,
    random_state=42,
)

print(raw.head())
print(raw.shape)
```

The synthetic table contains participant and trial identity, millisecond timestamps, pixel coordinates, and pupil values. Occasional missing gaze samples and saccade-like jumps make it useful for a first QC pass.

## 2. Canonicalise explicitly

```python
from gazeforge import canonicalize_gaze

gaze = canonicalize_gaze(
    raw,
    sampling_rate_hz=60,
    screen_size_px=(1920, 1080),
)

print(gaze.sampling_rate_hz)
print(gaze.data.columns.tolist())
```

The important idea is not the synthetic source. It is that the analysis now has an explicit sampling rate, coordinate convention, participant/trial boundary, and canonical table.

## 3. Add anomaly flags without deleting rows

```python
from gazeforge import ai_flag_anomalies

flagged = ai_flag_anomalies(
    gaze.data,
    sampling_rate_hz=gaze.sampling_rate_hz,
    random_state=42,
)

print(flagged[["qc_anomaly_score", "qc_flag"]].head())
```

`ai_flag_anomalies()` adds an Isolation Forest score and binary flag. The original rows remain present.

That distinction matters: an unusual sample is a **review target**, not automatically an invalid observation.

## 4. Summarise trial quality

```python
from gazeforge import score_trial_quality

quality = score_trial_quality(
    flagged,
    screen_size_px=(1920, 1080),
)

print(
    quality[
        [
            "participant_id",
            "trial_id",
            "missing_rate",
            "offscreen_rate",
            "anomaly_rate",
            "large_gap_rate",
            "quality_score",
        ]
    ].to_string(index=False)
)
```

The summary is descriptive. A low `quality_score` should trigger inspection and a prespecified decision rule; it should not silently remove a trial.

## 5. Inspect the rows behind a suspicious trial

```python
worst = quality.sort_values("quality_score").iloc[0]

mask = (
    (flagged["participant_id"] == worst["participant_id"])
    & (flagged["trial_id"] == worst["trial_id"])
)

review = flagged.loc[
    mask,
    [
        "participant_id",
        "trial_id",
        "timestamp_ms",
        "x_px",
        "y_px",
        "pupil",
        "qc_anomaly_score",
        "qc_flag",
    ],
]

print(review.head(20).to_string(index=False))
```

This is the intended review loop: summary → candidate problem → underlying rows → documented decision.

## 6. Continue to a transparent event baseline

Once the QC layer is understood, continue with the [I-VT baseline tutorial](tutorial-ivt-baseline.md). It uses the same synthetic recording and creates deterministic fixation/saccade/noise labels without fitting a learned model.

## Complete runnable example

The repository contains the same workflow as [`examples/01_synthetic_qc.py`](https://github.com/stefanosbalaskas/GazeForge/blob/main/examples/01_synthetic_qc.py).

## What to carry into empirical work

Record at least:

- GazeForge version or commit SHA;
- tracker/export source;
- native sampling rate and any inferred/declared rate;
- coordinate basis and screen geometry;
- QC algorithm and random seed;
- prespecified exclusion/review rule;
- number of samples/trials flagged and number actually excluded;
- whether the raw/canonical rows were retained for audit.

The core principle is simple: **QC should create inspectable evidence before it creates an exclusion.**
