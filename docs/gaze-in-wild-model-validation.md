# Gaze-in-the-Wild model validation

GazeForge provides a participant-disjoint event-model validation path for **source-audited** Gaze-in-the-Wild data. The workflow is intentionally downstream of the authoritative-source audit and does not accept an unaudited MATLAB directory as model-validation evidence.

## Scientific gate

`prepare_gaze_in_wild_benchmark()` requires a verified `GazeInWildSourceAuditRun` and revalidates the audit and specification fingerprints before preparing any modelling rows. Pixel-space kinematic models are enabled only when the source audit establishes all three of the following:

- the point-of-regard coordinate unit is verified;
- that unit is explicitly `pixels`;
- `pixel_kinematics_compatible=true` is recorded in the audited source specification.

A verified non-pixel coordinate system can still be scientifically valid for other analyses, but it is not silently treated as pixels for I-VT, Random Forest, or ContextMLP kinematics.

## Heterogeneous file cadence

The published 120 Hz hardware rate remains provenance only. Preparation uses each selected label file's **timestamp-inferred cadence** from `LabelData.T`.

When a common lower analysis rate is requested, each file is downsampled independently from its own audited rate. GazeForge refuses any requested rate that would require upsampling even one selected file. This matters when a distributed benchmark snapshot contains files whose effective processed cadence is not identical.

Label transfer uses the existing majority-window purity rule. Ambiguous target windows are recorded before exclusion. Coordinates are interpolated only between the immediate finite source samples surrounding a target timestamp, with a gap bound expressed relative to that file's source period. Missing/invalid gaze is therefore not bridged across an intervening invalid source sample.

## Human reference stream

A labeller must be selected explicitly. The selected human stream is treated as a **human reference**, not as error-free ground truth. Human-human agreement remains a separate evidence layer and should accompany model-human performance when the authoritative corpus is eventually frozen.

The prepared benchmark records:

- source-audit, source-specification, label-manifest, and process-manifest fingerprints;
- selected labeller identity;
- per-file native cadence and declared common analysis cadence;
- per-file resampling ledgers;
- ambiguous and excluded sample counts;
- retained event-class counts;
- participant/trial counts and the protected split unit;
- explicit claim limits.

## Participant-held-out comparison

`run_gaze_in_wild_model_validation()` compares the same three model families used elsewhere in GazeForge on matched participant-held-out folds:

1. transparent pixel-space I-VT with an explicit velocity threshold;
2. Random Forest;
3. temporal-context MLP.

The two learned models are refitted inside every training fold. Participant identity is the protected grouping variable, and each test participant appears in only one fold per model.

The report contains sample-level discrimination metrics, calibration for probabilistic models, event-level temporal metrics, descriptive matched-fold model differences, and event-class sensitivity computed from the fixed out-of-fold predictions. Cross-validation folds are not treated as independent replicates for naive inferential p-values.

## Optional task sensitivity

Task labels are never guessed from filenames. If task sensitivity is required, provide an explicit `pandas.DataFrame` with one row for every selected participant/trial and columns:

```text
participant_id, trial_id, task_label
```

The mapping must exactly cover the selected audited trials. GazeForge fingerprints the sorted mapping and records that the task labels were not filename-inferred. Task-specific summaries are post-hoc summaries of fixed out-of-fold predictions; models are not refitted by task.

## Example

```python
import pandas as pd

from gazeforge.gaze_in_wild_audit import audit_gaze_in_wild_source
from gazeforge.gaze_in_wild_validation import run_gaze_in_wild_model_validation

# `spec` must be an empirical GazeInWildSourceAuditSpec built from a real,
# independently reviewed authoritative copy.
audit = audit_gaze_in_wild_source(
    "external/GazeInTheWild/LabelData",
    "external/GazeInTheWild/ProcessData",
    spec,
)

tasks = pd.DataFrame(
    {
        "participant_id": ["P01", "P02"],
        "trial_id": ["T01", "T02"],
        "task_label": ["walking", "search"],
    }
)

run = run_gaze_in_wild_model_validation(
    audit,
    labeller_id=1,
    target_sampling_rate_hz=60.0,
    task_mapping=tasks,
)
```

## Evidence status

This module is **validation infrastructure**, not a frozen empirical result. Until a real authoritative Gaze-in-the-Wild copy, current reuse terms, participant/task mapping, coordinate convention, and source manifests have been independently audited and the resulting report has passed scientific review, GazeForge makes no empirical Gaze-in-the-Wild model-performance claim from this code alone.

Gaze-in-the-Wild evidence also remains distinct from Gazepoint GP3-specific validation.