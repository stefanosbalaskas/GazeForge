# Gaze-in-the-Wild model validation

GazeForge provides a participant-disjoint event-model validation path for **source-audited** Gaze-in-the-Wild data. The exact-distribution workflow is downstream of the authoritative-source audit and refuses to treat an unaudited MATLAB directory, an inferred task mapping, or a convenient local copy as reviewed model-validation evidence.

## Exact-distribution scientific gate

The reviewed tranche is bound to the original Figshare `ProcessData` and `LabelData` distributions. Every selected file pair is reverified against frozen identities before analysis, and every selected `LabelData.T` vector must equal its paired `ProcessData.T` vector exactly. The workflow does not use `ProcessData_cleaned`, and raw MATLAB files are deleted after preparation rather than retained in the repository or workflow artifact.

The exact processed source has a nominal `ProcessData.SR = 300 Hz`. Analysis is performed on a **derived 60-Hz grid**, not on a native 60-Hz acquisition. Normalized scene point-of-regard coordinates are converted using the verified 1920×1080 scene resolution. Invalid source samples are not silently bridged during interpolation.

These distinctions are scientific boundaries: this evidence does not establish acquisition-hardware cadence, native-60-Hz validity, or Gazepoint GP3 validity.

## Preregistered human reference

The human reference is selected before model fitting by a deterministic source-only rule:

1. maximum distinct participant coverage;
2. then maximum recording coverage;
3. then lowest labeller ID.

Label frequencies and model performance cannot influence that choice. Labeller **5** is selected because labellers 5 and 6 both cover 12 participants, while labeller 5 covers 18 recordings versus 16 for labeller 6.

Labeller 5 is treated as a **human reference stream, not error-free ground truth**. The selected exact stream contains 1,590,659 source samples across 12 participants and 18 recordings.

## Preparation and protected split

The exact benchmark contains:

- **1,590,659** exact source samples;
- **318,145** derived 60-Hz rows before analysis-label exclusions;
- **157,850** retained analysis rows;
- 12 participants and 18 recordings;
- five participant-disjoint folds;
- identical out-of-fold rows across I-VT, Random Forest, and ContextMLP.

Retained analysis support is:

| Event class | Rows |
| --- | ---: |
| Blink | 13,889 |
| Fixation | 26,341 |
| Pursuit | 5,696 |
| Saccade | 20,061 |
| VOR | 91,863 |

Participant identity is the protected split unit. Learned models are refitted inside every training fold. No `TrIdx`→task mapping is inferred from filenames or publication prose, so this reviewed result is deliberately **task-agnostic**.

## Model comparison

The reviewed comparison uses the same three model families across the same five participant-held-out folds:

1. transparent I-VT;
2. Random Forest;
3. temporal-context MLP (`ContextMLP`).

The report includes sample-level discrimination, probabilistic calibration where applicable, event-level temporal metrics, per-class sample and event sensitivity, and descriptive paired-fold differences. Cross-validation folds are not treated as independent replicates for naive inferential p-values.

### Convergence-qualified protocol

The first exact discovery used the preregistered `ContextMLP` ceiling of 200 iterations, but every fold emitted a `ConvergenceWarning`. Those metrics were not promoted to reviewed evidence.

A convergence-only amendment changed exactly one parameter: `temporal_max_iter` from **200 to 1000**. The amendment was frozen before rerunning, was not selected using performance direction, required acceptance of the resulting metrics regardless of direction, and required **zero** `ContextMLP` convergence warnings. The qualifying run satisfied that requirement with 0 warnings.

## Reviewed participant-disjoint result

The convergence-qualified five-fold means are:

| Model | Balanced accuracy | Macro-F1 | Event-F1 |
| --- | ---: | ---: | ---: |
| I-VT | 0.2831 | 0.1165 | 0.1568 |
| RandomForest | 0.4973 | 0.4752 | 0.3085 |
| ContextMLP | **0.5286** | **0.5192** | **0.4396** |

These numbers establish a narrow, dataset-specific participant-held-out comparison under the frozen exact-distribution protocol. They do **not** imply uniformly strong event recognition, cross-dataset generalization, task-specific validity, or GP3 validity.

### Pursuit remains a material failure case

The reviewed evidence intentionally preserves the weakest class rather than hiding it behind aggregate scores:

| Model | Pursuit sample-F1 | Pursuit event-F1 | Matched reference pursuit events | Predicted pursuit events |
| --- | ---: | ---: | ---: | ---: |
| I-VT | 0.0000 | 0.0000 | 0 / 327 | 0 |
| RandomForest | 0.0769 | 0.0086 | 6 / 327 | 1,071 |
| ContextMLP | 0.0547 | 0.0030 | 1 / 327 | 349 |

ContextMLP therefore has the strongest aggregate balanced accuracy, macro-F1, and event-F1 in this exact benchmark while still detecting pursuit events very poorly. Aggregate superiority must not be restated as uniformly strong event recognition.

## Cryptographic evidence binding

The reviewed compact evidence record binds the complete metric sections without copying the full discovery report into the repository. It binds all 15 fold-metric rows, all 160 paired-fold deltas, 36 paired-model summary rows, 15 sample-class rows, 16 event-class rows, the three model summaries, class counts, and the deliberately empty task-specific sections.

Key identifiers for the reviewed source run are:

- exact discovery workflow run: `34273647914`;
- job: `102221217862`;
- discovery head: `9d2c5cd9c274527615e4e30b2feb53da2e20e523`;
- artifact: `10075402142`;
- artifact ZIP SHA-256: `3406abd4eddc080b9b72687e3b164d863fe0d925782c746d4b369c48dfcbdf87`;
- discovery fingerprint: `0623353dda03ab6f5988c671cbc6dd5e82af8fb30b84a18bd9364c3aae5e4513`;
- benchmark-report fingerprint: `170fab6ef5cf8bf109ad1f134b4d2b0a13f442e7d2b174f43e020441a3693c1f`;
- stable verified-pair manifest: `1c129f4c2c18f78dbc41892eff476374f5ccdaaf6ee90d22d1a5808d6fdc2407`;
- stable scientific identity: `772d632d8671e058407d0fe9fdfcd291c0371a45682ec9dfd145861a924eaf46`;
- reviewed compact evidence fingerprint: `fa45366ea855a0bad662514c42187ffe3d24e5ce8e191a351c8c9b478325df6f`.

The dedicated GitHub Actions workflow reruns the exact v2 discovery and fail-closes unless the source-pair manifest, convergence status, split, complete metric-section fingerprints, pursuit failure case, benchmark fingerprint, and stable scientific identity all reproduce exactly.

## Optional task sensitivity infrastructure

Task labels are never guessed from filenames. The general validation API can accept an explicit mapping with one row for every selected participant/trial and columns:

```text
participant_id, trial_id, task_label
```

That infrastructure is **not used by the reviewed exact-distribution result above**. An authoritative complete `TrIdx`→publication-task mapping has not been verified, so `task_stratified_model_validation_created` remains false.

## Scientific boundary after review

The reviewed evidence promotes only the narrow gates supported by the exact run:

- `performance_evidence_reviewed = true`;
- `participant_disjoint_model_validation_created = true`;
- `event_class_sensitivity_created = true`.

The following remain false/closed:

- `new_empirical_performance_claim_created`;
- task-stratified validation;
- authoritative file-to-publication task mapping;
- cross-dataset validation;
- native-60-Hz / GP3 validity;
- acquisition-hardware cadence verification by this validation;
- quarantine exit;
- raw dataset retention.

This distinction is intentional. The repository now contains reviewed **Gaze-in-the-Wild participant-disjoint evidence under one frozen exact protocol**, while broader performance/generalization/device claims remain outside the evidence actually created by this tranche.
