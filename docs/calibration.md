# Probability calibration and dataset holdouts

A probabilistic event classifier should be evaluated not only for label accuracy but also for
whether its confidence values mean what they claim.

## Calibration diagnostics

`evaluate_event_calibration()` reports:

- multiclass Brier score;
- top-label expected calibration error (ECE);
- a reliability table by confidence bin; and
- selective accuracy versus retained coverage.

The selective curve is especially useful for GazeForge's human-review model: researchers can set a
confidence threshold, retain high-confidence AI labels, and route uncertain samples to review.

Calibration diagnostics do **not** themselves recalibrate a model. Recalibration methods will be
added only with leakage-safe training/calibration partitions and benchmark evidence.

## Dataset-held-out validation

`dataset_holdout_event_validate()` leaves one complete dataset out at a time and fits a fresh model
on the remaining datasets. By default it also requires participant IDs to be disjoint between train
and test, preventing cross-dataset identity leakage.

This is a stronger generalisation test than ordinary sample-level cross-validation and is intended
for the later public-benchmark tranche.
