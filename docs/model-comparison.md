# Matched-fold event-model comparison

`compare_event_models_grouped()` compares the deterministic I-VT baseline, the probabilistic
Random Forest event model, and the temporal-context MLP on **identical participant/group-held-out
folds**.

Every learned model is fitted from scratch inside each training partition. The test-row positions
are retained, allowing researchers to verify that all methods were scored on exactly the same
samples rather than on independently generated splits.

Per-fold reporting includes accuracy, balanced accuracy, and macro-F1. Random Forest and
ContextMLP additionally receive multiclass Brier score and expected calibration error (ECE).
Calibration fields for I-VT are intentionally missing because a deterministic velocity threshold
does not produce calibrated class probabilities.

The returned `EventModelComparison` contains:

- `predictions`: long-form row-level predictions for every model and validation fold;
- `fold_metrics`: matched fold-level discrimination and calibration metrics;
- `summary`: mean and standard deviation across folds for each model; and
- `design`: the sampling rate, grouping unit, thresholds, context window, and other validation
  settings required to reconstruct the comparison.

This function is benchmark infrastructure, not evidence that one model is superior. Scientific
claims require expert-labelled empirical data, frozen splits, appropriate uncertainty around
between-fold differences, and validation at the sampling rates for which suitability is claimed.
