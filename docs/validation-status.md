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
| **Gaze-in-the-Wild** | distributed trained human labellers | published 120 Hz hardware acquisition; exact ProcessData nominal 300 Hz | **Frozen exact-distribution participant-disjoint evidence available**: all selected LabelData/ProcessData pairs reverified; exact timestamp-vector equality; preregistered labeller-5 reference; derived 60-Hz 5-fold participant-held-out I-VT/RF/ContextMLP comparison; complete sample/event class sensitivity; convergence-qualified ContextMLP; immutable source-run provenance plus 8-decimal cross-run scientific-signature certification | authoritative `TrIdx`→task mapping and task-stratified validation; cross-dataset validation; native-60-Hz/GP3 evidence; acquisition-hardware cadence verification; quarantine exit remain open |
| **VISUS** | one published curated AOI annotation process involving two human contributors | 60 Hz | **Infrastructure validated, empirical execution pending**: exact-source audit; reviewed human-reference canonical intake; audited model-prediction intake; explicit external-grid model-human validation; guarded bidirectional human-human agreement only when independent streams are verified | obtain and audit an authoritative current copy/reuse terms; extract/review canonical reference AOIs; determine whether independent streams exist; run at least one documented detector/tracker and freeze model-human evidence; freeze human-human evidence only if independence is verified |

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

## Gaze-in-the-Wild exact participant-disjoint checkpoint

The Gaze-in-the-Wild tranche is bound to the original Figshare `ProcessData` and `LabelData` distributions. The selected human reference is labeller 5 under a deterministic pre-performance rule: maximum participant coverage, then maximum recording coverage, then lowest labeller ID. Labeller 5 and labeller 6 both cover 12 participants, while labeller 5 covers 18 recordings versus 16 for labeller 6.

The convergence-qualified benchmark uses 1,590,659 exact source samples, 318,145 derived 60-Hz rows, and 157,850 retained analysis rows across 12 participants, 18 recordings, and five participant-disjoint folds. No task mapping is inferred. `ProcessData_cleaned` is excluded and raw MATLAB files are not retained.

Five-fold means are:

| Model | Balanced accuracy | Macro-F1 | Event-F1 |
| --- | ---: | ---: | ---: |
| **I-VT** | 0.2831 | 0.1165 | 0.1568 |
| **RandomForest** | 0.4973 | 0.4752 | 0.3085 |
| **ContextMLP** | **0.5286** | **0.5192** | **0.4396** |

The aggregate result is not uniform across event classes. Pursuit remains a material failure case: RandomForest pursuit sample-F1 is 0.0769 and event-F1 is 0.0086 with 6/327 reference pursuit events matched; ContextMLP pursuit sample-F1 is 0.0547 and event-F1 is 0.0030 with 1/327 matched. These failures are retained explicitly in the reviewed evidence rather than hidden behind aggregate scores.

The reviewed compact evidence fingerprint is:

```text
b2fe85ec7e5d5cd425c0cd2593742bab835686c3f560d8a6c06e9c6d67dc547a
```

The reviewed source-run discovery fingerprint is `0623353dda03ab6f5988c671cbc6dd5e82af8fb30b84a18bd9364c3aae5e4513`, its benchmark-report fingerprint is `170fab6ef5cf8bf109ad1f134b4d2b0a13f442e7d2b174f43e020441a3693c1f`, and its historical source-run scientific identity is `772d632d8671e058407d0fe9fdfcd291c0371a45682ec9dfd145861a924eaf46`.

Those whole-object hashes remain immutable provenance for the reviewed source execution. They are not required to repeat bit-for-bit across different hosted numerical backends. Cross-run certification instead requires exact source identities, split assignments, row/class counts, convergence state, protocol and scientific-boundary identities, while floating benchmark outputs are canonicalized to 8 decimal places. The frozen cross-run reproducibility signature is:

```text
f8c8d27ddbb1fe065a15df18d53c9fa84544315ef57cf2783554b236839ff286
```

This promotes only `performance_evidence_reviewed`, `participant_disjoint_model_validation_created`, and `event_class_sensitivity_created`. The broader `new_empirical_performance_claim_created` gate remains false. Task-stratified validation, authoritative file-to-task mapping, cross-dataset validation, native-60-Hz/GP3 validity, acquisition-hardware cadence verification, and quarantine exit remain closed.

See [Gaze-in-the-Wild model validation](gaze-in-wild-model-validation.md).

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

## VISUS annotation provenance and execution gates

The original VISUS benchmark paper reports a manual dynamic-AOI annotation process involving two human contributors. It describes the first contributor as performing the main annotation and the second contributor as adding annotations and refining existing annotations. That is not the same design as two independently labelled copies of every stimulus.

GazeForge therefore no longer treats the contributor count as evidence of independently comparable reference streams. The VISUS source-audit contract records `annotation_process_contributor_count` separately from `independent_annotation_streams_verified`. Human-human AOI agreement is eligible only if a real authoritative copy exposes separately recoverable streams and their independence is explicitly verified.

The implemented VISUS execution path now keeps source, human reference, model prediction, and evaluation protocol separate. A reviewed human-reference extraction is bound back to exact audited AOI XML files and converted from an explicit frame convention to canonical dynamic-AOI keyframes. Model predictions are separately bound to exact audited video identities, explicit model/version/artifact provenance, the audited coordinate basis, and the same explicit frame-time conversion. Detector emission frames never become the evaluation grid: model-human validation still requires a separately supplied, fingerprinted timestamp grid.

This architecture permits one curated human-reference stream to support model-human validation without fabricating human-human reliability evidence. If the authoritative source later verifies independent annotation streams, the guarded agreement runner can evaluate them bidirectionally without treating either human stream as error-free ground truth.

None of these VISUS components constitutes frozen empirical evidence until an authoritative copy, reviewed source/reuse provenance, canonical human extraction, documented model output, fixed evaluation grid, and resulting report are actually reviewed and frozen.

See [VISUS source audit](visus-source-audit.md), [VISUS canonical AOI intake](visus-canonical-intake.md), [VISUS model prediction intake](visus-prediction-intake.md), [VISUS model validation](visus-model-validation.md), and [VISUS human agreement](visus-human-agreement.md).

## Automated empirical execution

Dedicated GitHub Actions workflows use the existing GazeForge validation code to reproduce frozen evidence from pinned sources, reject raw benchmark retention, and expose summary-only artifacts for scientific review.

The Lund tranche was merged through PR #20. The exact Gaze-in-the-Wild workflow additionally re-downloads and re-verifies all 18 selected LabelData/ProcessData pairs, requires zero ContextMLP convergence warnings, preserves the discovery-only boundary during computation, verifies each fresh whole-object fingerprint against its own body, and fail-closes unless exact non-floating identities plus 8-decimal benchmark-section signatures reproduce. Diagnostic discovery output and the raw-byte cleanup check run even when certification fails.

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
- the reviewed Gaze-in-the-Wild result uses a derived 60-Hz analysis grid from exact processed timestamp grids and does not establish native-60-Hz or GP3 validity;
- VISUS can contribute native 60 Hz human dynamic-AOI evidence, not manually labelled fixation/saccade ground truth, and its published two-contributor annotation process is not assumed to provide two independent human-reference streams;
- a native 60 Hz/GP3-class manually event-labelled empirical corpus remains open.

## What GazeForge will not claim yet

GazeForge does not currently claim:

- universal superiority of learned event models over established detectors;
- GP3-specific event-classification validity;
- task-stratified Gaze-in-the-Wild validity without an authoritative complete task mapping;
- cross-dataset generalization from the Gaze-in-the-Wild exact result;
- uniformly strong recognition of all Gaze-in-the-Wild event classes, especially pursuit;
- generalizable dynamic semantic-AOI performance;
- VISUS human-human reliability unless independent annotation streams are verified from the source;
- equivalence between algorithmic/vendor event labels and human annotation;
- mature stable-release scientific performance.

The current external evidence instead demonstrates that performance depends on the estimand, dataset, class, and validation boundary. Aggregate sample-level or event-level performance must not erase class-specific failures or provenance limits.

## Roadmap evidence gates

The primary empirical work remains tracked in [GitHub Issue #1](https://github.com/stefanosbalaskas/GazeForge/issues/1). The Lund tranche is frozen, the exact Gaze-in-the-Wild participant-disjoint tranche now has reviewed evidence, and the native-rate intake, human-agreement workflow, and suite-completion infrastructure are implemented. The highest-priority remaining event-model gate is independent **native 60 Hz/GP3-class human event evidence**. Gaze-in-the-Wild task mapping/task-stratified validation and cross-dataset validation remain separate open gates. Dynamic AOI validation remains tracked separately in the project roadmap.
