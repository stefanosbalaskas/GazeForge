# Stratified out-of-fold performance

GazeForge can summarize an already completed held-out event-model comparison by a declared
experimental stratum without fitting any new model. This is useful when overall validation may hide
meaningful differences across stimulus families, tasks, devices, or other pre-existing categories.

The central rule is simple:

> **Stratification describes fixed held-out predictions; it does not create a second training
> experiment.**

`summary_event_predictions_by_stratum()` is intentionally not a training API. The input must already
contain out-of-fold predictions, model identifiers, validation folds, reference labels, and the
stratification variable.

```python
from gazeforge import summarize_event_predictions_by_stratum

family = summarize_event_predictions_by_stratum(
    comparison.predictions,
    stratify_col="stimulus_type",
    sampling_rate_hz=60,
)

print(family.summary)
```

## Reported metrics

For each model × fold × stratum cell, the evaluator records:

- test-row and held-out-group counts;
- accuracy, balanced accuracy, and macro-F1;
- multiclass Brier score and expected calibration error when genuine model probabilities exist;
- event precision, recall, F1, and mean matched temporal IoU;
- absolute onset, offset, and duration errors for matched events.

The aggregate table then reports the number of contributing folds, total test rows, unique held-out
groups, metric means, and fold-to-fold standard deviations.

Deterministic models such as I-VT are **not** assigned fabricated calibration values. When a model
has no probability output, Brier score and ECE remain missing.

## Event-boundary guardrail

Event-level metrics require each event grouping unit—by default one `participant_id × trial_id`—to
belong to exactly one stratum within each model/fold. GazeForge raises an error if a trial crosses
strata instead of slicing an event sequence at an arbitrary category boundary.

If event-level analysis is inappropriate for a use case, it can be disabled explicitly:

```python
family = summarize_event_predictions_by_stratum(
    predictions,
    stratify_col="task_condition",
    sampling_rate_hz=60,
    include_event_level_metrics=False,
)
```

## Lund2013 stimulus families

The Lund2013 loader normalizes source files into three stimulus families:

- `image`;
- `moving_dot`;
- `video`.

`run_lund2013_event_benchmark()` now computes stimulus-family performance from the same
participant-held-out predictions used for the overall I-VT, Random Forest, and ContextMLP
comparison. The frozen report records:

- `metrics.stimulus_type_summary`;
- `metrics.stimulus_type_fold_metrics`;
- `protocol.stimulus_type_design`;
- `protocol.preparation.stimulus_type_counts`.

The design metadata explicitly records `models_refit_by_stratum = false`.

This means a family result answers **“how did the already validated model behave on held-out rows of
this family?”**, not **“how well would a model trained specifically for this family perform?”**.

## Interpretation

Stratified metrics are descriptive validation diagnostics. They can reveal heterogeneity that should
be reported or investigated, but they do not by themselves establish a statistically significant
model × stimulus interaction. Formal inferential comparisons require an analysis designed for that
question, with its uncertainty structure and multiplicity handled explicitly.
