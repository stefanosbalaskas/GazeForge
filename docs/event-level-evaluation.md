# Event-level evaluation

Sample-level accuracy is not sufficient for eye-event validation. A classifier can label most
samples correctly while still fragmenting one fixation into several events, missing short
saccades, or shifting event boundaries. GazeForge therefore supports explicit temporal event-level
evaluation alongside sample-level discrimination and calibration metrics.

## From samples to events

`samples_to_event_intervals()` converts contiguous sample labels into half-open
`[start_ms, end_ms)` intervals using the declared sampling rate. The half-open convention gives a
single sample a non-zero duration equal to one sample period and makes adjacent events meet without
overlapping.

Segmentation has two important guardrails:

- excluded labels such as `ambiguous`, `unlabelled`, and `undefined` are removed **after** run
  segmentation, so they remain hard separators rather than joining two events across uncertainty;
- timestamp gaps larger than a configurable multiple of the nominal sample period split an event
  even when the labels on both sides are identical.

Group identifiers must be present and timestamps must be strictly increasing inside every
participant/trial. Event intervals supplied directly to the matching API cannot overlap within a
group.

## One-to-one temporal matching

`match_event_intervals()` uses Hungarian assignment independently within each participant/trial.
Candidate pairs are scored by temporal intersection-over-union (IoU). By default the event labels
must also match and the IoU must be at least 0.50. Events from different trials are never eligible
to match.

For each accepted match GazeForge retains:

- temporal IoU;
- signed onset error;
- signed offset error; and
- signed duration error.

Unmatched predicted events are false positives and unmatched reference events are false negatives.

## Metrics

`evaluate_event_intervals()` and `evaluate_sample_event_predictions()` return:

- event precision, recall, and F1;
- matched-event mean temporal IoU;
- mean absolute onset error;
- mean absolute offset error;
- mean absolute duration error;
- per-class versions of the same metrics; and
- the complete one-to-one match table for auditing.

```python
from gazeforge import evaluate_sample_event_predictions

result = evaluate_sample_event_predictions(
    predictions,
    true_label_col="event_label",
    predicted_label_col="predicted_event",
    sampling_rate_hz=60,
    min_iou=0.50,
)

print(result.summary)
print(result.per_class)
```

## Benchmark integration

`compare_event_models_grouped()` now reports event-level metrics on the same held-out folds used for
sample-level metrics. The cross-dataset RF/ContextMLP validator does the same for each held-out
dataset. Consequently a frozen benchmark can expose both sample discrimination/calibration and
event-boundary performance without changing train/test partitions.

The primary benchmark interpretation should report both levels. High sample accuracy does not
override poor event-level recall, fragmentation, temporal IoU, or boundary error.
