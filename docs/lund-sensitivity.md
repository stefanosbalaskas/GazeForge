# Lund2013 sampling and boundary sensitivity

The primary derived 60 Hz Lund benchmark is only one point in a larger methodological question: **how much do lower temporal resolution and event-boundary uncertainty change model performance?**

GazeForge therefore provides a dedicated Lund2013 sensitivity runner around the generic sampling/purity framework.

## One-command workflow

```bash
gazeforge lund2013-sensitivity /path/to/lund \
  --annotator RA \
  --target-rates 120,90,60,30 \
  --purities 0.60,0.75,0.90 \
  --ivt-threshold-deg-s 45 \
  --n-splits 5 \
  --output validation/lund2013-ra-sensitivity.json
```

The runner:

1. loads one expert annotation stream from Lund2013;
2. infers the native source sampling rate from the benchmark adapter;
3. independently resamples each target-rate/purity combination;
4. records ambiguous boundary prevalence before exclusions;
5. applies the same primary-analysis exclusion policy as the Lund benchmark;
6. compares angular I-VT, Random Forest, and ContextMLP on matched participant-held-out folds;
7. includes sample-level, calibration, and event-level metrics;
8. writes a deterministic benchmark report with a SHA-256 fingerprint.

## Why vary label purity?

A lower-rate sample window may span a manually labelled event boundary. Assigning the majority label without reporting its composition would turn annotation uncertainty into hidden ground truth.

GazeForge records the proportion of source labels supporting each transferred label. Windows below the selected minimum purity become `ambiguous` rather than being forced into an event class.

A stricter purity threshold can therefore improve label certainty while reducing retained data. The sensitivity report keeps both effects visible.

## Why keep angular I-VT fixed?

The Lund baseline uses a geometry-normalized angular velocity threshold rather than pixels/second. The default sensitivity runner keeps the baseline at **45°/s** across target rates so the detector definition does not change while sampling resolution changes.

This is a sensitivity analysis, not threshold re-optimization at every rate.

## Report structure

The frozen JSON contains:

- benchmark evidence card;
- source rate and target-rate grid;
- purity grid;
- participant/trial counts;
- exclusion policy;
- complete settings ledger;
- ambiguity and retained-row fractions;
- model metrics for evaluable cells;
- sensitivity-surface fingerprint;
- final benchmark-report fingerprint.

Conditions that no longer contain enough participants or labels for the requested validation design remain in the settings ledger with `comparison_status = not_evaluable` and an explicit reason.

## Interpretation

The surface should be interpreted as a **measurement/annotation robustness analysis**, not as a search for the rate/purity combination with the largest score.

A defensible report should discuss at least:

- how ambiguity changes with target rate;
- how much data remain after exclusions;
- whether sample-level and event-level metrics deteriorate similarly;
- whether learned models and I-VT respond differently to lower temporal resolution;
- whether conclusions persist across human annotators;
- whether a setting with better performance simply discarded more difficult boundary samples.

## Evidence classification

Every target-rate condition is derived from the native 500 Hz human annotations. The dataset card is therefore classified as **derived-human-reference** for the sensitivity surface.

A 60 Hz point in this report is not equivalent to a native 60 Hz expert-labelled recording.

See [Validation status](validation-status.md) and [Sampling sensitivity](sampling-sensitivity.md).
