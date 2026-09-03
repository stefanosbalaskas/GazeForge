# Sampling-rate and boundary-purity sensitivity

Eye-event benchmark performance can change for two distinct reasons when a high-rate human-labelled
recording is converted to a lower rate:

1. temporal information is removed by lower sampling; and
2. target windows near human event boundaries contain mixed source labels.

GazeForge evaluates those effects jointly with `evaluate_sampling_purity_sensitivity()` rather than
selecting one convenient resampling configuration.

## Sensitivity surface

The function evaluates a Cartesian grid of target sampling rates and minimum majority-label purity
thresholds. A typical Lund2013 analysis can compare, for example, 120, 90, 60, and 30 Hz at label
purities of 0.60, 0.75, and 0.90.

Every grid condition is retained in the result even when model comparison is not scientifically
possible after exclusions.

`SamplingSensitivityResult.settings` contains one row per rate/purity setting with:

- source and target sampling rate;
- minimum label-purity threshold;
- source and target row counts;
- ambiguous row count and fraction;
- mean source-label purity;
- total rows excluded after resampling;
- retained row count and fraction;
- retained participant/group and event-class counts; and
- `comparison_status` plus a machine-readable reason when the setting is not evaluable.

`SamplingSensitivityResult.model_metrics` contains the matched-fold I-VT, Random Forest, and
ContextMLP summary rows for evaluable settings. These include the package's existing sample-level,
calibration, and event-level temporal metrics.

## Label policy

The default exclusion policy matches the primary Lund2013 benchmark:

- `ambiguous`;
- `unlabelled`; and
- `undefined`.

Their prevalence is recorded **before** exclusion. They are not converted into trainable event
classes. This prevents a low-rate setting from appearing better or worse merely because its
boundary uncertainty was learned as another category.

Custom exclusions are allowed, but a sensitivity report intended for comparison with the main Lund
benchmark should retain the same policy.

## Non-evaluable settings

A sensitivity condition is recorded as `not_evaluable` when, after label exclusions, it has:

- no analysis rows;
- fewer participant/groups than the requested number of folds; or
- fewer than two event classes.

Such conditions remain in the settings ledger but do not receive fabricated model metrics.
Unexpected model-fitting errors are not swallowed by this mechanism; they still fail the analysis.

## Deterministic provenance

The result includes a SHA-256 fingerprint generated from the normalized design, complete settings
ledger, and model-metrics table. Duplicate input sampling rates and purity values are normalized to a
deterministic grid order before evaluation.

## Interpretation

The preferred interpretation is a **trade-off surface**, not a search for the single setting with the
highest score. Report at least:

- ambiguity fraction versus target sampling rate;
- retained fraction versus label-purity threshold;
- sample-level macro-F1 or balanced accuracy;
- event-level F1 and temporal IoU;
- onset/offset/duration error; and
- calibration for probabilistic models.

If performance changes at 60 Hz, the ambiguity ledger helps distinguish degradation associated with
temporal downsampling from degradation associated with uncertain boundary transfer.

A 500→60 Hz Lund result remains a **derived 60 Hz human reference**. This sensitivity analysis does
not make it equivalent to native 60 Hz human-labelled GP3 data.
