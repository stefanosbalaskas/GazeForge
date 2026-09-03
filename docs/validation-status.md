# Validation status

GazeForge distinguishes **implemented software**, **validated methodology**, and **frozen empirical evidence**. A capability appearing in the API does not by itself mean that its scientific performance has been established for every tracker, task, sampling rate, or population.

## Evidence states

| State | Meaning |
| --- | --- |
| **Implemented** | code, tests, documentation, and reproducible interfaces exist |
| **Infrastructure validated** | leakage guards, metrics, provenance, and benchmark execution paths are tested |
| **Empirical execution pending** | the benchmark path is supported but a real audited dataset run has not yet been frozen in the repository |
| **Frozen empirical evidence** | a versioned report with deterministic fingerprint has been produced from an audited dataset copy and passed the repository evidence gate |

## Current benchmark matrix

| Benchmark | Annotation source | Native sampling | Current GazeForge evidence | Remaining evidence work |
| --- | --- | ---: | --- | --- |
| **Lund2013** | paired expert manual labels | 500 Hz | **Frozen external evidence available**: native and derived-60-Hz MN/RA agreement; derived-60-Hz participant-held-out I-VT/RF/ContextMLP comparison; MN annotator sensitivity; stimulus-family summaries; 120/90/60/30-Hz × .60/.75/.90 purity sensitivity | native 60-Hz/GP3-class expert-labelled events still required for device-specific validity |
| **Native 60 Hz / GP3-class event corpus** | intended expert manual labels | 60 Hz | **Infrastructure validated, empirical execution pending**: strict native-rate intake, source/spec fingerprints, complete multi-annotator sample/gaze-identity verification, all-label and analysis-label human agreement, bidirectional event-boundary agreement, participant-held-out I-VT/RF/ContextMLP comparison, event metrics, three-report suite orchestration/verification, and non-executable protocol template | collect or independently obtain a real authoritative native corpus; document expert annotation protocol; freeze and review the complete native suite |
| **Hollywood2EM** | novice labels corrected by expert | 500 Hz | ARFF adapter; explicit student/expert streams; exact-source audit contract; common-label harmonisation; leave-one-dataset-out infrastructure with source-audit requirement | obtain and audit an authoritative local copy; verify real identity/coordinate/reuse evidence; freeze annotator sensitivity and cross-dataset reports |
| **Gaze-in-the-Wild** | five trained annotators | published 120 Hz hardware acquisition | MATLAB adapter; exact-source audit contract; per-file timestamp-rate ledger; audited labeller-agreement runner; participant-held-out I-VT/RF/ContextMLP validation runner with event/task sensitivity and no-upsampling guardrail | obtain and audit the authoritative copy; verify real participant/task/POR evidence; freeze sampling-rate, labeller-agreement, and model-validation reports |
| **VISUS** | one published curated AOI annotation process involving two human contributors | 60 Hz | dynamic track representation; time-grid matching; IoU/semantic metrics; fixation-assignment kappa; source-audit contract; corrected candidate protocol that does not assume two independent annotation streams | obtain and audit an authoritative current copy/reuse terms; determine whether separately recoverable independent annotation streams exist; freeze model-human evidence, and human-human evidence only if independence is verified |

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

## Native 60 Hz / GP3-class intake status

GazeForge now provides the native event specification/intake, individual model-human benchmark, paired human-human agreement, and three-report validation-suite APIs. CLI commands cover `native-event-benchmark`, `native-event-agreement`, `native-event-suite`, and `native-event-suite-validate`. These components prepare the software for a real native expert-labelled 60 Hz corpus; they are not themselves empirical GP3 evidence.

The intake requires an explicit JSON specification and verifies:

- the declared native rate against timestamps globally and inside every participant/trial;
- one-to-one participant/trial/timestamp sample keys;
- explicit human annotation provenance;
- an explicit annotation stream when multiple annotators are present;
- at least two retained event classes and at least two participants;
- no resampling step before a report is allowed to claim `sampling_origin="native"`;
- explicit screen/viewing geometry when angular I-VT is requested.

For paired human annotation streams, the agreement runner additionally requires complete one-to-one sample alignment and identical underlying gaze coordinates. It reports all-label and analysis-retained sample agreement plus event-level temporal agreement in both annotator directions. Analysis-excluded labels remain temporal separators during event segmentation.

The native suite computes human-human agreement, primary-annotator model validation, and second-annotator sensitivity before freezing any report. It cross-checks source/specification identities across all three children and writes the completion manifest last. A child report without a valid completion manifest is therefore not treated as a complete native validation tranche.

The repository template `validation/protocols/native-60hz-expert-event-template.json` has `dataset_status="template"`. GazeForge refuses to turn that template into an empirical report until a researcher replaces its placeholders with real corpus provenance and deliberately changes the status to `empirical`.

The resulting reports and suite manifest record source-file and specification fingerprints, observed sampling-rate provenance, agreement/model metrics, child report fingerprints, and deterministic report/suite fingerprints.

See [Native 60 Hz expert-event validation](native-60hz-validation.md) and [Native event validation suite](native-event-suite.md).

## VISUS annotation provenance gate

The original VISUS benchmark paper reports a manual dynamic-AOI annotation process involving two human contributors. It describes the first contributor as performing the main annotation and the second contributor as adding annotations and refining existing annotations. That is not the same design as two independently labelled copies of every stimulus.

GazeForge therefore no longer treats the contributor count as evidence of independently comparable reference streams. The VISUS source-audit contract records `annotation_process_contributor_count` separately from `independent_annotation_streams_verified`. Human-human AOI agreement is eligible only if a real authoritative copy exposes separately recoverable streams and their independence is explicitly verified.

This correction does not weaken VISUS as a model-human dynamic-AOI benchmark. It prevents a stronger human-human reliability claim from being made from provenance that does not establish independent labelling.

See [VISUS source audit](visus-source-audit.md).

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
- the native-event intake, agreement runner, and validation suite can verify and freeze a future GP3-class corpus but do not manufacture that corpus;
- Gaze-in-the-Wild can contribute native lower-rate human-reference evidence but differs in hardware and naturalistic head-mounted task domain;
- VISUS can contribute native 60 Hz human dynamic-AOI evidence, not manually labelled fixation/saccade ground truth, and its published two-contributor annotation process is not assumed to provide two independent human-reference streams;
- a native 60 Hz/GP3-class manually event-labelled empirical corpus remains open.

## What GazeForge will not claim yet

GazeForge does not currently claim:

- universal superiority of learned event models over established detectors;
- GP3-specific event-classification validity;
- generalizable dynamic semantic-AOI performance;
- VISUS human-human reliability unless independent annotation streams are verified from the source;
- equivalence between algorithmic/vendor event labels and human annotation;
- mature stable-release scientific performance.

The current external Lund result instead demonstrates that performance depends on the estimand: sample-level class discrimination and event-boundary fidelity favour different methods.

## Roadmap evidence gates

The primary empirical work remains tracked in [GitHub Issue #1](https://github.com/stefanosbalaskas/GazeForge/issues/1). The Lund tranche is frozen and the native-rate intake, human-agreement workflow, and suite-completion infrastructure are implemented; the highest-priority remaining event-model gate is independent **native 60 Hz/GP3-class human event evidence**. Dynamic AOI validation remains tracked separately in the project roadmap.
