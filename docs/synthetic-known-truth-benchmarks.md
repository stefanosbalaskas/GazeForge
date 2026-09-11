# Known-truth synthetic benchmarks

GazeForge distinguishes **synthetic smoke data** from **known-truth methodological validation**.
The existing `simulate_gaze()` helper remains appropriate for examples and pipeline smoke tests.
It does not preserve a latent reference signal, so it cannot quantify recovery error.

The known-truth benchmark contract instead freezes two separate layers:

```text
latent truth
    ↓
controlled artifact model
    ↓
observed signal
    ↓
analysis / estimator
    ↓
estimate
    ↓
compare to exact truth
    ↓
synthetic recovery certificate
```

This architecture is intended for testing whether an analysis method can recover a quantity that
is exactly known under controlled noise, dropout, calibration bias, sampling rate, and event
regimes. It deliberately does **not** convert simulation performance into evidence of empirical
accuracy on a device, participant population, or external dataset.

## Contract

`simulate_known_truth_gaze()` returns `SyntheticGazeBenchmarkRun` with four separately
fingerprinted tables:

- `truth`: exact latent x/y coordinates, pupil size, and sample-level event state;
- `observed_signal`: the corrupted gaze/pupil stream presented to an analysis pipeline;
- `artifact`: the exact injected measurement noise, dropout state, pupil noise, and calibration
  bias for every sample;
- `event_truth`: contiguous fixation/saccade intervals derived from the latent event state.

The run also records the random seed, sampling rate, artifact model, expected recovery metrics,
and an explicit claim boundary. Reusing the same `SyntheticGazeSpec` and seed reproduces the same
contract fingerprint.

```python
from gazeforge.synthetic_benchmark import (
    SyntheticGazeSpec,
    build_synthetic_recovery_certificate,
    simulate_known_truth_gaze,
)

spec = SyntheticGazeSpec(
    n_participants=12,
    sampling_rate_hz=60.0,
    measurement_noise_sd_px=8.0,
    calibration_bias_px=(12.0, -8.0),
    dropout_probability=0.02,
    random_state=2026,
)
run = simulate_known_truth_gaze(spec)

# Replace this with the output of the method being evaluated.
estimates = run.observed_signal

certificate = build_synthetic_recovery_certificate(
    run,
    estimates,
    estimator_name="uncorrected-observation-baseline",
    thresholds={
        "coordinate_rmse_px": 25.0,
        "valid_coordinate_fraction": 0.95,
    },
)
```

## Fail-closed recovery scoring

`score_synthetic_gaze_recovery()` requires exactly one estimate row for every
participant/trial/sample key. Missing, duplicated, or additional sample identities are rejected.
Coordinate missingness is allowed but lowers the reported coverage. Optional event estimates add
sample-level accuracy and macro-F1 against exact latent event states.

Estimate columns are internally namespaced before they are joined to the truth table, so an
estimator may legitimately use names such as `x_true_px`, `y_true_px`, or `event_label` without
silently colliding with the latent reference columns. The selected x/y/event estimate columns must
still be distinct.

This prevents an estimator from improving its apparent error by silently dropping difficult
samples, changing the evaluation set, or creating ambiguous reference/estimate joins.

## Synthetic recovery certificates

`build_synthetic_recovery_certificate()` binds:

- the complete simulation-contract fingerprint;
- separate truth, observed-signal, artifact, and event-truth fingerprints;
- the estimator-output fingerprint;
- seed and sampling rate;
- recovery metrics and optional acceptance thresholds; and
- a closed scientific claim boundary.

Error thresholds are maxima; coverage, accuracy, and F1 thresholds are minima. Unknown or
non-finite thresholds fail closed. `freeze_synthetic_recovery_certificate()` first validates the
certificate fingerprint, dataset-card semantics, threshold consistency, and closed claim boundary,
then protects an existing certificate from accidental overwrite by default. A re-fingerprinted
certificate with a promoted empirical claim is therefore rejected before any file is written.

A passing certificate means only that the specified method met the declared recovery criteria
**under the frozen simulator assumptions**. It explicitly does not establish:

- GP3 or other eye-tracker empirical accuracy;
- person-independent or subject-independent generalisation;
- cross-dataset generalisation;
- human-reference ground truth;
- eligibility for public Frozen empirical evidence.

## Recommended benchmark surfaces

A single synthetic condition is useful for regression testing, but methodological validation is
stronger when recovery is mapped across an **error surface**. Useful sweeps include sampling rate,
coordinate noise, calibration bias, dropout probability, fixation duration, saccade duration, and
participant/trial count. These surfaces can reveal where a method fails even when its performance
looks acceptable at one convenient setting.

The same contract pattern can later be extended to pupil dynamics, fixation-boundary uncertainty,
timestamp offsets, and multimodal streams without mixing latent truth into the observed signal.
