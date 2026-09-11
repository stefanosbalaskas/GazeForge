# Motion-quality reliability gating

Multimodal recordings should distinguish three questions that are often conflated:

**sensor present → signal usable → signal contributes to analysis**

A sensor channel can exist in the data while being temporarily unreliable. GazeForge therefore supports time-varying **reliability weighting** rather than forcing every quality decision into an all-or-nothing exclusion.

The motion-quality workflow is:

```text
aligned accelerometer axes
        ↓
vector jerk
        ↓
trailing RMS motion index
        ↓
explicit clean / severe thresholds
        ↓
continuous reliability weight [0, 1]
        ↓
downstream weighted model or multimodal fusion
```

The gate does **not** remove samples, rewrite the physiological signal, or claim to correct motion artifacts.

## Why vector jerk?

`derive_accelerometer_motion_index()` computes the Euclidean norm of the derivative of the accelerometer vector and then a trailing root-mean-square value over a specified time window. Using vector jerk makes the index respond to changes in movement rather than treating a fixed sensor orientation or gravity component as motion contamination.

The first sample in each participant/trial group remains unknown because there is no preceding within-group transition from which jerk can be estimated. Motion is never computed across participant or trial boundaries, and a boundary sample is never reinterpreted as clean merely because no derivative is available.

Rows with missing acceleration or any other unevaluable transition likewise remain missing. GazeForge deliberately does not reinterpret missing motion evidence as a clean segment.

```python
from gazeforge.quality_gating import derive_accelerometer_motion_index

indexed = derive_accelerometer_motion_index(
    data,
    accel_cols=("acc_x", "acc_y", "acc_z"),
    smoothing_window_ms=250,
)
```

Timestamps must be finite and strictly increasing within every group. Duplicate or reversed timestamps fail closed because a derivative would otherwise be undefined or misleading.

## Thresholds are explicit, not universal

Accelerometer units, mounting position, device dynamics, task demands, and participant behavior differ across studies. GazeForge therefore does **not** ship a universal motion threshold.

A gate requires an explicit `MotionQualityGateSpec`:

```python
from gazeforge.quality_gating import MotionQualityGateSpec

spec = MotionQualityGateSpec(
    clean_threshold=2.0,
    severe_threshold=12.0,
    minimum_weight=0.10,
    smoothing_window_ms=250,
    threshold_basis="device-specific pilot analysis",
)
```

`threshold_basis` records why those thresholds were chosen. It is provenance, not an automatic validation claim. The certificate always records that threshold validity requires separate domain justification. Numeric threshold/window inputs are canonicalized to finite floats and the basis text is trimmed before certification so semantically equivalent settings replay identically.

## Continuous quality weights

`quality_weight_from_motion()` maps the motion index to a bounded reliability weight:

- motion at or below `clean_threshold` → `1.0`;
- motion at or above `severe_threshold` → `minimum_weight`;
- intermediate motion → linear interpolation;
- missing motion evidence → missing weight.

This preserves uncertainty. A missing accelerometer segment or unevaluable group-boundary transition is not silently treated as fully reliable.

```python
from gazeforge.quality_gating import quality_weight_from_motion

weights = quality_weight_from_motion(
    indexed["motion_index"],
    clean_threshold=2.0,
    severe_threshold=12.0,
    minimum_weight=0.10,
)
```

## Apply a modality gate

`apply_accelerometer_quality_gate()` derives motion and appends the reliability fields in one operation:

```python
from gazeforge.quality_gating import apply_accelerometer_quality_gate

gated = apply_accelerometer_quality_gate(
    data,
    spec=spec,
    modality="pupil",
    signal_cols=("pupil",),
)
```

The output adds:

| Column | Meaning |
| --- | --- |
| `motion_jerk` | instantaneous vector-jerk magnitude |
| `motion_index` | trailing RMS vector jerk |
| `quality_modality` | modality to which the gate is being applied |
| `quality_weight` | continuous reliability weight |
| `quality_state` | `clean`, `downweighted`, `severe`, `motion_unknown`, or `signal_missing` |

If a declared signal column is missing at a row, that row receives weight `0` and state `signal_missing`. If the signal exists but motion cannot be estimated—including the first sample after each participant/trial boundary—the weight remains missing and the state is `motion_unknown`.

The original rows, index, and source/signal values are preserved. Existing generated output columns are protected from silent overwrite by default. `overwrite=True` may refresh prior generated quality outputs, but output names must remain distinct and can never alias protected grouping, timestamp, accelerometer, motion-index, or declared signal columns.

## Summarize effective information

`summarize_motion_quality()` reports more than the number of retained rows. It includes:

- known and unknown weight counts;
- the effective weight sum;
- mean and minimum known reliability weight; and
- the fraction of samples in each quality state.

Summary input is itself validated: finite quality weights must remain in `[0, 1]`, and states must belong to the fixed gate-state taxonomy. This prevents a manually modified table from being summarized as though it were a valid gate output.

This supports reporting how much usable information remained after quality weighting instead of merely stating that a sensor was recorded.

## Replayable quality certificate

`build_motion_quality_certificate()` binds the exact input table, gate specification, output fingerprint, motion-index definition, summary, and scientific claim boundary:

```python
from gazeforge.quality_gating import build_motion_quality_certificate

certificate = build_motion_quality_certificate(
    data,
    spec=spec,
    modality="pupil",
    signal_cols=("pupil",),
)
```

The certificate can be replay-validated from the exact input:

```python
from gazeforge.quality_gating import validate_motion_quality_certificate

validate_motion_quality_certificate(certificate, data)
```

A re-signed JSON file cannot promote the gate into an artifact-correction or sensor-validity claim because the fixed claim boundary and the exact output are rebuilt during replay.

`freeze_motion_quality_certificate()` performs exact replay before persistence and refuses to overwrite an existing file unless explicitly requested.

## Scientific claim boundary

A motion-quality certificate means that the specified reliability-weight calculation is reproducible for the exact bound input and settings. It does **not** establish that:

- the accelerometer is a validated motion-artifact detector for the target modality;
- the chosen thresholds are universally or empirically optimal;
- contaminated physiological samples were corrected;
- a particular modality improves prediction; or
- weighted fusion is superior to exclusion or an unweighted analysis.

Those are empirical questions. The gate is an auditable preprocessing abstraction that makes reliability assumptions explicit.

## Recommended validation

When using the gate in a scientific study, report a sensitivity surface over plausible clean/severe thresholds or justify thresholds from an independent calibration/pilot set. For known-truth development, combine the gate with controlled simulation:

```text
latent signal → inject motion-linked contamination → estimate motion reliability
              → weighted analysis → compare recovery against exact truth
```

This separates **quality estimation** from **downstream scientific performance** and makes failure regimes visible.
