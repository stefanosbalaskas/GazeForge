# Scientific governance

GazeForge treats AI predictions as measurements with uncertainty, not ground truth.

## Non-negotiable defaults

- AI functions add columns or derived objects; they do not silently delete raw samples.
- Confidence/probability scores are retained.
- Model identity and version are retained with inference outputs.
- Event models enforce sampling-rate compatibility.
- AOI proposals can be corrected by humans, with the correction retained.
- Confirmatory analysis should lock the reviewed AOI/model version before hypothesis testing.
- Participant-level leakage must be prevented in validation.
- Stimulus-level and dataset-level holdouts should be used when the intended generalisation requires them.
- Classical deterministic baselines should be reported beside learned systems when feasible.

## Scope restriction

GazeForge is not intended to infer diagnoses, protected characteristics, personality, emotions,
or other unsupported latent mental states from eye movements. Predictive modules should target
observable, explicitly defined research outcomes and be validated for that exact task.

## 60 Hz recordings

Models trained at high sampling rates must not be assumed valid for 60 Hz data. GazeForge stores
the training sampling rate in event-model metadata and rejects materially incompatible inference
by default. A dedicated 60 Hz benchmark will be part of the validation programme.
