# Validation status

GazeForge distinguishes **implemented software**, **validated methodology**, and **frozen empirical evidence**. A capability appearing in the API does not by itself mean that its scientific performance has been established for every tracker, task, sampling rate, or population.

## Evidence states

| State | Meaning |
| --- | --- |
| **Implemented** | code, tests, documentation, and reproducible interfaces exist |
| **Infrastructure validated** | leakage guards, metrics, provenance, and benchmark execution paths are tested |
| **Empirical execution pending** | the external benchmark is supported but a pinned/audited dataset run has not yet been frozen in the repository |
| **Frozen empirical evidence** | a versioned report with deterministic fingerprint has been produced from an audited dataset copy |

## Current benchmark matrix

| Benchmark | Annotation source | Native sampling | GazeForge support | Remaining evidence work |
| --- | --- | ---: | --- | --- |
| **Lund2013** | paired expert manual labels | 500 Hz | MATLAB adapter; RA/MN agreement; angular I-VT; RF/ContextMLP matched folds; 500→lower-rate purity-aware resampling; event-level metrics; paired model deltas; stimulus-family reporting; sampling/purity sensitivity; pinned automated execution/review workflow | execute the pinned workflow, inspect the generated evidence branch, and merge only scientifically accepted frozen reports |
| **Hollywood2EM** | novice labels corrected by expert | 500 Hz | ARFF adapter; explicit annotator streams; common-label harmonisation; leave-one-dataset-out infrastructure | audit authoritative participant mapping, coordinate units, and current reuse terms before frozen cross-dataset modelling |
| **Gaze-in-the-Wild** | five trained annotators | published 120 Hz hardware acquisition | MATLAB adapter; confidence-based track loss; single-labeller safeguard; timestamp-inferred analysis cadence; human-reference dataset card | audit authoritative copy, participant/task mapping, POR coordinate units, per-file sampling-rate distribution, and labeller agreement |
| **VISUS** | two independent dynamic-AOI annotators | 60 Hz | dynamic track representation; time-grid matching; IoU/semantic metrics; fixation-assignment kappa; candidate protocol | verify authoritative current distribution/reuse terms; freeze human-human and model-human dynamic-AOI reports |

## Automated Lund empirical execution

The repository contains a dedicated GitHub Actions evidence workflow that uses the existing GazeForge CLI to fetch and verify the pinned Lund2013 corpus, execute the complete five-report suite, revalidate every report fingerprint, and push only JSON evidence to `evidence/lund2013-auto`.

Raw MATLAB benchmark files remain in the runner's temporary directory and are explicitly blocked from the evidence tree. The generated branch is reviewed through an ordinary pull request before any empirical result becomes part of `main` or the public website.

See [Empirical benchmark execution](empirical-execution.md) for the execution and review contract.

## Event-model validation stack

### Sample level

GazeForge reports conventional classification measures such as accuracy, balanced accuracy, and macro-F1. Probabilistic models additionally support multiclass Brier score and expected calibration error.

### Event level

Sample accuracy can remain high while event boundaries, counts, and durations are poor. GazeForge therefore converts contiguous labels into half-open temporal intervals and reports:

- event precision, recall, and F1;
- temporal intersection-over-union;
- onset error;
- offset error;
- duration error;
- per-class event metrics.

Ambiguous, undefined, or excluded samples act as separators rather than being removed first and accidentally joining events across a boundary.

### Split level

Implemented split designs include:

- participant/group-held-out cross-validation;
- dataset-held-out validation;
- matched-fold comparison of I-VT, Random Forest, and ContextMLP;
- descriptive paired model differences on identical held-out folds;
- post-hoc stimulus-family performance from fixed out-of-fold predictions;
- dataset-namespaced identities for cross-dataset evaluation.

Learned models are refitted inside every training fold. Cross-validation folds are not treated as independent replicates for naive significance testing.

## Sampling-rate evidence

Sampling rate is treated as part of model compatibility and benchmark provenance.

The Lund sensitivity framework evaluates a configurable grid of target sampling rates and boundary-label purity thresholds. Every condition remains in a complete settings ledger, including settings that become non-evaluable after ambiguity or exclusion filtering.

Typical planned grid:

```text
sampling rate: 120, 90, 60, 30 Hz
label purity:  0.60, 0.75, 0.90
```

Each cell records ambiguity prevalence and retained sample fraction alongside model performance. This prevents a seemingly better model score from hiding the fact that a stricter setting discarded substantially more boundary data.

See [Sampling sensitivity](sampling-sensitivity.md).

## Native versus derived evidence

A 500 Hz expert-labelled corpus resampled to 60 Hz is **derived human-reference evidence**. It is useful for understanding the consequences of lower temporal resolution, but it is not equivalent to collecting expert labels on a native 60 Hz system.

Accordingly:

- Lund2013-derived 60 Hz evidence cannot establish GP3-specific validity;
- Gaze-in-the-Wild adds native lower-rate human reference evidence but differs in hardware and naturalistic head-mounted task domain;
- VISUS contributes native 60 Hz human AOI evidence, not manually labelled fixation/saccade ground truth;
- a native 60 Hz/GP3-class manually event-labelled corpus remains open.

## What GazeForge will not claim yet

GazeForge does not currently claim:

- validated superiority of the learned models over established detectors across trackers;
- GP3-specific event-classification validity;
- generalizable dynamic semantic-AOI performance;
- equivalence between algorithmic/vendor event labels and human annotation;
- mature stable-release scientific performance.

Those claims require frozen empirical evidence from audited benchmark copies and, where relevant, independent native-rate/device-specific validation.

## Roadmap evidence gates

The primary empirical work is tracked in [GitHub Issue #1](https://github.com/stefanosbalaskas/GazeForge/issues/1). Dynamic AOI validation is tracked separately in the project roadmap issues.
