# Gaze-in-the-Wild source audit

GazeForge treats **source identity, reuse permission, participant/task mapping, coordinate semantics,
and file cadence as separate scientific gates** from MATLAB parsing. The existing adapter can read
`LabelData` and paired `ProcessData` files, but successful parsing does not establish that a local
copy is the authoritative distribution, that participant identities are correct, that `ETG.POR`
coordinates are comparable across datasets, or that current reuse terms permit the intended
analysis.

The source-audit layer therefore verifies those claims before any Gaze-in-the-Wild result is treated
as frozen empirical evidence.

## What the audit binds

`GazeInWildSourceAuditSpec` separates the distributed corpus into two exact manifests.

Each **label file** records:

- a safe relative MATLAB path;
- SHA-256 digest and byte size;
- participant identity;
- trial/task identity;
- human labeller ID; and
- the exact paired `ProcessData` path.

Each **process file** records its safe relative MATLAB path, SHA-256 digest, and byte size. The audit
also records a pinned source revision or snapshot identifier, reviewed reuse terms, explicit
analysis-use permission, raw-data redistribution status, the participant/task mapping basis, the
`ETG.POR` coordinate-unit verification basis, and the confidence threshold applied by the adapter.

Analysis-use permission and raw-data redistribution permission are deliberately separate fields.
Passing the audit never implies that GazeForge may redistribute the external raw corpus.

## Sampling-rate provenance

The primary Gaze-in-the-Wild publication describes 120 Hz acquisition hardware. GazeForge keeps
that fact as **hardware provenance** rather than forcing every distributed file to 120 Hz.

During an empirical audit, every label stream is loaded independently and its observed analysis
cadence is inferred from `LabelData.T`. The resulting report records:

- the published hardware sampling rate;
- one observed inferred rate for every label file; and
- the minimum, median, and maximum observed rates across the audited snapshot.

This prevents a secondary processed-data description or an assumed nominal rate from silently
replacing the timestamps actually present in the reviewed files.

## Multi-labeller gaze identity

When two or more audited label files describe the same participant/trial, every stream must point to
the same audited `ProcessData` file. The audit then verifies equality of participant/trial identity,
timestamps, point-of-regard samples, validity, and confidence before those streams are eligible for
human-human annotation analysis.

Labels themselves are not required to agree. Their disagreement is the empirical quantity that a
later labeller-agreement analysis should measure.

## Non-executable template

The repository contains:

```text
validation/protocols/gaze-in-wild-source-audit-template.json
```

The template intentionally uses `dataset_status: "template"`, empty manifests, unresolved coordinate
semantics, and unverified reuse/identity fields. `audit_gaze_in_wild_source()` refuses to turn that
file into empirical evidence.

A completed label entry has this shape:

```json
{
  "path": "participant/task_Lbr_2.mat",
  "sha256": "<64 hex characters>",
  "bytes": 123456,
  "participant_id": "P01",
  "trial_id": "task-01",
  "labeller_id": 2,
  "process_path": "participant/task.mat"
}
```

A completed process entry has this shape:

```json
{
  "path": "participant/task.mat",
  "sha256": "<64 hex characters>",
  "bytes": 654321
}
```

Absolute paths, parent traversal, duplicate paths, unresolved participant/trial identifiers,
duplicate participant/trial/labeller identities, missing process-manifest links, and inconsistent
process links across labellers for one trial are rejected.

## Python workflow

```python
from gazeforge import (
    audit_gaze_in_wild_source,
    audited_gaze_in_wild_files_by_labeller,
    load_gaze_in_wild_source_audit_spec,
)

spec = load_gaze_in_wild_source_audit_spec("gaze-in-wild-source-audit.json")
audit = audit_gaze_in_wild_source(
    "/path/to/LabelData",
    "/path/to/ProcessData",
    spec,
)

by_labeller = audited_gaze_in_wild_files_by_labeller(audit)
```

The audit returns one stamped `GazeFrame` per verified label/process pair rather than pretending that
all source files necessarily share one cadence. Each frame carries the source-audit report and
specification fingerprints plus the label/process manifest fingerprints, source revision, reuse
status, coordinate evidence, and participant-mapping basis.

## What this closes — and what it does not

This tranche closes the **software contract** needed to audit an authoritative Gaze-in-the-Wild
snapshot. It does not claim that such a snapshot has already been independently reviewed, and it
adds no model-performance or labeller-agreement result.

The remaining empirical sequence is:

1. obtain and review the authoritative current distribution and reuse terms;
2. populate the exact label/process manifests and participant/task mapping;
3. verify `ETG.POR` coordinate semantics and whether pixel-based kinematics are scientifically
   comparable;
4. run and freeze the source audit and per-file sampling-rate ledger;
5. quantify labeller-to-labeller sample-level and event-level agreement on verified overlapping
   streams; and
6. run participant-disjoint model validation with task/event-class sensitivity.

Even after those steps, Gaze-in-the-Wild remains complementary naturalistic head-mounted evidence.
It is **not Gazepoint GP3-specific validation** and should not be presented as a substitute for a
native GP3-class manually labelled 60 Hz corpus.
