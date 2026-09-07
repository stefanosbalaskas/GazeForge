# Gaze-in-the-Wild participant/task publication metadata

This note freezes a **publication-level** participant/task identity result for the
Gaze-in-the-Wild (GIW) dataset. It does not promote an unverified local copy,
does not infer a universal trial-index lookup, and does not authorize empirical
execution.

## Authoritative publication table

The first-party GIW README at commit
`52262d44e366a53369e10ca73c5f41daf0e8f1e5` explicitly points readers to the
Scientific Reports supplementary document for the official list of
participants, recorded tasks, and label availability.

The exact official Springer supplementary PDF reviewed for this tranche has
SHA-256
`b700b1deec97be82d81cba2cf4eba605d110ec5d8175b6c5681ac372b61c7f3d`.
The author arXiv v1 PDF independently contains the same table and has SHA-256
`b4db32a89765aa96952ee2ae88e502600c1f97a607e3c58f9550ceb36e37fdd5`.

Supplementary Table 1 contains 19 published participant identifiers:

`1, 2, 3, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23`.

The four publication task columns are:

- indoor navigation;
- ball catching;
- visual search;
- tea making.

For every participant/task cell, GazeForge now freezes the publication status as
one of `multiple_labellers`, `single_labeller`, `not_labeled`, or `discarded`.
The complete immutable matrix is stored in
`validation/evidence/gaze-in-wild/gaze-in-wild-participant-task-metadata-evidence-v2.json`.
Its evidence fingerprint is
`55b279fadd969e23b535fff3aac92327a45eb89cd0f365d90c0e5c6cae351017`.

## First-party processing identity convention

The pinned processing code provides a separate, narrower identity convention:

- `ParticipantInfo(PrIdx).Name` is used when constructing the raw participant
  directory;
- `PrIdx` and `TrIdx` are passed into processing;
- processed files use `PrIdx_%d_TrIdx_%d.mat`;
- label files use `PrIdx_%d_TrIdx_%d_Lbr_%d.mat`.

This supports the first-party participant-number/processing-index convention.
It is **not** equivalent to verifying every file in a recovered authoritative
distribution.

The publication reports participant 18 as age 34, while the reviewed processing
metadata records age 45. GazeForge therefore explicitly forbids age from being
used as an identity join.

## Why `TrIdx` is not promoted to a task-name lookup

The publication task matrix and the first-party trial vectors do not support a
single universal `TrIdx -> task` mapping. Some participants have later tasks
recorded while an earlier publication task is marked discarded, and the
first-party plotting code demonstrates task-directory context separately from
the numeric trial index.

Consequently the following remain unresolved until an authoritative dataset
copy and its task-directory structure are audited:

- universal `TrIdx` to task-name mapping;
- exact `ProcessData` file to publication-task mapping;
- task-directory to task-name mapping across the authoritative distribution.

## Still outside this evidence

This tranche does not establish:

- acquisition or exact equivalence of the full authoritative GIW distribution;
- current reuse terms, analysis permission, or redistribution permission;
- the per-file sampling-rate distribution;
- frozen human-human agreement;
- participant-disjoint model validation;
- cross-dataset validation;
- native-60-Hz or GP3 validity;
- any new empirical performance claim.

The issue-level GIW participant/task/POR checklist therefore remains open until
the exact distributed task/file mapping is resolved, even though publication
participant/task metadata and POR coordinate semantics are now separately
frozen.
