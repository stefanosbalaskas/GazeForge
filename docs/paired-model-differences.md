# Matched-fold model differences

Absolute benchmark scores are useful, but they can obscure how consistently two models differ on
the **same held-out folds**. GazeForge therefore provides a descriptive paired-fold layer through
`paired_model_metric_differences()`.

```python
from gazeforge import paired_model_metric_differences

paired = paired_model_metric_differences(comparison.fold_metrics)
print(paired.summary)
```

## What is paired

The input is the fold-metric table produced by a matched validation design. Every model must have
exactly the same validation-fold identifiers. Missing an entire model/fold is a hard error rather
than an invitation to compare only the intersection of available folds.

Metric-level missingness is different. For example, deterministic I-VT has no probability
calibration score. Its Brier/ECE pairings therefore report zero paired folds, while Random Forest
and ContextMLP can still be compared on those metrics.

## Raw delta and improvement direction

For every model pair, the raw delta is always:

`model_a - model_b`

That definition never changes with the metric. GazeForge also reports `improvement_for_a`, whose
sign is oriented so that **positive always means model A performed better**.

Higher-is-better metrics include accuracy, balanced accuracy, macro-F1, event precision/recall/F1,
and matched temporal IoU. Lower-is-better metrics include Brier score, ECE, and absolute event
onset/offset/duration errors. For lower-is-better metrics, only the improvement sign is reversed;
the raw delta remains model A minus model B.

## Descriptive summary

For each model pair × metric, GazeForge records:

- number of folds with values for both models;
- mean, median, standard deviation, minimum, and maximum raw paired delta;
- mean direction-normalized improvement for model A;
- model-A wins, ties, and model-B wins under an explicit numerical tie tolerance.

Per-fold values and deltas are retained separately from the aggregate summary.

## Why there are no cross-validation p-values

The paired-fold table is intentionally descriptive. K-fold validation folds share substantial
training data, so the fold estimates are not treated as independent experimental replicates.
GazeForge therefore does **not** attach naive paired t tests, Wilcoxon tests, p-values, or confidence
intervals to the fold deltas.

The design metadata records:

- `inferential_p_values = false`;
- `confidence_intervals = false`;
- `folds_treated_as_independent_replicates = false`.

A formal inferential comparison requires a validation design and resampling/inference strategy that
supports the intended claim. This descriptive layer instead answers a narrower question: **on the
same held-out folds, how large and how directionally consistent were the observed metric
differences?**

## Lund2013 integration

`run_lund2013_event_benchmark()` embeds the paired-fold comparison in both RA- and MN-labelled model
reports. The frozen report contains:

- `metrics.paired_model_difference_summary`;
- `metrics.paired_model_fold_deltas`;
- `protocol.paired_model_difference_design`.

Because `lund2013-suite` uses the same benchmark runner for the RA primary analysis and MN annotator
sensitivity analysis, both corresponding suite child reports inherit this comparison automatically.
No empirical paired differences are shown on the public evidence site until genuine fingerprinted
benchmark reports are frozen.
