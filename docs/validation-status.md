# Validation status

GazeForge distinguishes **implemented software**, **validated methodology**, and **frozen empirical evidence**. A capability appearing in the API does not by itself mean that its scientific performance has been established for every tracker, task, sampling rate, or population.

## Evidence states

| State | Meaning |
| --- | --- |
| **Implemented** | code, tests, documentation, and reproducible interfaces exist |
| **Infrastructure validated** | leakage guards, metrics, provenance, and benchmark execution paths are tested |
| **Empirical execution pending** | the external benchmark is supported but a pinned/audited dataset run has not yet been frozen in the repository |
| **Frozen empirical evidence** | a versioned report with deterministic fingerprint has been produced from an audited dataset copy and passed the repository evidence gate |

## Current benchmark matrix

| Benchmark | Annotation source | Native sampling | Current GazeForge evidence | Remaining evidence work |
| --- | --- | ---: | --- | --- |
| **Lund2013** | paired expert manual labels | 500 Hz | **Frozen external evidence available**: native and derived-60-Hz MN/RA agreement; derived-60-Hz participant-held-out I-VT/RF/ContextMLP comparison; MN annotator sensitivity; stimulus-family summaries; 120/90/60/30-Hz × .60/.75/.90 purity sensitivity | native 60-Hz/GP3-class expert-labelled events still required for device-specific validity |
| **Hollywood2EM** | novice labels corrected by expert | 500 Hz | ARFF adapter; explicit annotator streams; common-label harmonisation; leave-one-dataset-out infrastructure | audit authoritative participant mapping, coordinate units, and current reuse terms before frozen cross-dataset modelling |
| **Gaze-in-the-Wild** | five trained annotators | published 120 Hz hardware acquisition | MATLAB adapter; confidence-based track loss; single-labeller safeguard; timestamp-inferred analysis cadence; human-reference dataset card | audit authoritative copy, participant/task mapping, POR coordinate units, per-file sampling-rate distribution, and labeller agreement |
| **VISUS** | two independent dynamic-AOI annotators | 60 Hz | dynamic track representation; time-grid matching; IoU/semantic metrics; fixation-assignment kappa; candidate protocol | verify authoritative current distribution/reuse terms; freeze human-human and model-human dynamic-AOI reports |

## Frozen Lund2013 checkpoint

The first empirical tranche was produced from the pinned public source repository `richardandersson/EyeMovementDetectorEvaluation` at commit `3e12416ab3fd6254c81811cf03f8e5d67c5d7129`. All 68 expected source files were verified by Git blob identity and byte size before analysis. Raw MATLAB benchmark files remain external to GazeForge.

The complete five-report suite was generated at GazeForge commit `84fba6601843d00116c878b0f2efaef834bf9e47`, revalidated, reviewed through PR #20, and merged as frozen JSON evidence. Suite fingerprint:

```text
5dc6d6336b505b0a2283fe64d478a27b0394c9568a86fc4eb4d2771b8d600f93
```

### Primary derived-60-Hz RA model comparison

Participant-held-out five-fold summaries:

| Model | Accuracy | Balanced accuracy | Macro-F1 | Event-F1 | Event matched IoU |
| --- | ---: | ---: | ---: | ---: | ---: |
| **I-VT** | 0.637 | 0.388 | 0.287 | **0.626** | **0.921** |
| **RandomForest** | 0.676 | 0.670 | 0.595 | 0.440 | 0.892 |
| **ContextMLP** | **0.694** | **0.679** | **0.649** | 0.535 | 0.900 |

These metrics support a **complementary** interpretation. ContextMLP is strongest for sample-level multiclass classification, while I-VT is stronger for contiguous event segmentation, event IoU, and boundary timing. The result does not support a blanket claim that learned models replace transparent event detectors.

The paired-fold differences are descriptive. Cross-validation folds are not treated as independent replicates and the frozen report does not attach naive inferential p-values to those fold comparisons.

### Annotator sensitivity

Using MN rather than RA as the human reference reproduces the broad result:

| Model | Accuracy | Balanced accuracy | Macro-F1 | Event-F1 |
| --- | ---: | ---: | ---: | ---: |
| **I-VT** | 0.682 | 0.396 | 0.301 | **0.624** |
| **RandomForest** | 0.699 | 0.641 | 0.574 | 0.471 |
| **ContextMLP** | **0.732** | **0.688** | **0.629** | 0.582 |

RandomForest is better calibrated by expected calibration error in both RA and MN primary comparisons, so calibration quality is reported separately from discrimination and event segmentation.

### Human-human agreement

| Condition | Exact agreement | Cohen's κ |
| --- | ---: | ---: |
| Native 500 Hz | 0.893 | 0.815 |
| Derived 60 Hz | 0.880 | 0.799 |

Agreement therefore decreases only modestly after the declared 500→60-Hz derivation. Video has the lowest agreement among the image, moving-dot, and video stimulus families, reinforcing the need to report stimulus context rather than only pooled performance.

Human-human agreement is a reference for annotation variability, not an error-free performance ceiling.

### Sampling-rate and boundary-purity sensitivity

The frozen sensitivity surface evaluates 120, 90, 60, and 30 Hz at minimum label-purity thresholds .60, .75, and .90. Every cell records ambiguity and retained-data fractions alongside model performance.

At the planned **60 Hz / .75 purity** condition, 94.4% of target samples are retained. At **30 Hz / .75 purity**, retention falls to 87.8% as boundary ambiguity increases. The model trade-off remains visible at 30 Hz/.75: ContextMLP has the strongest sample-level macro-F1 (0.608), while I-VT has the strongest event-F1 (0.659).

This prevents apparent score changes from being interpreted without accounting for how much boundary data were retained.

[Inspect the generated frozen-evidence tables →](frozen-evidence.md)

## Automated empirical execution

The dedicated GitHub Actions workflow uses the existing GazeForge CLI to:

1. fetch and verify the pinned Lund2013 corpus;
2. execute the complete five-report suite;
3. revalidate every report fingerprint;
4. reject non-JSON/raw benchmark output from the evidence tree;
5. publish only the evidence branch for ordinary scientific review.

The first complete run passed this gate and was merged through PR #20. Future reruns use the same review boundary rather than silently changing the evidence on `main`.

See [Empirical benchmark execution](empirical-execution.md).

## Event-model validation stack

### Sample level

GazeForge reports accuracy, balanced accuracy, and macro-F1. Probabilistic models additionally support multiclass Brier score and expected calibration error.

### Event level

Sample accuracy can remain high while event boundaries, counts, and durations are poor. GazeForge therefore converts contiguous labels into half-open temporal intervals and reports event precision/recall/F1, temporal IoU, onset error, offset error, duration error, and per-class event metrics.

Ambiguous, undefined, or excluded samples act as separators rather than being removed first and accidentally joining events across a boundary.

### Split level

Implemented designs include participant/group-held-out cross-validation, dataset-held-out validation, matched-fold I-VT/RF/ContextMLP comparison, descriptive paired fold differences, post-hoc stimulus-family performance from fixed out-of-fold predictions, and dataset-namespaced identities for cross-dataset evaluation.

Learned models are refitted inside every training fold.

## Native versus derived evidence

A 500 Hz expert-labelled corpus resampled to 60 Hz is **derived human-reference evidence**. It is useful for understanding lower temporal resolution but is not equivalent to expert annotation collected on a native 60 Hz system.

Accordingly:

- Lund2013-derived 60 Hz evidence cannot establish GP3-specific validity;
- Gaze-in-the-Wild can contribute native lower-rate human-reference evidence but differs in hardware and naturalistic head-mounted task domain;
- VISUS can contribute native 60 Hz human dynamic-AOI evidence, not manually labelled fixation/saccade ground truth;
- a native 60 Hz/GP3-class manually event-labelled corpus remains open.

## What GazeForge will not claim yet

GazeForge does not currently claim:

- universal superiority of learned event models over established detectors;
- GP3-specific event-classification validity;
- generalizable dynamic semantic-AOI performance;
- equivalence between algorithmic/vendor event labels and human annotation;
- mature stable-release scientific performance.

The current external Lund result instead demonstrates that performance depends on the estimand: sample-level class discrimination and event-boundary fidelity favour different methods.

## Roadmap evidence gates

The primary empirical work remains tracked in [GitHub Issue #1](https://github.com/stefanosbalaskas/GazeForge/issues/1). The Lund tranche is frozen; the highest-priority remaining event-model gate is independent **native 60 Hz/GP3-class human event validation**. Dynamic AOI validation remains tracked separately in the project roadmap.
